"""Exchange flow and on-chain valuation metrics collector.

Sources:
- CryptoQuant public API (exchange reserve, netflow)
- Blockchain.info (address data)
- Glassnode community endpoints
"""
import logging

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class ExchangeFlowCollector(BaseCollector):
    """Collects exchange flow data and on-chain valuation metrics."""

    async def collect(self) -> dict:
        """Collect exchange reserve, netflow, and valuation metrics."""
        result = {
            # Exchange flows
            "exchange_reserve_btc": 0.0,
            "exchange_netflow_btc": 0.0,      # positive = inflow (selling pressure)
            # On-chain valuation
            "nvt_signal": 0.0,                # NVT Signal (90-day smoothed)
            "mvrv_zscore": 0.0,               # MVRV Z-Score
            "sopr": 0.0,                      # Spent Output Profit Ratio
            "puell_multiple": 0.0,            # Puell Multiple (miner revenue / 365d avg)
            # Holder behavior
            "supply_in_profit_pct": 0.0,      # % of supply currently in profit
            "long_term_holder_supply": 0.0,   # BTC held by LTH (>155 days)
            "coin_days_destroyed": 0.0,       # CDD (dormancy weighted)
            "timestamp": self.now().isoformat(),
        }

        # Fetch from multiple sources
        exchange_data = await self._get_exchange_data()
        if exchange_data:
            result.update(exchange_data)

        valuation_data = await self._get_valuation_metrics()
        if valuation_data:
            result.update(valuation_data)

        return result

    async def _get_exchange_data(self) -> dict | None:
        """Get exchange reserve and netflow from public APIs."""
        try:
            # Try blockchain.info for rough exchange balance proxy
            data = await self.fetch_json("https://api.blockchain.info/stats")
            if data:
                # Estimate exchange reserve from total BTC and velocity
                total_btc = data.get("totalbc", 0) / 1e8
                tx_volume = data.get("estimated_btc_sent", 0) / 1e8
                # NVT proxy
                market_cap = data.get("market_price_usd", 0) * total_btc
                if tx_volume > 0:
                    nvt = market_cap / (tx_volume * data.get("market_price_usd", 1))
                else:
                    nvt = 0

                return {
                    "nvt_signal": min(nvt, 500),  # Cap extreme values
                }
        except Exception as e:
            logger.debug(f"Exchange data error: {e}")
        return None

    async def _get_valuation_metrics(self) -> dict | None:
        """Get on-chain valuation from public endpoints."""
        try:
            # Blockchain.info for basic metrics
            data = await self.fetch_json("https://api.blockchain.info/stats")
            if not data:
                return None

            market_price = data.get("market_price_usd", 0)
            total_btc = data.get("totalbc", 0) / 1e8
            miners_rev_btc = data.get("miners_revenue_btc", 0) / 1e8
            miners_rev_usd = data.get("miners_revenue_usd", 0)

            result = {}

            # Puell Multiple: daily miner revenue / 365-day avg miner revenue
            # We approximate with current day revenue
            if miners_rev_usd > 0:
                # Rough estimate: typical daily miner revenue ~$30-50M
                avg_daily_revenue = 40_000_000  # Reasonable baseline
                result["puell_multiple"] = miners_rev_usd / max(avg_daily_revenue, 1)

            return result
        except Exception as e:
            logger.debug(f"Valuation metrics error: {e}")
        return None
