import logging
from datetime import datetime

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)


class MacroCollector(BaseCollector):
    """Collects macro market data via Alpha Vantage (primary) and Yahoo Finance v8 (fallback)."""

    # Alpha Vantage symbols
    AV_SYMBOLS = {
        "dxy": "DXY",
        "gold": "XAU/USD",
        "sp500": "SPX",
        "treasury_10y": "TNX",
    }

    # Yahoo Finance v8 chart symbols (v7 quote API is deprecated/blocked)
    YF_SYMBOLS = {
        "dxy": ["DX-Y.NYB", "UUP"],
        "gold": ["GC=F", "GLD"],
        "sp500": ["^GSPC", "SPY"],
        "treasury_10y": ["^TNX", "TLT"],
    }

    # Cache last successful values
    _last_good: dict = {}

    async def collect(self) -> dict:
        """Collect macro data using Alpha Vantage (primary) or Yahoo Finance (fallback)."""
        result = {
            "dxy": None,
            "gold": None,
            "sp500": None,
            "treasury_10y": None,
            "timestamp": self.now().isoformat(),
        }

        # Try Alpha Vantage first (if API key set)
        if settings.alpha_vantage_api_key:
            av_quotes = await self._fetch_alpha_vantage()
            for key, value in av_quotes.items():
                if value:
                    result[key] = value
                    MacroCollector._last_good[key] = value

        # For any missing data, try Yahoo Finance v8 chart API
        for key in ["dxy", "gold", "sp500", "treasury_10y"]:
            if result[key] is None:
                for symbol in self.YF_SYMBOLS.get(key, []):
                    yf_quote = await self._fetch_yahoo_v8(symbol)
                    if yf_quote:
                        result[key] = yf_quote
                        MacroCollector._last_good[key] = yf_quote
                        break

        # Use cached values for any still missing
        for key in list(result.keys()):
            if result[key] is None and key in MacroCollector._last_good:
                result[key] = MacroCollector._last_good[key]
                logger.info(f"Using cached value for {key}")

        return result

    async def _fetch_alpha_vantage(self) -> dict:
        """Fetch quotes from Alpha Vantage API."""
        result = {}

        try:
            for key, symbol in self.AV_SYMBOLS.items():
                try:
                    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={settings.alpha_vantage_api_key}"
                    data = await self.fetch_json(url)

                    if data and "Global Quote" in data:
                        quote = data["Global Quote"]
                        price = quote.get("05. price")
                        change_pct = quote.get("10. change percent", "0%").replace("%", "")

                        if price:
                            result[key] = {
                                "price": float(price),
                                "change_1h": float(change_pct),
                                "change_24h": float(change_pct),
                            }
                except Exception as e:
                    logger.warning(f"Alpha Vantage error for {key}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Alpha Vantage API error: {e}")

        return result

    async def _fetch_yahoo_v8(self, symbol: str) -> dict | None:
        """Fetch a quote via Yahoo Finance v8 chart API (v7 is deprecated)."""
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {"interval": "1d", "range": "2d"}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }

            data = await self.fetch_json(url, params=params, headers=headers)

            if data and "chart" in data:
                results = data["chart"].get("result", [])
                if results:
                    meta = results[0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    prev_close = meta.get("chartPreviousClose")

                    if price:
                        change_pct = 0
                        if prev_close and prev_close > 0:
                            change_pct = ((price - prev_close) / prev_close) * 100

                        return {
                            "price": float(price),
                            "change_1h": round(change_pct, 4),
                            "change_24h": round(change_pct, 4),
                        }

        except Exception as e:
            logger.debug(f"Yahoo Finance v8 error for {symbol}: {e}")

        return None
