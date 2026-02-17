"""Chart API endpoints — serve generated PNG charts for social media."""
import logging
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    get_session, Price, Prediction, Signal, MacroData, GeneratedImage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/charts", tags=["charts"])

# Simple in-memory TTL cache
_cache: dict[str, tuple[bytes, float]] = {}
CACHE_TTL = 300  # 5 minutes


def _get_cached(key: str) -> bytes | None:
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: bytes):
    _cache[key] = (data, time.time())
    # Evict old entries if cache gets large
    if len(_cache) > 50:
        oldest_key = min(_cache, key=lambda k: _cache[k][1])
        del _cache[oldest_key]


def _png_response(data: bytes) -> Response:
    return Response(
        content=data,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=300",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/prediction-card.png")
async def prediction_card_png(
    timeframe: str = Query("24h", regex="^(1h|4h|24h)$"),
    size: str = Query("default", regex="^(twitter|instagram|telegram|default)$"),
    session: AsyncSession = Depends(get_session),
):
    """Generate prediction card PNG."""
    cache_key = f"prediction-card:{timeframe}:{size}"
    cached = _get_cached(cache_key)
    if cached:
        return _png_response(cached)

    from app.charts.prediction_card import render_prediction_card

    # Get latest prediction for timeframe
    result = await session.execute(
        select(Prediction)
        .where(Prediction.timeframe == timeframe)
        .order_by(desc(Prediction.timestamp))
        .limit(1)
    )
    pred = result.scalar_one_or_none()

    # Get fear & greed
    macro_result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    macro = macro_result.scalar_one_or_none()

    if not pred:
        # Render a placeholder card
        data = render_prediction_card(
            current_price=0,
            direction="neutral",
            confidence=0,
            predicted_change_pct=None,
            timeframe=timeframe,
            size=size,
        )
    else:
        data = render_prediction_card(
            current_price=pred.current_price,
            direction=pred.direction,
            confidence=pred.confidence,
            predicted_change_pct=pred.predicted_change_pct,
            timeframe=timeframe,
            predicted_price=pred.predicted_price,
            fear_greed=macro.fear_greed_index if macro else None,
            size=size,
        )

    _set_cache(cache_key, data)
    return _png_response(data)


@router.get("/price.png")
async def price_chart_png(
    hours: int = Query(24, ge=1, le=168),
    size: str = Query("default", regex="^(twitter|instagram|telegram|default)$"),
    session: AsyncSession = Depends(get_session),
):
    """Generate price chart PNG."""
    cache_key = f"price:{hours}:{size}"
    cached = _get_cached(cache_key)
    if cached:
        return _png_response(cached)

    from app.charts.price_chart import render_price_chart

    since = datetime.utcnow() - timedelta(hours=hours)
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices_raw = result.scalars().all()

    prices = [
        {"timestamp": p.timestamp, "close": p.close, "high": p.high, "low": p.low}
        for p in prices_raw
    ]

    # Get predictions in timeframe
    pred_result = await session.execute(
        select(Prediction)
        .where(Prediction.timestamp >= since)
        .order_by(Prediction.timestamp)
    )
    preds_raw = pred_result.scalars().all()
    predictions = [
        {"timestamp": p.timestamp, "direction": p.direction, "confidence": p.confidence, "price": p.current_price}
        for p in preds_raw
    ]

    data = await render_price_chart(prices, predictions, hours=hours, size=size)
    _set_cache(cache_key, data)
    return _png_response(data)


@router.get("/accuracy.png")
async def accuracy_chart_png(
    days: int = Query(7, ge=1, le=90),
    size: str = Query("default", regex="^(twitter|instagram|telegram|default)$"),
    session: AsyncSession = Depends(get_session),
):
    """Generate accuracy bar chart PNG."""
    cache_key = f"accuracy:{days}:{size}"
    cached = _get_cached(cache_key)
    if cached:
        return _png_response(cached)

    from app.charts.accuracy_chart import render_accuracy_chart

    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(Prediction)
        .where(Prediction.timestamp >= since)
        .where(Prediction.was_correct.isnot(None))
    )
    preds = result.scalars().all()

    accuracy_data = {}
    for tf in ["1h", "4h", "24h"]:
        tf_preds = [p for p in preds if p.timeframe == tf]
        accuracy_data[tf] = {
            "total": len(tf_preds),
            "correct": sum(1 for p in tf_preds if p.was_correct),
        }
    accuracy_data["overall"] = {
        "total": len(preds),
        "correct": sum(1 for p in preds if p.was_correct),
    }

    data = render_accuracy_chart(accuracy_data, days=days, size=size)
    _set_cache(cache_key, data)
    return _png_response(data)


@router.get("/signal.png")
async def signal_card_png(
    size: str = Query("telegram", regex="^(twitter|instagram|telegram|default)$"),
    session: AsyncSession = Depends(get_session),
):
    """Generate signal card PNG."""
    cache_key = f"signal:{size}"
    cached = _get_cached(cache_key)
    if cached:
        return _png_response(cached)

    from app.charts.signal_card import render_signal_card

    result = await session.execute(
        select(Signal).order_by(desc(Signal.timestamp)).limit(1)
    )
    signal = result.scalar_one_or_none()

    if not signal:
        data = render_signal_card(
            action="hold", entry_price=0, target_price=0, stop_loss=0,
            confidence=0, risk_rating=5, timeframe="1h", size=size,
        )
    else:
        data = render_signal_card(
            action=signal.action,
            entry_price=signal.entry_price,
            target_price=signal.target_price,
            stop_loss=signal.stop_loss,
            confidence=signal.confidence,
            risk_rating=signal.risk_rating,
            timeframe=signal.timeframe,
            reasoning=signal.reasoning,
            size=size,
        )

    _set_cache(cache_key, data)
    return _png_response(data)


@router.get("/fear-greed.png")
async def fear_greed_png(
    size: str = Query("default", regex="^(twitter|instagram|telegram|default)$"),
    session: AsyncSession = Depends(get_session),
):
    """Generate Fear & Greed gauge PNG."""
    cache_key = f"fear-greed:{size}"
    cached = _get_cached(cache_key)
    if cached:
        return _png_response(cached)

    from app.charts.fear_greed import render_fear_greed

    result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    macro = result.scalar_one_or_none()

    index = macro.fear_greed_index if macro and macro.fear_greed_index is not None else 50
    label = macro.fear_greed_label if macro else None

    data = render_fear_greed(index=index, label=label, size=size)
    _set_cache(cache_key, data)
    return _png_response(data)


@router.get("/weekly-summary.png")
async def weekly_summary_png(
    size: str = Query("default", regex="^(twitter|instagram|telegram|default)$"),
    session: AsyncSession = Depends(get_session),
):
    """Generate weekly summary infographic PNG."""
    cache_key = f"weekly-summary:{size}"
    cached = _get_cached(cache_key)
    if cached:
        return _png_response(cached)

    from app.charts.weekly_summary import render_weekly_summary
    from app.database import BotUser, Signal as SignalModel

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    # Accuracy
    pred_result = await session.execute(
        select(Prediction)
        .where(Prediction.timestamp >= week_ago)
        .where(Prediction.was_correct.isnot(None))
    )
    preds = pred_result.scalars().all()
    total = len(preds)
    correct = sum(1 for p in preds if p.was_correct)

    # Price
    price_now_result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price_week_result = await session.execute(
        select(Price).where(Price.timestamp <= week_ago).order_by(desc(Price.timestamp)).limit(1)
    )
    price_now = price_now_result.scalar_one_or_none()
    price_week = price_week_result.scalar_one_or_none()

    price_end = price_now.close if price_now else 0
    price_start = price_week.close if price_week else price_end
    pct_change = ((price_end - price_start) / price_start * 100) if price_start else 0

    # Signals
    sig_result = await session.execute(
        select(SignalModel).where(SignalModel.timestamp >= week_ago)
    )
    signals = sig_result.scalars().all()

    # Streak
    streak = 0
    for p in reversed(preds):
        if p.was_correct:
            streak += 1
        else:
            break

    # Users
    user_count_result = await session.execute(select(func.count(BotUser.id)))
    new_users_result = await session.execute(
        select(func.count(BotUser.id)).where(BotUser.joined_at >= week_ago)
    )
    premium_result = await session.execute(
        select(func.count(BotUser.id)).where(BotUser.subscription_tier == "premium")
    )

    stats = {
        "accuracy_pct": (correct / total * 100) if total > 0 else 0,
        "total_predictions": total,
        "correct_predictions": correct,
        "price_start": price_start,
        "price_end": price_end,
        "price_change_pct": round(pct_change, 2),
        "signals_count": len(signals),
        "profitable_signals": 0,  # Would need trade results to compute
        "streak": streak,
        "users_total": user_count_result.scalar() or 0,
        "users_new": new_users_result.scalar() or 0,
        "premium_count": premium_result.scalar() or 0,
    }

    data = render_weekly_summary(stats, size=size)
    _set_cache(cache_key, data)
    return _png_response(data)
