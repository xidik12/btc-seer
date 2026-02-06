import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class XGBoostPredictor:
    """XGBoost model for feature-based BTC price direction prediction."""

    def __init__(self, model_path: str = None):
        self.model = None

        if model_path and Path(model_path).exists():
            self.load(model_path)
            logger.info(f"XGBoost model loaded from {model_path}")
        else:
            logger.warning("XGBoost model not found, will use heuristic fallback")

    def predict(self, features: np.ndarray) -> dict:
        """
        Predict price direction from feature vector.

        Args:
            features: 1D numpy array of features

        Returns:
            Dict with direction probability and confidence
        """
        if self.model is not None:
            return self._model_predict(features)
        return self._heuristic_predict(features)

    def _model_predict(self, features: np.ndarray) -> dict:
        """Prediction using trained XGBoost model."""
        try:
            import xgboost as xgb

            dmatrix = xgb.DMatrix(features.reshape(1, -1))
            prob = self.model.predict(dmatrix)[0]

            return {
                "bullish_prob": float(prob),
                "bearish_prob": float(1 - prob),
                "direction": "bullish" if prob > 0.5 else "bearish",
                "confidence": float(abs(prob - 0.5) * 200),
            }
        except Exception as e:
            logger.error(f"XGBoost prediction error: {e}")
            return self._heuristic_predict(features)

    def _heuristic_predict(self, features: np.ndarray) -> dict:
        """Simple heuristic fallback when no trained model is available.

        Uses RSI, MACD, and momentum from the feature vector.
        """
        # Feature indices (must match FeatureBuilder.ALL_FEATURES order)
        # RSI is at index 5, MACD at 6, MACD hist at 8, ROC_1 at 16
        signals = []

        if len(features) > 5:
            rsi = features[5]
            if rsi < 30:
                signals.append(0.7)  # Oversold → bullish
            elif rsi > 70:
                signals.append(0.3)  # Overbought → bearish
            else:
                signals.append(0.5)

        if len(features) > 8:
            macd_hist = features[8]
            if macd_hist > 0:
                signals.append(0.6)
            else:
                signals.append(0.4)

        if len(features) > 16:
            roc = features[16]
            if roc > 0:
                signals.append(0.55)
            else:
                signals.append(0.45)

        if not signals:
            prob = 0.5
        else:
            prob = float(np.mean(signals))

        return {
            "bullish_prob": prob,
            "bearish_prob": 1 - prob,
            "direction": "bullish" if prob > 0.5 else "bearish",
            "confidence": float(abs(prob - 0.5) * 200),
        }

    def save(self, path: str):
        if self.model:
            self.model.save_model(path)

    def load(self, path: str):
        try:
            import xgboost as xgb
            self.model = xgb.Booster()
            self.model.load_model(path)
        except Exception as e:
            logger.error(f"Error loading XGBoost model: {e}")
            self.model = None
