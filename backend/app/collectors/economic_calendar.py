"""Economic calendar with hardcoded recurring US macro events + FRED enrichment."""
import logging
from datetime import datetime, timedelta

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

# Major recurring events
RECURRING_EVENTS = [
    # FOMC meetings (~8x/year) - approximate 2026 dates
    {"name": "FOMC Rate Decision", "importance": "high", "months": [1, 3, 5, 6, 7, 9, 11, 12], "day_of_month": "wed_3"},
    # CPI (monthly, ~12th-15th)
    {"name": "CPI (Consumer Price Index)", "importance": "high", "monthly": True, "day_range": (10, 15)},
    # NFP (first Friday of month)
    {"name": "Non-Farm Payrolls (NFP)", "importance": "high", "monthly": True, "first_friday": True},
    # GDP (quarterly, last week of month following quarter end)
    {"name": "GDP (Preliminary)", "importance": "high", "months": [1, 4, 7, 10], "day_range": (25, 30)},
    # PPI (monthly)
    {"name": "PPI (Producer Price Index)", "importance": "medium", "monthly": True, "day_range": (11, 16)},
    # Retail Sales (monthly)
    {"name": "Retail Sales", "importance": "medium", "monthly": True, "day_range": (13, 17)},
    # Jobless Claims (weekly, Thursdays)
    {"name": "Initial Jobless Claims", "importance": "low", "weekly_day": 3},  # Thursday
]


class EconomicCalendarCollector(BaseCollector):
    """Generates upcoming economic events from hardcoded schedule."""

    async def get_upcoming_events(self, days: int = 14) -> list[dict]:
        """Return upcoming economic events in the next N days."""
        now = datetime.utcnow()
        end = now + timedelta(days=days)
        events = []

        for event_def in RECURRING_EVENTS:
            name = event_def["name"]
            importance = event_def["importance"]

            if event_def.get("weekly_day") is not None:
                # Weekly events (e.g., jobless claims on Thursday)
                d = now
                while d <= end:
                    if d.weekday() == event_def["weekly_day"]:
                        events.append({
                            "event_date": d.strftime("%Y-%m-%dT13:30:00Z"),
                            "event_name": name,
                            "country": "US",
                            "importance": importance,
                            "actual": None,
                            "forecast": None,
                            "previous": None,
                            "source": "scheduled",
                        })
                    d += timedelta(days=1)
            elif event_def.get("first_friday"):
                # First Friday of each month in range
                d = now.replace(day=1)
                for _ in range(3):  # check current + next 2 months
                    first_day = d.replace(day=1)
                    # Find first Friday
                    day = first_day
                    while day.weekday() != 4:  # Friday
                        day += timedelta(days=1)
                    if now <= day <= end:
                        events.append({
                            "event_date": day.strftime("%Y-%m-%dT13:30:00Z"),
                            "event_name": name,
                            "country": "US",
                            "importance": importance,
                            "actual": None,
                            "forecast": None,
                            "previous": None,
                            "source": "scheduled",
                        })
                    # Move to next month
                    if d.month == 12:
                        d = d.replace(year=d.year + 1, month=1)
                    else:
                        d = d.replace(month=d.month + 1)
            elif event_def.get("monthly") and event_def.get("day_range"):
                # Monthly events in a day range
                lo, hi = event_def["day_range"]
                mid = (lo + hi) // 2
                d = now.replace(day=1)
                for _ in range(3):
                    try:
                        target = d.replace(day=mid)
                    except ValueError:
                        target = d.replace(day=28)
                    if now <= target <= end:
                        events.append({
                            "event_date": target.strftime("%Y-%m-%dT13:30:00Z"),
                            "event_name": name,
                            "country": "US",
                            "importance": importance,
                            "actual": None,
                            "forecast": None,
                            "previous": None,
                            "source": "scheduled",
                        })
                    if d.month == 12:
                        d = d.replace(year=d.year + 1, month=1)
                    else:
                        d = d.replace(month=d.month + 1)
            elif event_def.get("months"):
                # Specific months (FOMC, GDP)
                lo, hi = event_def.get("day_range", (15, 20))
                mid = (lo + hi) // 2
                for m in event_def["months"]:
                    try:
                        target = now.replace(month=m, day=mid)
                    except ValueError:
                        continue
                    # Check this year and next
                    for y_offset in [0, 1]:
                        t = target.replace(year=now.year + y_offset)
                        if now <= t <= end:
                            events.append({
                                "event_date": t.strftime("%Y-%m-%dT13:30:00Z"),
                                "event_name": name,
                                "country": "US",
                                "importance": importance,
                                "actual": None,
                                "forecast": None,
                                "previous": None,
                                "source": "scheduled",
                            })

        # Sort by date
        events.sort(key=lambda e: e["event_date"])
        return events

    async def get_past_events(self, days: int = 7) -> list[dict]:
        """Return recent past events (stub — could be enriched from DB)."""
        now = datetime.utcnow()
        start = now - timedelta(days=days)
        all_events = await self.get_upcoming_events(days=0)
        # For past events, shift the window
        past = []
        for event_def in RECURRING_EVENTS:
            if event_def.get("weekly_day") is not None:
                d = start
                while d <= now:
                    if d.weekday() == event_def["weekly_day"]:
                        past.append({
                            "event_date": d.strftime("%Y-%m-%dT13:30:00Z"),
                            "event_name": event_def["name"],
                            "country": "US",
                            "importance": event_def["importance"],
                            "actual": None,
                            "forecast": None,
                            "previous": None,
                            "source": "scheduled",
                        })
                    d += timedelta(days=1)
        past.sort(key=lambda e: e["event_date"], reverse=True)
        return past
