from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Prediction

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/accuracy")
async def get_accuracy(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    """Get prediction accuracy statistics."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(Prediction)
        .where(Prediction.timestamp >= since)
        .where(Prediction.was_correct.isnot(None))
    )
    predictions = result.scalars().all()

    if not predictions:
        return {
            "days": days,
            "total": 0,
            "accuracy": None,
            "by_timeframe": {},
        }

    # Overall accuracy
    correct = sum(1 for p in predictions if p.was_correct)
    total = len(predictions)

    # By timeframe
    by_timeframe = {}
    for tf in ["1h", "4h", "24h"]:
        tf_preds = [p for p in predictions if p.timeframe == tf]
        tf_correct = sum(1 for p in tf_preds if p.was_correct)
        tf_total = len(tf_preds)
        by_timeframe[tf] = {
            "total": tf_total,
            "correct": tf_correct,
            "accuracy_pct": round(tf_correct / tf_total * 100, 1) if tf_total > 0 else None,
        }

    # By confidence level
    high_conf = [p for p in predictions if p.confidence >= 70]
    med_conf = [p for p in predictions if 40 <= p.confidence < 70]
    low_conf = [p for p in predictions if p.confidence < 40]

    by_confidence = {}
    for label, group in [("high", high_conf), ("medium", med_conf), ("low", low_conf)]:
        g_correct = sum(1 for p in group if p.was_correct)
        g_total = len(group)
        by_confidence[label] = {
            "total": g_total,
            "correct": g_correct,
            "accuracy_pct": round(g_correct / g_total * 100, 1) if g_total > 0 else None,
        }

    # Daily accuracy trend
    daily = {}
    for p in predictions:
        day = p.timestamp.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"correct": 0, "total": 0}
        daily[day]["total"] += 1
        if p.was_correct:
            daily[day]["correct"] += 1

    daily_trend = [
        {
            "date": day,
            "accuracy_pct": round(d["correct"] / d["total"] * 100, 1),
            "total": d["total"],
        }
        for day, d in sorted(daily.items())
    ]

    return {
        "days": days,
        "total": total,
        "correct": correct,
        "accuracy_pct": round(correct / total * 100, 1),
        "by_timeframe": by_timeframe,
        "by_confidence": by_confidence,
        "daily_trend": daily_trend,
    }
