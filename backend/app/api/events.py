from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, EventImpact
from app.models.event_memory import EventPatternMatcher

router = APIRouter(prefix="/api/events", tags=["events"])
pattern_matcher = EventPatternMatcher()


@router.get("/recent")
async def get_recent_events(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get recent classified events with their measured price impacts."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(EventImpact)
        .where(EventImpact.timestamp >= since)
        .order_by(desc(EventImpact.timestamp))
        .limit(limit)
    )
    events = result.scalars().all()

    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "source": e.source,
                "category": e.category,
                "subcategory": e.subcategory,
                "keywords": e.keywords,
                "severity": e.severity,
                "sentiment_score": e.sentiment_score,
                "price_at_event": e.price_at_event,
                "change_pct_1h": e.change_pct_1h,
                "change_pct_4h": e.change_pct_4h,
                "change_pct_24h": e.change_pct_24h,
                "change_pct_7d": e.change_pct_7d,
                "sentiment_was_predictive": e.sentiment_was_predictive,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/category-stats")
async def get_category_stats(
    session: AsyncSession = Depends(get_session),
):
    """Get average price impact per event category.

    This shows the system's learned knowledge: how each type of event
    historically affects BTC price.
    """
    result = await session.execute(
        select(EventImpact).where(EventImpact.evaluated_1h == True)
    )
    events = result.scalars().all()

    event_dicts = [
        {
            "category": e.category,
            "keywords": e.keywords,
            "change_pct_1h": e.change_pct_1h,
            "change_pct_4h": e.change_pct_4h,
            "change_pct_24h": e.change_pct_24h,
            "sentiment_was_predictive": e.sentiment_was_predictive,
        }
        for e in events
    ]

    stats = pattern_matcher.get_category_stats(event_dicts)

    # Transform dict → array with frontend-expected field names
    categories_list = []
    if isinstance(stats, dict):
        for cat_name, cat_data in stats.items():
            entry = {"category": cat_name, "count": cat_data.get("count", 0)}
            for key in ("avg_1h", "avg_4h", "avg_24h", "avg_7d"):
                tf = key.replace("avg_", "")
                entry[f"avg_impact_{tf}"] = cat_data.get(key, 0.0)
            categories_list.append(entry)
    elif isinstance(stats, list):
        categories_list = stats
    else:
        categories_list = []

    return {
        "total_events_evaluated": len(events),
        "categories": categories_list,
    }


@router.get("/memory")
async def get_event_memory_status(
    session: AsyncSession = Depends(get_session),
):
    """Get the overall status of the event memory system."""
    total = await session.execute(select(func.count(EventImpact.id)))
    total_count = total.scalar()

    evaluated = await session.execute(
        select(func.count(EventImpact.id)).where(EventImpact.evaluated_1h == True)
    )
    evaluated_count = evaluated.scalar()

    predictive = await session.execute(
        select(func.count(EventImpact.id)).where(EventImpact.sentiment_was_predictive == True)
    )
    predictive_count = predictive.scalar()

    # Get category breakdown
    result = await session.execute(
        select(
            EventImpact.category,
            func.count(EventImpact.id).label("count"),
        )
        .group_by(EventImpact.category)
        .order_by(desc("count"))
    )
    cat_rows = result.all()
    num_categories = len(cat_rows)
    most_impactful = cat_rows[0].category if cat_rows else None

    # Compute avg_per_day using rolling 7-day window (not lifetime,
    # which gets skewed by RSS feeds with old published dates)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_count_result = await session.execute(
        select(func.count(EventImpact.id)).where(
            EventImpact.timestamp >= seven_days_ago
        )
    )
    recent_count = recent_count_result.scalar() or 0
    avg_per_day = round(recent_count / 7, 1)

    return {
        "total_events": total_count,
        "evaluated_events": evaluated_count,
        "sentiment_predictive_count": predictive_count,
        "sentiment_accuracy": round(
            (predictive_count / evaluated_count * 100) if evaluated_count > 0 else 0, 1
        ),
        "categories": num_categories,
        "avg_per_day": avg_per_day,
        "most_impactful_category": most_impactful,
    }
