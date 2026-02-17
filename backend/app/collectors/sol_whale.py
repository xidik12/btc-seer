import logging
from datetime import datetime

from app.collectors.base import BaseCollector
from app.config import settings
from app.database import async_session, WhaleTransaction

logger = logging.getLogger(__name__)

# Threshold: 1000 SOL
MIN_SOL = 1000

# Severity based on SOL amount
SEVERITY_THRESHOLDS = [
    (100000, 10),
    (50000, 9),
    (20000, 8),
    (10000, 7),
    (5000, 6),
    (2000, 5),
    (1000, 4),
]


def calculate_severity(amount_sol: float) -> int:
    for threshold, severity in SEVERITY_THRESHOLDS:
        if amount_sol >= threshold:
            return severity
    return 3


class SolWhaleCollector(BaseCollector):
    """Collects large SOL transfers (>1000 SOL) from Solscan API.

    Uses the public Solscan API to fetch recent transactions and filters
    for large SOL transfers.  If a Pro API key is configured, uses the
    Pro endpoint for better rate limits (10M free Computing Units).

    Fallback: public-api.solscan.io (no auth required, lower limits).
    """

    PRO_API_URL = "https://pro-api.solscan.io/v2.0/transaction/last"
    PUBLIC_API_URL = "https://public-api.solscan.io/transaction/last"

    # SOL has 9 decimal places (lamports)
    LAMPORTS_PER_SOL = 10**9

    def __init__(self):
        super().__init__()
        self._seen_hashes: set[str] = set()

    async def collect(self) -> dict:
        """Fetch recent Solana transactions and filter for large SOL transfers."""
        transactions: list[dict] = []

        tx_list = await self._get_recent_transactions()
        if not tx_list:
            logger.warning("SolWhaleCollector: failed to fetch recent transactions")
            return {"transactions": [], "count": 0}

        for tx in tx_list:
            tx_hash = tx.get("txHash") or tx.get("signature") or ""
            if not tx_hash or tx_hash in self._seen_hashes:
                continue

            # Extract SOL amount -- different field names depending on API version
            lamports = tx.get("lamport") or tx.get("lamports") or 0
            amount_sol = lamports / self.LAMPORTS_PER_SOL

            if amount_sol < MIN_SOL:
                continue

            # Parse timestamp
            block_time = tx.get("blockTime") or tx.get("block_time")
            if block_time:
                try:
                    tx_dt = datetime.utcfromtimestamp(int(block_time))
                except (ValueError, TypeError, OSError):
                    tx_dt = datetime.utcnow()
            else:
                tx_dt = datetime.utcnow()

            src = tx.get("src") or tx.get("signer") or ""
            dst = tx.get("dst") or ""

            self._seen_hashes.add(tx_hash)
            transactions.append({
                "tx_hash": tx_hash,
                "amount_sol": round(amount_sol, 4),
                "amount_btc": 0.0,  # Compatibility; use token_symbol to distinguish
                "timestamp": tx_dt.isoformat(),
                "from_address": src,
                "to_address": dst,
                "severity": calculate_severity(amount_sol),
                "chain": "solana",
                "token_symbol": "SOL",
                "status": tx.get("status", ""),
            })

        # Trim seen hashes
        if len(self._seen_hashes) > 5000:
            self._seen_hashes = set(list(self._seen_hashes)[-3000:])

        logger.info(f"SolWhaleCollector: {len(transactions)} large SOL transfers found")
        return {"transactions": transactions, "count": len(transactions)}

    async def _get_recent_transactions(self) -> list[dict] | None:
        """Fetch recent Solana transactions from Solscan."""
        # Try Pro API first if key is available
        if settings.solscan_api_key:
            headers = {"token": settings.solscan_api_key}
            data = await self.fetch_json(
                self.PRO_API_URL,
                params={"limit": "40"},
                headers=headers,
            )
            if data:
                # Pro API returns {"success": true, "data": [...]}
                if isinstance(data, dict) and "data" in data:
                    result = data["data"]
                    if isinstance(result, list):
                        return result
                # Or may return a list directly
                if isinstance(data, list):
                    return data

        # Fallback to public API (no auth)
        data = await self.fetch_json(
            self.PUBLIC_API_URL,
            params={"limit": "40"},
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("data", data.get("result", []))
        return None


async def collect_sol_whale_transactions():
    """Scheduled job: collect large SOL whale transfers every 5 minutes."""
    collector = SolWhaleCollector()
    try:
        result = await collector.collect()
        transactions = result.get("transactions", [])

        if not transactions:
            return

        async with async_session() as session:
            from sqlalchemy import select

            stored = 0
            for tx_data in transactions:
                # Deduplicate by tx_hash
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
                    amount_btc=tx_data["amount_sol"],  # Stored in amount_btc column; token_symbol distinguishes
                    amount_usd=None,
                    direction="unknown",
                    from_entity="unknown",
                    to_entity="unknown",
                    severity=tx_data["severity"],
                    btc_price_at_tx=None,
                    from_address=tx_data.get("from_address"),
                    to_address=tx_data.get("to_address"),
                    source="solscan",
                    chain="solana",
                    token_symbol="SOL",
                    raw_data=None,
                )
                session.add(whale_tx)
                stored += 1

            await session.commit()

        if stored:
            logger.info(f"SOL whale transactions stored: {stored} new")

    except Exception as e:
        logger.error(f"SOL whale collection error: {e}")
    finally:
        await collector.close()
