import logging
from datetime import datetime

from sqlalchemy import select

from app.collectors.base import BaseCollector
from app.config import settings
from app.database import async_session, CoinInfo, CoinPrice

logger = logging.getLogger(__name__)

# Permanently tracked coins — top 20 by market cap
TRACKED_COINS = [
    {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "coingecko_id": "bitcoin", "binance_symbol": "BTCUSDT"},
    {"coin_id": "ethereum", "symbol": "ETH", "name": "Ethereum", "coingecko_id": "ethereum", "binance_symbol": "ETHUSDT"},
    {"coin_id": "ripple", "symbol": "XRP", "name": "XRP", "coingecko_id": "ripple", "binance_symbol": "XRPUSDT"},
    {"coin_id": "solana", "symbol": "SOL", "name": "Solana", "coingecko_id": "solana", "binance_symbol": "SOLUSDT"},
    {"coin_id": "binancecoin", "symbol": "BNB", "name": "BNB", "coingecko_id": "binancecoin", "binance_symbol": "BNBUSDT"},
    {"coin_id": "cardano", "symbol": "ADA", "name": "Cardano", "coingecko_id": "cardano", "binance_symbol": "ADAUSDT"},
    {"coin_id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin", "coingecko_id": "dogecoin", "binance_symbol": "DOGEUSDT"},
    {"coin_id": "avalanche-2", "symbol": "AVAX", "name": "Avalanche", "coingecko_id": "avalanche-2", "binance_symbol": "AVAXUSDT"},
    {"coin_id": "polkadot", "symbol": "DOT", "name": "Polkadot", "coingecko_id": "polkadot", "binance_symbol": "DOTUSDT"},
    {"coin_id": "chainlink", "symbol": "LINK", "name": "Chainlink", "coingecko_id": "chainlink", "binance_symbol": "LINKUSDT"},
    {"coin_id": "matic-network", "symbol": "MATIC", "name": "Polygon", "coingecko_id": "matic-network", "binance_symbol": "MATICUSDT"},
    {"coin_id": "shiba-inu", "symbol": "SHIB", "name": "Shiba Inu", "coingecko_id": "shiba-inu", "binance_symbol": "SHIBUSDT"},
    {"coin_id": "uniswap", "symbol": "UNI", "name": "Uniswap", "coingecko_id": "uniswap", "binance_symbol": "UNIUSDT"},
    {"coin_id": "litecoin", "symbol": "LTC", "name": "Litecoin", "coingecko_id": "litecoin", "binance_symbol": "LTCUSDT"},
    {"coin_id": "cosmos", "symbol": "ATOM", "name": "Cosmos", "coingecko_id": "cosmos", "binance_symbol": "ATOMUSDT"},
    {"coin_id": "near", "symbol": "NEAR", "name": "NEAR Protocol", "coingecko_id": "near", "binance_symbol": "NEARUSDT"},
    {"coin_id": "aptos", "symbol": "APT", "name": "Aptos", "coingecko_id": "aptos", "binance_symbol": "APTUSDT"},
    {"coin_id": "arbitrum", "symbol": "ARB", "name": "Arbitrum", "coingecko_id": "arbitrum", "binance_symbol": "ARBUSDT"},
    {"coin_id": "optimism", "symbol": "OP", "name": "Optimism", "coingecko_id": "optimism", "binance_symbol": "OPUSDT"},
    {"coin_id": "sui", "symbol": "SUI", "name": "Sui", "coingecko_id": "sui", "binance_symbol": "SUIUSDT"},
]

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


class CoinCollector(BaseCollector):
    """Collects price data for multiple tracked coins via CoinGecko."""

    @property
    def CG_HEADERS(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        if settings.coingecko_api_key:
            headers["x-cg-demo-api-key"] = settings.coingecko_api_key
        return headers

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

        data = await self.fetch_json(url, params=params, headers=self.CG_HEADERS)
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

                # Save price snapshot (upsert to avoid duplicate key errors)
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                stmt = pg_insert(CoinPrice).values(
                    coin_id=coin["coin_id"],
                    price_usd=coin["price_usd"],
                    market_cap=coin.get("market_cap"),
                    volume_24h=coin.get("volume_24h"),
                    change_1h=coin.get("change_1h"),
                    change_24h=coin.get("change_24h"),
                    change_7d=coin.get("change_7d"),
                    timestamp=now,
                ).on_conflict_do_update(
                    constraint="coin_prices_pkey",
                    set_={
                        "price_usd": coin["price_usd"],
                        "market_cap": coin.get("market_cap"),
                        "volume_24h": coin.get("volume_24h"),
                        "change_1h": coin.get("change_1h"),
                        "change_24h": coin.get("change_24h"),
                        "change_7d": coin.get("change_7d"),
                    },
                )
                await session.execute(stmt)

            await session.commit()
            logger.info(f"Collected prices for {len(coins)} coins")
    except Exception as e:
        logger.error(f"collect_coin_prices error: {e}", exc_info=True)
    finally:
        await collector.close()
