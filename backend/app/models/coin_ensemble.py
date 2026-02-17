"""Lightweight ensemble predictor for altcoin predictions.

Architecture (no heavy neural networks):
  XGBoost  (60%) — gradient-boosted trees on feature vector
  Momentum (40%) — SMA crossover + RSI + volume trend heuristic

Falls back to pure momentum logic when no trained XGBoost model is
available for a given coin.
"""

import logging
from pathlib import Path

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class CoinEnsemblePredictor:
    """Lightweight ensemble for per-coin direction / confidence prediction.

    Usage::

        predictor = CoinEnsemblePredictor()
        result = predictor.predict(
            features=feature_dict,
            price_history=last_200_closes,
            coin_id="ethereum",
            timeframe="1h",
        )
    """

    # Component weights
    W_XGB = 0.60
    W_MOM = 0.40

    # Timeframe scaling — longer horizons have larger expected moves
    TF_SCALE = {"1h": 1.0, "4h": 2.5, "24h": 6.0}

    def predict(
        self,
        features: dict,
        price_history: list[float],
        coin_id: str = "unknown",
        timeframe: str = "1h",
    ) -> dict:
        """Generate a prediction for a single coin.

        Args:
            features: Full feature dict from CoinFeatureBuilder.
            price_history: Recent close prices (at least 24 values, ideally 200).
            coin_id: Coin identifier (used to locate trained model file).
            timeframe: One of ``1h``, ``4h``, ``24h``.

        Returns:
            dict with keys ``direction``, ``confidence``, ``predicted_change_pct``,
            and ``model_outputs``.
        """
        xgb_result = self._xgboost_predict(features, coin_id)
        mom_result = self._momentum_predict(price_history, timeframe)

        # Determine effective weights — fall back to momentum-only when
        # XGBoost has no trained model.
        if xgb_result["has_model"]:
            w_xgb, w_mom = self.W_XGB, self.W_MOM
        else:
            w_xgb, w_mom = 0.0, 1.0

        # Weighted bullish probability
        total_w = w_xgb + w_mom
        bullish_prob = (
            w_xgb * xgb_result["bullish_prob"] + w_mom * mom_result["bullish_prob"]
        ) / total_w

        # Direction
        if bullish_prob >= 0.58:
            direction = "bullish"
        elif bullish_prob <= 0.42:
            direction = "bearish"
        else:
            direction = "neutral"

        # Confidence (0.0 - 1.0)
        signal_strength = abs(bullish_prob - 0.5) * 2  # 0..1
        base_confidence = 0.30 + signal_strength * 0.55

        # Agreement bonus
        xgb_dir = "bullish" if xgb_result["bullish_prob"] >= 0.5 else "bearish"
        mom_dir = "bullish" if mom_result["bullish_prob"] >= 0.5 else "bearish"
        if xgb_result["has_model"] and xgb_dir == mom_dir:
            base_confidence += 0.10

        # Trained-model bonus
        if xgb_result["has_model"]:
            base_confidence += 0.05

        confidence = float(np.clip(base_confidence, 0.15, 0.95))

        # Predicted change percentage — scale by timeframe
        tf_mult = self.TF_SCALE.get(timeframe, 1.0)
        magnitude = (bullish_prob - 0.5) * 2 * tf_mult  # roughly +-tf_mult %

        # Incorporate momentum magnitude if available
        mom_mag = mom_result.get("magnitude_pct", 0.0)
        if abs(mom_mag) > 0.01:
            magnitude = magnitude * 0.6 + mom_mag * tf_mult * 0.4

        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "predicted_change_pct": round(float(magnitude), 4),
            "bullish_prob": round(float(bullish_prob), 4),
            "model_outputs": {
                "xgboost": {
                    "bullish_prob": round(xgb_result["bullish_prob"], 4),
                    "has_model": xgb_result["has_model"],
                    "weight": round(w_xgb / total_w, 2),
                },
                "momentum": {
                    "bullish_prob": round(mom_result["bullish_prob"], 4),
                    "sma_cross": mom_result.get("sma_cross"),
                    "rsi_signal": mom_result.get("rsi_signal"),
                    "volume_trend": mom_result.get("volume_trend"),
                    "weight": round(w_mom / total_w, 2),
                },
            },
        }

    # ------------------------------------------------------------------
    # XGBoost component
    # ------------------------------------------------------------------

    def _xgboost_predict(self, features: dict, coin_id: str) -> dict:
        """Try to run XGBoost prediction from a trained per-coin model.

        Falls back to a simple feature-based heuristic when no model file
        exists, returning bullish_prob = 0.5 (neutral).
        """
        model_path = settings.model_path / f"coin_xgb_{coin_id}.json"

        if model_path.exists():
            try:
                xgb = _lazy_load_xgboost()
                if xgb is not None:
                    return self._run_xgb_model(xgb, model_path, features)
            except Exception as e:
                logger.warning(
                    f"[CoinEnsemble] XGBoost inference failed for {coin_id}: {e}"
                )

        # Heuristic fallback — use key features for a rough signal
        return self._xgboost_heuristic(features)

    @staticmethod
    def _run_xgb_model(xgb_module, model_path: Path, features: dict) -> dict:
        """Load a trained XGBoost model and predict."""
        import numpy as _np

        booster = xgb_module.Booster()
        booster.load_model(str(model_path))

        # Build feature array in the order the model expects.
        # The model stores its feature names; fall back to dict order.
        try:
            expected_names = booster.feature_names
        except Exception:
            expected_names = None

        if expected_names:
            arr = _np.array(
                [float(features.get(n, 0.0)) for n in expected_names],
                dtype=_np.float32,
            ).reshape(1, -1)
            dmat = xgb_module.DMatrix(arr, feature_names=expected_names)
        else:
            arr = _np.array(
                list(features.values()), dtype=_np.float32
            ).reshape(1, -1)
            dmat = xgb_module.DMatrix(arr)

        pred = booster.predict(dmat)
        bullish_prob = float(pred[0])
        return {"bullish_prob": bullish_prob, "has_model": True}

    @staticmethod
    def _xgboost_heuristic(features: dict) -> dict:
        """Simple feature-based heuristic when no trained XGBoost model exists.

        Combines RSI, MACD histogram, and Bollinger Band position into a
        rough bullish probability.  Returns neutral (0.5) when features are
        missing.
        """
        rsi = features.get("rsi", 50.0)
        macd_hist = features.get("macd_hist", 0.0)
        bb_pos = features.get("bb_position", 0.5)
        adx = features.get("adx", 20.0)

        # RSI signal: 0 (oversold=bullish) to 1 (overbought=bearish)
        rsi_signal = np.clip((rsi - 30) / 40, 0, 1)  # 30-70 mapped to 0-1

        # MACD histogram — positive = bullish
        macd_signal = 0.5 + np.clip(macd_hist / 100, -0.3, 0.3)

        # BB position — near lower band = bullish
        bb_signal = 1.0 - np.clip(bb_pos, 0, 1)

        # Weighted combination (invert rsi_signal because high RSI = bearish)
        bullish_prob = 0.4 * (1 - rsi_signal) + 0.35 * macd_signal + 0.25 * bb_signal

        # Dampen toward neutral when ADX is low (no trend)
        if adx < 20:
            bullish_prob = 0.5 + (bullish_prob - 0.5) * 0.5

        return {
            "bullish_prob": float(np.clip(bullish_prob, 0.05, 0.95)),
            "has_model": False,
        }

    # ------------------------------------------------------------------
    # Momentum component
    # ------------------------------------------------------------------

    @staticmethod
    def _momentum_predict(price_history: list[float], timeframe: str = "1h") -> dict:
        """Momentum-based prediction using SMA crossover, RSI, and volume proxy.

        Analyses the last 24 close prices to determine trend direction.
        """
        result = {
            "bullish_prob": 0.5,
            "sma_cross": "neutral",
            "rsi_signal": "neutral",
            "volume_trend": "flat",
            "magnitude_pct": 0.0,
        }

        if not price_history or len(price_history) < 24:
            return result

        prices = np.array(price_history[-200:], dtype=np.float64)
        n = len(prices)

        # --- SMA crossover (fast 9 vs slow 21) ---
        sma_cross_signal = 0.0
        if n >= 21:
            sma_9 = np.mean(prices[-9:])
            sma_21 = np.mean(prices[-21:])
            if sma_21 > 0:
                ratio = sma_9 / sma_21
                if ratio > 1.002:
                    sma_cross_signal = min((ratio - 1.0) * 50, 1.0)
                    result["sma_cross"] = "bullish"
                elif ratio < 0.998:
                    sma_cross_signal = max((ratio - 1.0) * 50, -1.0)
                    result["sma_cross"] = "bearish"

        # --- RSI (14-period) ---
        rsi_signal = 0.0
        if n >= 15:
            deltas = np.diff(prices[-15:])
            gains = np.where(deltas > 0, deltas, 0.0)
            losses = np.where(deltas < 0, -deltas, 0.0)
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - 100 / (1 + rs)
            else:
                rsi = 100.0 if avg_gain > 0 else 50.0

            if rsi > 70:
                rsi_signal = -0.5  # Overbought = bearish momentum
                result["rsi_signal"] = "overbought"
            elif rsi < 30:
                rsi_signal = 0.5  # Oversold = bullish momentum
                result["rsi_signal"] = "oversold"
            else:
                # Scale linearly: 30->+0.3, 50->0, 70->-0.3
                rsi_signal = (50 - rsi) / 66.7
                result["rsi_signal"] = "neutral"

        # --- Volume trend (price volatility as proxy) ---
        vol_signal = 0.0
        if n >= 24:
            recent_vol = np.std(prices[-12:])
            older_vol = np.std(prices[-24:-12])
            if older_vol > 0:
                vol_ratio = recent_vol / older_vol
                if vol_ratio > 1.3:
                    vol_signal = 0.2 if prices[-1] > prices[-12] else -0.2
                    result["volume_trend"] = "increasing"
                elif vol_ratio < 0.7:
                    result["volume_trend"] = "decreasing"
                else:
                    result["volume_trend"] = "flat"

        # --- Combine signals ---
        raw_signal = 0.40 * sma_cross_signal + 0.35 * rsi_signal + 0.25 * vol_signal
        bullish_prob = 0.5 + np.clip(raw_signal, -0.45, 0.45)

        # Magnitude: recent % change (24 bars)
        if prices[-24] > 0:
            pct_change = (prices[-1] / prices[-24] - 1)
        else:
            pct_change = 0.0

        result["bullish_prob"] = float(bullish_prob)
        result["magnitude_pct"] = float(np.clip(pct_change, -0.20, 0.20))

        return result


# ------------------------------------------------------------------
# Lazy import helper for XGBoost
# ------------------------------------------------------------------

_xgb_module = None
_xgb_checked = False


def _lazy_load_xgboost():
    """Import xgboost only when needed to avoid import errors in minimal environments."""
    global _xgb_module, _xgb_checked
    if _xgb_checked:
        return _xgb_module
    _xgb_checked = True
    try:
        import xgboost as xgb  # noqa: F811
        _xgb_module = xgb
        logger.debug("[CoinEnsemble] XGBoost library loaded")
    except ImportError:
        logger.info("[CoinEnsemble] XGBoost not installed; using heuristic fallback")
        _xgb_module = None
    return _xgb_module
