import logging

import numpy as np
import pandas as pd

import ta as ta_lib

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
    """Calculates technical indicators from OHLCV price data.

    Performance-optimised:
    - New columns collected in dicts, bulk-concatenated (eliminates DataFrame fragmentation)
    - Vectorised numpy/pandas ops replace Python loops and slow rolling applies
    - Intermediate results (ATR, returns) computed once and reused
    """

    EXTENDED_COLS = [
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

    ADVANCED_COLS = [
        "kama_10", "t3_10", "dema_21",
        "trix_14", "bop", "psar", "psar_dir",
        "candle_three_white", "candle_three_black", "candle_dark_cloud",
        "candle_piercing", "candle_harami", "candle_kicking", "candle_three_line_strike",
        "typical_price", "weighted_close", "median_price",
        "return_1h", "return_skew_24", "return_kurtosis_24",
        "return_autocorr_1", "return_autocorr_6", "return_autocorr_24",
        "hurst_exponent",
        "garch_vol_forecast", "vol_risk_premium",
        "wavelet_trend", "wavelet_detail_1", "wavelet_detail_2",
        "hour_sin", "hour_cos", "day_of_week_sin", "day_of_week_cos",
        "hash_ribbon",
        "rsi_macd_divergence", "volume_price_trend", "atr_ratio_50_14",
    ]

    # ─────────────────────────────────────────────────────────
    #  MAIN ENTRY POINT
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators. Expects columns: open, high, low, close, volume."""
        df = df.copy()
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        open_ = df["open"]

        cols = {}

        # ── Moving Averages ──
        for p in (9, 21, 50, 200):
            cols[f"ema_{p}"] = close.ewm(span=p, adjust=False).mean()
        sma_20 = close.rolling(20).mean()
        cols["sma_20"] = sma_20

        # ── RSI ──
        rsi_14 = TechnicalFeatures._rsi(close, 14)
        cols["rsi"] = rsi_14

        # ── MACD ──
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - macd_signal
        cols["macd"] = macd
        cols["macd_signal"] = macd_signal
        cols["macd_hist"] = macd_hist

        # ── Bollinger Bands ──
        bb_std = close.rolling(20).std()
        bb_upper = sma_20 + 2 * bb_std
        bb_lower = sma_20 - 2 * bb_std
        cols["bb_middle"] = sma_20
        cols["bb_upper"] = bb_upper
        cols["bb_lower"] = bb_lower
        cols["bb_width"] = (bb_upper - bb_lower) / sma_20
        cols["bb_position"] = (close - bb_lower) / (bb_upper - bb_lower)

        # ── ATR (cached for reuse) ──
        atr_14 = TechnicalFeatures._atr(high, low, close, 14)
        cols["atr"] = atr_14

        # ── OBV (vectorised) ──
        direction = np.sign(close.diff())
        cols["obv"] = (direction * volume).fillna(0).cumsum()

        # ── VWAP ──
        cols["vwap"] = (close * volume).cumsum() / volume.cumsum()

        # ── Rate of Change ──
        for p in (1, 6, 12, 24):
            cols[f"roc_{p}"] = close.pct_change(p) * 100

        # ── Momentum ──
        cols["momentum_10"] = close - close.shift(10)
        cols["momentum_20"] = close - close.shift(20)

        # ── Volume features ──
        vol_sma = volume.rolling(20).mean()
        cols["volume_sma_20"] = vol_sma
        cols["volume_ratio"] = volume / vol_sma

        # ── Price vs EMAs ──
        for p in (9, 21, 50):
            ema = cols[f"ema_{p}"]
            cols[f"price_vs_ema{p}"] = (close - ema) / ema * 100

        # ── Volatility ──
        cols["volatility_24h"] = close.rolling(24).std() / close.rolling(24).mean() * 100

        # ── Pivot Points ──
        pivot = (high + low + close) / 3
        cols["pivot"] = pivot
        cols["support_1"] = 2 * pivot - high
        cols["resistance_1"] = 2 * pivot - low

        # ── Candle Metrics (numpy-fast) ──
        co_max = np.maximum(close, open_)
        co_min = np.minimum(close, open_)
        body_size = (close - open_).abs() / open_ * 100
        cols["body_size"] = body_size
        cols["upper_shadow"] = (high - co_max) / open_ * 100
        cols["lower_shadow"] = (co_min - low) / open_ * 100

        # ── Extended SMAs ──
        cols["sma_111"] = close.rolling(111, min_periods=50).mean()
        sma_200 = close.rolling(200, min_periods=100).mean()
        cols["sma_200"] = sma_200
        sma_350 = close.rolling(350, min_periods=150).mean()
        cols["sma_350"] = sma_350

        # ── Multi-timeframe RSI ──
        cols["rsi_7"] = TechnicalFeatures._rsi(close, 7)
        cols["rsi_30"] = TechnicalFeatures._rsi(close, 30)

        # ── ADX (inlined, reuses atr_14) ──
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        plus_di_base = 100 * (plus_dm.rolling(14).mean() / atr_14)
        minus_di_base = 100 * (minus_dm.rolling(14).mean() / atr_14)
        dx = 100 * (plus_di_base - minus_di_base).abs() / (plus_di_base + minus_di_base)
        cols["adx"] = dx.rolling(14).mean()

        # ── Extra momentum ──
        cols["momentum_30"] = close - close.shift(30)

        # ── Derived ratios ──
        cols["mayer_multiple"] = close / sma_200
        cols["pi_cycle_ratio"] = cols["sma_111"] / (sma_350 * 2)
        cols["ema_cross"] = cols["ema_50"] / cols["ema_200"]
        cols["zscore_20"] = (close - sma_20) / close.rolling(20).std()

        # ── Stochastic RSI ──
        rsi_min = rsi_14.rolling(14).min()
        rsi_max = rsi_14.rolling(14).max()
        stoch_rsi_k = ((rsi_14 - rsi_min) / (rsi_max - rsi_min)) * 100
        stoch_rsi_k = stoch_rsi_k.rolling(3).mean()
        cols["stoch_rsi_k"] = stoch_rsi_k
        cols["stoch_rsi_d"] = stoch_rsi_k.rolling(3).mean()

        # ── Williams %R ──
        high_14 = high.rolling(14).max()
        low_14 = low.rolling(14).min()
        cols["williams_r"] = ((high_14 - close) / (high_14 - low_14)) * -100

        # ── Ichimoku ──
        high_9 = high.rolling(9).max()
        low_9 = low.rolling(9).min()
        tenkan = (high_9 + low_9) / 2
        cols["ichimoku_tenkan"] = tenkan
        high_26 = high.rolling(26).max()
        low_26 = low.rolling(26).min()
        kijun = (high_26 + low_26) / 2
        cols["ichimoku_kijun"] = kijun
        cols["ichimoku_senkou_a"] = ((tenkan + kijun) / 2).shift(26)
        high_52 = high.rolling(52).max()
        low_52 = low.rolling(52).min()
        cols["ichimoku_senkou_b"] = ((high_52 + low_52) / 2).shift(26)
        cols["ichimoku_chikou"] = close.shift(-26)

        # ── Candlestick Patterns ──
        cols["candle_doji"] = (body_size < 0.1).astype(int)

        body = close - open_
        body_abs = body.abs()
        lower = co_min - low
        upper = high - co_max

        cols["candle_hammer"] = ((lower > body_abs * 2) & (upper < body_abs * 0.5) & (body_abs > 0)).astype(int)
        cols["candle_inverted_hammer"] = ((upper > body_abs * 2) & (lower < body_abs * 0.5) & (body_abs > 0)).astype(int)

        prev_body = body.shift(1)
        cols["candle_bullish_engulfing"] = (
            (prev_body < 0) & (body > 0) &
            (open_ <= close.shift(1)) & (close >= open_.shift(1))
        ).astype(int)
        cols["candle_bearish_engulfing"] = (
            (prev_body > 0) & (body < 0) &
            (open_ >= close.shift(1)) & (close <= open_.shift(1))
        ).astype(int)

        body_2ago = body.shift(2)
        body_1ago = prev_body
        cols["candle_morning_star"] = (
            (body_2ago < 0) &
            (body_1ago.abs() < body_2ago.abs() * 0.3) &
            (body > 0) &
            (close > (open_.shift(2) + close.shift(2)) / 2)
        ).astype(int)
        cols["candle_evening_star"] = (
            (body_2ago > 0) &
            (body_1ago.abs() < body_2ago.abs() * 0.3) &
            (body < 0) &
            (close < (open_.shift(2) + close.shift(2)) / 2)
        ).astype(int)

        # ── Trend (vectorised slope) ──
        cols["trend_short"] = TechnicalFeatures._classify_trend(close, 20)
        cols["trend_medium"] = TechnicalFeatures._classify_trend(close, 50)
        cols["trend_long"] = TechnicalFeatures._classify_trend(close, 100)

        # ── Fill NaN for base cols ──
        for key in cols:
            v = cols[key]
            if isinstance(v, pd.Series):
                cols[key] = v.fillna(0.0)

        # Bulk concat — single allocation instead of 80+ individual inserts
        df = pd.concat([df, pd.DataFrame(cols, index=df.index)], axis=1)

        # Extended indicators (ta library)
        df = TechnicalFeatures.calculate_pandas_ta_indicators(df)

        # Advanced quantitative indicators
        df = TechnicalFeatures.calculate_advanced_indicators(df)

        return df

    # ─────────────────────────────────────────────────────────
    #  EXTENDED INDICATORS (ta library + numpy)
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def calculate_pandas_ta_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Compute ~45 extended indicators using ta library + pandas/numpy."""
        cols = {}
        try:
            high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]

            # ── Momentum (14) ──
            midpoint = (high + low) / 2
            cols["ao"] = midpoint.rolling(5).mean() - midpoint.rolling(34).mean()

            cols["cci_20"] = ta_lib.trend.cci(high, low, close, window=20)

            # CMO (Chande Momentum Oscillator)
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0).rolling(14).sum()
            loss = (-delta.where(delta < 0, 0.0)).rolling(14).sum()
            cols["cmo_14"] = 100 * (gain - loss) / (gain + loss)

            # Fisher Transform
            hl2 = midpoint
            max_h = hl2.rolling(9).max()
            min_l = hl2.rolling(9).min()
            raw = 2 * ((hl2 - min_l) / (max_h - min_l).replace(0, np.nan) - 0.5)
            raw = raw.clip(-0.999, 0.999).fillna(0)
            fisher_val = 0.5 * np.log((1 + raw) / (1 - raw))
            cols["fisher_9"] = fisher_val
            cols["fisher_signal"] = fisher_val.shift(1)

            # KST (Know Sure Thing)
            roc10 = close.pct_change(10) * 100
            roc15 = close.pct_change(15) * 100
            roc20 = close.pct_change(20) * 100
            roc30 = close.pct_change(30) * 100
            kst_val = (roc10.rolling(10).mean() * 1
                       + roc15.rolling(10).mean() * 2
                       + roc20.rolling(10).mean() * 3
                       + roc30.rolling(15).mean() * 4)
            cols["kst"] = kst_val
            cols["kst_signal"] = kst_val.rolling(9).mean()

            # PPO (Percentage Price Oscillator)
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            ppo_val = (ema12 - ema26) / ema26 * 100
            ppo_sig = ppo_val.ewm(span=9, adjust=False).mean()
            cols["ppo"] = ppo_val
            cols["ppo_signal"] = ppo_sig
            cols["ppo_hist"] = ppo_val - ppo_sig

            # Stochastic Oscillator
            stoch_ind = ta_lib.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
            cols["stoch_k"] = stoch_ind.stoch()
            cols["stoch_d"] = stoch_ind.stoch_signal()

            # TSI
            cols["tsi"] = ta_lib.momentum.TSIIndicator(close, window_slow=25, window_fast=13).tsi()

            # Ultimate Oscillator
            cols["uo"] = ta_lib.momentum.UltimateOscillator(high, low, close).ultimate_oscillator()

            # ── Trend (8) ──
            aroon_ind = ta_lib.trend.AroonIndicator(high, low, window=25)
            cols["aroon_osc"] = aroon_ind.aroon_indicator()

            # Choppiness Index (reuse cached ATR)
            atr_14 = df["atr"] if "atr" in df.columns else TechnicalFeatures._atr(high, low, close, 14)
            atr_sum = atr_14.rolling(14).sum()
            hh = high.rolling(14).max()
            ll = low.rolling(14).min()
            cols["chop_14"] = 100 * np.log10(atr_sum / (hh - ll).replace(0, np.nan)) / np.log10(14)

            # DPO
            cols["dpo_20"] = ta_lib.trend.DPOIndicator(close, window=20).dpo()

            # Supertrend (numpy loop — inherently sequential, but pure-scalar fast)
            atr_7 = TechnicalFeatures._atr(high, low, close, 7)
            hl_avg = (high + low) / 2
            ub = (hl_avg + 3.0 * atr_7).values
            lb = (hl_avg - 3.0 * atr_7).values
            c = close.values
            n = len(c)
            st_arr = np.zeros(n, dtype=np.int8)
            for i in range(1, n):
                if c[i] > ub[i - 1]:
                    st_arr[i] = -1
                elif c[i] < lb[i - 1]:
                    st_arr[i] = 1
                else:
                    st_arr[i] = st_arr[i - 1]
            cols["supertrend_dir"] = pd.Series(st_arr, index=df.index)

            # Vortex
            vortex_ind = ta_lib.trend.VortexIndicator(high, low, close, window=14)
            cols["vortex_diff"] = vortex_ind.vortex_indicator_pos() - vortex_ind.vortex_indicator_neg()

            # Mass Index
            cols["mass_index"] = ta_lib.trend.MassIndex(high, low).mass_index()

            # Plus/Minus DI
            adx_ind = ta_lib.trend.ADXIndicator(high, low, close, window=14)
            cols["plus_di"] = adx_ind.adx_pos()
            cols["minus_di"] = adx_ind.adx_neg()

            # ── Volatility (9) ──
            dc_ind = ta_lib.volatility.DonchianChannel(high, low, close, window=20)
            dc_upper = dc_ind.donchian_channel_hband()
            dc_lower = dc_ind.donchian_channel_lband()
            dc_mid = dc_ind.donchian_channel_mband()
            cols["donchian_upper"] = dc_upper
            cols["donchian_lower"] = dc_lower
            cols["donchian_mid"] = dc_mid
            cols["donchian_width"] = (dc_upper - dc_lower) / dc_mid.replace(0, np.nan)

            kc_ind = ta_lib.volatility.KeltnerChannel(high, low, close, window=20, window_atr=20)
            kc_upper = kc_ind.keltner_channel_hband()
            kc_lower = kc_ind.keltner_channel_lband()
            kc_range = kc_upper - kc_lower
            cols["kc_upper"] = kc_upper
            cols["kc_lower"] = kc_lower
            cols["kc_position"] = ((close - kc_lower) / kc_range.replace(0, np.nan)).fillna(0.5)

            cols["natr"] = (atr_14 / close) * 100
            cols["ui"] = ta_lib.volatility.UlcerIndex(close, window=14).ulcer_index()

            # ── Volume (6) ──
            cols["ad"] = ta_lib.volume.AccDistIndexIndicator(high, low, close, volume).acc_dist_index()
            cols["cmf"] = ta_lib.volume.ChaikinMoneyFlowIndicator(high, low, close, volume, window=20).chaikin_money_flow()
            cols["efi_13"] = ta_lib.volume.ForceIndexIndicator(close, volume, window=13).force_index()
            cols["mfi"] = ta_lib.volume.MFIIndicator(high, low, close, volume, window=14).money_flow_index()
            cols["nvi"] = ta_lib.volume.NegativeVolumeIndexIndicator(close, volume).negative_volume_index()

            # PVI (vectorised with cumprod)
            c_arr = close.values.astype(float)
            v_arr = volume.values.astype(float)
            ret = np.zeros(len(c_arr) - 1)
            nz = c_arr[:-1] != 0
            ret[nz] = np.diff(c_arr)[nz] / c_arr[:-1][nz]
            vol_up = v_arr[1:] > v_arr[:-1]
            factors = np.where(vol_up, 1 + ret, 1.0)
            pvi_arr = np.empty(len(c_arr))
            pvi_arr[0] = 1000.0
            pvi_arr[1:] = 1000.0 * np.cumprod(factors)
            cols["pvi"] = pd.Series(pvi_arr, index=df.index)

            # ── Statistics (8) ──
            pct = close.pct_change()

            def _entropy(x):
                s = x.sum()
                if s <= 0:
                    return 0.0
                p = x / s
                return float(-np.sum(p * np.log(p + 1e-10)))

            cols["entropy_10"] = pct.abs().rolling(10).apply(_entropy, raw=True)
            cols["kurtosis_20"] = pct.rolling(20).kurt()
            cols["skew_20"] = pct.rolling(20).skew()
            cols["variance_20"] = pct.rolling(20).var()

            mean_14 = close.rolling(14).mean()
            std_14 = close.rolling(14).std()
            cols["zscore_14"] = (close - mean_14) / std_14.replace(0, np.nan)
            cols["stdev_20"] = close.rolling(20).std()

            # Linreg slope and R² (vectorised convolution)
            slope, r2 = TechnicalFeatures._rolling_slope_r2(close, 20)
            cols["linreg_slope"] = slope
            cols["linreg_r2"] = r2

        except Exception as e:
            logger.error(f"Error computing extended indicators: {e}")

        # Fill NaN / ensure all expected columns exist
        for col in TechnicalFeatures.EXTENDED_COLS:
            if col in cols:
                v = cols[col]
                cols[col] = v.fillna(0.0) if isinstance(v, pd.Series) else v
            else:
                cols[col] = 0.0

        return pd.concat([df, pd.DataFrame(cols, index=df.index)], axis=1)

    # ─────────────────────────────────────────────────────────
    #  ADVANCED QUANTITATIVE INDICATORS
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def calculate_advanced_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Compute advanced quantitative indicators."""
        cols = {}
        try:
            close = df["close"]
            high = df["high"]
            low = df["low"]
            volume = df["volume"]
            open_ = df["open"]
            returns = close.pct_change()

            # ── Adaptive Moving Averages ──
            cols["kama_10"] = ta_lib.momentum.KAMAIndicator(close, window=10).kama()

            ema1 = close.ewm(span=10, adjust=False).mean()
            ema2 = ema1.ewm(span=10, adjust=False).mean()
            ema3 = ema2.ewm(span=10, adjust=False).mean()
            cols["t3_10"] = 3 * ema1 - 3 * ema2 + ema3

            ema_21 = close.ewm(span=21, adjust=False).mean()
            cols["dema_21"] = 2 * ema_21 - ema_21.ewm(span=21, adjust=False).mean()

            # ── Additional Momentum ──
            ema_t1 = close.ewm(span=14, adjust=False).mean()
            ema_t2 = ema_t1.ewm(span=14, adjust=False).mean()
            ema_t3 = ema_t2.ewm(span=14, adjust=False).mean()
            cols["trix_14"] = ema_t3.pct_change() * 100

            psar_ind = ta_lib.trend.PSARIndicator(high, low, close)
            psar_up = psar_ind.psar_up()
            psar_down = psar_ind.psar_down()
            cols["psar"] = psar_up.fillna(psar_down)
            cols["psar_dir"] = psar_up.notna().astype(int) * 2 - 1

            range_ = high - low
            cols["bop"] = ((close - open_) / range_.replace(0, np.nan)).fillna(0)

            # ── Additional Candlestick Patterns ──
            body = close - open_
            prev_body = body.shift(1)
            prev2_body = body.shift(2)

            cols["candle_three_white"] = (
                (body > 0) & (prev_body > 0) & (prev2_body > 0) &
                (close > close.shift(1)) & (close.shift(1) > close.shift(2))
            ).astype(int)
            cols["candle_three_black"] = (
                (body < 0) & (prev_body < 0) & (prev2_body < 0) &
                (close < close.shift(1)) & (close.shift(1) < close.shift(2))
            ).astype(int)
            cols["candle_dark_cloud"] = (
                (prev_body > 0) & (body < 0) &
                (open_ > close.shift(1)) &
                (close < (open_.shift(1) + close.shift(1)) / 2)
            ).astype(int)
            cols["candle_piercing"] = (
                (prev_body < 0) & (body > 0) &
                (open_ < close.shift(1)) &
                (close > (open_.shift(1) + close.shift(1)) / 2)
            ).astype(int)
            cols["candle_harami"] = (
                (body.abs() < prev_body.abs() * 0.5) &
                (close.clip(upper=open_).clip(lower=open_) <= close.shift(1).clip(upper=open_.shift(1))) &
                (body.abs() > 0)
            ).astype(int)
            cols["candle_kicking"] = (
                ((prev_body < 0) & (body > 0) & (open_ > open_.shift(1))) |
                ((prev_body > 0) & (body < 0) & (open_ < open_.shift(1)))
            ).astype(int)
            cols["candle_three_line_strike"] = (
                (prev2_body > 0) & (prev_body > 0) & (body < 0) &
                (close < open_.shift(2))
            ).astype(int)

            # ── Price Transforms ──
            cols["typical_price"] = (high + low + close) / 3
            cols["weighted_close"] = (high + low + 2 * close) / 4
            cols["median_price"] = (high + low) / 2

            # ── Return-based Statistics ──
            cols["return_1h"] = returns.fillna(0)
            cols["return_skew_24"] = returns.rolling(24).skew().fillna(0)
            cols["return_kurtosis_24"] = returns.rolling(24).kurt().fillna(0)

            # Autocorrelation (vectorised — native rolling.corr instead of slow apply)
            cols["return_autocorr_1"] = returns.rolling(48).corr(returns.shift(1)).fillna(0)
            cols["return_autocorr_6"] = returns.rolling(48).corr(returns.shift(6)).fillna(0)
            cols["return_autocorr_24"] = returns.rolling(72).corr(returns.shift(24)).fillna(0)

            # ── Hurst Exponent (fast: vectorised chunks + subsampling) ──
            cols["hurst_exponent"] = TechnicalFeatures._rolling_hurst(close, window=100)

            # ── GARCH Volatility Forecast ──
            garch_vol, vol_premium = TechnicalFeatures._garch_volatility(returns)
            cols["garch_vol_forecast"] = garch_vol
            cols["vol_risk_premium"] = vol_premium

            # ── Wavelet Decomposition ──
            w_trend, w_d1, w_d2 = TechnicalFeatures._wavelet_features(close)
            cols["wavelet_trend"] = w_trend
            cols["wavelet_detail_1"] = w_d1
            cols["wavelet_detail_2"] = w_d2

            # ── Calendar Features ──
            if hasattr(df.index, 'hour'):
                hours = df.index.hour
                days = df.index.dayofweek
            else:
                n = len(df)
                hours = np.arange(n) % 24
                days = (np.arange(n) // 24) % 7

            cols["hour_sin"] = pd.Series(np.sin(2 * np.pi * hours / 24), index=df.index)
            cols["hour_cos"] = pd.Series(np.cos(2 * np.pi * hours / 24), index=df.index)
            cols["day_of_week_sin"] = pd.Series(np.sin(2 * np.pi * days / 7), index=df.index)
            cols["day_of_week_cos"] = pd.Series(np.cos(2 * np.pi * days / 7), index=df.index)

            # ── Hash Ribbon ──
            if "hash_rate_col" in df.columns:
                hr = df["hash_rate_col"]
                hr_30d = hr.rolling(30 * 24, min_periods=24).mean()
                hr_60d = hr.rolling(60 * 24, min_periods=24).mean()
                cols["hash_ribbon"] = (hr_30d > hr_60d).astype(int) * 2 - 1
            else:
                cols["hash_ribbon"] = 0.0

            # ── Cross-feature Interactions ──
            rsi_slope = df.get("rsi", pd.Series(50, index=df.index)).diff(5)
            macd_slope = df.get("macd_hist", pd.Series(0, index=df.index)).diff(5)
            cols["rsi_macd_divergence"] = (rsi_slope * macd_slope < 0).astype(int)

            cols["volume_price_trend"] = (volume * returns).cumsum().fillna(0)

            atr_cached = df["atr"] if "atr" in df.columns else TechnicalFeatures._atr(high, low, close, 14)
            atr_50 = TechnicalFeatures._atr(high, low, close, 50)
            cols["atr_ratio_50_14"] = (atr_cached / atr_50.replace(0, np.nan)).fillna(1.0)

        except Exception as e:
            logger.error(f"Error computing advanced indicators: {e}")

        # Fill NaN / ensure all expected columns exist
        for col in TechnicalFeatures.ADVANCED_COLS:
            if col in cols:
                v = cols[col]
                cols[col] = v.fillna(0.0) if isinstance(v, pd.Series) else v
            else:
                cols[col] = 0.0

        return pd.concat([df, pd.DataFrame(cols, index=df.index)], axis=1)

    # ─────────────────────────────────────────────────────────
    #  VECTORISED HELPER METHODS
    # ─────────────────────────────────────────────────────────

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
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """ATR using numpy — avoids pd.concat for true range."""
        h, l, c = high.values, low.values, close.values
        prev_c = np.empty_like(c)
        prev_c[0] = c[0]
        prev_c[1:] = c[:-1]
        tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
        return pd.Series(tr, index=high.index).rolling(period).mean()

    @staticmethod
    def _classify_trend(series: pd.Series, period: int) -> pd.Series:
        """Classify trend using vectorised rolling slope (no polyfit apply)."""
        slope = TechnicalFeatures._rolling_slope(series, period)
        return np.sign(slope).fillna(0).astype(int)

    @staticmethod
    def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
        """Vectorised rolling linear regression slope via convolution.

        For x = [0, 1, ..., w-1]:
            slope = (mean(x*y) - mean(x)*mean(y)) / var(x)
        The x*y rolling sum is computed via np.convolve — O(n) with no Python loop.
        """
        y = np.nan_to_num(series.values.astype(float))
        n = len(y)
        w = window
        if n < w:
            return pd.Series(0.0, index=series.index)

        x_mean = (w - 1) / 2.0
        # var(x) = Σ(x-x̄)²/w = (w²-1)/12
        var_x = (w * w - 1) / 12.0

        # Rolling mean of y
        cum_y = np.cumsum(np.insert(y, 0, 0.0))
        y_mean = (cum_y[w:] - cum_y[:-w]) / w

        # Rolling weighted sum: Σ(k=0..w-1) k * y[j+k] via convolution
        kernel = np.arange(w, dtype=float)
        xy_mean = np.convolve(y, kernel[::-1], mode='valid') / w  # length n-w+1

        slope = (xy_mean - x_mean * y_mean) / var_x

        result = np.full(n, np.nan)
        result[w - 1:] = slope
        return pd.Series(result, index=series.index)

    @staticmethod
    def _rolling_slope_r2(series: pd.Series, window: int):
        """Vectorised rolling linear regression slope AND R² in one pass."""
        y = np.nan_to_num(series.values.astype(float))
        n = len(y)
        w = window
        if n < w:
            z = pd.Series(0.0, index=series.index)
            return z, z.copy()

        x_mean = (w - 1) / 2.0
        ss_xx = w * (w * w - 1) / 12.0  # Σ(x - x̄)²

        cum_y = np.cumsum(np.insert(y, 0, 0.0))
        sum_y = cum_y[w:] - cum_y[:-w]
        y_mean = sum_y / w

        cum_y2 = np.cumsum(np.insert(y ** 2, 0, 0.0))
        sum_y2 = cum_y2[w:] - cum_y2[:-w]

        kernel = np.arange(w, dtype=float)
        sum_xy = np.convolve(y, kernel[::-1], mode='valid')

        slope = (sum_xy / w - x_mean * y_mean) / (ss_xx / w)

        ss_yy = sum_y2 - sum_y ** 2 / w
        r2 = np.where(ss_yy > 1e-10, slope ** 2 * ss_xx / ss_yy, 0.0)
        r2 = np.clip(r2, 0.0, 1.0)

        slope_out = np.full(n, 0.0)
        slope_out[w - 1:] = slope
        r2_out = np.full(n, 0.0)
        r2_out[w - 1:] = r2

        return (pd.Series(slope_out, index=series.index),
                pd.Series(r2_out, index=series.index))

    @staticmethod
    def _rolling_hurst(series: pd.Series, window: int = 100) -> pd.Series:
        """Rolling Hurst exponent — vectorised R/S chunks, subsampled every 5 points."""
        values = series.values.astype(float)
        n = len(values)
        result = np.full(n, 0.5)
        step = 5  # compute every 5th point

        for i in range(window, n, step):
            ts = values[i - window:i]
            result[i] = TechnicalFeatures._fast_hurst(ts)

        # Forward-fill the gaps
        for i in range(window + 1, n):
            if i % step != (window % step):
                result[i] = result[i - 1]

        return pd.Series(result, index=series.index)

    @staticmethod
    def _fast_hurst(ts):
        """Fast Hurst via R/S analysis with vectorised chunk processing."""
        ts = ts[~np.isnan(ts)]
        n = len(ts)
        if n < 20:
            return 0.5

        max_lag = min(n // 2, 20)
        lags = np.arange(2, max_lag + 1)
        rs = np.zeros(len(lags))

        for idx, lag in enumerate(lags):
            n_chunks = n // lag
            if n_chunks == 0:
                continue
            # Reshape into chunks — fully vectorised within each lag
            chunks = ts[:n_chunks * lag].reshape(n_chunks, lag)
            means = chunks.mean(axis=1, keepdims=True)
            cumdev = np.cumsum(chunks - means, axis=1)
            R = cumdev.max(axis=1) - cumdev.min(axis=1)
            S = chunks.std(axis=1, ddof=1)
            valid = S > 0
            if valid.any():
                rs[idx] = np.mean(R[valid] / S[valid])

        valid_mask = rs > 0
        if valid_mask.sum() < 3:
            return 0.5

        h = np.polyfit(np.log(lags[valid_mask]), np.log(rs[valid_mask]), 1)[0]
        return float(np.clip(h, 0.0, 1.0))

    @staticmethod
    def _garch_volatility(returns: pd.Series) -> tuple:
        """GARCH(1,1) volatility forecast and risk premium."""
        garch_vol = pd.Series(0.0, index=returns.index)
        vol_premium = pd.Series(0.0, index=returns.index)

        if not ARCH_AVAILABLE:
            return garch_vol, vol_premium

        try:
            clean_returns = returns.dropna() * 100
            if len(clean_returns) < 100:
                return garch_vol, vol_premium

            recent = clean_returns.iloc[-200:]
            am = arch_model(recent, vol="Garch", p=1, q=1, mean="Zero", rescale=False)
            res = am.fit(disp="off", show_warning=False)

            forecast = res.forecast(horizon=1)
            cond_var = res.conditional_volatility
            garch_vol.iloc[-len(cond_var):] = cond_var.values / 100

            realized = returns.rolling(24).std().fillna(0)
            vol_premium = garch_vol - realized

        except Exception as e:
            logger.debug(f"GARCH estimation error: {e}")

        return garch_vol.fillna(0), vol_premium.fillna(0)

    @staticmethod
    def _wavelet_features(series: pd.Series) -> tuple:
        """Wavelet decomposition into trend + detail components."""
        trend = pd.Series(0.0, index=series.index)
        detail_1 = pd.Series(0.0, index=series.index)
        detail_2 = pd.Series(0.0, index=series.index)

        if not PYWT_AVAILABLE:
            return trend, detail_1, detail_2

        try:
            data = series.dropna().values
            if len(data) < 16:
                return trend, detail_1, detail_2

            n = len(data)
            coeffs = pywt.wavedec(data, 'db4', level=2)
            cA2, cD2, cD1 = coeffs[0], coeffs[1], coeffs[2]

            trend_arr = pywt.upcoef('a', cA2, 'db4', level=2, take=n)
            d1_arr = pywt.upcoef('d', cD1, 'db4', level=1, take=n)
            d2_arr = pywt.upcoef('d', cD2, 'db4', level=2, take=n)

            price_mean = np.mean(data)
            if price_mean > 0:
                trend.iloc[-n:] = trend_arr / price_mean
                detail_1.iloc[-n:] = d1_arr / price_mean
                detail_2.iloc[-n:] = d2_arr / price_mean

        except Exception as e:
            logger.debug(f"Wavelet decomposition error: {e}")

        return trend.fillna(0), detail_1.fillna(0), detail_2.fillna(0)
