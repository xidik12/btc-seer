import logging

import numpy as np

from app.models.lstm import LSTMPredictor
from app.models.xgboost_model import XGBoostPredictor
from app.models.sentiment import SentimentModel

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    """Combines LSTM, XGBoost, and Sentiment models for final predictions."""

    # Weights when LSTM is trained
    LSTM_WEIGHT_TRAINED = 0.45
    XGBOOST_WEIGHT_TRAINED = 0.35
    SENTIMENT_WEIGHT_TRAINED = 0.20

    # Weights when LSTM is untrained (random weights = noise)
    LSTM_WEIGHT_UNTRAINED = 0.05
    XGBOOST_WEIGHT_UNTRAINED = 0.60
    SENTIMENT_WEIGHT_UNTRAINED = 0.35

    def __init__(
        self,
        lstm_model_path: str = None,
        xgboost_model_path: str = None,
        use_finbert: bool = False,
        num_features: int = 50,
    ):
        self.lstm = LSTMPredictor(input_size=num_features, model_path=lstm_model_path)
        self.xgboost = XGBoostPredictor(model_path=xgboost_model_path)
        self.sentiment_model = SentimentModel(use_finbert=use_finbert)

        # Detect if models are trained
        self.lstm_trained = getattr(self.lstm, 'is_trained', False)
        self.xgboost_trained = self.xgboost.model is not None

    def predict(
        self,
        feature_sequence: np.ndarray,
        current_features: np.ndarray,
        news_data: list[dict] = None,
        reddit_data: list[dict] = None,
    ) -> dict:
        """Generate ensemble prediction with adaptive model weighting."""
        lstm_pred = self.lstm.predict(feature_sequence)
        xgb_pred = self.xgboost.predict(current_features)
        sentiment = self.sentiment_model.get_sentiment_signal(news_data, reddit_data)

        # Select weights based on model training status
        if self.lstm_trained:
            w_lstm = self.LSTM_WEIGHT_TRAINED
            w_xgb = self.XGBOOST_WEIGHT_TRAINED
            w_sent = self.SENTIMENT_WEIGHT_TRAINED
        else:
            w_lstm = self.LSTM_WEIGHT_UNTRAINED
            w_xgb = self.XGBOOST_WEIGHT_UNTRAINED
            w_sent = self.SENTIMENT_WEIGHT_UNTRAINED

        predictions = {}

        for timeframe in ["1h", "4h", "24h"]:
            lstm_tf = lstm_pred.get(timeframe, lstm_pred.get("1h", {}))
            lstm_bullish = lstm_tf.get("bullish_prob", 0.5)

            xgb_bullish = xgb_pred.get("bullish_prob", 0.5)
            sent_score = sentiment.get("score", 0)

            # Weighted ensemble
            base_prob = (
                w_lstm * lstm_bullish
                + w_xgb * xgb_bullish
                + w_sent * (0.5 + sent_score / 2)
            )

            # Apply sentiment modifier (amplify or dampen)
            modifier = sentiment.get("modifier", 1.0)
            adjusted_prob = 0.5 + (base_prob - 0.5) * modifier
            adjusted_prob = max(0.05, min(0.95, adjusted_prob))

            # Confidence scoring: combines signal strength + model confidence + agreement
            xgb_conf = xgb_pred.get("confidence", 0)
            signal_strength = abs(adjusted_prob - 0.5) * 2  # 0-1 scale

            # Base: 30% just for having data + indicators running
            # Signal contribution: up to +35% based on how decisive the probability is
            # XGBoost confidence: up to +15% from the heuristic's own confidence
            base_confidence = 30 + signal_strength * 70 + min(xgb_conf, 30) * 0.5

            # Model agreement bonus
            probs = [xgb_bullish, 0.5 + sent_score / 2]
            if self.lstm_trained:
                probs.append(lstm_bullish)
            all_agree = all(p > 0.5 for p in probs) or all(p < 0.5 for p in probs)
            agreement_bonus = 10 if all_agree else -5

            confidence = base_confidence + agreement_bonus
            max_conf = 95 if self.lstm_trained and self.xgboost_trained else 85
            confidence = float(np.clip(confidence, 25, max_conf))

            # Direction — NO neutral. Any signal, however small, picks a side.
            direction = "bullish" if adjusted_prob >= 0.5 else "bearish"

            # Magnitude estimation based on probability distance from 0.5
            tf_multiplier = {"1h": 1.0, "4h": 2.5, "24h": 5.0}.get(timeframe, 1.0)
            magnitude = (adjusted_prob - 0.5) * 2 * tf_multiplier

            # Use LSTM magnitude if trained and available
            lstm_mag = lstm_tf.get("magnitude_pct", 0)
            if self.lstm_trained and abs(lstm_mag) > 0.01:
                magnitude = lstm_mag

            predictions[timeframe] = {
                "direction": direction,
                "bullish_prob": float(adjusted_prob),
                "bearish_prob": float(1 - adjusted_prob),
                "confidence": float(confidence),
                "magnitude_pct": float(magnitude),
                "model_outputs": {
                    "lstm": {
                        "bullish_prob": float(lstm_bullish),
                        "confidence": float(lstm_tf.get("confidence", 0)),
                    },
                    "xgboost": {
                        "bullish_prob": float(xgb_bullish),
                        "confidence": float(xgb_conf),
                    },
                    "sentiment": {
                        "score": float(sent_score),
                        "direction": sentiment.get("direction", "neutral"),
                        "modifier": float(modifier),
                    },
                },
            }

        return predictions

    def update_weights(self, lstm_w: float, xgb_w: float, sent_w: float):
        """Update ensemble weights (must sum to 1.0)."""
        total = lstm_w + xgb_w + sent_w
        self.LSTM_WEIGHT = lstm_w / total
        self.XGBOOST_WEIGHT = xgb_w / total
        self.SENTIMENT_WEIGHT = sent_w / total
        logger.info(f"Ensemble weights updated: LSTM={self.LSTM_WEIGHT:.2f}, "
                     f"XGB={self.XGBOOST_WEIGHT:.2f}, SENT={self.SENTIMENT_WEIGHT:.2f}")
