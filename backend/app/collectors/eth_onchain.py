import logging
from datetime import datetime

from app.collectors.base import BaseCollector
from app.config import settings
from app.database import async_session, MultichainOnchain

logger = logging.getLogger(__name__)

# DeFi Llama chain name -> our chain identifier
CHAIN_MAP = {
    "Ethereum": "ethereum",
    "BSC": "bsc",
    "Solana": "solana",
}


class EthOnChainCollector(BaseCollector):
    """Collects multichain on-chain metrics.

    Sources:
    - Etherscan V2 Gas Oracle: Ethereum gas prices (fast/safe/propose).
    - DeFi Llama /v2/chains: DeFi TVL for Ethereum, BSC, and Solana (free, no auth).

    Stores results in the MultichainOnchain table, one row per chain per cycle.
    """

    ETHERSCAN_V2_BASE = "https://api.etherscan.io/v2/api"
    DEFILLAMA_CHAINS_URL = "https://api.llama.fi/v2/chains"

    async def collect(self) -> dict:
        """Collect gas prices and DeFi TVL for Ethereum, BSC, and Solana."""
        gas_data = await self._get_eth_gas()
        tvl_data = await self._get_defi_tvl()

        return {
            "gas": gas_data,
            "tvl": tvl_data,
            "timestamp": self.now().isoformat(),
        }

    async def _get_eth_gas(self) -> dict | None:
        """Fetch Ethereum gas prices from Etherscan V2 Gas Oracle."""
        params = {
            "chainid": "1",
            "module": "gastracker",
            "action": "gasoracle",
        }
        if settings.etherscan_api_key:
            params["apikey"] = settings.etherscan_api_key

        data = await self.fetch_json(self.ETHERSCAN_V2_BASE, params=params)
        if not data:
            return None

        result = data.get("result")
        if not isinstance(result, dict):
            return None

        try:
            return {
                "safe_gas": float(result.get("SafeGasPrice", 0)),
                "propose_gas": float(result.get("ProposeGasPrice", 0)),
                "fast_gas": float(result.get("FastGasPrice", 0)),
                "base_fee": float(result.get("suggestBaseFee", 0)),
            }
        except (ValueError, TypeError):
            return None

    async def _get_defi_tvl(self) -> dict[str, float]:
        """Fetch DeFi TVL per chain from DeFi Llama (free, no auth)."""
        data = await self.fetch_json(self.DEFILLAMA_CHAINS_URL)
        tvl_map: dict[str, float] = {}

        if not data or not isinstance(data, list):
            return tvl_map

        for chain_info in data:
            chain_name = chain_info.get("name", "")
            if chain_name in CHAIN_MAP:
                tvl = chain_info.get("tvl")
                if tvl is not None:
                    try:
                        tvl_map[CHAIN_MAP[chain_name]] = float(tvl)
                    except (ValueError, TypeError):
                        pass

        return tvl_map


async def collect_multichain_onchain():
    """Scheduled job: collect multichain on-chain data every hour.

    Stores one MultichainOnchain row per chain (ethereum, bsc, solana).
    """
    collector = EthOnChainCollector()
    try:
        data = await collector.collect()
        gas = data.get("gas")
        tvl = data.get("tvl", {})
        now = datetime.utcnow()

        async with async_session() as session:
            # Ethereum row -- includes gas price data
            eth_avg_gas = None
            if gas:
                # Use the "propose" gas price as the average
                eth_avg_gas = gas.get("propose_gas")

            eth_tvl = tvl.get("ethereum")
            if eth_avg_gas is not None or eth_tvl is not None:
                session.add(MultichainOnchain(
                    chain="ethereum",
                    timestamp=now,
                    avg_gas_price=eth_avg_gas,
                    defi_tvl=eth_tvl,
                ))

            # BSC row
            bsc_tvl = tvl.get("bsc")
            if bsc_tvl is not None:
                session.add(MultichainOnchain(
                    chain="bsc",
                    timestamp=now,
                    defi_tvl=bsc_tvl,
                ))

            # Solana row
            sol_tvl = tvl.get("solana")
            if sol_tvl is not None:
                session.add(MultichainOnchain(
                    chain="solana",
                    timestamp=now,
                    defi_tvl=sol_tvl,
                ))

            await session.commit()

        chains_stored = sum(1 for c in ["ethereum", "bsc", "solana"] if tvl.get(c) is not None)
        logger.info(
            f"Multichain on-chain collected: gas={'yes' if gas else 'no'}, "
            f"TVL for {chains_stored} chains"
        )

    except Exception as e:
        logger.error(f"Multichain on-chain collection error: {e}")
    finally:
        await collector.close()
