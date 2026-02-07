"""Google TimesFM foundation model for zero-shot BTC price forecasting.

TimesFM is a pre-trained time-series foundation model that can forecast
without any fine-tuning. We use it as a baseline / sanity check against
our trained models.
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

try:
    import timesfm
    TIMESFM_AVAILABLE = True
except ImportError:
    TIMESFM_AVAILABLE = False
    logger.info("timesfm not installed — TimesFM model will use statistical fallback")


class TimesFMPredictor:
    """Google TimesFM foundation model for zero-shot baseline."""

    def __init__(self):
        self.model = None
        self.is_available = False

        if TIMESFM_AVAILABLE:
            try:
                self.model = timesfm.TimesFm(
                    hparams=timesfm.TimesFmHparams(
                        backend="gpu" if self._has_gpu() else "cpu",
                        per_core_batch_size=1,
                        horizon_len=24,
                    ),
                    checkpoint=timesfm.TimesFmCheckpoint(
                        huggingface_repo_id="google/timesfm-2.0-200m-pytorch",
                    ),
                )
                self.is_available = True
                logger.info("TimesFM model loaded successfully")
            except Exception as e:
                logger.warning(f"TimesFM failed to load: {e}")

    def _has_gpu(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def predict(self, price_history: list[float]) -> dict:
        """Generate price forecasts from historical close prices.

        Args:
            price_history: List of hourly close prices (ideally 512+)

        Returns:
            Dict with 1h, 4h, 24h predictions
        """
        if self.is_available and self.model is not None:
            return self._model_predict(price_history)
        return self._statistical_predict(price_history)

    def _model_predict(self, price_history: list[float]) -> dict:
        """Zero-shot forecasting with TimesFM."""
        try:
            prices = np.array(price_history, dtype=np.float32)

            # TimesFM expects 2D input: (num_series, time_steps)
            forecast_input = prices.reshape(1, -1)
            frequency_input = [0]  # 0 = high frequency (hourly)

            point_forecast, _ = self.model.forecast(
                forecast_input,
                freq=frequency_input,
            )

            # point_forecast shape: (1, horizon_len)
            forecasted = point_forecast[0]
            current_price = prices[-1]

            predictions = {}
            for tf, idx in [("1h", 0), ("4h", 3), ("24h", 23)]:
                if idx < len(forecasted):
                    predicted_price = float(forecasted[idx])
                else:
                    predicted_price = float(forecasted[-1])

                change_pct = (predicted_price - current_price) / current_price * 100
                prob = 0.5 + np.clip(change_pct * 5, -0.4, 0.4)

                predictions[tf] = {
                    "bullish_prob": float(prob),
                    "bearish_prob": float(1 - prob),
                    "direction": "bullish" if predicted_price > current_price else "bearish",
                    "magnitude_pct": float(change_pct),
                    "predicted_price": float(predicted_price),
                    "confidence": float(abs(prob - 0.5) * 200),
                }

            return predictions

        except Exception as e:
            logger.error(f"TimesFM prediction error: {e}")
            return self._statistical_predict(price_history)

    def _statistical_predict(self, price_history: list[float]) -> dict:
        """Statistical fallback: exponential moving average extrapolation."""
        predictions = {}

        if not price_history or len(price_history) < 10:
            for tf in ["1h", "4h", "24h"]:
                predictions[tf] = {
                    "bullish_prob": 0.5,
                    "bearish_prob": 0.5,
                    "direction": "bullish",
                    "magnitude_pct": 0.0,
                    "confidence": 0.0,
                }
            return predictions

        prices = np.array(price_history, dtype=np.float64)
        current = prices[-1]

        # Calculate momentum at different scales
        returns_1h = (prices[-1] - prices[-2]) / prices[-2] if len(prices) >= 2 else 0
        returns_4h = (prices[-1] - prices[-4]) / prices[-4] if len(prices) >= 4 else 0
        returns_24h = (prices[-1] - prices[-24]) / prices[-24] if len(prices) >= 24 else 0

        # EMA-based trend
        ema_12 = self._ema(prices, 12)
        ema_26 = self._ema(prices, 26)
        trend_signal = (ema_12 - ema_26) / current if current > 0 else 0

        for tf, horizon_returns, weight in [
            ("1h", returns_1h, 0.5),
            ("4h", returns_4h, 0.3),
            ("24h", returns_24h, 0.2),
        ]:
            # Combine momentum with trend
            signal = horizon_returns * weight + trend_signal * (1 - weight)
            prob = 0.5 + np.clip(signal * 20, -0.3, 0.3)

            tf_multiplier = {"1h": 1.0, "4h": 2.5, "24h": 5.0}[tf]
            magnitude = signal * 100 * tf_multiplier

            predictions[tf] = {
                "bullish_prob": float(prob),
                "bearish_prob": float(1 - prob),
                "direction": "bullish" if prob >= 0.5 else "bearish",
                "magnitude_pct": float(np.clip(magnitude, -10, 10)),
                "confidence": float(abs(prob - 0.5) * 200),
            }

        return predictions

    @staticmethod
    def _ema(data: np.ndarray, span: int) -> float:
        if len(data) < span:
            return float(data[-1])
        alpha = 2.0 / (span + 1)
        ema = data[-span]
        for price in data[-span + 1:]:
            ema = alpha * price + (1 - alpha) * ema
        return float(ema)
