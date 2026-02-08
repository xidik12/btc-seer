import logging
from datetime import datetime

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class MacroCollector(BaseCollector):
    """Collects macro market data: DXY, Gold, S&P 500, Treasury yields via Yahoo Finance API."""

    # Yahoo Finance symbols for macro indicators
    SYMBOLS = {
        "dxy": "DX-Y.NYB",      # US Dollar Index
        "gold": "GC=F",         # Gold Futures
        "sp500": "^GSPC",       # S&P 500 Index
        "treasury_10y": "^TNX", # 10-Year Treasury Yield
    }

    # Fallback symbols if primary fails
    FALLBACK_SYMBOLS = {
        "dxy": "UUP",
        "gold": "GLD",
        "sp500": "SPY",
        "treasury_10y": "TLT",
    }

    # Cache last successful values
    _last_good: dict = {}

    async def collect(self) -> dict:
        """Collect macro data using Yahoo Finance quote API."""
        result = {
            "dxy": None,
            "gold": None,
            "sp500": None,
            "treasury_10y": None,
            "timestamp": self.now().isoformat(),
        }

        # Try to fetch all symbols in one request
        symbols_list = list(self.SYMBOLS.values())
        quotes = await self._fetch_quotes(symbols_list)

        # Map responses to our keys
        for key, symbol in self.SYMBOLS.items():
            if symbol in quotes:
                result[key] = quotes[symbol]
                MacroCollector._last_good[key] = result[key]
            elif key in self.FALLBACK_SYMBOLS:
                # Try fallback symbol
                fallback = self.FALLBACK_SYMBOLS[key]
                fallback_quotes = await self._fetch_quotes([fallback])
                if fallback in fallback_quotes:
                    result[key] = fallback_quotes[fallback]
                    MacroCollector._last_good[key] = result[key]

        # Use cached values for any that failed
        for key in result.keys():
            if result[key] is None and key in MacroCollector._last_good:
                result[key] = MacroCollector._last_good[key]
                logger.info(f"Using cached value for {key}")

        return result

    async def _fetch_quotes(self, symbols: list) -> dict:
        """Fetch current quotes from Yahoo Finance API."""
        try:
            symbols_param = ",".join(symbols)
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_param}"

            data = await self.fetch_json(url)

            if not data or "quoteResponse" not in data:
                return {}

            quotes = {}
            for quote in data["quoteResponse"].get("result", []):
                symbol = quote.get("symbol")
                if not symbol:
                    continue

                price = quote.get("regularMarketPrice")
                prev_close = quote.get("regularMarketPreviousClose")

                if price is not None:
                    change_pct = 0
                    if prev_close and prev_close > 0:
                        change_pct = ((price - prev_close) / prev_close) * 100

                    quotes[symbol] = {
                        "price": float(price),
                        "change_1h": round(change_pct, 4),  # Using daily change as approximation
                        "change_24h": round(change_pct, 4),
                    }

            return quotes

        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return {}
