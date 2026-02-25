"""Consolidated dashboard endpoint — single API call replaces 14+ widget calls."""
import time
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    get_session, Price, Prediction, QuantPrediction,
    News, OnChainData, MacroData, BtcDominance,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# TTL cache
_cache: dict[str, tuple[dict, float]] = {}


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        data, expires = _cache[key]
        if time.monotonic() < expires:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: dict, ttl: int) -> None:
    _cache[key] = (data, time.monotonic() + ttl)


@router.get("/summary")
async def get_dashboard_summary(session: AsyncSession = Depends(get_session)):
    """Single consolidated endpoint for all dashboard widget data.

    Replaces 14+ individual API calls with one efficient query batch.
    Cached for 30 seconds.
    """
    cached = _get_cached("dashboard_summary")
    if cached is not None:
        return cached

    now = datetime.utcnow()

    # 1. Latest price + 24h ago price (2 queries)
    price_result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    current_price_row = price_result.scalar_one_or_none()

    price_data = None
    if current_price_row:
        yesterday = current_price_row.timestamp - timedelta(hours=24)
        prev_result = await session.execute(
            select(Price)
            .where(Price.timestamp <= yesterday)
            .order_by(desc(Price.timestamp))
            .limit(1)
        )
        prev_price = prev_result.scalar_one_or_none()

        change_24h = None
        change_24h_pct = None
        if prev_price and prev_price.close:
            change_24h = round(current_price_row.close - prev_price.close, 2)
            change_24h_pct = round(change_24h / prev_price.close * 100, 2)

        price_data = {
            "price": current_price_row.close,
            "open": current_price_row.open,
            "high": current_price_row.high,
            "low": current_price_row.low,
            "volume": current_price_row.volume,
            "change_24h": change_24h,
            "change_24h_pct": change_24h_pct,
            "timestamp": current_price_row.timestamp.isoformat(),
        }

    # 2. Latest predictions — one per timeframe (1 query)
    pred_result = await session.execute(
        select(Prediction).order_by(desc(Prediction.timestamp)).limit(5)
    )
    predictions_raw = pred_result.scalars().all()
    predictions = {}
    for p in predictions_raw:
        if p.timeframe not in predictions:
            predictions[p.timeframe] = {
                "direction": p.direction,
                "confidence": p.confidence,
                "predicted_price": p.predicted_price,
                "predicted_change_pct": p.predicted_change_pct,
                "current_price": p.current_price,
                "timestamp": p.timestamp.isoformat(),
            }

    # 3. Latest quant prediction (1 query)
    quant_result = await session.execute(
        select(QuantPrediction).order_by(desc(QuantPrediction.timestamp)).limit(1)
    )
    quant_row = quant_result.scalar_one_or_none()
    quant_data = None
    if quant_row:
        quant_data = {
            "composite_score": quant_row.composite_score,
            "action": quant_row.action,
            "direction": quant_row.direction,
            "confidence": quant_row.confidence,
            "timestamp": quant_row.timestamp.isoformat(),
        }

    # 4. Latest news (1 query)
    news_result = await session.execute(
        select(News).order_by(desc(News.timestamp)).limit(10)
    )
    news_list = [
        {
            "title": n.title,
            "source": n.source,
            "sentiment_score": n.sentiment_score,
            "timestamp": n.timestamp.isoformat(),
        }
        for n in news_result.scalars().all()
    ]

    # 5. On-chain data (1 query)
    onchain_result = await session.execute(
        select(OnChainData).order_by(desc(OnChainData.timestamp)).limit(1)
    )
    onchain_row = onchain_result.scalar_one_or_none()
    onchain_data = None
    if onchain_row:
        onchain_data = {
            "hash_rate": onchain_row.hash_rate,
            "mempool_size": onchain_row.mempool_size,
            "active_addresses": onchain_row.active_addresses,
            "timestamp": onchain_row.timestamp.isoformat(),
        }

    # 6. Macro data (1 query)
    macro_result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    macro_row = macro_result.scalar_one_or_none()
    macro_data = None
    if macro_row:
        macro_data = {
            "dxy": macro_row.dxy,
            "gold": macro_row.gold,
            "sp500": macro_row.sp500,
            "fear_greed_index": macro_row.fear_greed_index,
            "fear_greed_label": macro_row.fear_greed_label,
            "timestamp": macro_row.timestamp.isoformat(),
        }

    # 7. BTC dominance (1 query)
    dom_result = await session.execute(
        select(BtcDominance).order_by(desc(BtcDominance.timestamp)).limit(1)
    )
    dom_row = dom_result.scalar_one_or_none()
    dominance_data = None
    if dom_row:
        dominance_data = {
            "btc_dominance": dom_row.btc_dominance,
            "total_market_cap": dom_row.total_market_cap,
            "timestamp": dom_row.timestamp.isoformat(),
        }

    result = {
        "price": price_data,
        "predictions": predictions,
        "quant": quant_data,
        "news": news_list,
        "onchain": onchain_data,
        "macro": macro_data,
        "dominance": dominance_data,
        "generated_at": now.isoformat(),
    }
    _set_cache("dashboard_summary", result, 30)
    return result
