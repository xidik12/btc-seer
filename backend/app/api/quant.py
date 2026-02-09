from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, QuantPrediction

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/quant")
async def get_quant_prediction(session: AsyncSession = Depends(get_session)):
    """Get the latest quant theory-based prediction with signal breakdown."""
    try:
        result = await session.execute(
            select(QuantPrediction)
            .order_by(desc(QuantPrediction.timestamp))
            .limit(1)
        )
        qp = result.scalar_one_or_none()
    except Exception:
        return {"prediction": None, "message": "Quant prediction data initializing"}

    if not qp:
        return {"prediction": None, "message": "No quant predictions available yet"}

    return {
        "prediction": {
            "timestamp": qp.timestamp.isoformat(),
            "current_price": qp.current_price,
            "composite_score": qp.composite_score,
            "action": qp.action,
            "direction": qp.direction,
            "confidence": qp.confidence,
            "predictions": {
                "1h": {
                    "direction": qp.direction,
                    "predicted_price": qp.pred_1h_price,
                    "predicted_change_pct": qp.pred_1h_change_pct,
                    "confidence": qp.confidence,
                },
                "4h": {
                    "direction": qp.direction,
                    "predicted_price": qp.pred_4h_price,
                    "predicted_change_pct": qp.pred_4h_change_pct,
                    "confidence": qp.confidence,
                },
                "24h": {
                    "direction": qp.direction,
                    "predicted_price": qp.pred_24h_price,
                    "predicted_change_pct": qp.pred_24h_change_pct,
                    "confidence": qp.confidence,
                },
            },
            "active_signals": qp.active_signals,
            "bullish_signals": qp.bullish_signals,
            "bearish_signals": qp.bearish_signals,
            "agreement_ratio": qp.agreement_ratio,
            "signal_breakdown": qp.signal_breakdown,
        }
    }


@router.get("/quant/history")
async def get_quant_history(
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Get quant prediction history for accuracy tracking."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(QuantPrediction)
        .where(QuantPrediction.timestamp >= since)
        .order_by(desc(QuantPrediction.timestamp))
    )
    predictions = result.scalars().all()

    history = []
    correct_1h = 0
    correct_24h = 0
    evaluated_1h = 0
    evaluated_24h = 0

    for p in predictions:
        entry = {
            "timestamp": p.timestamp.isoformat(),
            "direction": p.direction,
            "composite_score": p.composite_score,
            "action": p.action,
            "confidence": p.confidence,
            "current_price": p.current_price,
            "pred_1h_price": p.pred_1h_price,
            "pred_24h_price": p.pred_24h_price,
            "actual_price_1h": p.actual_price_1h,
            "actual_price_24h": p.actual_price_24h,
            "was_correct_1h": p.was_correct_1h,
            "was_correct_24h": p.was_correct_24h,
        }
        history.append(entry)

        if p.was_correct_1h is not None:
            evaluated_1h += 1
            if p.was_correct_1h:
                correct_1h += 1
        if p.was_correct_24h is not None:
            evaluated_24h += 1
            if p.was_correct_24h:
                correct_24h += 1

    accuracy_1h = (correct_1h / evaluated_1h * 100) if evaluated_1h > 0 else None
    accuracy_24h = (correct_24h / evaluated_24h * 100) if evaluated_24h > 0 else None

    return {
        "days": days,
        "total_predictions": len(history),
        "accuracy_1h": round(accuracy_1h, 1) if accuracy_1h else None,
        "accuracy_24h": round(accuracy_24h, 1) if accuracy_24h else None,
        "evaluated_1h": evaluated_1h,
        "evaluated_24h": evaluated_24h,
        "history": history,
    }
