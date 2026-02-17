import logging
from datetime import datetime

from app.collectors.base import BaseCollector
from app.config import settings
from app.database import async_session, WhaleTransaction

logger = logging.getLogger(__name__)

# Threshold: 100 ETH in wei
MIN_ETH_WEI = 100 * 10**18

# Severity based on ETH amount
SEVERITY_THRESHOLDS = [
    (50000, 10),
    (20000, 9),
    (10000, 8),
    (5000, 7),
    (2000, 6),
    (1000, 5),
    (500, 4),
    (200, 3),
]


def calculate_severity(amount_eth: float) -> int:
    for threshold, severity in SEVERITY_THRESHOLDS:
        if amount_eth >= threshold:
            return severity
    return 2


class EthWhaleCollector(BaseCollector):
    """Collects large ETH transfers (>100 ETH) from Etherscan V2 API.

    Strategy: fetch the latest block, iterate its transactions, and filter
    for transfers with value > 100 ETH.  This avoids needing to know
    specific wallet addresses and catches all whale-sized movements.

    Rate limit: 5 calls/sec on the free tier (we make ~1-2 per cycle).
    """

    ETHERSCAN_V2_BASE = "https://api.etherscan.io/v2/api"

    def __init__(self):
        super().__init__()
        self._seen_hashes: set[str] = set()

    async def collect(self) -> dict:
        """Fetch the latest Ethereum block and filter for large value transfers."""
        transactions: list[dict] = []

        # Step 1: Get latest block with full transaction objects
        block = await self._get_latest_block()
        if not block:
            logger.warning("EthWhaleCollector: failed to fetch latest block")
            return {"transactions": [], "count": 0}

        block_number_hex = block.get("number", "0x0")
        block_timestamp_hex = block.get("timestamp", "0x0")

        try:
            block_number = int(block_number_hex, 16)
            block_timestamp = int(block_timestamp_hex, 16)
        except (ValueError, TypeError):
            block_number = 0
            block_timestamp = int(datetime.utcnow().timestamp())

        block_dt = datetime.utcfromtimestamp(block_timestamp)

        # Step 2: Filter transactions for large ETH transfers
        txs = block.get("transactions", [])
        if not isinstance(txs, list):
            return {"transactions": [], "count": 0}

        for tx in txs:
            # Skip if tx is just a hash string (boolean=false was used)
            if isinstance(tx, str):
                continue

            tx_hash = tx.get("hash", "")
            if not tx_hash or tx_hash in self._seen_hashes:
                continue

            value_hex = tx.get("value", "0x0")
            try:
                value_wei = int(value_hex, 16)
            except (ValueError, TypeError):
                continue

            if value_wei < MIN_ETH_WEI:
                continue

            amount_eth = value_wei / 10**18
            from_addr = tx.get("from", "")
            to_addr = tx.get("to", "") or ""

            self._seen_hashes.add(tx_hash)
            transactions.append({
                "tx_hash": tx_hash,
                "amount_eth": round(amount_eth, 4),
                "amount_btc": 0.0,  # Not BTC; stored as amount_btc in WhaleTransaction for compatibility
                "timestamp": block_dt.isoformat(),
                "from_address": from_addr,
                "to_address": to_addr,
                "block_number": block_number,
                "severity": calculate_severity(amount_eth),
                "chain": "ethereum",
                "token_symbol": "ETH",
            })

        # Trim seen hashes to prevent memory bloat
        if len(self._seen_hashes) > 5000:
            self._seen_hashes = set(list(self._seen_hashes)[-3000:])

        logger.info(f"EthWhaleCollector: {len(transactions)} large ETH transfers in block {block_number}")
        return {"transactions": transactions, "count": len(transactions)}

    async def _get_latest_block(self) -> dict | None:
        """Fetch the latest Ethereum block with full transaction objects."""
        params = {
            "chainid": "1",
            "module": "proxy",
            "action": "eth_getBlockByNumber",
            "tag": "latest",
            "boolean": "true",
        }
        if settings.etherscan_api_key:
            params["apikey"] = settings.etherscan_api_key

        data = await self.fetch_json(self.ETHERSCAN_V2_BASE, params=params)
        if not data:
            return None

        # Etherscan V2 wraps proxy results in {"jsonrpc": ..., "result": {...}}
        result = data.get("result")
        if isinstance(result, dict):
            return result
        return None


async def collect_eth_whale_transactions():
    """Scheduled job: collect large ETH whale transfers every 5 minutes."""
    collector = EthWhaleCollector()
    try:
        result = await collector.collect()
        transactions = result.get("transactions", [])

        if not transactions:
            return

        async with async_session() as session:
            stored = 0
            for tx_data in transactions:
                # Check for duplicate
                from sqlalchemy import select
                existing = await session.execute(
                    select(WhaleTransaction.id).where(
                        WhaleTransaction.tx_hash == tx_data["tx_hash"]
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    continue

                whale_tx = WhaleTransaction(
                    tx_hash=tx_data["tx_hash"],
                    timestamp=datetime.fromisoformat(tx_data["timestamp"]),
                    amount_btc=tx_data["amount_eth"],  # Stored in amount_btc column; use token_symbol to distinguish
                    amount_usd=None,
                    direction="unknown",
                    from_entity="unknown",
                    to_entity="unknown",
                    severity=tx_data["severity"],
                    btc_price_at_tx=None,
                    from_address=tx_data.get("from_address"),
                    to_address=tx_data.get("to_address"),
                    source="etherscan_v2",
                    chain="ethereum",
                    token_symbol="ETH",
                    raw_data=None,
                )
                session.add(whale_tx)
                stored += 1

            await session.commit()

        if stored:
            logger.info(f"ETH whale transactions stored: {stored} new")

    except Exception as e:
        logger.error(f"ETH whale collection error: {e}")
    finally:
        await collector.close()
