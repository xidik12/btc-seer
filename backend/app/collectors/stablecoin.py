"""Stablecoin supply and flow collector.

Source: DefiLlama API (free, no auth)
"""
import logging

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class StablecoinCollector(BaseCollector):
    """Collects stablecoin supply metrics from DefiLlama."""

    DEFILLAMA_STABLECOINS_URL = "https://stablecoins.llama.fi/stablecoins"
    DEFILLAMA_TVL_URL = "https://api.llama.fi/v2/historicalChainTvl"

    async def collect(self) -> dict:
        """Collect stablecoin supply and DeFi TVL data."""
        result = {
            "usdt_market_cap": 0.0,
            "usdc_market_cap": 0.0,
            "total_stablecoin_supply": 0.0,
            "stablecoin_supply_change_7d": 0.0,  # % change in 7 days
            "defi_tvl_usd": 0.0,                 # Total DeFi TVL
            "timestamp": self.now().isoformat(),
        }

        stable_data = await self._get_stablecoin_supply()
        if stable_data:
            result.update(stable_data)

        tvl_data = await self._get_defi_tvl()
        if tvl_data:
            result.update(tvl_data)

        return result

    async def _get_stablecoin_supply(self) -> dict | None:
        """Get stablecoin market caps from DefiLlama."""
        try:
            data = await self.fetch_json(
                self.DEFILLAMA_STABLECOINS_URL,
                params={"includePrices": "false"},
            )
            if not data or "peggedAssets" not in data:
                return None

            usdt_mcap = 0.0
            usdc_mcap = 0.0
            total = 0.0

            for asset in data["peggedAssets"]:
                symbol = asset.get("symbol", "").upper()
                # Current peg = total circulating across all chains
                chains = asset.get("chainCirculating", {})
                mcap = 0.0
                for chain_data in chains.values():
                    mcap += float(chain_data.get("current", {}).get("peggedUSD", 0) or 0)

                if mcap == 0:
                    mcap = float(asset.get("circulating", {}).get("peggedUSD", 0) or 0)

                total += mcap
                if symbol == "USDT":
                    usdt_mcap = mcap
                elif symbol == "USDC":
                    usdc_mcap = mcap

            return {
                "usdt_market_cap": usdt_mcap,
                "usdc_market_cap": usdc_mcap,
                "total_stablecoin_supply": total,
            }
        except Exception as e:
            logger.debug(f"Stablecoin supply error: {e}")
            return None

    async def _get_defi_tvl(self) -> dict | None:
        """Get total DeFi TVL from DefiLlama."""
        try:
            data = await self.fetch_json(self.DEFILLAMA_TVL_URL)
            if data and len(data) > 0:
                latest = data[-1]
                return {
                    "defi_tvl_usd": float(latest.get("tvl", 0) or 0),
                }
        except Exception as e:
            logger.debug(f"DeFi TVL error: {e}")
        return None
