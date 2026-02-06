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

    return {
        "total_events_evaluated": len(events),
        "categories": stats,
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
    categories = {row.category: row.count for row in result.all()}

    return {
        "total_events": total_count,
        "evaluated_events": evaluated_count,
        "sentiment_predictive_count": predictive_count,
        "sentiment_accuracy": round(
            (predictive_count / evaluated_count * 100) if evaluated_count > 0 else 0, 1
        ),
        "categories": categories,
    }
