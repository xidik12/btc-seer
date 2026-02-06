import logging
from datetime import datetime

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class MacroCollector(BaseCollector):
    """Collects macro market data: DXY, Gold, S&P 500, Treasury yields via yfinance."""

    SYMBOLS = {
        "dxy": "DX-Y.NYB",       # US Dollar Index
        "gold": "GC=F",          # Gold Futures
        "sp500": "ES=F",         # S&P 500 Futures
        "treasury_10y": "^TNX",  # 10-Year Treasury Yield
    }

    async def collect(self) -> dict:
        """Collect macro data using yfinance (sync, run in executor)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._collect_sync)

    def _collect_sync(self) -> dict:
        """Synchronous collection using yfinance."""
        try:
            import yfinance as yf

            result = {
                "dxy": None,
                "gold": None,
                "sp500": None,
                "treasury_10y": None,
                "timestamp": self.now().isoformat(),
            }

            for key, symbol in self.SYMBOLS.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="2d", interval="1h")
                    if not hist.empty:
                        result[key] = {
                            "price": float(hist["Close"].iloc[-1]),
                            "change_1h": float(
                                (hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100
                            ) if len(hist) >= 2 else 0,
                            "change_24h": float(
                                (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100
                            ) if len(hist) >= 2 else 0,
                        }
                except Exception as e:
                    logger.error(f"Error fetching {key} ({symbol}): {e}")

            return result

        except ImportError:
            logger.error("yfinance not installed")
            return {"error": "yfinance not installed", "timestamp": self.now().isoformat()}
