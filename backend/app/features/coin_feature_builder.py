"""Feature builder for altcoin prediction pipeline.

Fetches OHLCV data from CoinOHLCV, computes technical indicators via
TechnicalFeatures, adds BTC correlation metrics and sentiment features,
and returns a flat feature dictionary ready for CoinEnsemblePredictor.
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select, desc

from app.database import async_session, CoinOHLCV, CoinSentiment
from app.features.technical import TechnicalFeatures

logger = logging.getLogger(__name__)

# Minimum rows required to compute meaningful technical indicators
MIN_ROWS = 50


class CoinFeatureBuilder:
    """Builds a feature vector for a single altcoin.

    Features include:
      - ~100+ technical indicators from TechnicalFeatures.calculate_all()
      - 4 BTC correlation features (24h corr, 7d corr, beta, relative strength)
      - 4 sentiment features (news_sentiment_1h, news_sentiment_24h,
        social_sentiment, news_volume)
    """

    async def build_features(self, coin_id: str) -> dict | None:
        """Build the complete feature dict for *coin_id*.

        Returns None when there is insufficient OHLCV data (< MIN_ROWS rows).
        """
        try:
            # 1. Fetch coin OHLCV
            coin_df = await self._fetch_ohlcv(coin_id, limit=200)
            if coin_df is None or len(coin_df) < MIN_ROWS:
                logger.debug(
                    f"[CoinFeatureBuilder] Insufficient data for {coin_id}: "
                    f"{0 if coin_df is None else len(coin_df)} rows"
                )
                return None

            # 2. Technical indicators
            tech_df = TechnicalFeatures.calculate_all(coin_df)
            latest = tech_df.iloc[-1]
            features: dict = {}
            for col in tech_df.columns:
                if col in ("timestamp",):
                    continue
                val = latest.get(col)
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    features[col] = float(val)
                else:
                    features[col] = 0.0

            # 3. BTC correlation features
            btc_corr = await self._compute_btc_correlation(coin_df)
            features.update(btc_corr)

            # 4. Sentiment features
            sentiment = await self._fetch_sentiment(coin_id)
            features.update(sentiment)

            return features

        except Exception as e:
            logger.error(
                f"[CoinFeatureBuilder] Error building features for {coin_id}: {e}",
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _fetch_ohlcv(coin_id: str, limit: int = 200) -> pd.DataFrame | None:
        """Fetch the last *limit* 1h candles for *coin_id* from CoinOHLCV."""
        async with async_session() as session:
            result = await session.execute(
                select(CoinOHLCV)
                .where(CoinOHLCV.coin_id == coin_id, CoinOHLCV.interval == "1h")
                .order_by(desc(CoinOHLCV.timestamp))
                .limit(limit)
            )
            rows = result.scalars().all()

        if not rows:
            return None

        # Oldest-first for indicator computation
        rows = list(reversed(rows))

        df = pd.DataFrame(
            [
                {
                    "timestamp": r.timestamp,
                    "open": float(r.open),
                    "high": float(r.high),
                    "low": float(r.low),
                    "close": float(r.close),
                    "volume": float(r.volume),
                }
                for r in rows
            ]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        return df

    async def _compute_btc_correlation(self, coin_df: pd.DataFrame) -> dict:
        """Compute BTC correlation, beta, and relative-strength features.

        Returns a dict with keys:
          btc_corr_24h, btc_corr_7d, btc_beta, btc_relative_strength
        """
        defaults = {
            "btc_corr_24h": 0.0,
            "btc_corr_7d": 0.0,
            "btc_beta": 1.0,
            "btc_relative_strength": 1.0,
        }

        try:
            btc_df = await self._fetch_ohlcv("bitcoin", limit=200)
            if btc_df is None or len(btc_df) < MIN_ROWS:
                return defaults

            # Align on overlapping timestamps
            coin_close = coin_df["close"].copy()
            btc_close = btc_df["close"].copy()

            # Align to common index
            common = coin_close.index.intersection(btc_close.index)
            if len(common) < 24:
                return defaults

            coin_aligned = coin_close.loc[common].sort_index()
            btc_aligned = btc_close.loc[common].sort_index()

            # Returns
            coin_ret = coin_aligned.pct_change().dropna()
            btc_ret = btc_aligned.pct_change().dropna()

            # Re-align after dropna
            common_ret = coin_ret.index.intersection(btc_ret.index)
            coin_ret = coin_ret.loc[common_ret]
            btc_ret = btc_ret.loc[common_ret]

            # 24h correlation (last 24 data points)
            if len(coin_ret) >= 24:
                corr_24 = coin_ret.iloc[-24:].corr(btc_ret.iloc[-24:])
                defaults["btc_corr_24h"] = 0.0 if np.isnan(corr_24) else float(corr_24)

            # 7d correlation (last 168 data points)
            window_7d = min(168, len(coin_ret))
            if window_7d >= 24:
                corr_7d = coin_ret.iloc[-window_7d:].corr(btc_ret.iloc[-window_7d:])
                defaults["btc_corr_7d"] = 0.0 if np.isnan(corr_7d) else float(corr_7d)

            # Beta: cov(coin, btc) / var(btc)
            btc_var = btc_ret.var()
            if btc_var and btc_var > 0:
                beta = coin_ret.cov(btc_ret) / btc_var
                defaults["btc_beta"] = 0.0 if np.isnan(beta) else float(beta)

            # Relative strength: coin 24h % change / btc 24h % change
            if len(coin_aligned) >= 24 and len(btc_aligned) >= 24:
                coin_chg = (coin_aligned.iloc[-1] / coin_aligned.iloc[-24] - 1) * 100
                btc_chg = (btc_aligned.iloc[-1] / btc_aligned.iloc[-24] - 1) * 100
                if abs(btc_chg) > 0.001:
                    rs = coin_chg / btc_chg
                    defaults["btc_relative_strength"] = (
                        0.0 if np.isnan(rs) else float(np.clip(rs, -10.0, 10.0))
                    )

        except Exception as e:
            logger.warning(f"[CoinFeatureBuilder] BTC correlation error: {e}")

        return defaults

    @staticmethod
    async def _fetch_sentiment(coin_id: str) -> dict:
        """Fetch the most recent sentiment row for *coin_id*.

        Returns a dict with keys:
          news_sentiment_1h, news_sentiment_24h, social_sentiment, news_volume
        """
        defaults = {
            "news_sentiment_1h": 0.0,
            "news_sentiment_24h": 0.0,
            "social_sentiment": 0.0,
            "news_volume": 0,
        }

        try:
            async with async_session() as session:
                # Get sentiment from last 1 hour
                cutoff_1h = datetime.utcnow() - timedelta(hours=1)
                result_1h = await session.execute(
                    select(CoinSentiment)
                    .where(
                        CoinSentiment.coin_id == coin_id,
                        CoinSentiment.timestamp >= cutoff_1h,
                    )
                    .order_by(desc(CoinSentiment.timestamp))
                    .limit(1)
                )
                sent_1h = result_1h.scalar_one_or_none()

                # Get sentiment from last 24 hours
                cutoff_24h = datetime.utcnow() - timedelta(hours=24)
                result_24h = await session.execute(
                    select(CoinSentiment)
                    .where(
                        CoinSentiment.coin_id == coin_id,
                        CoinSentiment.timestamp >= cutoff_24h,
                    )
                    .order_by(desc(CoinSentiment.timestamp))
                    .limit(1)
                )
                sent_24h = result_24h.scalar_one_or_none()

            if sent_1h:
                defaults["news_sentiment_1h"] = float(sent_1h.news_sentiment_avg or 0)
                defaults["social_sentiment"] = float(sent_1h.social_sentiment_avg or 0)
                defaults["news_volume"] = int(sent_1h.news_volume or 0)

            if sent_24h:
                defaults["news_sentiment_24h"] = float(sent_24h.news_sentiment_avg or 0)

        except Exception as e:
            logger.warning(f"[CoinFeatureBuilder] Sentiment fetch error for {coin_id}: {e}")

        return defaults
