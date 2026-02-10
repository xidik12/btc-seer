import logging
from datetime import datetime

import numpy as np
import pandas as pd

try:
    import pandas_ta as pta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False

try:
    from arch import arch_model
    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False

try:
    import pywt
    PYWT_AVAILABLE = True
except ImportError:
    PYWT_AVAILABLE = False

logger = logging.getLogger(__name__)


class TechnicalFeatures:
    """Calculates technical indicators from OHLCV price data."""

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators. Expects columns: open, high, low, close, volume."""
        df = df.copy()

        # Moving Averages
        for period in [9, 21, 50, 200]:
            df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()
        df["sma_20"] = df["close"].rolling(20).mean()

        # RSI (14)
        df["rsi"] = TechnicalFeatures._rsi(df["close"], 14)

        # MACD
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # Bollinger Bands
        df["bb_middle"] = df["close"].rolling(20).mean()
        bb_std = df["close"].rolling(20).std()
        df["bb_upper"] = df["bb_middle"] + 2 * bb_std
        df["bb_lower"] = df["bb_middle"] - 2 * bb_std
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # ATR (Average True Range)
        df["atr"] = TechnicalFeatures._atr(df, 14)

        # OBV (On Balance Volume)
        df["obv"] = TechnicalFeatures._obv(df)

        # VWAP
        df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()

        # Rate of Change
        for period in [1, 6, 12, 24]:
            df[f"roc_{period}"] = df["close"].pct_change(period) * 100

        # Momentum
        df["momentum_10"] = df["close"] - df["close"].shift(10)
        df["momentum_20"] = df["close"] - df["close"].shift(20)

        # Volume features
        df["volume_sma_20"] = df["volume"].rolling(20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma_20"]

        # Price position relative to EMAs
        df["price_vs_ema9"] = (df["close"] - df["ema_9"]) / df["ema_9"] * 100
        df["price_vs_ema21"] = (df["close"] - df["ema_21"]) / df["ema_21"] * 100
        df["price_vs_ema50"] = (df["close"] - df["ema_50"]) / df["ema_50"] * 100

        # Volatility
        df["volatility_24h"] = df["close"].rolling(24).std() / df["close"].rolling(24).mean() * 100

        # Support/Resistance levels (simplified pivot points)
        df["pivot"] = (df["high"] + df["low"] + df["close"]) / 3
        df["support_1"] = 2 * df["pivot"] - df["high"]
        df["resistance_1"] = 2 * df["pivot"] - df["low"]

        # Candle patterns
        df["body_size"] = abs(df["close"] - df["open"]) / df["open"] * 100
        df["upper_shadow"] = (df["high"] - df[["close", "open"]].max(axis=1)) / df["open"] * 100
        df["lower_shadow"] = (df[["close", "open"]].min(axis=1) - df["low"]) / df["open"] * 100

        # ── Extended indicators for Quant Theory predictor ──

        # Long SMAs for cycle indicators
        df["sma_111"] = df["close"].rolling(111, min_periods=50).mean()
        df["sma_200"] = df["close"].rolling(200, min_periods=100).mean()
        df["sma_350"] = df["close"].rolling(350, min_periods=150).mean()

        # Multi-timeframe RSI
        df["rsi_7"] = TechnicalFeatures._rsi(df["close"], 7)
        df["rsi_30"] = TechnicalFeatures._rsi(df["close"], 30)

        # ADX (Average Directional Index) — regime detection
        df["adx"] = TechnicalFeatures._adx(df, 14)

        # Extra momentum
        df["momentum_30"] = df["close"] - df["close"].shift(30)

        # Mayer Multiple (price / SMA_200)
        df["mayer_multiple"] = df["close"] / df["sma_200"]

        # Pi Cycle Top: SMA_111 vs SMA_350 * 2
        df["pi_cycle_ratio"] = df["sma_111"] / (df["sma_350"] * 2)

        # Golden/Death cross: EMA_50 vs EMA_200
        df["ema_cross"] = df["ema_50"] / df["ema_200"]

        # Mean reversion Z-score: how far price is from 20-day SMA in std devs
        df["zscore_20"] = (df["close"] - df["sma_20"]) / df["close"].rolling(20).std()

        # ── New indicators ──

        # Stochastic RSI
        rsi_14 = df["rsi"]
        rsi_min = rsi_14.rolling(14).min()
        rsi_max = rsi_14.rolling(14).max()
        stoch_rsi_k = ((rsi_14 - rsi_min) / (rsi_max - rsi_min)) * 100
        df["stoch_rsi_k"] = stoch_rsi_k.rolling(3).mean()
        df["stoch_rsi_d"] = df["stoch_rsi_k"].rolling(3).mean()

        # Williams %R
        high_14 = df["high"].rolling(14).max()
        low_14 = df["low"].rolling(14).min()
        df["williams_r"] = ((high_14 - df["close"]) / (high_14 - low_14)) * -100

        # Ichimoku Cloud
        high_9 = df["high"].rolling(9).max()
        low_9 = df["low"].rolling(9).min()
        df["ichimoku_tenkan"] = (high_9 + low_9) / 2

        high_26 = df["high"].rolling(26).max()
        low_26 = df["low"].rolling(26).min()
        df["ichimoku_kijun"] = (high_26 + low_26) / 2

        df["ichimoku_senkou_a"] = ((df["ichimoku_tenkan"] + df["ichimoku_kijun"]) / 2).shift(26)
        high_52 = df["high"].rolling(52).max()
        low_52 = df["low"].rolling(52).min()
        df["ichimoku_senkou_b"] = ((high_52 + low_52) / 2).shift(26)

        df["ichimoku_chikou"] = df["close"].shift(-26)

        # Candlestick patterns
        df["candle_doji"] = (df["body_size"] < 0.1).astype(int)

        body = df["close"] - df["open"]
        body_abs = body.abs()
        lower = df[["close", "open"]].min(axis=1) - df["low"]
        upper = df["high"] - df[["close", "open"]].max(axis=1)

        df["candle_hammer"] = ((lower > body_abs * 2) & (upper < body_abs * 0.5) & (body_abs > 0)).astype(int)
        df["candle_inverted_hammer"] = ((upper > body_abs * 2) & (lower < body_abs * 0.5) & (body_abs > 0)).astype(int)

        prev_body = body.shift(1)
        df["candle_bullish_engulfing"] = (
            (prev_body < 0) & (body > 0) &
            (df["open"] <= df["close"].shift(1)) &
            (df["close"] >= df["open"].shift(1))
        ).astype(int)
        df["candle_bearish_engulfing"] = (
            (prev_body > 0) & (body < 0) &
            (df["open"] >= df["close"].shift(1)) &
            (df["close"] <= df["open"].shift(1))
        ).astype(int)

        # Morning/Evening star (3-candle)
        body_2ago = body.shift(2)
        body_1ago = body.shift(1)
        df["candle_morning_star"] = (
            (body_2ago < 0) &
            (body_1ago.abs() < body_2ago.abs() * 0.3) &
            (body > 0) &
            (df["close"] > (df["open"].shift(2) + df["close"].shift(2)) / 2)
        ).astype(int)
        df["candle_evening_star"] = (
            (body_2ago > 0) &
            (body_1ago.abs() < body_2ago.abs() * 0.3) &
            (body < 0) &
            (df["close"] < (df["open"].shift(2) + df["close"].shift(2)) / 2)
        ).astype(int)

        # Trend identification
        df["trend_short"] = TechnicalFeatures._classify_trend(df["close"], 20)
        df["trend_medium"] = TechnicalFeatures._classify_trend(df["close"], 50)
        df["trend_long"] = TechnicalFeatures._classify_trend(df["close"], 100)

        # pandas-ta extended indicators
        df = TechnicalFeatures.calculate_pandas_ta_indicators(df)

        # Advanced quantitative indicators
        df = TechnicalFeatures.calculate_advanced_indicators(df)

        return df

    @staticmethod
    def calculate_pandas_ta_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Compute ~45 additional indicators using pandas-ta."""
        if not PANDAS_TA_AVAILABLE:
            logger.warning("pandas-ta not installed — skipping extended indicators")
            # Fill with zeros so feature array shape is consistent
            pta_cols = [
                "ao", "cci_20", "cmo_14", "fisher_9", "fisher_signal",
                "kst", "kst_signal", "ppo", "ppo_signal", "ppo_hist",
                "stoch_k", "stoch_d", "tsi", "uo",
                "aroon_osc", "chop_14", "dpo_20", "supertrend_dir",
                "vortex_diff", "mass_index", "plus_di", "minus_di",
                "donchian_upper", "donchian_lower", "donchian_mid", "donchian_width",
                "kc_upper", "kc_lower", "kc_position", "natr", "ui",
                "ad", "cmf", "efi_13", "mfi", "nvi", "pvi",
                "entropy_10", "kurtosis_20", "skew_20", "variance_20",
                "zscore_14", "stdev_20", "linreg_slope", "linreg_r2",
            ]
            for col in pta_cols:
                if col not in df.columns:
                    df[col] = 0.0
            return df

        try:
            high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]

            # ── Momentum (14) ──
            ao = pta.ao(high, low)
            if ao is not None:
                df["ao"] = ao
            else:
                df["ao"] = 0.0

            cci = pta.cci(high, low, close, length=20)
            df["cci_20"] = cci if cci is not None else 0.0

            cmo = pta.cmo(close, length=14)
            df["cmo_14"] = cmo if cmo is not None else 0.0

            fisher = pta.fisher(high, low, length=9)
            if fisher is not None and len(fisher.columns) >= 2:
                df["fisher_9"] = fisher.iloc[:, 0]
                df["fisher_signal"] = fisher.iloc[:, 1]
            else:
                df["fisher_9"] = 0.0
                df["fisher_signal"] = 0.0

            kst_result = pta.kst(close)
            if kst_result is not None and len(kst_result.columns) >= 2:
                df["kst"] = kst_result.iloc[:, 0]
                df["kst_signal"] = kst_result.iloc[:, 1]
            else:
                df["kst"] = 0.0
                df["kst_signal"] = 0.0

            ppo_result = pta.ppo(close)
            if ppo_result is not None and len(ppo_result.columns) >= 3:
                df["ppo"] = ppo_result.iloc[:, 0]
                df["ppo_signal"] = ppo_result.iloc[:, 1]
                df["ppo_hist"] = ppo_result.iloc[:, 2]
            else:
                df["ppo"] = 0.0
                df["ppo_signal"] = 0.0
                df["ppo_hist"] = 0.0

            stoch = pta.stoch(high, low, close)
            if stoch is not None and len(stoch.columns) >= 2:
                df["stoch_k"] = stoch.iloc[:, 0]
                df["stoch_d"] = stoch.iloc[:, 1]
            else:
                df["stoch_k"] = 0.0
                df["stoch_d"] = 0.0

            tsi_val = pta.tsi(close)
            if tsi_val is not None and len(tsi_val.columns) >= 1:
                df["tsi"] = tsi_val.iloc[:, 0]
            else:
                df["tsi"] = 0.0

            uo_val = pta.uo(high, low, close)
            df["uo"] = uo_val if uo_val is not None else 0.0

            # ── Trend (8) ──
            aroon = pta.aroon(high, low, length=25)
            if aroon is not None and len(aroon.columns) >= 3:
                df["aroon_osc"] = aroon.iloc[:, 2]  # oscillator column
            else:
                df["aroon_osc"] = 0.0

            chop = pta.chop(high, low, close, length=14)
            df["chop_14"] = chop if chop is not None else 0.0

            dpo = pta.dpo(close, length=20)
            df["dpo_20"] = dpo if dpo is not None else 0.0

            st = pta.supertrend(high, low, close, length=7, multiplier=3.0)
            if st is not None:
                # Direction column: -1 = uptrend, 1 = downtrend
                dir_col = [c for c in st.columns if "SUPERTd" in c]
                if dir_col:
                    df["supertrend_dir"] = st[dir_col[0]]
                else:
                    df["supertrend_dir"] = 0.0
            else:
                df["supertrend_dir"] = 0.0

            vortex = pta.vortex(high, low, close, length=14)
            if vortex is not None and len(vortex.columns) >= 2:
                df["vortex_diff"] = vortex.iloc[:, 0] - vortex.iloc[:, 1]
            else:
                df["vortex_diff"] = 0.0

            mi = pta.massi(high, low)
            df["mass_index"] = mi if mi is not None else 0.0

            # Plus/Minus DI from ADX calculation
            adx_result = pta.adx(high, low, close, length=14)
            if adx_result is not None and len(adx_result.columns) >= 3:
                df["plus_di"] = adx_result.iloc[:, 1]
                df["minus_di"] = adx_result.iloc[:, 2]
            else:
                df["plus_di"] = 0.0
                df["minus_di"] = 0.0

            # ── Volatility (9) ──
            dc = pta.donchian(high, low, lower_length=20, upper_length=20)
            if dc is not None and len(dc.columns) >= 3:
                df["donchian_lower"] = dc.iloc[:, 0]
                df["donchian_mid"] = dc.iloc[:, 1]
                df["donchian_upper"] = dc.iloc[:, 2]
                dc_range = df["donchian_upper"] - df["donchian_lower"]
                df["donchian_width"] = dc_range / df["donchian_mid"]
            else:
                df["donchian_upper"] = 0.0
                df["donchian_lower"] = 0.0
                df["donchian_mid"] = 0.0
                df["donchian_width"] = 0.0

            kc = pta.kc(high, low, close, length=20, scalar=1.5)
            if kc is not None and len(kc.columns) >= 3:
                df["kc_lower"] = kc.iloc[:, 0]
                df["kc_upper"] = kc.iloc[:, 2]
                kc_range = df["kc_upper"] - df["kc_lower"]
                df["kc_position"] = (close - df["kc_lower"]) / kc_range.replace(0, np.nan)
                df["kc_position"] = df["kc_position"].fillna(0.5)
            else:
                df["kc_upper"] = 0.0
                df["kc_lower"] = 0.0
                df["kc_position"] = 0.0

            natr = pta.natr(high, low, close, length=14)
            df["natr"] = natr if natr is not None else 0.0

            ui_val = pta.ui(close, length=14)
            df["ui"] = ui_val if ui_val is not None else 0.0

            # ── Volume (6) ──
            ad_val = pta.ad(high, low, close, volume)
            df["ad"] = ad_val if ad_val is not None else 0.0

            cmf_val = pta.cmf(high, low, close, volume, length=20)
            df["cmf"] = cmf_val if cmf_val is not None else 0.0

            efi = pta.efi(close, volume, length=13)
            df["efi_13"] = efi if efi is not None else 0.0

            mfi_val = pta.mfi(high, low, close, volume, length=14)
            df["mfi"] = mfi_val if mfi_val is not None else 0.0

            nvi_val = pta.nvi(close, volume)
            if nvi_val is not None:
                df["nvi"] = nvi_val.iloc[:, 0] if hasattr(nvi_val, 'columns') else nvi_val
            else:
                df["nvi"] = 0.0

            pvi_val = pta.pvi(close, volume)
            if pvi_val is not None:
                df["pvi"] = pvi_val.iloc[:, 0] if hasattr(pvi_val, 'columns') else pvi_val
            else:
                df["pvi"] = 0.0

            # ── Statistics (8) ──
            ent = pta.entropy(close, length=10)
            df["entropy_10"] = ent if ent is not None else 0.0

            kurt = pta.kurtosis(close, length=20)
            df["kurtosis_20"] = kurt if kurt is not None else 0.0

            skw = pta.skew(close, length=20)
            df["skew_20"] = skw if skw is not None else 0.0

            var_val = pta.variance(close, length=20)
            df["variance_20"] = var_val if var_val is not None else 0.0

            zs = pta.zscore(close, length=14)
            df["zscore_14"] = zs if zs is not None else 0.0

            sd = pta.stdev(close, length=20)
            df["stdev_20"] = sd if sd is not None else 0.0

            lr_slope = pta.linreg(close, length=20, slope=True)
            df["linreg_slope"] = lr_slope if lr_slope is not None else 0.0

            lr_r = pta.linreg(close, length=20, r=True)
            df["linreg_r2"] = lr_r if lr_r is not None else 0.0

            # Fill any remaining NaN from warmup periods
            pta_cols = [
                "ao", "cci_20", "cmo_14", "fisher_9", "fisher_signal",
                "kst", "kst_signal", "ppo", "ppo_signal", "ppo_hist",
                "stoch_k", "stoch_d", "tsi", "uo",
                "aroon_osc", "chop_14", "dpo_20", "supertrend_dir",
                "vortex_diff", "mass_index", "plus_di", "minus_di",
                "donchian_upper", "donchian_lower", "donchian_mid", "donchian_width",
                "kc_upper", "kc_lower", "kc_position", "natr", "ui",
                "ad", "cmf", "efi_13", "mfi", "nvi", "pvi",
                "entropy_10", "kurtosis_20", "skew_20", "variance_20",
                "zscore_14", "stdev_20", "linreg_slope", "linreg_r2",
            ]
            for col in pta_cols:
                if col in df.columns:
                    df[col] = df[col].fillna(0.0)
                else:
                    df[col] = 0.0

        except Exception as e:
            logger.error(f"Error computing pandas-ta indicators: {e}")
            # Ensure all columns exist even on error
            pta_cols = [
                "ao", "cci_20", "cmo_14", "fisher_9", "fisher_signal",
                "kst", "kst_signal", "ppo", "ppo_signal", "ppo_hist",
                "stoch_k", "stoch_d", "tsi", "uo",
                "aroon_osc", "chop_14", "dpo_20", "supertrend_dir",
                "vortex_diff", "mass_index", "plus_di", "minus_di",
                "donchian_upper", "donchian_lower", "donchian_mid", "donchian_width",
                "kc_upper", "kc_lower", "kc_position", "natr", "ui",
                "ad", "cmf", "efi_13", "mfi", "nvi", "pvi",
                "entropy_10", "kurtosis_20", "skew_20", "variance_20",
                "zscore_14", "stdev_20", "linreg_slope", "linreg_r2",
            ]
            for col in pta_cols:
                if col not in df.columns:
                    df[col] = 0.0

        return df

    @staticmethod
    def _classify_trend(series: pd.Series, period: int) -> pd.Series:
        """Classify trend as 1 (up), -1 (down), 0 (sideways)."""
        slope = series.rolling(period).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= 2 else 0,
            raw=True,
        )
        mean_price = series.rolling(period).mean()
        threshold = mean_price * 0.0002  # 0.02% per candle
        return slope.apply(lambda s: 1 if s > 0 else (-1 if s < 0 else 0) if not pd.isna(s) else 0)

    @staticmethod
    def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average Directional Index — measures trend strength (0-100)."""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        return adx

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean()

    @staticmethod
    def _obv(df: pd.DataFrame) -> pd.Series:
        obv = [0]
        for i in range(1, len(df)):
            if df["close"].iloc[i] > df["close"].iloc[i - 1]:
                obv.append(obv[-1] + df["volume"].iloc[i])
            elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
                obv.append(obv[-1] - df["volume"].iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=df.index)

    # ─────────────────────────────────────────────────────────
    #  ADVANCED QUANTITATIVE INDICATORS
    # ─────────────────────────────────────────────────────────

    ADVANCED_COLS = [
        # Adaptive MAs (3)
        "kama_10", "t3_10", "dema_21",
        # Additional momentum (4)
        "trix_14", "bop", "psar", "psar_dir",
        # Additional candlestick patterns (7)
        "candle_three_white", "candle_three_black", "candle_dark_cloud",
        "candle_piercing", "candle_harami", "candle_kicking", "candle_three_line_strike",
        # Price transforms (3)
        "typical_price", "weighted_close", "median_price",
        # Return-based statistics (6)
        "return_1h", "return_skew_24", "return_kurtosis_24",
        "return_autocorr_1", "return_autocorr_6", "return_autocorr_24",
        # Hurst exponent (1)
        "hurst_exponent",
        # GARCH volatility (2)
        "garch_vol_forecast", "vol_risk_premium",
        # Wavelet features (3)
        "wavelet_trend", "wavelet_detail_1", "wavelet_detail_2",
        # Calendar features (4)
        "hour_sin", "hour_cos", "day_of_week_sin", "day_of_week_cos",
        # Hash Ribbon (1)
        "hash_ribbon",
        # Cross-feature interactions (3)
        "rsi_macd_divergence", "volume_price_trend", "atr_ratio_50_14",
    ]

    @staticmethod
    def calculate_advanced_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Compute advanced quantitative indicators."""
        try:
            close = df["close"]
            high = df["high"]
            low = df["low"]
            volume = df["volume"]
            open_ = df["open"]
            returns = close.pct_change()

            # ── Adaptive Moving Averages ──
            if PANDAS_TA_AVAILABLE:
                kama = pta.kama(close, length=10)
                df["kama_10"] = kama if kama is not None else 0.0

                t3 = pta.t3(close, length=10)
                df["t3_10"] = t3 if t3 is not None else 0.0

                dema = pta.dema(close, length=21)
                df["dema_21"] = dema if dema is not None else 0.0
            else:
                df["kama_10"] = close.ewm(span=10, adjust=False).mean()
                df["t3_10"] = close.ewm(span=10, adjust=False).mean()
                df["dema_21"] = close.ewm(span=21, adjust=False).mean()

            # ── Additional Momentum ──
            if PANDAS_TA_AVAILABLE:
                trix = pta.trix(close, length=14)
                if trix is not None:
                    df["trix_14"] = trix.iloc[:, 0] if hasattr(trix, 'columns') else trix
                else:
                    df["trix_14"] = 0.0

                psar = pta.psar(high, low, close)
                if psar is not None:
                    # Direction: 1 = bullish (price above SAR), -1 = bearish
                    long_col = [c for c in psar.columns if "PSARl" in c]
                    short_col = [c for c in psar.columns if "PSARs" in c]
                    if long_col and short_col:
                        df["psar"] = psar[long_col[0]].fillna(psar[short_col[0]])
                        df["psar_dir"] = psar[long_col[0]].notna().astype(int) * 2 - 1
                    else:
                        df["psar"] = 0.0
                        df["psar_dir"] = 0.0
                else:
                    df["psar"] = 0.0
                    df["psar_dir"] = 0.0
            else:
                df["trix_14"] = 0.0
                df["psar"] = 0.0
                df["psar_dir"] = 0.0

            # Balance of Power
            range_ = high - low
            df["bop"] = ((close - open_) / range_.replace(0, np.nan)).fillna(0)

            # ── Additional Candlestick Patterns ──
            body = close - open_
            body_abs = body.abs()
            prev_body = body.shift(1)
            prev2_body = body.shift(2)

            # Three White Soldiers (3 consecutive bullish candles with higher closes)
            df["candle_three_white"] = (
                (body > 0) & (prev_body > 0) & (prev2_body > 0) &
                (close > close.shift(1)) & (close.shift(1) > close.shift(2))
            ).astype(int)

            # Three Black Crows
            df["candle_three_black"] = (
                (body < 0) & (prev_body < 0) & (prev2_body < 0) &
                (close < close.shift(1)) & (close.shift(1) < close.shift(2))
            ).astype(int)

            # Dark Cloud Cover (bearish after bullish)
            df["candle_dark_cloud"] = (
                (prev_body > 0) & (body < 0) &
                (open_ > close.shift(1)) &
                (close < (open_.shift(1) + close.shift(1)) / 2)
            ).astype(int)

            # Piercing (bullish after bearish)
            df["candle_piercing"] = (
                (prev_body < 0) & (body > 0) &
                (open_ < close.shift(1)) &
                (close > (open_.shift(1) + close.shift(1)) / 2)
            ).astype(int)

            # Harami (small body inside previous body)
            df["candle_harami"] = (
                (body_abs < prev_body.abs() * 0.5) &
                (close.clip(upper=open_).clip(lower=open_) <= close.shift(1).clip(upper=open_.shift(1))) &
                (body_abs > 0)
            ).astype(int)

            # Kicking (gap + opposite direction)
            df["candle_kicking"] = (
                ((prev_body < 0) & (body > 0) & (open_ > open_.shift(1))) |
                ((prev_body > 0) & (body < 0) & (open_ < open_.shift(1)))
            ).astype(int)

            # Three Line Strike (3-bar pattern + reversal)
            df["candle_three_line_strike"] = (
                (prev2_body > 0) & (prev_body > 0) & (body.shift(0) < 0) &
                (close < open_.shift(2))
            ).astype(int)

            # ── Price Transforms ──
            df["typical_price"] = (high + low + close) / 3
            df["weighted_close"] = (high + low + 2 * close) / 4
            df["median_price"] = (high + low) / 2

            # ── Return-based Statistics ──
            df["return_1h"] = returns.fillna(0)
            df["return_skew_24"] = returns.rolling(24).skew().fillna(0)
            df["return_kurtosis_24"] = returns.rolling(24).kurt().fillna(0)
            df["return_autocorr_1"] = returns.rolling(48).apply(
                lambda x: x.autocorr(lag=1) if len(x) >= 2 else 0, raw=False
            ).fillna(0)
            df["return_autocorr_6"] = returns.rolling(48).apply(
                lambda x: x.autocorr(lag=6) if len(x) >= 7 else 0, raw=False
            ).fillna(0)
            df["return_autocorr_24"] = returns.rolling(72).apply(
                lambda x: x.autocorr(lag=24) if len(x) >= 25 else 0, raw=False
            ).fillna(0)

            # ── Hurst Exponent (rolling) ──
            df["hurst_exponent"] = TechnicalFeatures._rolling_hurst(close, window=100)

            # ── GARCH Volatility Forecast ──
            garch_vol, vol_premium = TechnicalFeatures._garch_volatility(returns)
            df["garch_vol_forecast"] = garch_vol
            df["vol_risk_premium"] = vol_premium

            # ── Wavelet Decomposition ──
            w_trend, w_d1, w_d2 = TechnicalFeatures._wavelet_features(close)
            df["wavelet_trend"] = w_trend
            df["wavelet_detail_1"] = w_d1
            df["wavelet_detail_2"] = w_d2

            # ── Calendar Features (cyclical encoding) ──
            if hasattr(df.index, 'hour'):
                hours = df.index.hour
                days = df.index.dayofweek
            else:
                # Use position-based proxy
                n = len(df)
                hours = pd.Series([(i % 24) for i in range(n)], index=df.index)
                days = pd.Series([(i // 24) % 7 for i in range(n)], index=df.index)

            df["hour_sin"] = np.sin(2 * np.pi * hours / 24)
            df["hour_cos"] = np.cos(2 * np.pi * hours / 24)
            df["day_of_week_sin"] = np.sin(2 * np.pi * days / 7)
            df["day_of_week_cos"] = np.cos(2 * np.pi * days / 7)

            # ── Hash Ribbon (from hash rate if available) ──
            # Will be computed if hash_rate column exists (added by jobs.py)
            if "hash_rate_col" in df.columns:
                hr = df["hash_rate_col"]
                hr_30d = hr.rolling(30 * 24, min_periods=24).mean()
                hr_60d = hr.rolling(60 * 24, min_periods=24).mean()
                df["hash_ribbon"] = (hr_30d > hr_60d).astype(int) * 2 - 1  # 1=bullish, -1=capitulation
            else:
                df["hash_ribbon"] = 0.0

            # ── Cross-feature Interactions ──
            # RSI-MACD divergence: RSI trending up while MACD trending down (or vice versa)
            rsi_slope = df.get("rsi", pd.Series(50, index=df.index)).diff(5)
            macd_slope = df.get("macd_hist", pd.Series(0, index=df.index)).diff(5)
            df["rsi_macd_divergence"] = (rsi_slope * macd_slope < 0).astype(int)

            # Volume-Price Trend
            df["volume_price_trend"] = (volume * returns).cumsum().fillna(0)

            # ATR ratio (short vs long term volatility)
            atr_14 = df.get("atr", TechnicalFeatures._atr(df, 14))
            atr_50 = TechnicalFeatures._atr(df, 50)
            df["atr_ratio_50_14"] = (atr_14 / atr_50.replace(0, np.nan)).fillna(1.0)

            # Fill NaN
            for col in TechnicalFeatures.ADVANCED_COLS:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
                else:
                    df[col] = 0.0

        except Exception as e:
            logger.error(f"Error computing advanced indicators: {e}")
            for col in TechnicalFeatures.ADVANCED_COLS:
                if col not in df.columns:
                    df[col] = 0.0

        return df

    @staticmethod
    def _rolling_hurst(series: pd.Series, window: int = 100) -> pd.Series:
        """Compute rolling Hurst exponent via R/S analysis."""
        def hurst(ts):
            if len(ts) < 20:
                return 0.5
            try:
                ts = np.array(ts, dtype=float)
                ts = ts[~np.isnan(ts)]
                if len(ts) < 20:
                    return 0.5
                lags = range(2, min(len(ts) // 2, 20))
                tau = []
                for lag in lags:
                    chunks = [ts[i:i + lag] for i in range(0, len(ts) - lag, lag)]
                    rs_values = []
                    for chunk in chunks:
                        if len(chunk) < 2:
                            continue
                        mean_c = np.mean(chunk)
                        cumdev = np.cumsum(chunk - mean_c)
                        r = np.max(cumdev) - np.min(cumdev)
                        s = np.std(chunk, ddof=1)
                        if s > 0:
                            rs_values.append(r / s)
                    if rs_values:
                        tau.append(np.mean(rs_values))
                    else:
                        tau.append(0)

                valid = [(l, t) for l, t in zip(lags, tau) if t > 0]
                if len(valid) < 3:
                    return 0.5
                log_lags = np.log([v[0] for v in valid])
                log_tau = np.log([v[1] for v in valid])
                h = np.polyfit(log_lags, log_tau, 1)[0]
                return float(np.clip(h, 0.0, 1.0))
            except Exception:
                return 0.5

        return series.rolling(window, min_periods=30).apply(hurst, raw=True).fillna(0.5)

    @staticmethod
    def _garch_volatility(returns: pd.Series) -> tuple[pd.Series, pd.Series]:
        """Compute GARCH(1,1) volatility forecast and volatility risk premium."""
        garch_vol = pd.Series(0.0, index=returns.index)
        vol_premium = pd.Series(0.0, index=returns.index)

        if not ARCH_AVAILABLE:
            return garch_vol, vol_premium

        try:
            # Use last 200 returns for GARCH estimation
            clean_returns = returns.dropna() * 100  # Scale to percentage
            if len(clean_returns) < 100:
                return garch_vol, vol_premium

            recent = clean_returns.iloc[-200:]
            am = arch_model(recent, vol="Garch", p=1, q=1, mean="Zero", rescale=False)
            res = am.fit(disp="off", show_warning=False)

            # One-step-ahead forecast
            forecast = res.forecast(horizon=1)
            cond_var = res.conditional_volatility

            # Fill in the conditional volatility for the fitted period
            garch_vol.iloc[-len(cond_var):] = cond_var.values / 100  # Back to decimal

            # Volatility risk premium: GARCH forecast vs realized vol
            realized = returns.rolling(24).std().fillna(0)
            vol_premium = garch_vol - realized

        except Exception as e:
            logger.debug(f"GARCH estimation error: {e}")

        return garch_vol.fillna(0), vol_premium.fillna(0)

    @staticmethod
    def _wavelet_features(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Decompose price into wavelet components (trend + details)."""
        trend = pd.Series(0.0, index=series.index)
        detail_1 = pd.Series(0.0, index=series.index)
        detail_2 = pd.Series(0.0, index=series.index)

        if not PYWT_AVAILABLE:
            return trend, detail_1, detail_2

        try:
            data = series.dropna().values
            if len(data) < 16:
                return trend, detail_1, detail_2

            # Ensure power-of-2 length for clean decomposition
            n = len(data)
            coeffs = pywt.wavedec(data, 'db4', level=2)
            # coeffs = [cA2, cD2, cD1]

            # Reconstruct approximation (trend) and details
            cA2 = coeffs[0]
            cD2 = coeffs[1]
            cD1 = coeffs[2]

            # Reconstruct each component to original length
            trend_arr = pywt.upcoef('a', cA2, 'db4', level=2, take=n)
            d1_arr = pywt.upcoef('d', cD1, 'db4', level=1, take=n)
            d2_arr = pywt.upcoef('d', cD2, 'db4', level=2, take=n)

            # Normalize by price to get relative features
            price_mean = np.mean(data)
            if price_mean > 0:
                trend.iloc[-n:] = trend_arr / price_mean
                detail_1.iloc[-n:] = d1_arr / price_mean
                detail_2.iloc[-n:] = d2_arr / price_mean

        except Exception as e:
            logger.debug(f"Wavelet decomposition error: {e}")

        return trend.fillna(0), detail_1.fillna(0), detail_2.fillna(0)
