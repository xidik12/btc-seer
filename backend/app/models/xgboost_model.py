import logging
from pathlib import Path

import numpy as np

from app.features.builder import FeatureBuilder

logger = logging.getLogger(__name__)

# Build feature-name → index mapping for named lookups
_FEATURE_INDEX = {name: i for i, name in enumerate(FeatureBuilder.ALL_FEATURES)}


class XGBoostPredictor:
    """XGBoost model for feature-based BTC price direction prediction."""

    def __init__(self, model_path: str = None):
        self.model = None
        self._models = {}  # per-timeframe models: {"1h": Booster, "4h": Booster, ...}
        self._model_dir = None

        if model_path:
            self._model_dir = Path(model_path).parent
            if Path(model_path).exists():
                self.load(model_path)
                logger.info(f"XGBoost model loaded from {model_path}")
            else:
                logger.warning("XGBoost model not found, will use heuristic fallback")

            # Load per-timeframe models if available
            self._load_timeframe_models()

    def _load_timeframe_models(self):
        """Load per-timeframe XGBoost models (xgboost_1h.json, xgboost_4h.json, etc.)."""
        if not self._model_dir:
            return
        try:
            import xgboost as xgb
            for tf in ["1h", "4h", "24h", "1w", "1mo"]:
                path = self._model_dir / f"xgboost_{tf}.json"
                if path.exists():
                    model = xgb.Booster()
                    model.load_model(str(path))
                    self._models[tf] = model
            if self._models:
                logger.info(f"XGBoost per-timeframe models loaded: {list(self._models.keys())}")
        except Exception as e:
            logger.debug(f"Per-timeframe XGBoost load error: {e}")

    def predict(self, features: np.ndarray, timeframe: str = None) -> dict:
        """
        Predict price direction from feature vector.

        Args:
            features: 1D numpy array of features

        Returns:
            Dict with direction probability and confidence
        """
        # Use per-timeframe model if available, otherwise fall back to primary
        model = self._models.get(timeframe, self.model) if timeframe else self.model
        if model is not None:
            return self._model_predict(features, model=model)
        return self._heuristic_predict(features)

    def _model_predict(self, features: np.ndarray, model=None) -> dict:
        """Prediction using trained XGBoost model."""
        try:
            import xgboost as xgb

            model = model or self.model
            dmatrix = xgb.DMatrix(features.reshape(1, -1))
            prob = model.predict(dmatrix)[0]

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
        """Smart heuristic fallback using named feature lookups.

        Uses _FEATURE_INDEX for robust index resolution — immune to
        feature list reordering or expansion.
        """
        n = len(features)

        def _get(name: str) -> float | None:
            """Safely retrieve a feature value by name."""
            idx = _FEATURE_INDEX.get(name)
            if idx is None or idx >= n:
                return None
            v = features[idx]
            return float(v) if v != 0 else None

        # Weighted signals: (probability, weight)
        signals = []

        # ── RSI (weight 3) — strongest mean-reversion signal ──
        rsi = _get("rsi")
        if rsi is not None:
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
        macd_h = _get("macd_hist")
        if macd_h is not None:
            sig = np.clip(macd_h * 50, -1, 1)
            signals.append((0.5 + sig * 0.3, 2.5))

        # ── Bollinger position (weight 2) — mean reversion ──
        bb_pos = _get("bb_position")
        if bb_pos is not None:
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

        # ── Rate of Change — momentum across timeframes ──
        for roc_name, w in [("roc_1", 1.5), ("roc_6", 2.0), ("roc_12", 2.0), ("roc_24", 2.5)]:
            roc = _get(roc_name)
            if roc is not None:
                sig = np.clip(roc * 10, -1, 1)
                signals.append((0.5 + sig * 0.25, w))

        # ── Price vs EMAs (weight 2) — trend alignment ──
        ema_bullish = 0
        ema_count = 0
        for name in ["price_vs_ema9", "price_vs_ema21", "price_vs_ema50"]:
            val = _get(name)
            if val is not None:
                if val > 0:
                    ema_bullish += 1
                ema_count += 1
        if ema_count > 0:
            ema_ratio = ema_bullish / ema_count
            signals.append((0.35 + ema_ratio * 0.30, 2.0))

        # ── Momentum (weight 1.5) ──
        for name in ["momentum_10", "momentum_20"]:
            mom = _get(name)
            if mom is not None:
                sig = np.clip(mom * 5, -1, 1)
                signals.append((0.5 + sig * 0.2, 1.5))

        # ── Volume ratio (weight 1) — confirms moves ──
        vol_ratio = _get("volume_ratio")
        if vol_ratio is not None:
            if vol_ratio > 1.5:
                signals.append((0.55, 1.0))
            elif vol_ratio < 0.5:
                signals.append((0.45, 0.5))

        # ── News sentiment (weight 2.5) — very impactful ──
        sent = _get("news_sentiment_1h")
        if sent is not None:
            sig = np.clip(sent * 2, -1, 1)
            signals.append((0.5 + sig * 0.3, 2.5))

        # ── Fear & Greed (weight 1.5) — contrarian signal ──
        fg = _get("fear_greed_value")
        if fg is not None:
            if fg < 20:
                signals.append((0.70, 1.5))
            elif fg < 35:
                signals.append((0.60, 1.0))
            elif fg > 80:
                signals.append((0.30, 1.5))
            elif fg > 65:
                signals.append((0.40, 1.0))

        # ── Event memory expected impact (weight 2) ──
        ev_impact = _get("event_expected_impact_1h")
        if ev_impact is not None:
            sig = np.clip(ev_impact, -1, 1)
            signals.append((0.5 + sig * 0.25, 2.0))

        # ── Funding rate (weight 2) — derivatives signal ──
        fr = _get("funding_rate")
        if fr is not None:
            if fr > 0.001:
                signals.append((0.35, 2.0))
            elif fr > 0.0005:
                signals.append((0.42, 1.5))
            elif fr < -0.001:
                signals.append((0.65, 2.0))
            elif fr < -0.0005:
                signals.append((0.58, 1.5))

        # ── Mark-index spread (weight 1.5) — premium/discount ──
        spread = _get("mark_index_spread")
        if spread is not None:
            sig = np.clip(spread * 0.1, -1, 1)
            signals.append((0.5 + sig * 0.15, 1.5))

        # ── BTC dominance change (weight 1) ──
        mcap_chg = _get("market_cap_change")
        if mcap_chg is not None:
            sig = np.clip(mcap_chg * 2, -1, 1)
            signals.append((0.5 + sig * 0.15, 1.0))

        # ── NEW: ADX (weight 2) — trend strength ──
        adx_val = _get("adx")
        if adx_val is not None:
            # Strong trend (ADX > 25) amplifies momentum direction
            if adx_val > 40:
                # Very strong trend — trust momentum signals more
                mom_10 = _get("momentum_10")
                if mom_10 is not None:
                    signals.append((0.70 if mom_10 > 0 else 0.30, 2.0))
            elif adx_val > 25:
                mom_10 = _get("momentum_10")
                if mom_10 is not None:
                    signals.append((0.60 if mom_10 > 0 else 0.40, 1.5))

        # ── NEW: MFI (weight 2) — money flow index (volume-weighted RSI) ──
        mfi_val = _get("mfi")
        if mfi_val is not None:
            if mfi_val < 20:
                signals.append((0.75, 2.0))  # Oversold
            elif mfi_val > 80:
                signals.append((0.25, 2.0))  # Overbought

        # ── NEW: CMF (weight 1.5) — Chaikin Money Flow ──
        cmf_val = _get("cmf")
        if cmf_val is not None:
            sig = np.clip(cmf_val * 5, -1, 1)
            signals.append((0.5 + sig * 0.2, 1.5))

        # ── NEW: Supertrend direction (weight 2) ──
        st_dir = _get("supertrend_dir")
        if st_dir is not None:
            # -1 = uptrend (bullish), 1 = downtrend (bearish)
            if st_dir < 0:
                signals.append((0.65, 2.0))
            elif st_dir > 0:
                signals.append((0.35, 2.0))

        # ── NEW: CCI (weight 1.5) — Commodity Channel Index ──
        cci_val = _get("cci_20")
        if cci_val is not None:
            if cci_val < -200:
                signals.append((0.80, 1.5))  # Extremely oversold
            elif cci_val < -100:
                signals.append((0.65, 1.5))
            elif cci_val > 200:
                signals.append((0.20, 1.5))  # Extremely overbought
            elif cci_val > 100:
                signals.append((0.35, 1.5))

        # ── NEW: Fisher Transform (weight 1.5) ──
        fisher = _get("fisher_9")
        if fisher is not None:
            sig = np.clip(fisher, -3, 3) / 3  # Normalize to -1..+1
            signals.append((0.5 + sig * 0.2, 1.5))

        # ── NEW: Long/Short Ratio (weight 2) — crowd positioning ──
        ls_ratio = _get("long_short_ratio")
        if ls_ratio is not None:
            # Contrarian: extreme longs = bearish, extreme shorts = bullish
            if ls_ratio > 3.0:
                signals.append((0.30, 2.0))  # Too many longs
            elif ls_ratio > 2.0:
                signals.append((0.40, 1.5))
            elif ls_ratio < 0.5:
                signals.append((0.70, 2.0))  # Too many shorts
            elif ls_ratio < 0.8:
                signals.append((0.60, 1.5))

        # ── NEW: Taker Buy/Sell Ratio (weight 2) — aggression ──
        taker = _get("taker_buy_sell_ratio")
        if taker is not None:
            if taker > 1.1:
                signals.append((0.65, 2.0))  # Aggressive buying
            elif taker > 1.02:
                signals.append((0.57, 1.5))
            elif taker < 0.9:
                signals.append((0.35, 2.0))  # Aggressive selling
            elif taker < 0.98:
                signals.append((0.43, 1.5))

        # ── NEW: DVOL — BTC implied volatility (weight 1.5) ──
        dvol = _get("dvol")
        if dvol is not None:
            # High DVOL = uncertainty, low DVOL = complacency
            if dvol > 80:
                signals.append((0.45, 1.5))  # Fear/uncertainty
            elif dvol < 40:
                signals.append((0.55, 1.0))  # Calm — slight bullish

        # ── NEW: Liquidation imbalance (weight 2) ──
        long_liq = _get("long_liquidation_24h")
        short_liq = _get("short_liquidation_24h")
        if long_liq is not None and short_liq is not None:
            total_liq = long_liq + short_liq
            if total_liq > 0:
                # If mostly longs liquidated → contrarian bullish (cascade exhausted)
                long_pct = long_liq / total_liq
                if long_pct > 0.7:
                    signals.append((0.60, 2.0))  # Long squeeze exhaustion
                elif long_pct < 0.3:
                    signals.append((0.40, 2.0))  # Short squeeze exhaustion

        # ── NEW: ETF Net Flow (weight 2.5) — institutional demand ──
        etf_flow = _get("etf_net_flow_usd")
        if etf_flow is not None:
            if etf_flow > 500e6:
                signals.append((0.75, 2.5))  # Massive inflow
            elif etf_flow > 100e6:
                signals.append((0.63, 2.0))
            elif etf_flow < -500e6:
                signals.append((0.25, 2.5))  # Massive outflow
            elif etf_flow < -100e6:
                signals.append((0.37, 2.0))

        # ── NEW: Exchange Netflow (weight 2) — coins entering/leaving exchanges ──
        exch_net = _get("exchange_netflow_btc")
        if exch_net is not None:
            # Positive netflow = coins to exchanges = sell pressure
            if exch_net > 5000:
                signals.append((0.30, 2.0))  # Heavy inflows — bearish
            elif exch_net > 1000:
                signals.append((0.40, 1.5))
            elif exch_net < -5000:
                signals.append((0.70, 2.0))  # Heavy outflows — bullish
            elif exch_net < -1000:
                signals.append((0.60, 1.5))

        # ── NEW: NVT Signal (weight 1.5) — on-chain valuation ──
        nvt = _get("nvt_signal")
        if nvt is not None:
            if nvt > 150:
                signals.append((0.30, 1.5))  # Overvalued by transaction volume
            elif nvt < 30:
                signals.append((0.65, 1.5))  # Undervalued

        # ── NEW: MVRV Z-Score (weight 2) — market vs realized value ──
        mvrv = _get("mvrv_zscore")
        if mvrv is not None:
            if mvrv > 7:
                signals.append((0.15, 2.0))  # Extreme overvaluation
            elif mvrv > 3:
                signals.append((0.35, 1.5))
            elif mvrv < 0:
                signals.append((0.75, 2.0))  # Below realized value — strong buy
            elif mvrv < 1:
                signals.append((0.60, 1.5))

        # ── NEW: SOPR (weight 1.5) — Spent Output Profit Ratio ──
        sopr = _get("sopr")
        if sopr is not None:
            if sopr < 0.95:
                signals.append((0.70, 1.5))  # Sellers at a loss — capitulation
            elif sopr > 1.05:
                signals.append((0.40, 1.0))  # Profit taking

        # ── NEW: Puell Multiple (weight 1.5) — miner revenue vs avg ──
        puell = _get("puell_multiple")
        if puell is not None:
            if puell > 4:
                signals.append((0.25, 1.5))  # Miners over-earning — top signal
            elif puell < 0.5:
                signals.append((0.70, 1.5))  # Miners under-earning — bottom signal

        # ── NEW: Hurst Exponent (weight 2) — regime detection ──
        hurst = _get("hurst_exponent")
        if hurst is not None:
            # H > 0.5 = trending, H < 0.5 = mean-reverting, H ≈ 0.5 = random
            mom_10 = _get("momentum_10")
            if hurst > 0.65 and mom_10 is not None:
                # Strong trend — follow momentum direction
                signals.append((0.70 if mom_10 > 0 else 0.30, 2.0))
            elif hurst < 0.35 and rsi is not None:
                # Mean-reverting — contrarian play
                if rsi < 35:
                    signals.append((0.70, 2.0))
                elif rsi > 65:
                    signals.append((0.30, 2.0))

        # ── NEW: GARCH Volatility Forecast (weight 1) ──
        garch_vol = _get("garch_vol_forecast")
        if garch_vol is not None:
            # High predicted volatility = uncertainty
            if garch_vol > 0.05:
                signals.append((0.45, 1.0))  # Slight bearish bias in high vol
            elif garch_vol < 0.01:
                signals.append((0.55, 0.5))  # Low vol — calm markets

        # ── NEW: Parabolic SAR Direction (weight 2) — trend ──
        psar_d = _get("psar_dir")
        if psar_d is not None:
            if psar_d > 0:
                signals.append((0.62, 2.0))  # SAR below price — bullish
            elif psar_d < 0:
                signals.append((0.38, 2.0))  # SAR above price — bearish

        # ── NEW: Return Skew (weight 1) — asymmetry of returns ──
        skew = _get("return_skew_24")
        if skew is not None:
            # Positive skew = more right tail = bullish potential
            sig = np.clip(skew, -2, 2) / 2
            signals.append((0.5 + sig * 0.15, 1.0))

        # ── NEW: Aroon Oscillator (weight 1.5) — trend direction ──
        aroon = _get("aroon_osc")
        if aroon is not None:
            sig = np.clip(aroon / 100, -1, 1)
            signals.append((0.5 + sig * 0.2, 1.5))

        # ── NEW: TSI (weight 1.5) — True Strength Index ──
        tsi_val = _get("tsi")
        if tsi_val is not None:
            sig = np.clip(tsi_val / 30, -1, 1)
            signals.append((0.5 + sig * 0.2, 1.5))

        # ── NEW: Stablecoin Supply Change 7d (weight 1.5) — liquidity ──
        stable_chg = _get("stablecoin_supply_change_7d")
        if stable_chg is not None:
            # Growing stablecoin supply = more dry powder = bullish
            if stable_chg > 2:
                signals.append((0.65, 1.5))
            elif stable_chg > 0.5:
                signals.append((0.57, 1.0))
            elif stable_chg < -2:
                signals.append((0.35, 1.5))
            elif stable_chg < -0.5:
                signals.append((0.43, 1.0))

        # ── NEW: Hash Ribbon (weight 1.5) — miner capitulation ──
        hash_rib = _get("hash_ribbon")
        if hash_rib is not None:
            if hash_rib < 0:
                signals.append((0.65, 1.5))  # Miner capitulation — buy signal
            elif hash_rib > 0:
                signals.append((0.50, 0.5))  # Recovery/expansion

        # ── NEW: Estimated Leverage Ratio (weight 1.5) ──
        leverage = _get("estimated_leverage_ratio")
        if leverage is not None:
            if leverage > 0.3:
                signals.append((0.40, 1.5))  # High leverage — risk of cascade
            elif leverage < 0.1:
                signals.append((0.55, 1.0))  # Low leverage — healthy

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
