import logging
from datetime import datetime, timezone

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)


class MarketCollector(BaseCollector):
    """Collects BTC market data from Binance and CoinGecko."""

    BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
    BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
    BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
    BINANCE_OI_URL = "https://fapi.binance.com/fapi/v1/openInterest"
    BINANCE_PREMIUM_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
    COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
    SYMBOL = "BTCUSDT"

    async def collect(self) -> dict:
        """Collect current BTC price and recent candles."""
        ticker = await self._get_ticker()
        klines = await self._get_klines(interval="1h", limit=168)  # 7 days
        coingecko = await self._get_coingecko()

        return {
            "ticker": ticker,
            "klines": klines,
            "coingecko": coingecko,
            "timestamp": self.now().isoformat(),
        }

    async def get_current_price(self) -> float | None:
        """Get the current BTC price."""
        ticker = await self._get_ticker()
        if ticker:
            return float(ticker.get("lastPrice", 0))
        return None

    async def _get_ticker(self) -> dict | None:
        return await self.fetch_json(
            self.BINANCE_TICKER_URL,
            params={"symbol": self.SYMBOL},
        )

    async def _get_klines(self, interval: str = "1h", limit: int = 168) -> list[dict] | None:
        """Get historical klines (candlestick) data."""
        data = await self.fetch_json(
            self.BINANCE_KLINES_URL,
            params={
                "symbol": self.SYMBOL,
                "interval": interval,
                "limit": limit,
            },
        )
        if not data:
            return None

        klines = []
        for k in data:
            klines.append({
                "timestamp": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).isoformat(),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": datetime.fromtimestamp(k[6] / 1000, tz=timezone.utc).isoformat(),
                "quote_volume": float(k[7]),
                "trades": int(k[8]),
            })
        return klines

    async def _get_coingecko(self) -> dict | None:
        return await self.fetch_json(
            self.COINGECKO_URL,
            params={
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
            },
        )

    async def get_funding_rate(self) -> dict | None:
        """Get current and recent BTC perpetual funding rates from Binance Futures."""
        try:
            data = await self.fetch_json(
                self.BINANCE_PREMIUM_URL,
                params={"symbol": self.SYMBOL},
            )
            if data:
                return {
                    "funding_rate": float(data.get("lastFundingRate", 0)),
                    "mark_price": float(data.get("markPrice", 0)),
                    "index_price": float(data.get("indexPrice", 0)),
                    "next_funding_time": data.get("nextFundingTime"),
                }
        except Exception as e:
            logger.debug(f"Funding rate fetch error: {e}")
        return None

    async def get_open_interest(self) -> dict | None:
        """Get BTC perpetual open interest from Binance Futures."""
        try:
            data = await self.fetch_json(
                self.BINANCE_OI_URL,
                params={"symbol": self.SYMBOL},
            )
            if data:
                return {
                    "open_interest": float(data.get("openInterest", 0)),
                    "symbol": data.get("symbol"),
                }
        except Exception as e:
            logger.debug(f"Open interest fetch error: {e}")
        return None

    async def get_btc_dominance(self) -> dict | None:
        """Get BTC dominance from CoinGecko global endpoint."""
        try:
            data = await self.fetch_json("https://api.coingecko.com/api/v3/global")
            if data and "data" in data:
                gd = data["data"]
                return {
                    "btc_dominance": gd.get("market_cap_percentage", {}).get("bitcoin"),
                    "eth_dominance": gd.get("market_cap_percentage", {}).get("ethereum"),
                    "total_market_cap": gd.get("total_market_cap", {}).get("usd"),
                    "total_volume": gd.get("total_volume", {}).get("usd"),
                    "market_cap_change_24h": gd.get("market_cap_change_percentage_24h_usd"),
                }
        except Exception as e:
            logger.debug(f"BTC dominance fetch error: {e}")
        return None

    async def get_historical_klines(
        self,
        interval: str = "1h",
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[dict] | None:
        """Get historical klines for training data."""
        params = {
            "symbol": self.SYMBOL,
            "interval": interval,
            "limit": limit,
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data = await self.fetch_json(self.BINANCE_KLINES_URL, params=params)
        if not data:
            return None

        return [
            {
                "timestamp": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
            for k in data
        ]
