"""Historical BTC price collector for backfilling pre-2017 data."""
import json
import logging
from datetime import datetime
from pathlib import Path

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


class HistoricalBTCCollector(BaseCollector):
    """Fetches historical BTC prices from multiple sources for backfill."""

    async def collect(self) -> dict:
        """Main entry point — collects from all sources."""
        return await self.fetch_all_historical()

    def load_early_prices(self) -> list[dict]:
        """Load pre-CoinGecko era prices (2009-2013) from static JSON."""
        path = DATA_DIR / "btc_early_prices.json"
        if not path.exists():
            logger.warning("btc_early_prices.json not found")
            return []
        with open(path) as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} early BTC prices from static file")
        return data

    async def fetch_coingecko_daily(self, start_ts: int, end_ts: int) -> list[dict]:
        """Fetch daily prices from CoinGecko (2013-2017 era)."""
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
        params = {
            "vs_currency": "usd",
            "from": start_ts,
            "to": end_ts,
        }
        data = await self.fetch_json(url, params=params)
        if not data or "prices" not in data:
            logger.warning("CoinGecko returned no data")
            return []

        results = []
        for ts_ms, price in data["prices"]:
            dt = datetime.utcfromtimestamp(ts_ms / 1000)
            results.append({
                "date": dt.strftime("%Y-%m-%d"),
                "timestamp": dt,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 0,
                "source": "coingecko",
            })
        logger.info(f"Fetched {len(results)} prices from CoinGecko")
        return results

    async def fetch_binance_daily(self, start_ts: int, end_ts: int) -> list[dict]:
        """Fetch daily klines from Binance (2017-present)."""
        url = "https://api.binance.com/api/v3/klines"
        all_results = []
        current_start = start_ts * 1000  # Binance uses ms

        while current_start < end_ts * 1000:
            params = {
                "symbol": "BTCUSDT",
                "interval": "1d",
                "startTime": current_start,
                "limit": 1000,
            }
            data = await self.fetch_json(url, params=params)
            if not data or len(data) == 0:
                break

            for k in data:
                dt = datetime.utcfromtimestamp(k[0] / 1000)
                all_results.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "timestamp": dt,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "source": "binance",
                })
            current_start = data[-1][0] + 86400000  # Next day

            import asyncio
            await asyncio.sleep(0.5)  # Rate limit

        logger.info(f"Fetched {len(all_results)} prices from Binance")
        return all_results

    async def fetch_all_historical(self) -> dict:
        """Combine all sources with date-based deduplication."""
        seen_dates = set()
        all_prices = []

        # 1. Early prices (2009-2013)
        early = self.load_early_prices()
        for p in early:
            date = p.get("date")
            if date and date not in seen_dates:
                seen_dates.add(date)
                all_prices.append({
                    "date": date,
                    "timestamp": datetime.strptime(date, "%Y-%m-%d"),
                    "open": p.get("price", 0),
                    "high": p.get("price", 0),
                    "low": p.get("price", 0),
                    "close": p.get("price", 0),
                    "volume": 0,
                    "source": "historical_backfill",
                })

        # 2. CoinGecko (2013-2017)
        try:
            cg_start = int(datetime(2013, 4, 28).timestamp())
            cg_end = int(datetime(2017, 8, 1).timestamp())
            cg_prices = await self.fetch_coingecko_daily(cg_start, cg_end)
            for p in cg_prices:
                if p["date"] not in seen_dates:
                    seen_dates.add(p["date"])
                    p["source"] = "historical_backfill"
                    all_prices.append(p)
        except Exception as e:
            logger.error(f"CoinGecko fetch failed: {e}")

        # 3. Binance (2017-present)
        try:
            bn_start = int(datetime(2017, 8, 1).timestamp())
            bn_end = int(datetime.utcnow().timestamp())
            bn_prices = await self.fetch_binance_daily(bn_start, bn_end)
            for p in bn_prices:
                if p["date"] not in seen_dates:
                    seen_dates.add(p["date"])
                    p["source"] = "historical_backfill"
                    all_prices.append(p)
        except Exception as e:
            logger.error(f"Binance fetch failed: {e}")

        all_prices.sort(key=lambda x: x["date"])
        logger.info(f"Total historical prices: {len(all_prices)} (deduplicated)")
        return {"prices": all_prices, "count": len(all_prices)}
