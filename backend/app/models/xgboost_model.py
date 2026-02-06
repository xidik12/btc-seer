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
        """Smart heuristic fallback using all available technical + sentiment features.

        Feature indices match FeatureBuilder.ALL_FEATURES order:
          0-4: ema_9, ema_21, ema_50, ema_200, sma_20
          5: rsi, 6: macd, 7: macd_signal, 8: macd_hist
          9: bb_upper, 10: bb_lower, 11: bb_width, 12: bb_position
          13: atr, 14: obv, 15: vwap
          16-19: roc_1, roc_6, roc_12, roc_24
          20-21: momentum_10, momentum_20
          22: volume_ratio, 23: volatility_24h
          24-26: price_vs_ema9, price_vs_ema21, price_vs_ema50
          27-29: body_size, upper_shadow, lower_shadow
          30-32: news_sentiment_1h, 4h, 24h
          33-35: news_volume_1h, news_bullish_pct, news_bearish_pct
          36: reddit_sentiment, 37: reddit_volume
          38: fear_greed_value
        """
        n = len(features)
        # Weighted signals: (probability, weight)
        signals = []

        # ── RSI (weight 3) — strongest mean-reversion signal ──
        if n > 5 and features[5] != 0:
            rsi = features[5]
            if rsi < 20:
                signals.append((0.85, 3.0))
            elif rsi < 30:
                signals.append((0.75, 3.0))
            elif rsi < 40:
                signals.append((0.60, 2.0))
            elif rsi > 80:
                signals.append((0.15, 3.0))
            elif rsi > 70:
                signals.append((0.25, 3.0))
            elif rsi > 60:
                signals.append((0.40, 2.0))
            else:
                signals.append((0.50, 1.0))

        # ── MACD histogram (weight 2.5) — trend momentum ──
        if n > 8 and features[8] != 0:
            macd_h = features[8]
            # Normalize MACD by price scale (feature may be raw or normalized)
            sig = np.clip(macd_h * 50, -1, 1)  # Scale to -1..+1
            signals.append((0.5 + sig * 0.3, 2.5))

        # ── Bollinger position (weight 2) — mean reversion ──
        if n > 12 and features[12] != 0:
            bb_pos = features[12]  # 0 = lower band, 1 = upper band
            if bb_pos < 0.1:
                signals.append((0.80, 2.0))
            elif bb_pos < 0.25:
                signals.append((0.65, 1.5))
            elif bb_pos > 0.9:
                signals.append((0.20, 2.0))
            elif bb_pos > 0.75:
                signals.append((0.35, 1.5))
            else:
                signals.append((0.50, 0.5))

        # ── Rate of Change — momentum across timeframes (weight 2) ──
        roc_weights = {16: 1.5, 17: 2.0, 18: 2.0, 19: 2.5}  # roc_1, roc_6, roc_12, roc_24
        for idx, w in roc_weights.items():
            if n > idx and features[idx] != 0:
                roc = features[idx]
                sig = np.clip(roc * 10, -1, 1)
                signals.append((0.5 + sig * 0.25, w))

        # ── Price vs EMAs (weight 2) — trend alignment ──
        ema_bullish = 0
        ema_count = 0
        for idx in [24, 25, 26]:  # price_vs_ema9, ema21, ema50
            if n > idx:
                val = features[idx]
                if val > 0:
                    ema_bullish += 1
                ema_count += 1
        if ema_count > 0:
            ema_ratio = ema_bullish / ema_count
            signals.append((0.35 + ema_ratio * 0.30, 2.0))

        # ── Momentum (weight 1.5) ──
        for idx in [20, 21]:  # momentum_10, momentum_20
            if n > idx and features[idx] != 0:
                sig = np.clip(features[idx] * 5, -1, 1)
                signals.append((0.5 + sig * 0.2, 1.5))

        # ── Volume ratio (weight 1) — confirms moves ──
        if n > 22 and features[22] != 0:
            vol_ratio = features[22]
            if vol_ratio > 1.5:
                signals.append((0.55, 1.0))  # High volume slightly bullish (buying pressure)
            elif vol_ratio < 0.5:
                signals.append((0.45, 0.5))

        # ── News sentiment (weight 2.5) — very impactful ──
        if n > 30 and features[30] != 0:
            sent = features[30]  # news_sentiment_1h
            sig = np.clip(sent * 2, -1, 1)
            signals.append((0.5 + sig * 0.3, 2.5))

        # ── Fear & Greed (weight 1.5) — contrarian signal ──
        if n > 38 and features[38] != 0:
            fg = features[38]
            if fg < 20:
                signals.append((0.70, 1.5))  # Extreme fear → contrarian bullish
            elif fg < 35:
                signals.append((0.60, 1.0))
            elif fg > 80:
                signals.append((0.30, 1.5))  # Extreme greed → contrarian bearish
            elif fg > 65:
                signals.append((0.40, 1.0))

        # ── Event memory expected impact (weight 2) ──
        if n > 52 and features[52] != 0:
            expected_1h = features[52]
            sig = np.clip(expected_1h, -1, 1)
            signals.append((0.5 + sig * 0.25, 2.0))

        # ── Compute weighted average ──
        if not signals:
            prob = 0.5
        else:
            total_weight = sum(w for _, w in signals)
            prob = sum(p * w for p, w in signals) / total_weight

        # Clamp to reasonable range
        prob = float(np.clip(prob, 0.10, 0.90))

        return {
            "bullish_prob": prob,
            "bearish_prob": 1 - prob,
            "direction": "bullish" if prob >= 0.5 else "bearish",
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
