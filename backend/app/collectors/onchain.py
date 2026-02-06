import logging

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class OnChainCollector(BaseCollector):
    """Collects Bitcoin on-chain metrics from blockchain.com and mempool.space."""

    BLOCKCHAIN_STATS_URL = "https://api.blockchain.info/stats"
    BLOCKCHAIN_HASHRATE_URL = "https://api.blockchain.info/charts/hash-rate"
    MEMPOOL_FEES_URL = "https://mempool.space/api/v1/fees/recommended"
    MEMPOOL_STATS_URL = "https://mempool.space/api/mempool"
    BLOCKCHAIR_STATS_URL = "https://api.blockchair.com/bitcoin/stats"

    async def collect(self) -> dict:
        """Collect on-chain data from multiple sources."""
        blockchain_stats = await self._get_blockchain_stats()
        mempool_data = await self._get_mempool_data()
        blockchair_data = await self._get_blockchair_data()

        result = {
            "hash_rate": None,
            "difficulty": None,
            "mempool_size": None,
            "mempool_fees": None,
            "tx_volume": None,
            "active_addresses": None,
            "large_tx_count": None,
            "timestamp": self.now().isoformat(),
        }

        if blockchain_stats:
            result["hash_rate"] = blockchain_stats.get("hash_rate")
            result["difficulty"] = blockchain_stats.get("difficulty")
            result["tx_volume"] = blockchain_stats.get("estimated_btc_sent")

        if mempool_data:
            result["mempool_size"] = mempool_data.get("count")
            result["mempool_fees"] = mempool_data.get("fee_rate")

        if blockchair_data:
            data = blockchair_data.get("data", {})
            result["active_addresses"] = data.get("nodes")
            result["large_tx_count"] = data.get("largest_transaction_24h")

        return result

    async def _get_blockchain_stats(self) -> dict | None:
        return await self.fetch_json(self.BLOCKCHAIN_STATS_URL)

    async def _get_mempool_data(self) -> dict | None:
        fees = await self.fetch_json(self.MEMPOOL_FEES_URL)
        stats = await self.fetch_json(self.MEMPOOL_STATS_URL)

        if not fees and not stats:
            return None

        result = {}
        if fees:
            result["fee_rate"] = fees.get("fastestFee")
        if stats:
            result["count"] = stats.get("count")
            result["vsize"] = stats.get("vsize")

        return result

    async def _get_blockchair_data(self) -> dict | None:
        return await self.fetch_json(self.BLOCKCHAIR_STATS_URL)
