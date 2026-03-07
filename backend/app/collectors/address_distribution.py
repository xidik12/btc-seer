"""Bitcoin address distribution collector — fetches address balance buckets from Blockchair."""

import logging
from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Address distribution buckets (label, min BTC, max BTC or None for unlimited)
BUCKETS = [
    ("Shrimp",       0,       0.1),
    ("Crab",         0.1,     1),
    ("Octopus",      1,       10),
    ("Fish",         10,      50),
    ("Dolphin",      50,      100),
    ("Shark",        100,     1000),
    ("Whale",        1000,    5000),
    ("Humpback",     5000,    10000),
    ("Mega Whale",   10000,   None),
]

# Blockchair stats fields mapping: field_name -> (min_btc, max_btc) in satoshis
BLOCKCHAIR_FIELDS = {
    "hodling_addresses_count_0.001": (0, 0.001),
    "hodling_addresses_count_0.01": (0.001, 0.01),
    "hodling_addresses_count_0.1": (0.01, 0.1),
    "hodling_addresses_count_1": (0.1, 1),
    "hodling_addresses_count_10": (1, 10),
    "hodling_addresses_count_100": (10, 100),
    "hodling_addresses_count_1000": (100, 1000),
    "hodling_addresses_count_10000": (1000, 10000),
    "hodling_addresses_count_100000": (10000, 100000),
}


class AddressDistributionCollector(BaseCollector):
    """Fetches Bitcoin address distribution from Blockchair stats API."""

    BLOCKCHAIR_URL = "https://api.blockchair.com/bitcoin/stats"

    async def collect(self) -> dict:
        data = await self.fetch_json(self.BLOCKCHAIR_URL)
        if not data or "data" not in data:
            logger.warning("Blockchair stats returned no data")
            return {"buckets": [], "total_addresses": 0, "total_with_balance": 0}

        stats = data["data"]

        # Raw counts from Blockchair
        raw = {}
        for field, (lo, hi) in BLOCKCHAIR_FIELDS.items():
            raw[(lo, hi)] = stats.get(field, 0) or 0

        # Aggregate into our 9 buckets
        buckets = []
        total_with_balance = 0

        for label, bmin, bmax in BUCKETS:
            count = 0
            for (lo, hi), val in raw.items():
                # Check overlap: bucket [bmin, bmax) overlaps with raw range [lo, hi)
                if bmax is None:
                    # Mega Whale: bmin+ — include any raw range where hi > bmin
                    if hi > bmin:
                        count += val
                elif lo >= bmin and hi <= (bmax if bmax else float('inf')):
                    count += val
                elif lo < bmin < hi:
                    # Partial overlap — approximate proportionally
                    overlap = min(hi, bmax or hi) - bmin
                    total_range = hi - lo
                    count += int(val * (overlap / total_range)) if total_range > 0 else 0
                elif lo < (bmax or float('inf')) and hi > bmin and lo >= bmin:
                    count += val

            total_with_balance += count
            btc_range = f"{bmin}+" if bmax is None else f"{bmin}-{bmax}"
            buckets.append({
                "label": label,
                "btc_range": btc_range,
                "count": count,
                "pct": 0,  # calculated below
            })

        # Calculate percentages
        for b in buckets:
            b["pct"] = round(b["count"] / total_with_balance * 100, 2) if total_with_balance > 0 else 0

        total_addresses = stats.get("hodling_addresses", 0) or total_with_balance

        return {
            "buckets": buckets,
            "total_addresses": total_addresses,
            "total_with_balance": total_with_balance,
        }
