"""Bitcoin address distribution collector — scrapes BitInfoCharts for balance buckets."""

import logging
import re
from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Our display buckets: (label, min_btc, max_btc or None)
BUCKETS = [
    ("Dust",         0,       0.001),
    ("Micro",        0.001,   0.01),
    ("Shrimp",       0.01,    0.1),
    ("Crab",         0.1,     1),
    ("Octopus",      1,       10),
    ("Fish",         10,      50),
    ("Dolphin",      50,      100),
    ("Shark",        100,     1_000),
    ("Whale",        1_000,   5_000),
    ("Humpback",     5_000,   10_000),
    ("Mega Whale",   10_000,  None),
]


class AddressDistributionCollector(BaseCollector):
    """Scrapes Bitcoin address distribution from BitInfoCharts."""

    URL = "https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html"

    async def collect(self) -> dict:
        session = await self.get_session()
        try:
            async with session.get(
                self.URL,
                headers={"User-Agent": "Mozilla/5.0 (compatible; BTCSeer/1.0)"},
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"BitInfoCharts returned {resp.status}")
                    return {"buckets": [], "total_addresses": 0, "total_with_balance": 0}
                html = await resp.text()
        except Exception as e:
            logger.error(f"BitInfoCharts fetch error: {e}")
            return {"buckets": [], "total_addresses": 0, "total_with_balance": 0}

        # Parse raw tiers from HTML table
        # Matches: (0 - 0.00001) or [0.001 - 0.01) with data-val count
        pattern = r"<td[^>]*>[\[\(]([\d.,]+)\s*-\s*([\d.,]+)[\]\)]?</td><td[^>]*data-val='(\d+)'>"
        matches = re.findall(pattern, html)

        if not matches:
            logger.warning("BitInfoCharts: could not parse distribution table")
            return {"buckets": [], "total_addresses": 0, "total_with_balance": 0}

        # Build raw tiers: list of (lo_btc, hi_btc, count)
        raw_tiers = []
        for lo_str, hi_str, count_str in matches:
            lo = float(lo_str.replace(",", ""))
            hi = float(hi_str.replace(",", ""))
            count = int(count_str)
            raw_tiers.append((lo, hi, count))

        # Aggregate raw tiers into our 11 display buckets
        buckets = []
        total_with_balance = 0

        for label, bmin, bmax in BUCKETS:
            count = 0
            for lo, hi, val in raw_tiers:
                if val == 0:
                    continue

                # Skip dust tier (0 - 0.00001) for "with balance" count
                # but still include in Shrimp bucket

                # Determine overlap between raw tier [lo, hi) and bucket [bmin, bmax)
                eff_max = bmax if bmax is not None else float("inf")

                if lo >= eff_max or hi <= bmin:
                    # No overlap
                    continue

                if lo >= bmin and hi <= eff_max:
                    # Fully contained
                    count += val
                else:
                    # Partial overlap — approximate proportionally (log scale would be better
                    # but linear is fine for display purposes)
                    overlap_lo = max(lo, bmin)
                    overlap_hi = min(hi, eff_max)
                    tier_range = hi - lo
                    if tier_range > 0:
                        fraction = (overlap_hi - overlap_lo) / tier_range
                        count += int(val * fraction)

            total_with_balance += count
            btc_range = f"{bmin}+" if bmax is None else f"{bmin}-{bmax}"
            buckets.append({
                "label": label,
                "btc_range": btc_range,
                "count": count,
                "pct": 0,
            })

        # Calculate percentages
        for b in buckets:
            b["pct"] = round(b["count"] / total_with_balance * 100, 2) if total_with_balance > 0 else 0

        return {
            "buckets": buckets,
            "total_addresses": total_with_balance,
            "total_with_balance": total_with_balance,
        }
