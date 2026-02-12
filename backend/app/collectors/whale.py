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
    """Hybrid whale collector using Blockchair (discovery) + BTCScan (details) + mempool.space (fallback).

    Source 1: Blockchair — discovers large tx hashes (>100 BTC)
    Source 2: BTCScan — fetches full tx details (addresses) and monitors known entity wallets
    Source 3: mempool.space — fallback for whale-size mempool txs if Blockchair fails
    """

    BLOCKCHAIR_TX_URL = "https://api.blockchair.com/bitcoin/transactions"
    BTCSCAN_TX_URL = "https://btcscan.org/api/tx"
    BTCSCAN_ADDR_URL = "https://btcscan.org/api/address"
    MEMPOOL_RECENT_URL = "https://mempool.space/api/mempool/recent"

    def __init__(self):
        super().__init__()
        self._last_seen_hashes: set = set()
        self._last_entity_check: dict[str, datetime] = {}  # addr -> last checked time

    async def collect(self) -> dict:
        """Collect large BTC transactions from Blockchair, enriched via BTCScan."""
        transactions = []

        # Step 1: Blockchair for large tx discovery
        blockchair_txs = await self._fetch_blockchair_large_txs()
        if blockchair_txs is not None:
            for tx_hash, raw_tx in blockchair_txs:
                # Step 2: BTCScan for address details
                tx_detail = await self._fetch_tx_details(tx_hash)
                if tx_detail:
                    tx_data = self._process_tx_detail(tx_hash, tx_detail, raw_tx)
                    if tx_data:
                        transactions.append(tx_data)
                await asyncio.sleep(0.5)  # rate limit BTCScan
        else:
            # Fallback: mempool.space for large mempool txs
            mempool_txs = await self._fetch_mempool_whales()
            for tx_data in mempool_txs:
                transactions.append(tx_data)

        logger.info(f"Whale collector: {len(transactions)} new large txs found")
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

                    # Calculate total output value
                    total_out = sum(
                        vout.get("value", 0)
                        for vout in tx.get("vout", [])
                    )
                    amount_btc = total_out / 1e8

                    if amount_btc < 100:
                        continue

                    # Check if tx is recent (within last 15 min if we have a last_check)
                    tx_time = tx.get("status", {}).get("block_time")
                    if tx_time and last_check:
                        tx_dt = datetime.utcfromtimestamp(tx_time)
                        if tx_dt < last_check:
                            continue

                    tx_data = self._process_tx_detail(tx_hash, tx, None)
                    if tx_data:
                        self._last_seen_hashes.add(tx_hash)
                        transactions.append(tx_data)

                self._last_entity_check[addr] = now
                await asyncio.sleep(0.5)  # rate limit

            except Exception as e:
                logger.debug(f"Error monitoring {addr[:12]}...: {e}")

        if transactions:
            logger.info(f"Entity monitor: {len(transactions)} new whale txs from monitored addresses")
        return {"transactions": transactions, "count": len(transactions)}

    # ── Private Methods ──

    async def _fetch_blockchair_large_txs(self) -> list[tuple[str, dict]] | None:
        """Fetch large tx hashes from Blockchair. Returns list of (hash, raw_data) or None on failure."""
        params = {
            "q": "output_total(10000000000..)",
            "s": "time(desc)",
            "limit": "10",
        }

        data = await self.fetch_json(self.BLOCKCHAIR_TX_URL, params=params)
        if not data:
            return None

        raw_txs = data.get("data", [])
        if not raw_txs:
            return None

        results = []
        new_hashes = set()

        for tx in raw_txs:
            tx_hash = tx.get("hash", "")
            if not tx_hash:
                continue
            new_hashes.add(tx_hash)
            if tx_hash not in self._last_seen_hashes:
                results.append((tx_hash, tx))

        self._last_seen_hashes = new_hashes
        return results

    async def _fetch_tx_details(self, tx_hash: str) -> dict | None:
        """Fetch full transaction details from BTCScan (free, includes addresses)."""
        url = f"{self.BTCSCAN_TX_URL}/{tx_hash}"
        return await self.fetch_json(url)

    async def _fetch_address_txs(self, address: str) -> list[dict] | None:
        """Fetch recent transactions for an address from BTCScan."""
        url = f"{self.BTCSCAN_ADDR_URL}/{address}/txs"
        data = await self.fetch_json(url)
        if isinstance(data, list):
            return data
        return None

    async def _fetch_mempool_whales(self) -> list[dict]:
        """Fallback: check mempool.space for whale-size mempool transactions."""
        data = await self.fetch_json(self.MEMPOOL_RECENT_URL)
        if not data or not isinstance(data, list):
            return []

        transactions = []
        for tx in data:
            value = tx.get("value", 0)
            amount_btc = value / 1e8

            if amount_btc < 100:
                continue

            tx_hash = tx.get("txid", "")
            if not tx_hash or tx_hash in self._last_seen_hashes:
                continue

            self._last_seen_hashes.add(tx_hash)
            transactions.append({
                "tx_hash": tx_hash,
                "amount_btc": round(amount_btc, 4),
                "timestamp": datetime.utcnow().isoformat(),
                "direction": "unknown",
                "from_entity": "unknown",
                "to_entity": "unknown",
                "entity_name": None,
                "entity_type": None,
                "entity_wallet": None,
                "severity": calculate_severity(amount_btc),
                "raw_data": tx,
                "source": "mempool",
            })

        if transactions:
            logger.info(f"Mempool fallback: {len(transactions)} whale-size txs found")
        return transactions

    def _process_tx_detail(self, tx_hash: str, tx_detail: dict, blockchair_raw: dict | None) -> dict | None:
        """Process a BTCScan tx detail into a whale transaction dict with entity labels."""
        # Extract input addresses
        input_addrs = []
        for vin in tx_detail.get("vin", []):
            addr = vin.get("prevout", {}).get("scriptpubkey_address")
            if addr:
                input_addrs.append(addr)

        # Extract output addresses
        output_addrs = []
        total_out = 0
        for vout in tx_detail.get("vout", []):
            addr = vout.get("scriptpubkey_address")
            if addr:
                output_addrs.append(addr)
            total_out += vout.get("value", 0)

        amount_btc = total_out / 1e8
        if amount_btc < 100:
            return None

        # Classify using known entities
        direction, from_entity, to_entity, entity_info = self._classify_transaction(input_addrs, output_addrs)

        # Extract timestamp
        timestamp = ""
        status = tx_detail.get("status", {})
        block_time = status.get("block_time")
        if block_time:
            timestamp = datetime.utcfromtimestamp(block_time).isoformat()
        elif blockchair_raw:
            timestamp = blockchair_raw.get("time", "")

        return {
            "tx_hash": tx_hash,
            "amount_btc": round(amount_btc, 4),
            "timestamp": timestamp or datetime.utcnow().isoformat(),
            "direction": direction,
            "from_entity": from_entity,
            "to_entity": to_entity,
            "entity_name": entity_info.get("name") if entity_info else None,
            "entity_type": entity_info.get("type") if entity_info else None,
            "entity_wallet": entity_info.get("wallet") if entity_info else None,
            "severity": calculate_severity(amount_btc),
            "raw_data": blockchair_raw,
            "source": "btcscan",
        }

    def _classify_transaction(self, input_addrs: list[str], output_addrs: list[str]) -> tuple[str, str, str, dict | None]:
        """Classify transaction direction and identify entities.

        Returns: (direction, from_entity, to_entity, primary_entity_info)
        """
        from_entity_info = identify_any(input_addrs)
        to_entity_info = identify_any(output_addrs)

        from_entity = from_entity_info["name"] if from_entity_info else "unknown"
        to_entity = to_entity_info["name"] if to_entity_info else "unknown"

        # Determine direction
        if from_entity_info and not to_entity_info:
            direction = "exchange_out"
            primary_entity = from_entity_info
        elif not from_entity_info and to_entity_info:
            direction = "exchange_in"
            primary_entity = to_entity_info
        elif from_entity_info and to_entity_info:
            direction = "exchange_in"  # inter-entity transfer
            primary_entity = to_entity_info
        else:
            direction = "unknown"
            primary_entity = None

        return direction, from_entity, to_entity, primary_entity
