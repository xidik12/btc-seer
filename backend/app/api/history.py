from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case, cast, Date, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Prediction
from app.cache import cache_get, cache_set

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/accuracy")
async def get_accuracy(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    """Get prediction accuracy statistics (SQL aggregation, cached 60s)."""
    cached = await cache_get(f"history:accuracy:{days}")
    if cached is not None:
        return cached

    since = datetime.utcnow() - timedelta(days=days)

    # Overall counts via SQL
    overall_result = await session.execute(
        select(
            func.count().label("total"),
            func.count().filter(Prediction.was_correct == True).label("correct"),
        )
        .where(Prediction.timestamp >= since)
        .where(Prediction.was_correct.isnot(None))
    )
    overall = overall_result.first()
    total = overall.total if overall else 0
    correct = overall.correct if overall else 0

    if total == 0:
        return {
            "days": days,
            "total": 0,
            "accuracy": None,
            "by_timeframe": {},
        }

    # By timeframe via SQL
    tf_result = await session.execute(
        select(
            Prediction.timeframe,
            func.count().label("total"),
            func.count().filter(Prediction.was_correct == True).label("correct"),
        )
        .where(Prediction.timestamp >= since)
        .where(Prediction.was_correct.isnot(None))
        .group_by(Prediction.timeframe)
    )
    by_timeframe = {}
    for row in tf_result:
        by_timeframe[row.timeframe] = {
            "total": row.total,
            "correct": row.correct,
            "accuracy_pct": round(row.correct / row.total * 100, 1) if row.total > 0 else None,
        }
    # Ensure all timeframes present
    for tf in ["1h", "4h", "24h"]:
        if tf not in by_timeframe:
            by_timeframe[tf] = {"total": 0, "correct": 0, "accuracy_pct": None}

    # By confidence level via SQL
    conf_result = await session.execute(
        select(
            case(
                (Prediction.confidence >= 70, "high"),
                (Prediction.confidence >= 40, "medium"),
                else_="low",
            ).label("level"),
            func.count().label("total"),
            func.count().filter(Prediction.was_correct == True).label("correct"),
        )
        .where(Prediction.timestamp >= since)
        .where(Prediction.was_correct.isnot(None))
        .group_by("level")
    )
    by_confidence = {}
    for row in conf_result:
        by_confidence[row.level] = {
            "total": row.total,
            "correct": row.correct,
            "accuracy_pct": round(row.correct / row.total * 100, 1) if row.total > 0 else None,
        }
    for level in ["high", "medium", "low"]:
        if level not in by_confidence:
            by_confidence[level] = {"total": 0, "correct": 0, "accuracy_pct": None}

    # Daily trend via SQL (limited to last 90 days max for performance)
    daily_sql = text("""
        SELECT
            CAST(timestamp AS DATE) as day,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE was_correct = true) as correct
        FROM predictions
        WHERE timestamp >= :since AND was_correct IS NOT NULL
        GROUP BY CAST(timestamp AS DATE)
        ORDER BY day
    """)
    daily_result = await session.execute(daily_sql, {"since": since})
    daily_trend = [
        {
            "date": str(row.day),
            "accuracy_pct": round(row.correct / row.total * 100, 1),
            "accuracy": round(row.correct / row.total * 100, 1),
            "total": row.total,
        }
        for row in daily_result
    ]

    overall_pct = round(correct / total * 100, 1)

    response = {
        "days": days,
        "total": total,
        "correct": correct,
        "accuracy_pct": overall_pct,
        "overall": overall_pct,
        "total_predictions": total,
        "by_timeframe": by_timeframe,
        "by_confidence": by_confidence,
        "daily_trend": daily_trend,
    }
    await cache_set(f"history:accuracy:{days}", response, 60)
    return response
