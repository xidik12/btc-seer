from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Prediction

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/current")
async def get_current_predictions(session: AsyncSession = Depends(get_session)):
    """Get the latest predictions for all timeframes."""
    result = await session.execute(
        select(Prediction)
        .order_by(desc(Prediction.timestamp))
        .limit(3)
    )
    predictions = result.scalars().all()

    if not predictions:
        return {"predictions": {}, "message": "No predictions available yet"}

    pred_dict = {}
    for p in predictions:
        pred_dict[p.timeframe] = {
            "id": p.id,
            "direction": p.direction,
            "confidence": p.confidence,
            "predicted_price": p.predicted_price,
            "predicted_change_pct": p.predicted_change_pct,
            "current_price": p.current_price,
            "timestamp": p.timestamp.isoformat(),
            "model_outputs": p.model_outputs,
        }

    return {"predictions": pred_dict}


@router.get("/history")
async def get_prediction_history(
    timeframe: str = Query("1h", pattern="^(1h|4h|24h)$"),
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Get prediction history for accuracy tracking."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(Prediction)
        .where(Prediction.timeframe == timeframe)
        .where(Prediction.timestamp >= since)
        .order_by(desc(Prediction.timestamp))
    )
    predictions = result.scalars().all()

    history = []
    correct = 0
    total_with_result = 0

    for p in predictions:
        entry = {
            "id": p.id,
            "timestamp": p.timestamp.isoformat(),
            "direction": p.direction,
            "confidence": p.confidence,
            "current_price": p.current_price,
            "predicted_price": p.predicted_price,
            "actual_price": p.actual_price,
            "was_correct": p.was_correct,
        }
        history.append(entry)

        if p.was_correct is not None:
            total_with_result += 1
            if p.was_correct:
                correct += 1

    accuracy = (correct / total_with_result * 100) if total_with_result > 0 else None

    return {
        "timeframe": timeframe,
        "days": days,
        "total_predictions": len(history),
        "evaluated": total_with_result,
        "correct": correct,
        "accuracy_pct": round(accuracy, 1) if accuracy else None,
        "history": history,
    }
