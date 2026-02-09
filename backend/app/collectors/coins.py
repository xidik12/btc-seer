import logging
from datetime import datetime

from sqlalchemy import select

from app.collectors.base import BaseCollector
from app.database import async_session, CoinInfo, CoinPrice

logger = logging.getLogger(__name__)

# Permanently tracked coins
TRACKED_COINS = [
    {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "coingecko_id": "bitcoin"},
    {"coin_id": "ethereum", "symbol": "ETH", "name": "Ethereum", "coingecko_id": "ethereum"},
    {"coin_id": "solana", "symbol": "SOL", "name": "Solana", "coingecko_id": "solana"},
    {"coin_id": "ripple", "symbol": "XRP", "name": "XRP", "coingecko_id": "ripple"},
]

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


class CoinCollector(BaseCollector):
    """Collects price data for multiple tracked coins via CoinGecko."""

    async def collect(self) -> dict:
        """Fetch market data for all tracked coins in a single API call."""
        ids = ",".join(c["coingecko_id"] for c in TRACKED_COINS)
        url = f"{COINGECKO_BASE}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ids,
            "order": "market_cap_desc",
            "per_page": 20,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d",
        }

        data = await self.fetch_json(url, params=params)
        if not data:
            logger.warning("CoinCollector: No data from CoinGecko markets endpoint")
            return {"coins": []}

        coins = []
        for item in data:
            coins.append({
                "coin_id": item["id"],
                "symbol": item.get("symbol", "").upper(),
                "name": item.get("name", ""),
                "image_url": item.get("image"),
                "price_usd": item.get("current_price"),
                "market_cap": item.get("market_cap"),
                "volume_24h": item.get("total_volume"),
                "change_1h": item.get("price_change_percentage_1h_in_currency"),
                "change_24h": item.get("price_change_percentage_24h"),
                "change_7d": item.get("price_change_percentage_7d_in_currency"),
            })

        return {"coins": coins}


async def seed_tracked_coins():
    """Seed CoinInfo table with tracked coins if not already present."""
    async with async_session() as session:
        for coin in TRACKED_COINS:
            result = await session.execute(
                select(CoinInfo).where(CoinInfo.coin_id == coin["coin_id"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                session.add(CoinInfo(
                    coin_id=coin["coin_id"],
                    symbol=coin["symbol"],
                    name=coin["name"],
                    coingecko_id=coin["coingecko_id"],
                    is_tracked=True,
                ))
                logger.info(f"Seeded tracked coin: {coin['name']}")
        await session.commit()


async def collect_coin_prices():
    """Scheduled job: collect prices for all tracked coins."""
    collector = CoinCollector()
    try:
        result = await collector.collect()
        coins = result.get("coins", [])
        if not coins:
            return

        async with async_session() as session:
            now = datetime.utcnow()
            for coin in coins:
                # Update CoinInfo image_url if missing
                info_result = await session.execute(
                    select(CoinInfo).where(CoinInfo.coin_id == coin["coin_id"])
                )
                info = info_result.scalar_one_or_none()
                if info and not info.image_url and coin.get("image_url"):
                    info.image_url = coin["image_url"]

                # Save price snapshot
                session.add(CoinPrice(
                    coin_id=coin["coin_id"],
                    price_usd=coin["price_usd"],
                    market_cap=coin.get("market_cap"),
                    volume_24h=coin.get("volume_24h"),
                    change_1h=coin.get("change_1h"),
                    change_24h=coin.get("change_24h"),
                    change_7d=coin.get("change_7d"),
                    timestamp=now,
                ))

            await session.commit()
            logger.info(f"Collected prices for {len(coins)} coins")
    except Exception as e:
        logger.error(f"collect_coin_prices error: {e}", exc_info=True)
    finally:
        await collector.close()
