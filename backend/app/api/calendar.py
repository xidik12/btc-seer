import logging

from fastapi import APIRouter, Query

from app.collectors.economic_calendar import EconomicCalendarCollector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market/calendar", tags=["calendar"])

_calendar_collector = EconomicCalendarCollector()


@router.get("/upcoming")
async def get_upcoming_events(days: int = Query(default=14, ge=1, le=90)):
    """Get upcoming economic events."""
    events = await _calendar_collector.get_upcoming_events(days=days)
    return {"events": events, "count": len(events)}


@router.get("/past")
async def get_past_events(days: int = Query(default=7, ge=1, le=30)):
    """Get past economic events."""
    events = await _calendar_collector.get_past_events(days=days)
    return {"events": events, "count": len(events)}
