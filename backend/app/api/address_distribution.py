"""On-chain API — address distribution and related endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter

from app.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onchain", tags=["onchain"])


@router.get("/address-distribution")
async def get_address_distribution():
    """Bitcoin address distribution by balance bucket."""
    cached = await cache_get("btc:address_distribution")
    if cached is not None:
        return cached

    # On-demand fallback — fetch live
    from app.collectors.address_distribution import AddressDistributionCollector

    collector = AddressDistributionCollector()
    try:
        data = await collector.collect()
        data["timestamp"] = datetime.utcnow().isoformat()
        await cache_set("btc:address_distribution", data, 21600)  # 6h TTL
        return data
    finally:
        await collector.close()
