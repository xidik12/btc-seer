import logging
from datetime import datetime

from app.collectors.base import BaseCollector
from app.config import settings
from app.database import async_session, WhaleTransaction, AddressLabel
from sqlalchemy import select

logger = logging.getLogger(__name__)

ARKHAM_BASE_URL = "https://api.arkhamintelligence.com"


class ArkhamCollector(BaseCollector):
    """Polls Arkham Intelligence for large BTC transfers with entity labels.

    Gracefully degrades to no-op if arkham_api_key is not configured.
    """

    def __init__(self):
        super().__init__()
        self._seen_tx_ids: set = set()

    @property
    def _enabled(self) -> bool:
        return bool(settings.arkham_api_key)

    def _headers(self) -> dict:
        return {
            "API-Key": settings.arkham_api_key,
            "Accept": "application/json",
        }

    async def collect(self) -> dict:
        """Poll Arkham for large BTC transfers >$10M."""
        if not self._enabled:
            return {"transactions": [], "count": 0, "status": "disabled"}

        transactions = await self._fetch_large_transfers()
        if transactions:
            await self._store_transfers(transactions)

        logger.info(f"Arkham: {len(transactions)} large transfers fetched")
        return {"transactions": transactions, "count": len(transactions)}

    async def _fetch_large_transfers(self) -> list[dict]:
        """Fetch large BTC transfers from Arkham /transfers endpoint."""
        url = f"{ARKHAM_BASE_URL}/transfers"
        params = {
            "base": "bitcoin",
            "usdGte": "10000000",
            "limit": "50",
        }

        data = await self.fetch_json(url, params=params, headers=self._headers())
        if not data:
            return []

        transfers = data.get("transfers", [])
        if not isinstance(transfers, list):
            return []

        results = []
        for tx in transfers:
            tx_id = tx.get("transactionHash") or tx.get("id", "")
            if not tx_id or tx_id in self._seen_tx_ids:
                continue

            self._seen_tx_ids.add(tx_id)

            # Extract entity labels
            from_entity = tx.get("fromAddress", {})
            to_entity = tx.get("toAddress", {})
            from_name = from_entity.get("arkhamEntity", {}).get("name", "unknown") if isinstance(from_entity, dict) else "unknown"
            to_name = to_entity.get("arkhamEntity", {}).get("name", "unknown") if isinstance(to_entity, dict) else "unknown"
            from_addr = from_entity.get("address", "") if isinstance(from_entity, dict) else ""
            to_addr = to_entity.get("address", "") if isinstance(to_entity, dict) else ""

            # Determine entity type from Arkham labels
            entity_name = from_name if from_name != "unknown" else to_name
            entity_type = self._classify_entity(from_entity, to_entity)

            amount_usd = tx.get("unitValue", 0)
            amount_btc = tx.get("tokenValue", 0) or (amount_usd / 97000 if amount_usd else 0)

            # Determine direction
            if self._is_exchange(to_entity):
                direction = "exchange_in"
            elif self._is_exchange(from_entity):
                direction = "exchange_out"
            else:
                direction = "whale_to_whale"

            timestamp = tx.get("blockTimestamp", "")
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.utcfromtimestamp(timestamp / 1000).isoformat()

            severity = 10 if amount_btc >= 10000 else 9 if amount_btc >= 5000 else 8 if amount_btc >= 2000 else 7 if amount_btc >= 1000 else 6

            results.append({
                "tx_hash": tx_id[:64],
                "amount_btc": round(amount_btc, 4),
                "amount_usd": amount_usd,
                "timestamp": timestamp,
                "direction": direction,
                "from_entity": from_name,
                "to_entity": to_name,
                "entity_name": entity_name if entity_name != "unknown" else None,
                "entity_type": entity_type,
                "from_address": from_addr,
                "to_address": to_addr,
                "severity": severity,
                "source": "arkham",
            })

        # Trim seen set to avoid memory bloat
        if len(self._seen_tx_ids) > 5000:
            self._seen_tx_ids = set(list(self._seen_tx_ids)[-3000:])

        return results

    async def resolve_address(self, address: str) -> dict | None:
        """Use Arkham to identify who owns a Bitcoin address."""
        if not self._enabled:
            return None

        url = f"{ARKHAM_BASE_URL}/intelligence/address/{address}"
        data = await self.fetch_json(url, headers=self._headers())
        if not data:
            return None

        entity = data.get("arkhamEntity", {})
        if entity:
            return {
                "name": entity.get("name"),
                "type": entity.get("type", "unknown"),
                "source": "arkham",
                "confidence": 0.9,
            }
        return None

    async def enrich_unknown_addresses(self) -> int:
        """Resolve unknown whale tx addresses using Arkham Intelligence API."""
        if not self._enabled:
            return 0

        resolved = 0
        async with async_session() as session:
            # Find whale txs with unknown entities that have addresses
            result = await session.execute(
                select(WhaleTransaction).where(
                    WhaleTransaction.entity_name.is_(None),
                    WhaleTransaction.from_address.isnot(None),
                ).limit(20)
            )
            unknown_txs = result.scalars().all()

            for tx in unknown_txs:
                for addr in [tx.from_address, tx.to_address]:
                    if not addr:
                        continue

                    label = await self.resolve_address(addr)
                    if label and label.get("name"):
                        tx.entity_name = label["name"]
                        tx.entity_type = label.get("type")
                        resolved += 1

                        # Cache the label
                        existing = await session.execute(
                            select(AddressLabel).where(AddressLabel.address == addr)
                        )
                        if not existing.scalar_one_or_none():
                            session.add(AddressLabel(
                                address=addr,
                                entity_name=label["name"],
                                entity_type=label.get("type"),
                                source="arkham",
                                confidence=label.get("confidence", 0.9),
                            ))
                        break  # Found label, move to next tx

            await session.commit()

        if resolved:
            logger.info(f"Arkham: resolved {resolved} unknown whale addresses")
        return resolved

    async def _store_transfers(self, transfers: list[dict]) -> None:
        """Store Arkham transfers as WhaleTransactions."""
        async with async_session() as session:
            for tx_data in transfers:
                existing = await session.execute(
                    select(WhaleTransaction.id).where(WhaleTransaction.tx_hash == tx_data["tx_hash"])
                )
                if existing.scalar_one_or_none() is not None:
                    continue

                whale_tx = WhaleTransaction(
                    tx_hash=tx_data["tx_hash"],
                    timestamp=datetime.fromisoformat(tx_data["timestamp"]) if isinstance(tx_data["timestamp"], str) and tx_data["timestamp"] else datetime.utcnow(),
                    amount_btc=tx_data["amount_btc"],
                    amount_usd=tx_data.get("amount_usd"),
                    direction=tx_data["direction"],
                    from_entity=tx_data["from_entity"],
                    to_entity=tx_data["to_entity"],
                    entity_name=tx_data.get("entity_name"),
                    entity_type=tx_data.get("entity_type"),
                    severity=tx_data.get("severity", 6),
                    from_address=tx_data.get("from_address"),
                    to_address=tx_data.get("to_address"),
                    source="arkham",
                )
                session.add(whale_tx)

            await session.commit()

    @staticmethod
    def _is_exchange(entity: dict) -> bool:
        if not isinstance(entity, dict):
            return False
        arkham = entity.get("arkhamEntity", {})
        entity_type = (arkham.get("type") or "").lower()
        return "exchange" in entity_type

    @staticmethod
    def _classify_entity(from_entity: dict, to_entity: dict) -> str | None:
        for entity in [from_entity, to_entity]:
            if not isinstance(entity, dict):
                continue
            arkham = entity.get("arkhamEntity", {})
            entity_type = (arkham.get("type") or "").lower()
            if "exchange" in entity_type:
                return "exchange"
            if "fund" in entity_type or "institution" in entity_type or "corporate" in entity_type:
                return "institution"
            if "government" in entity_type:
                return "government"
        return None


# Module-level instance
arkham_collector = ArkhamCollector()


async def collect_arkham_transfers():
    """Scheduler entry point for Arkham Intelligence collection."""
    try:
        result = await arkham_collector.collect()
        # Also try to enrich unknown addresses
        await arkham_collector.enrich_unknown_addresses()
        logger.info(f"Arkham collection done: {result.get('count', 0)} transfers")
    except Exception as e:
        logger.error(f"Arkham collection failed: {e}", exc_info=True)
