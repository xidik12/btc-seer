import logging

import numpy as np

from app.models.lstm import LSTMPredictor
from app.models.xgboost_model import XGBoostPredictor
from app.models.sentiment import SentimentModel

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    """Combines LSTM, XGBoost, and Sentiment models for final predictions."""

    # Default weights (optimized via backtesting)
    LSTM_WEIGHT = 0.45
    XGBOOST_WEIGHT = 0.35
    SENTIMENT_WEIGHT = 0.20

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

    def predict(
        self,
        feature_sequence: np.ndarray,
        current_features: np.ndarray,
        news_data: list[dict] = None,
        reddit_data: list[dict] = None,
    ) -> dict:
        """
        Generate ensemble prediction.

        Args:
            feature_sequence: (seq_len, features) array for LSTM
            current_features: (features,) array for XGBoost
            news_data: Recent news items
            reddit_data: Recent Reddit posts

        Returns:
            Prediction dict with direction, confidence, and per-model outputs
        """
        # Get individual model predictions
        lstm_pred = self.lstm.predict(feature_sequence)
        xgb_pred = self.xgboost.predict(current_features)
        sentiment = self.sentiment_model.get_sentiment_signal(news_data, reddit_data)

        predictions = {}

        for timeframe in ["1h", "4h", "24h"]:
            lstm_tf = lstm_pred.get(timeframe, lstm_pred.get("1h", {}))
            lstm_bullish = lstm_tf.get("bullish_prob", 0.5)

            xgb_bullish = xgb_pred.get("bullish_prob", 0.5)
            sent_score = sentiment.get("score", 0)

            # Weighted ensemble
            base_prob = (
                self.LSTM_WEIGHT * lstm_bullish
                + self.XGBOOST_WEIGHT * xgb_bullish
                + self.SENTIMENT_WEIGHT * (0.5 + sent_score / 2)
            )

            # Apply sentiment modifier (amplify or dampen)
            modifier = sentiment.get("modifier", 1.0)
            adjusted_prob = 0.5 + (base_prob - 0.5) * modifier
            adjusted_prob = max(0.05, min(0.95, adjusted_prob))

            # Confidence = agreement between models
            probs = [lstm_bullish, xgb_bullish, 0.5 + sent_score / 2]
            agreement = 1 - np.std(probs) * 2  # Higher agreement = higher confidence
            confidence = float(abs(adjusted_prob - 0.5) * 200 * max(agreement, 0.3))
            confidence = min(confidence, 95)

            # Direction
            if adjusted_prob > 0.6:
                direction = "bullish"
            elif adjusted_prob < 0.4:
                direction = "bearish"
            else:
                direction = "neutral"

            # Magnitude (from LSTM)
            magnitude = lstm_tf.get("magnitude_pct", 0)

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
                        "confidence": float(xgb_pred.get("confidence", 0)),
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
