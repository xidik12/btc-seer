import logging
from datetime import datetime

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class MacroCollector(BaseCollector):
    """Collects macro market data: DXY, Gold, S&P 500, Treasury yields via yfinance."""

    # Primary and fallback symbols for each metric
    ALT_SYMBOLS = {
        "dxy": ["DX-Y.NYB", "UUP"],
        "gold": ["GC=F", "GLD"],
        "sp500": ["ES=F", "^GSPC", "SPY"],
        "treasury_10y": ["^TNX", "TLT"],
    }

    # Cache last successful values so we never return all-None
    _last_good: dict = {}

    async def collect(self) -> dict:
        """Collect macro data using yfinance (sync, run in executor)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._collect_sync)

    def _collect_sync(self) -> dict:
        """Synchronous collection using yfinance with fallback symbols."""
        try:
            import yfinance as yf

            result = {
                "dxy": None,
                "gold": None,
                "sp500": None,
                "treasury_10y": None,
                "timestamp": self.now().isoformat(),
            }

            for key, symbols in self.ALT_SYMBOLS.items():
                for symbol in symbols:
                    try:
                        ticker = yf.Ticker(symbol)
                        # Use 5d period for reliability on weekends/after-hours
                        hist = ticker.history(period="5d", interval="1h")
                        if not hist.empty and len(hist) >= 2:
                            result[key] = {
                                "price": float(hist["Close"].iloc[-1]),
                                "change_1h": float(
                                    (hist["Close"].iloc[-1] - hist["Close"].iloc[-2])
                                    / hist["Close"].iloc[-2] * 100
                                ),
                                "change_24h": float(
                                    (hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                                    / hist["Close"].iloc[0] * 100
                                ),
                            }
                            MacroCollector._last_good[key] = result[key]
                            break  # Got data, skip fallback symbols
                    except Exception as e:
                        logger.warning(f"Error fetching {key} via {symbol}: {e}")
                        continue

                # If all symbols failed, use cached value
                if result[key] is None and key in MacroCollector._last_good:
                    result[key] = MacroCollector._last_good[key]
                    logger.info(f"Using cached value for {key}")

            return result

        except ImportError:
            logger.error("yfinance not installed")
            return {"error": "yfinance not installed", "timestamp": self.now().isoformat()}
