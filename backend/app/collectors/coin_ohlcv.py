import asyncio
import logging
from datetime import datetime

from app.collectors.base import BaseCollector
from app.collectors.coins import TRACKED_COINS
from app.config import settings
from app.database import async_session, CoinOHLCV

logger = logging.getLogger(__name__)


class CoinOHLCVCollector(BaseCollector):
    """Fetches OHLCV kline data for all 20 tracked coins from Binance."""

    BINANCE_KLINES = "{base}/api/v3/klines"

    async def collect(self) -> dict:
        """Fetch latest 1h candle for all tracked coins."""
        results = []
        for coin in TRACKED_COINS:
            binance_sym = coin.get("binance_symbol")
            if not binance_sym:
                continue
            try:
                data = await self._fetch_kline(binance_sym)
                if data:
                    results.append({
                        "coin_id": coin["coin_id"],
                        "symbol": binance_sym,
                        **data,
                    })
            except Exception as e:
                logger.warning(f"OHLCV fetch failed for {binance_sym}: {e}")
            await asyncio.sleep(0.2)  # 200ms stagger to respect rate limits

        return {"candles": results, "count": len(results)}

    async def _fetch_kline(self, symbol: str) -> dict | None:
        """Fetch the latest completed 1h kline for a symbol."""
        url = self.BINANCE_KLINES.format(base=settings.binance_base_url)
        params = {
            "symbol": symbol,
            "interval": "1h",
            "limit": 2,  # current (incomplete) + previous (complete)
        }
        data = await self.fetch_json(url, params=params)
        if not data or len(data) < 2:
            return None

        # Use the second-to-last candle (most recently completed)
        k = data[-2]
        return {
            "timestamp": datetime.utcfromtimestamp(k[0] / 1000),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        }

    async def backfill(self, symbol: str, coin_id: str, limit: int = 200) -> list[dict]:
        """Backfill historical 1h klines for a single coin."""
        url = self.BINANCE_KLINES.format(base=settings.binance_base_url)
        params = {
            "symbol": symbol,
            "interval": "1h",
            "limit": limit,
        }
        data = await self.fetch_json(url, params=params)
        if not data:
            return []

        candles = []
        for k in data[:-1]:  # skip current incomplete candle
            candles.append({
                "coin_id": coin_id,
                "symbol": symbol,
                "timestamp": datetime.utcfromtimestamp(k[0] / 1000),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        return candles


async def collect_coin_ohlcv():
    """Scheduled job: collect 1h OHLCV candles for all 20 tracked coins."""
    collector = CoinOHLCVCollector()
    try:
        result = await collector.collect()
        candles = result.get("candles", [])
        if not candles:
            return

        async with async_session() as session:
            for c in candles:
                # Deduplicate by symbol+interval+timestamp
                from sqlalchemy import select
                existing = await session.execute(
                    select(CoinOHLCV.id).where(
                        CoinOHLCV.symbol == c["symbol"],
                        CoinOHLCV.interval == "1h",
                        CoinOHLCV.timestamp == c["timestamp"],
                    ).limit(1)
                )
                if existing.scalar_one_or_none() is not None:
                    continue

                session.add(CoinOHLCV(
                    coin_id=c["coin_id"],
                    symbol=c["symbol"],
                    interval="1h",
                    timestamp=c["timestamp"],
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c["volume"],
                    source="binance",
                ))
            await session.commit()
            logger.info(f"Collected OHLCV for {len(candles)} coins")
    except Exception as e:
        logger.error(f"collect_coin_ohlcv error: {e}", exc_info=True)
    finally:
        await collector.close()


async def backfill_coin_ohlcv():
    """One-time backfill: fetch 200 hourly candles for all tracked coins."""
    collector = CoinOHLCVCollector()
    try:
        total = 0
        for coin in TRACKED_COINS:
            binance_sym = coin.get("binance_symbol")
            if not binance_sym:
                continue

            # Check if we already have enough data
            from sqlalchemy import select, func
            async with async_session() as session:
                count_result = await session.execute(
                    select(func.count(CoinOHLCV.id)).where(
                        CoinOHLCV.symbol == binance_sym,
                        CoinOHLCV.interval == "1h",
                    )
                )
                existing_count = count_result.scalar() or 0
                if existing_count >= 100:
                    logger.debug(f"Skipping backfill for {binance_sym}: {existing_count} candles exist")
                    continue

            candles = await collector.backfill(binance_sym, coin["coin_id"], limit=200)
            if not candles:
                continue

            async with async_session() as session:
                stored = 0
                for c in candles:
                    existing = await session.execute(
                        select(CoinOHLCV.id).where(
                            CoinOHLCV.symbol == c["symbol"],
                            CoinOHLCV.interval == "1h",
                            CoinOHLCV.timestamp == c["timestamp"],
                        ).limit(1)
                    )
                    if existing.scalar_one_or_none() is not None:
                        continue

                    session.add(CoinOHLCV(
                        coin_id=c["coin_id"],
                        symbol=c["symbol"],
                        interval="1h",
                        timestamp=c["timestamp"],
                        open=c["open"],
                        high=c["high"],
                        low=c["low"],
                        close=c["close"],
                        volume=c["volume"],
                        source="binance",
                    ))
                    stored += 1
                await session.commit()
                total += stored
                logger.info(f"Backfilled {stored} OHLCV candles for {binance_sym}")

            await asyncio.sleep(0.5)

        logger.info(f"OHLCV backfill complete: {total} total candles stored")
    except Exception as e:
        logger.error(f"backfill_coin_ohlcv error: {e}", exc_info=True)
    finally:
        await collector.close()
