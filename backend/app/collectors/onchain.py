import logging

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class OnChainCollector(BaseCollector):
    """Collects Bitcoin on-chain metrics from blockchain.com, mempool.space, and blockchair."""

    BLOCKCHAIN_STATS_URL = "https://api.blockchain.info/stats"
    MEMPOOL_FEES_URL = "https://mempool.space/api/v1/fees/recommended"
    MEMPOOL_STATS_URL = "https://mempool.space/api/mempool"
    BLOCKCHAIR_STATS_URL = "https://api.blockchair.com/bitcoin/stats"

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> dict:
        """Collect on-chain data from multiple sources with fallbacks."""
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
            "exchange_reserve": None,
            "large_tx_count": None,
            "timestamp": self.now().isoformat(),
        }

        # blockchain.info — hash_rate (GH/s), difficulty, tx volume
        if blockchain_stats:
            raw_hr = blockchain_stats.get("hash_rate")
            if raw_hr:
                result["hash_rate"] = round(raw_hr / 1e9, 2)  # GH/s → EH/s
            result["difficulty"] = blockchain_stats.get("difficulty")
            result["tx_volume"] = blockchain_stats.get("estimated_btc_sent")
            result["active_addresses"] = blockchain_stats.get("n_unique_addresses")

        # mempool.space — fees + unconfirmed tx count
        if mempool_data:
            result["mempool_size"] = mempool_data.get("count")
            result["mempool_fees"] = mempool_data.get("fee_rate")

        # blockchair — richest source: transactions_24h, nodes, market data
        if blockchair_data:
            data = blockchair_data.get("data", {})

            result["large_tx_count"] = data.get("transactions_24h")

            if result["active_addresses"] is None:
                result["active_addresses"] = data.get("nodes")

            if result["mempool_size"] is None:
                result["mempool_size"] = data.get("mempool_transactions")

            if result["hash_rate"] is None:
                raw = data.get("hashrate_24h")
                if raw:
                    try:
                        result["hash_rate"] = round(int(raw) / 1e18, 2)  # H/s → EH/s
                    except (ValueError, TypeError):
                        pass

            if result["difficulty"] is None:
                result["difficulty"] = data.get("difficulty")

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
