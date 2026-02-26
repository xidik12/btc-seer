from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Signal

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/current")
async def get_current_signals(session: AsyncSession = Depends(get_session)):
    """Get the latest trading signals for all timeframes."""
    result = await session.execute(
        select(Signal)
        .order_by(desc(Signal.timestamp))
        .limit(3)
    )
    signals = result.scalars().all()

    if not signals:
        return {"signals": {}, "message": "No signals available yet"}

    sig_dict = {}
    for s in signals:
        sig_dict[s.timeframe] = {
            "id": s.id,
            "timeframe": s.timeframe,
            "action": s.action,
            "direction": s.direction,
            "confidence": s.confidence,
            "entry_price": s.entry_price,
            "target_price": s.target_price,
            "stop_loss": s.stop_loss,
            "risk_rating": s.risk_rating,
            "reasoning": s.reasoning,
            "timestamp": s.timestamp.isoformat(),
        }

    return {"signals": sig_dict}


@router.get("/history")
async def get_signal_history(
    timeframe: str = Query("1h", pattern="^(1h|4h|24h)$"),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get historical signals."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(Signal)
        .where(Signal.timeframe == timeframe)
        .where(Signal.timestamp >= since)
        .order_by(desc(Signal.timestamp))
        .limit(limit)
    )
    signals = result.scalars().all()

    return {
        "timeframe": timeframe,
        "count": len(signals),
        "signals": [
            {
                "id": s.id,
                "timeframe": s.timeframe,
                "action": s.action,
                "direction": s.direction,
                "confidence": s.confidence,
                "entry_price": s.entry_price,
                "target_price": s.target_price,
                "stop_loss": s.stop_loss,
                "risk_rating": s.risk_rating,
                "reasoning": s.reasoning,
                "timestamp": s.timestamp.isoformat(),
            }
            for s in signals
        ],
    }
