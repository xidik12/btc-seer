"""Consolidated dashboard endpoint — single API call replaces 14+ widget calls."""
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    get_session, async_session, Price, Prediction, QuantPrediction,
    News, OnChainData, MacroData, BtcDominance,
)
from app.cache import cache_get, cache_set

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(session: AsyncSession = Depends(get_session)):
    """Single consolidated endpoint for all dashboard widget data.

    Replaces 14+ individual API calls with one efficient query batch.
    All independent queries run in parallel with separate sessions.
    Cached for 30 seconds.
    """
    cached = await cache_get("dashboard_summary")
    if cached is not None:
        return cached

    now = datetime.utcnow()

    # --- Helper coroutines: each opens its own session for true parallelism ---

    async def _fetch_price():
        async with async_session() as s:
            res = await s.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            row = res.scalar_one_or_none()
            if not row:
                return None
            yesterday = row.timestamp - timedelta(hours=24)
            prev_res = await s.execute(
                select(Price)
                .where(Price.timestamp <= yesterday)
                .order_by(desc(Price.timestamp))
                .limit(1)
            )
            prev = prev_res.scalar_one_or_none()
            change_24h = None
            change_24h_pct = None
            if prev and prev.close:
                change_24h = round(row.close - prev.close, 2)
                change_24h_pct = round(change_24h / prev.close * 100, 2)
            return {
                "price": row.close, "open": row.open,
                "high": row.high, "low": row.low,
                "volume": row.volume,
                "change_24h": change_24h,
                "change_24h_pct": change_24h_pct,
                "timestamp": row.timestamp.isoformat(),
            }

    async def _fetch_predictions():
        async with async_session() as s:
            res = await s.execute(
                select(Prediction).order_by(desc(Prediction.timestamp)).limit(5)
            )
            preds = {}
            for p in res.scalars().all():
                if p.timeframe not in preds:
                    preds[p.timeframe] = {
                        "direction": p.direction,
                        "confidence": p.confidence,
                        "predicted_price": p.predicted_price,
                        "predicted_change_pct": p.predicted_change_pct,
                        "current_price": p.current_price,
                        "timestamp": p.timestamp.isoformat(),
                    }
            return preds

    async def _fetch_quant():
        async with async_session() as s:
            res = await s.execute(
                select(QuantPrediction).order_by(desc(QuantPrediction.timestamp)).limit(1)
            )
            row = res.scalar_one_or_none()
            if not row:
                return None
            return {
                "composite_score": row.composite_score,
                "action": row.action,
                "direction": row.direction,
                "confidence": row.confidence,
                "timestamp": row.timestamp.isoformat(),
            }

    async def _fetch_news():
        async with async_session() as s:
            res = await s.execute(
                select(News).order_by(desc(News.timestamp)).limit(10)
            )
            return [
                {
                    "title": n.title, "source": n.source,
                    "sentiment_score": n.sentiment_score,
                    "timestamp": n.timestamp.isoformat(),
                }
                for n in res.scalars().all()
            ]

    async def _fetch_onchain():
        async with async_session() as s:
            res = await s.execute(
                select(OnChainData).order_by(desc(OnChainData.timestamp)).limit(1)
            )
            row = res.scalar_one_or_none()
            if not row:
                return None
            return {
                "hash_rate": row.hash_rate,
                "mempool_size": row.mempool_size,
                "active_addresses": row.active_addresses,
                "timestamp": row.timestamp.isoformat(),
            }

    async def _fetch_macro():
        async with async_session() as s:
            res = await s.execute(
                select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
            )
            row = res.scalar_one_or_none()
            if not row:
                return None
            return {
                "dxy": row.dxy, "gold": row.gold,
                "sp500": row.sp500,
                "fear_greed_index": row.fear_greed_index,
                "fear_greed_label": row.fear_greed_label,
                "timestamp": row.timestamp.isoformat(),
            }

    async def _fetch_dominance():
        async with async_session() as s:
            res = await s.execute(
                select(BtcDominance).order_by(desc(BtcDominance.timestamp)).limit(1)
            )
            row = res.scalar_one_or_none()
            if not row:
                return None
            return {
                "btc_dominance": row.btc_dominance,
                "total_market_cap": row.total_market_cap,
                "timestamp": row.timestamp.isoformat(),
            }

    # Run all 7 query groups in parallel
    (price_data, predictions, quant_data,
     news_list, onchain_data, macro_data, dominance_data) = await asyncio.gather(
        _fetch_price(),
        _fetch_predictions(),
        _fetch_quant(),
        _fetch_news(),
        _fetch_onchain(),
        _fetch_macro(),
        _fetch_dominance(),
    )

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
    await cache_set("dashboard_summary", result, 30)
    return result
