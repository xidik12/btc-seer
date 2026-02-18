"""Ensemble predictor combining TFT, LSTM, XGBoost, and TimesFM models.

Architecture:
  TFT (40%) — Primary multi-horizon model with attention
  LSTM (20%) — Sequential pattern detection
  XGBoost (25%) — Feature-based classification
  TimesFM (15%) — Zero-shot foundation model baseline
  + Sentiment modifier (amplify/dampen ±50%)
  + Quant theory signal overlay
"""
import logging
from pathlib import Path

import numpy as np

from app.features.builder import FeatureBuilder
from app.models.lstm import LSTMPredictor
from app.models.xgboost_model import XGBoostPredictor
from app.models.tft_model import TFTPredictor
from app.models.timesfm_model import TimesFMPredictor
from app.models.sentiment import SentimentModel

logger = logging.getLogger(__name__)


def load_norm_params(path: str) -> dict | None:
    """Load normalization parameters (mean/std) from .npz file."""
    p = Path(path)
    if p.exists():
        data = np.load(str(p))
        return {"mean": data["mean"], "std": data["std"]}
    return None


class EnsemblePredictor:
    """Combines TFT, LSTM, XGBoost, TimesFM, and Sentiment for final predictions."""

    # Default weights (adaptive — updated by performance tracker)
    DEFAULT_WEIGHTS = {
        "tft": 0.40,
        "lstm": 0.20,
        "xgb": 0.25,
        "timesfm": 0.15,
    }

    # Weights when no models are trained (heuristic mode)
    UNTRAINED_WEIGHTS = {
        "tft": 0.15,
        "lstm": 0.05,
        "xgb": 0.50,
        "timesfm": 0.30,
    }

    def __init__(
        self,
        model_dir: str = "app/models/weights",
        num_features: int = None,
        use_finbert: bool = False,
    ):
        if num_features is None:
            num_features = len(FeatureBuilder.ALL_FEATURES)
        model_dir = Path(model_dir)

        # Load all models
        tft_path = model_dir / "tft_model.pt"
        lstm_path = model_dir / "lstm_model.pt"
        xgb_path = model_dir / "xgboost_model.json"

        self.tft = TFTPredictor(
            model_path=str(tft_path) if tft_path.exists() else None,
            num_features=num_features,
        )
        self.lstm = LSTMPredictor(
            input_size=num_features,
            model_path=str(lstm_path) if lstm_path.exists() else None,
        )
        self.xgboost = XGBoostPredictor(
            model_path=str(xgb_path) if xgb_path.exists() else None,
        )
        self.timesfm = TimesFMPredictor()
        self.sentiment_model = SentimentModel(use_finbert=use_finbert)

        # Load normalization params
        self.norm_params = (
            load_norm_params(str(model_dir / "lstm_norm_params.npz"))
            or load_norm_params(str(model_dir / "tft_norm_params.npz"))
        )

        # Detect training status
        self.tft_trained = self.tft.is_trained
        self.lstm_trained = getattr(self.lstm, 'is_trained', False)
        self.xgboost_trained = self.xgboost.model is not None
        self.timesfm_available = self.timesfm.is_available

        # Select weights based on training status
        any_trained = self.tft_trained or self.lstm_trained or self.xgboost_trained
        self.weights = dict(self.DEFAULT_WEIGHTS if any_trained else self.UNTRAINED_WEIGHTS)

        # Downweight untrained models
        if not self.tft_trained:
            self.weights["tft"] = 0.10
        if not self.lstm_trained:
            self.weights["lstm"] = 0.05
        if not self.xgboost_trained:
            # XGBoost heuristic is still useful
            pass
        if not self.timesfm_available:
            self.weights["timesfm"] = 0.05

        # Renormalize weights to sum to 1
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

        # Try to load adaptive weights from DB
        self._load_adaptive_weights()

        trained_models = [
            name for name, trained in [
                ("TFT", self.tft_trained), ("LSTM", self.lstm_trained),
                ("XGBoost", self.xgboost_trained), ("TimesFM", self.timesfm_available),
            ] if trained
        ]
        logger.info(
            f"Ensemble initialized: trained={trained_models or 'none'}, "
            f"weights={self.weights}, norm={'loaded' if self.norm_params else 'none'}"
        )

    def _normalize_sequence(self, sequence: np.ndarray) -> np.ndarray:
        """Apply z-score normalization using saved params."""
        if self.norm_params is None:
            return sequence

        mean = self.norm_params["mean"]
        std = self.norm_params["std"]

        # Handle shape mismatch (feature count may have changed)
        if sequence.shape[-1] != len(mean):
            logger.error(
                f"NORMALIZATION SKIPPED: feature count mismatch — "
                f"input has {sequence.shape[-1]} features but norm params have {len(mean)}. "
                f"Predictions will run on UNNORMALIZED inputs and may be unreliable. "
                f"Retrain models to fix: the saved lstm_norm_params.npz is stale."
            )
            return sequence

        if sequence.ndim == 2:
            return (sequence - mean) / std
        return sequence

    def predict(
        self,
        feature_sequence: np.ndarray,
        current_features: np.ndarray,
        news_data: list[dict] = None,
        reddit_data: list[dict] = None,
        price_history: list[float] = None,
    ) -> dict:
        """Generate ensemble prediction with adaptive model weighting.

        Args:
            feature_sequence: (168, num_features) sequence for LSTM/TFT
            current_features: (num_features,) current features for XGBoost
            news_data: Recent news for sentiment
            reddit_data: Reddit posts for sentiment
            price_history: List of close prices for TimesFM (ideally 512+)
        """
        # Normalize sequence for neural models
        norm_sequence = self._normalize_sequence(feature_sequence)

        # Get predictions from all models
        tft_pred = self.tft.predict(norm_sequence)
        lstm_pred = self.lstm.predict(norm_sequence)
        xgb_pred = self.xgboost.predict(current_features)
        sentiment = self.sentiment_model.get_sentiment_signal(news_data, reddit_data)

        # TimesFM uses raw price history
        timesfm_pred = {}
        if price_history and len(price_history) >= 48:
            timesfm_pred = self.timesfm.predict(price_history)

        w = self.weights
        predictions = {}

        tf_multiplier_map = {"1h": 1.0, "4h": 2.5, "24h": 5.0, "1w": 10.0, "1mo": 20.0}

        for timeframe in ["1h", "4h", "24h", "1w", "1mo"]:
            # Collect per-model bullish probabilities
            tft_tf = tft_pred.get(timeframe, tft_pred.get("1h", {}))
            lstm_tf = lstm_pred.get(timeframe, lstm_pred.get("1h", {}))
            tfm_tf = timesfm_pred.get(timeframe, {})

            tft_bullish = tft_tf.get("bullish_prob", 0.5)
            lstm_bullish = lstm_tf.get("bullish_prob", 0.5)
            xgb_bullish = xgb_pred.get("bullish_prob", 0.5)
            tfm_bullish = tfm_tf.get("bullish_prob", 0.5)
            sent_score = sentiment.get("score", 0)

            # Weighted ensemble of all 4 models
            base_prob = (
                w["tft"] * tft_bullish
                + w["lstm"] * lstm_bullish
                + w["xgb"] * xgb_bullish
                + w["timesfm"] * tfm_bullish
            )

            # Apply sentiment modifier (amplify or dampen signal)
            modifier = sentiment.get("modifier", 1.0)
            adjusted_prob = 0.5 + (base_prob - 0.5) * modifier
            adjusted_prob = max(0.05, min(0.95, adjusted_prob))

            # Confidence scoring — lower confidence for longer timeframes
            tft_conf = tft_tf.get("confidence", 0)
            lstm_conf = lstm_tf.get("confidence", 0)
            xgb_conf = xgb_pred.get("confidence", 0)
            tfm_conf = tfm_tf.get("confidence", 0)
            signal_strength = abs(adjusted_prob - 0.5) * 2  # 0-1 scale

            base_confidence = 30 + signal_strength * 70 + min(xgb_conf, 30) * 0.5

            # Model agreement bonus
            probs = [xgb_bullish, 0.5 + sent_score / 2]
            if self.tft_trained:
                probs.append(tft_bullish)
            if self.lstm_trained:
                probs.append(lstm_bullish)
            if timesfm_pred:
                probs.append(tfm_bullish)

            all_agree = all(p > 0.5 for p in probs) or all(p < 0.5 for p in probs)
            agreement_bonus = 10 if all_agree else -5

            # Extra bonus for trained model agreement
            trained_agreement = 0
            if self.tft_trained and self.lstm_trained:
                if (tft_bullish > 0.5) == (lstm_bullish > 0.5):
                    trained_agreement = 5

            confidence = base_confidence + agreement_bonus + trained_agreement
            # Reduce confidence for longer timeframes (more uncertainty)
            tf_conf_decay = {"1h": 1.0, "4h": 0.95, "24h": 0.9, "1w": 0.8, "1mo": 0.7}
            confidence *= tf_conf_decay.get(timeframe, 1.0)
            any_trained = self.tft_trained or self.lstm_trained or self.xgboost_trained
            max_conf = 95 if any_trained else 85
            confidence = float(np.clip(confidence, 25, max_conf))

            # Direction — NO neutral
            direction = "bullish" if adjusted_prob >= 0.5 else "bearish"

            # Magnitude estimation
            tf_multiplier = tf_multiplier_map.get(timeframe, 1.0)
            magnitude = (adjusted_prob - 0.5) * 2 * tf_multiplier

            # Prefer trained model magnitudes
            if self.tft_trained:
                tft_mag = tft_tf.get("magnitude_pct", 0)
                if abs(tft_mag) > 0.01:
                    magnitude = tft_mag * 0.5 + magnitude * 0.5
            elif self.lstm_trained:
                lstm_mag = lstm_tf.get("magnitude_pct", 0)
                if abs(lstm_mag) > 0.01:
                    magnitude = lstm_mag * 0.4 + magnitude * 0.6

            # TimesFM magnitude as sanity check
            if timesfm_pred and tfm_tf.get("magnitude_pct") is not None:
                tfm_mag = tfm_tf["magnitude_pct"]
                # If TimesFM strongly disagrees, dampen magnitude
                if (magnitude > 0) != (tfm_mag > 0):
                    magnitude *= 0.7

            predictions[timeframe] = {
                "direction": direction,
                "bullish_prob": float(adjusted_prob),
                "bearish_prob": float(1 - adjusted_prob),
                "confidence": float(confidence),
                "magnitude_pct": float(magnitude),
                "model_outputs": {
                    "tft": {
                        "bullish_prob": float(tft_bullish),
                        "confidence": float(tft_conf),
                        "trained": self.tft_trained,
                    },
                    "lstm": {
                        "bullish_prob": float(lstm_bullish),
                        "confidence": float(lstm_conf),
                        "trained": self.lstm_trained,
                    },
                    "xgboost": {
                        "bullish_prob": float(xgb_bullish),
                        "confidence": float(xgb_conf),
                        "trained": self.xgboost_trained,
                    },
                    "timesfm": {
                        "bullish_prob": float(tfm_bullish),
                        "confidence": float(tfm_conf),
                        "available": bool(timesfm_pred),
                    },
                    "sentiment": {
                        "score": float(sent_score),
                        "direction": sentiment.get("direction", "neutral"),
                        "modifier": float(modifier),
                    },
                },
            }

        return predictions

    def _load_adaptive_weights(self):
        """Try to load adaptive weights from the most recent DB entry."""
        try:
            import asyncio
            from app.database import async_session, ModelFeedback
            from sqlalchemy import select, desc

            async def _fetch():
                async with async_session() as session:
                    result = await session.execute(
                        select(ModelFeedback)
                        .where(ModelFeedback.period == "adaptive_weights")
                        .order_by(desc(ModelFeedback.timestamp))
                        .limit(1)
                    )
                    return result.scalar_one_or_none()

            # Try to get event loop, create new one if needed
            try:
                loop = asyncio.get_running_loop()
                # Can't await in sync __init__, will load on next cycle
                return
            except RuntimeError:
                pass

            fb = asyncio.run(_fetch())
            if fb and fb.feedback_json and fb.feedback_json.get("type") == "adaptive_weights":
                learned = fb.feedback_json["new_weights"]
                if all(k in learned for k in ("tft", "lstm", "xgb", "timesfm")):
                    self.weights = learned
                    logger.info(f"Loaded adaptive weights from DB: {learned}")
        except Exception as e:
            logger.debug(f"Could not load adaptive weights: {e}")

    def update_weights(self, weights: dict):
        """Update ensemble weights (must sum to 1.0)."""
        total = sum(weights.values())
        self.weights = {k: v / total for k, v in weights.items()}
        logger.info(f"Ensemble weights updated: {self.weights}")
