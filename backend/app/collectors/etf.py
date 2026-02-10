"""Bitcoin ETF flow data collector.

Sources:
- CoinGlass ETF API (public, no auth)
- Fallback: SoSoValue public endpoint
"""
import logging

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class ETFCollector(BaseCollector):
    """Collects Bitcoin spot ETF flow data."""

    COINGLASS_ETF_URL = "https://open-api.coinglass.com/public/v2/etf/bitcoin"

    async def collect(self) -> dict:
        """Collect latest BTC ETF flow data."""
        result = {
            "net_flow_usd": 0.0,        # Daily net inflow/outflow in USD
            "total_holdings_btc": 0.0,   # Total BTC held by all ETFs
            "ibit_flow": 0.0,           # BlackRock IBIT daily flow
            "fbtc_flow": 0.0,           # Fidelity FBTC daily flow
            "gbtc_flow": 0.0,           # Grayscale GBTC daily flow
            "etf_volume_usd": 0.0,      # Daily ETF trading volume
            "timestamp": self.now().isoformat(),
        }

        # Try CoinGlass public endpoint
        data = await self._get_coinglass()
        if data:
            result.update(data)
            return result

        # Fallback: try scraping public summary
        data = await self._get_fallback()
        if data:
            result.update(data)

        return result

    async def _get_coinglass(self) -> dict | None:
        try:
            data = await self.fetch_json(self.COINGLASS_ETF_URL)
            if not data or data.get("code") != "0":
                return None

            items = data.get("data", [])
            if not items:
                return None

            total_flow = 0.0
            total_holdings = 0.0
            total_volume = 0.0
            flows_by_ticker = {}

            for item in items:
                ticker = item.get("symbol", "")
                flow = float(item.get("netAssets", 0) or 0)
                holdings = float(item.get("holdings", 0) or 0)
                volume = float(item.get("volume", 0) or 0)

                total_flow += flow
                total_holdings += holdings
                total_volume += volume
                flows_by_ticker[ticker.upper()] = flow

            return {
                "net_flow_usd": total_flow,
                "total_holdings_btc": total_holdings,
                "ibit_flow": flows_by_ticker.get("IBIT", 0.0),
                "fbtc_flow": flows_by_ticker.get("FBTC", 0.0),
                "gbtc_flow": flows_by_ticker.get("GBTC", 0.0),
                "etf_volume_usd": total_volume,
            }
        except Exception as e:
            logger.debug(f"CoinGlass ETF error: {e}")
            return None

    async def _get_fallback(self) -> dict | None:
        """Fallback: try alternative free endpoints."""
        try:
            # CoinGlass alternative endpoint
            data = await self.fetch_json(
                "https://api.coinglass.com/api/index/bitcoin-etf"
            )
            if data and "data" in data:
                d = data["data"]
                return {
                    "net_flow_usd": float(d.get("totalNetFlow", 0) or 0),
                    "total_holdings_btc": float(d.get("totalHoldings", 0) or 0),
                    "etf_volume_usd": float(d.get("totalVolume", 0) or 0),
                }
        except Exception as e:
            logger.debug(f"ETF fallback error: {e}")
        return None
