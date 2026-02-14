import asyncio
import logging
from datetime import datetime, timedelta

from app.collectors.base import BaseCollector
from app.collectors.known_entities import KNOWN_ENTITIES, MONITORED_ADDRESSES, identify_any

logger = logging.getLogger(__name__)

# Amount thresholds for severity (BTC -> severity)
SEVERITY_THRESHOLDS = [
    (10000, 10),
    (5000, 9),
    (2000, 8),
    (1000, 7),
    (500, 6),
    (200, 5),
    (100, 4),
]


def calculate_severity(amount_btc: float) -> int:
    for threshold, severity in SEVERITY_THRESHOLDS:
        if amount_btc >= threshold:
            return severity
    return 3


class WhaleCollector(BaseCollector):
    """Whale collector using mempool.space block scanning + BTCScan address monitoring.

    Primary: mempool.space — scans recent blocks for large txs (>100 BTC)
             Already has full vin/vout with addresses, no second API call needed.
    Secondary: BTCScan — monitors known entity wallet addresses for new txs.
    Fallback: Blockchair — tried if mempool.space fails (often IP-banned).
    """

    MEMPOOL_BLOCKS_URL = "https://mempool.space/api/blocks"
    MEMPOOL_BLOCK_TXS_URL = "https://mempool.space/api/block/{block_hash}/txs/{start_index}"
    BTCSCAN_ADDR_URL = "https://btcscan.org/api/address"
    BLOCKCHAIR_TX_URL = "https://api.blockchair.com/bitcoin/transactions"

    # Scan first N txs per block (each page = 25 txs)
    PAGES_PER_BLOCK = 4  # 100 txs per block
    BLOCKS_TO_SCAN = 3   # ~30 min of blocks

    def __init__(self):
        super().__init__()
        self._last_seen_hashes: set = set()
        self._last_scanned_block: int = 0  # track highest block we've scanned
        self._last_entity_check: dict[str, datetime] = {}

    async def collect(self) -> dict:
        """Scan recent Bitcoin blocks for whale transactions (>100 BTC).

        Uses mempool.space /api/blocks + /api/block/{hash}/txs/{start}.
        Each block has ~3000 txs but whale txs are in the first 100 (sorted by fee).
        We scan 3 blocks x 4 pages (100 txs each) = ~300 txs checked per cycle.
        """
        transactions = []

        # Step 1: Get recent blocks
        blocks = await self.fetch_json(self.MEMPOOL_BLOCKS_URL)
        if not blocks or not isinstance(blocks, list):
            logger.warning("mempool.space /blocks failed, trying Blockchair fallback")
            return await self._blockchair_fallback()

        for block in blocks[:self.BLOCKS_TO_SCAN]:
            block_hash = block.get("id", "")
            block_height = block.get("height", 0)

            if not block_hash:
                continue

            # Skip blocks we already scanned
            if block_height <= self._last_scanned_block:
                continue

            # Scan pages of transactions
            for page_start in range(0, self.PAGES_PER_BLOCK * 25, 25):
                url = self.MEMPOOL_BLOCK_TXS_URL.format(
                    block_hash=block_hash, start_index=page_start
                )
                page_txs = await self.fetch_json(url)
                if not page_txs or not isinstance(page_txs, list):
                    break

                for tx in page_txs:
                    tx_hash = tx.get("txid", "")
                    if not tx_hash or tx_hash in self._last_seen_hashes:
                        continue

                    # Calculate total output
                    total_out = sum(
                        vout.get("value", 0) for vout in tx.get("vout", [])
                    )
                    amount_btc = total_out / 1e8

                    if amount_btc < 100:
                        continue

                    # This tx is a whale — process it (mempool.space already has full vin/vout)
                    tx_data = self._process_mempool_tx(tx, block.get("timestamp"))
                    if tx_data:
                        self._last_seen_hashes.add(tx_hash)
                        transactions.append(tx_data)

                if len(page_txs) < 25:
                    break  # last page

                await asyncio.sleep(0.3)  # gentle rate limit

            # Update last scanned block
            if block_height > self._last_scanned_block:
                self._last_scanned_block = block_height

        # Trim seen hashes to avoid memory bloat (keep last 5000)
        if len(self._last_seen_hashes) > 5000:
            self._last_seen_hashes = set(list(self._last_seen_hashes)[-3000:])

        logger.info(f"Whale collector: {len(transactions)} new large txs from block scan")
        return {"transactions": transactions, "count": len(transactions)}

    async def monitor_known_addresses(self) -> dict:
        """Monitor known entity addresses for new transactions via BTCScan.

        Returns new whale-sized transactions from monitored addresses.
        """
        transactions = []
        now = datetime.utcnow()

        for addr in MONITORED_ADDRESSES:
            last_check = self._last_entity_check.get(addr)
            try:
                addr_txs = await self._fetch_address_txs(addr)
                if not addr_txs:
                    continue

                for tx in addr_txs:
                    tx_hash = tx.get("txid", "")
                    if not tx_hash or tx_hash in self._last_seen_hashes:
                        continue

                    total_out = sum(
                        vout.get("value", 0) for vout in tx.get("vout", [])
                    )
                    amount_btc = total_out / 1e8

                    if amount_btc < 100:
                        continue

                    # Check if tx is recent
                    tx_time = tx.get("status", {}).get("block_time")
                    if tx_time and last_check:
                        tx_dt = datetime.utcfromtimestamp(tx_time)
                        if tx_dt < last_check:
                            continue

                    tx_data = self._process_mempool_tx(tx, tx_time)
                    if tx_data:
                        self._last_seen_hashes.add(tx_hash)
                        transactions.append(tx_data)

                self._last_entity_check[addr] = now
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.debug(f"Error monitoring {addr[:12]}...: {e}")

        if transactions:
            logger.info(f"Entity monitor: {len(transactions)} new whale txs from monitored addresses")
        return {"transactions": transactions, "count": len(transactions)}

    # ── Private Methods ──

    def _process_mempool_tx(self, tx: dict, block_timestamp: int | None = None) -> dict | None:
        """Process a mempool.space transaction into a whale dict with entity labels.

        mempool.space tx format has vin[].prevout.scriptpubkey_address and vout[].scriptpubkey_address.
        """
        tx_hash = tx.get("txid", "")

        # Extract input addresses
        input_addrs = []
        for vin in tx.get("vin", []):
            prevout = vin.get("prevout") or {}
            addr = prevout.get("scriptpubkey_address")
            if addr:
                input_addrs.append(addr)

        # Extract output addresses and total value
        output_addrs = []
        total_out = 0
        for vout in tx.get("vout", []):
            addr = vout.get("scriptpubkey_address")
            if addr:
                output_addrs.append(addr)
            total_out += vout.get("value", 0)

        amount_btc = total_out / 1e8
        if amount_btc < 100:
            return None

        # Classify
        direction, from_entity, to_entity, entity_info = self._classify_transaction(
            input_addrs, output_addrs
        )

        # Timestamp
        ts = block_timestamp
        if not ts:
            ts = tx.get("status", {}).get("block_time")
        if ts and isinstance(ts, (int, float)):
            timestamp = datetime.utcfromtimestamp(ts).isoformat()
        else:
            timestamp = datetime.utcnow().isoformat()

        # Pick primary addresses for transaction chaining
        from_addr = input_addrs[0] if input_addrs else None
        # Primary output = largest value output (not change)
        primary_output = max(tx.get("vout", []), key=lambda v: v.get("value", 0), default={})
        to_addr = primary_output.get("scriptpubkey_address")

        return {
            "tx_hash": tx_hash,
            "amount_btc": round(amount_btc, 4),
            "timestamp": timestamp,
            "direction": direction,
            "from_entity": from_entity,
            "to_entity": to_entity,
            "entity_name": entity_info.get("name") if entity_info else None,
            "entity_type": entity_info.get("type") if entity_info else None,
            "entity_wallet": entity_info.get("wallet") if entity_info else None,
            "severity": calculate_severity(amount_btc),
            "from_address": from_addr,
            "to_address": to_addr,
            "raw_data": None,  # don't store full tx to save DB space
            "source": "mempool_blocks",
        }

    async def _fetch_address_txs(self, address: str) -> list[dict] | None:
        """Fetch recent transactions for an address from BTCScan."""
        url = f"{self.BTCSCAN_ADDR_URL}/{address}/txs"
        data = await self.fetch_json(url)
        if isinstance(data, list):
            return data
        return None

    async def _blockchair_fallback(self) -> dict:
        """Fallback: try Blockchair if mempool.space is down (often IP-banned too)."""
        params = {
            "q": "output_total(10000000000..)",
            "s": "time(desc)",
            "limit": "10",
        }
        data = await self.fetch_json(self.BLOCKCHAIR_TX_URL, params=params)
        if not data or not data.get("data"):
            logger.warning("Both mempool.space and Blockchair failed")
            return {"transactions": [], "count": 0}

        transactions = []
        for tx in data.get("data", []):
            tx_hash = tx.get("hash", "")
            if not tx_hash or tx_hash in self._last_seen_hashes:
                continue

            output_total = tx.get("output_total", 0)
            amount_btc = output_total / 1e8
            if amount_btc < 100:
                continue

            self._last_seen_hashes.add(tx_hash)
            transactions.append({
                "tx_hash": tx_hash,
                "amount_btc": round(amount_btc, 4),
                "timestamp": tx.get("time", datetime.utcnow().isoformat()),
                "direction": "unknown",
                "from_entity": "unknown",
                "to_entity": "unknown",
                "entity_name": None,
                "entity_type": None,
                "entity_wallet": None,
                "severity": calculate_severity(amount_btc),
                "from_address": None,
                "to_address": None,
                "raw_data": None,
                "source": "blockchair_fallback",
            })

        return {"transactions": transactions, "count": len(transactions)}

    def _classify_transaction(self, input_addrs: list[str], output_addrs: list[str]) -> tuple[str, str, str, dict | None]:
        """Classify transaction direction and identify entities.

        Returns: (direction, from_entity, to_entity, primary_entity_info)
        """
        from_entity_info = identify_any(input_addrs)
        to_entity_info = identify_any(output_addrs)

        from_entity = from_entity_info["name"] if from_entity_info else "unknown"
        to_entity = to_entity_info["name"] if to_entity_info else "unknown"

        if from_entity_info and not to_entity_info:
            direction = "exchange_out"
            primary_entity = from_entity_info
        elif not from_entity_info and to_entity_info:
            direction = "exchange_in"
            primary_entity = to_entity_info
        elif from_entity_info and to_entity_info:
            direction = "exchange_in"
            primary_entity = to_entity_info
        else:
            direction = "unknown"
            primary_entity = None

        return direction, from_entity, to_entity, primary_entity
