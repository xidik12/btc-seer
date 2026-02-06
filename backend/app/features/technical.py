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

        return df

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
