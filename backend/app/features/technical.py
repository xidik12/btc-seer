import logging

import numpy as np
import pandas as pd

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
