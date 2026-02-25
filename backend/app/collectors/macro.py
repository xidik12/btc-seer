import logging
from datetime import datetime

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
        "nasdaq": "NDX",
        "vix": "VIX",
        "eurusd": "EUR/USD",
    }

    # Yahoo Finance v8 chart symbols (v7 quote API is deprecated/blocked)
    YF_SYMBOLS = {
        "dxy": ["DX-Y.NYB", "UUP"],
        "gold": ["GC=F", "GLD"],
        "sp500": ["^GSPC", "SPY"],
        "treasury_10y": ["^TNX", "TLT"],
        "nasdaq": ["^NDX", "QQQ"],
        "vix": ["^VIX"],
        "eurusd": ["EURUSD=X"],
        # Forex pairs
        "gbpusd": ["GBPUSD=X"],
        "usdjpy": ["JPY=X"],
        "usdchf": ["CHF=X"],
        "audusd": ["AUDUSD=X"],
        "usdcad": ["CADUSD=X"],
        "nzdusd": ["NZDUSD=X"],
        # Commodities
        "wti_oil": ["CL=F"],
        "silver": ["SI=F"],
        "copper": ["HG=F"],
        "natural_gas": ["NG=F"],
        # Indices
        "dow_jones": ["^DJI", "DIA"],
        "russell_2000": ["^RUT", "IWM"],
        "dax": ["^GDAXI"],
        "nikkei_225": ["^N225"],
        "ftse_100": ["^FTSE"],
    }

    ALL_KEYS = list(YF_SYMBOLS.keys())

    # Cache last successful values
    _last_good: dict = {}

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> dict:
        """Collect macro data using Alpha Vantage (primary) or Yahoo Finance (fallback)."""
        result = {key: None for key in self.ALL_KEYS}
        result["timestamp"] = self.now().isoformat()

        # Try Alpha Vantage first (if API key set) — only covers original 7
        if settings.alpha_vantage_api_key:
            av_quotes = await self._fetch_alpha_vantage()
            for key, value in av_quotes.items():
                if value:
                    result[key] = value
                    MacroCollector._last_good[key] = value

        # For any missing data, try Yahoo Finance v8 chart API
        for key in self.ALL_KEYS:
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

    async def fetch_m2_supply(self) -> float | None:
        """Fetch M2 money supply from FRED API or use fallback estimate."""
        if settings.fred_api_key:
            try:
                url = (
                    f"https://api.stlouisfed.org/fred/series/observations"
                    f"?series_id=M2SL&api_key={settings.fred_api_key}"
                    f"&sort_order=desc&limit=1&file_type=json"
                )
                data = await self.fetch_json(url)
                if data and "observations" in data and data["observations"]:
                    value_str = data["observations"][0].get("value", "")
                    if value_str and value_str != ".":
                        return float(value_str) / 1000.0
            except Exception as e:
                logger.warning(f"FRED M2 fetch error: {e}")

        base_date = datetime(2024, 1, 1)
        base_m2 = 20.8
        years_elapsed = (datetime.utcnow() - base_date).days / 365.25
        estimated_m2 = base_m2 * (1.072 ** years_elapsed)
        return round(estimated_m2, 2)

    async def fetch_treasury_yields(self) -> dict:
        """Fetch treasury yields (2Y, 5Y, 10Y, 30Y) from FRED API."""
        yields = {}
        series_map = {
            "treasury_2y": "DGS2",
            "treasury_5y": "DGS5",
            "treasury_10y": "DGS10",
            "treasury_30y": "DGS30",
        }

        if not settings.fred_api_key:
            return yields

        for key, series_id in series_map.items():
            try:
                url = (
                    f"https://api.stlouisfed.org/fred/series/observations"
                    f"?series_id={series_id}&api_key={settings.fred_api_key}"
                    f"&sort_order=desc&limit=1&file_type=json"
                )
                data = await self.fetch_json(url)
                if data and "observations" in data and data["observations"]:
                    value_str = data["observations"][0].get("value", "")
                    if value_str and value_str != ".":
                        yields[key] = float(value_str)
            except Exception as e:
                logger.debug(f"FRED {series_id} fetch error: {e}")

        return yields

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
