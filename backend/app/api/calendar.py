import logging

from fastapi import APIRouter, Query

from app.collectors.economic_calendar import EconomicCalendarCollector
from app.cache import cache_get, cache_set

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market/calendar", tags=["calendar"])

_calendar_collector = EconomicCalendarCollector()


@router.get("/upcoming")
async def get_upcoming_events(days: int = Query(default=14, ge=1, le=90)):
    """Get upcoming economic events."""
    cached = await cache_get(f"calendar:upcoming:{days}")
    if cached is not None:
        return cached
    events = await _calendar_collector.get_upcoming_events(days=days)
    data = {"events": events, "count": len(events)}
    await cache_set(f"calendar:upcoming:{days}", data, 300)
    return data


@router.get("/past")
async def get_past_events(days: int = Query(default=7, ge=1, le=30)):
    """Get past economic events."""
    events = await _calendar_collector.get_past_events(days=days)
    return {"events": events, "count": len(events)}
