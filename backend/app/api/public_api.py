"""Public versioned API endpoints (/api/v1/).

Clean, documented endpoints for external consumers.
Auth handled by APIKeyMiddleware (when enabled).
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    get_session, Price, Prediction, QuantPrediction,
    MacroData, OnChainData, ApiKey, ApiUsageLog,
)
from app.api.powerlaw import power_law_fair_value, CORRIDOR, get_valuation_label, BTC_GENESIS
from app.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["public-api-v1"])


# ── Price ──────────────────────────────────────────────────────

@router.get("/price")
async def get_price(session: AsyncSession = Depends(get_session)):
    """Get current BTC price."""
    cached = await cache_get("v1:price")
    if cached is not None:
        return cached

    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"error": "No price data available"}

    data = {
        "price": row.close,
        "high_24h": row.high,
        "low_24h": row.low,
        "volume": row.volume,
        "timestamp": row.timestamp.isoformat(),
    }
    await cache_set("v1:price", data, 15)
    return data


@router.get("/price/history")
async def get_price_history(
    hours: int = Query(24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    """Get historical BTC prices."""
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    return {
        "count": len(prices),
        "prices": [
            {
                "timestamp": p.timestamp.isoformat(),
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices
        ],
    }


# ── Predictions ────────────────────────────────────────────────

@router.get("/predictions/current")
async def get_predictions(session: AsyncSession = Depends(get_session)):
    """Get current AI predictions for all timeframes."""
    result = await session.execute(
        select(Prediction)
        .order_by(desc(Prediction.timestamp))
        .limit(5)
    )
    predictions = result.scalars().all()

    return {
        "predictions": [
            {
                "timeframe": p.timeframe,
                "direction": p.direction,
                "confidence": p.confidence,
                "predicted_price": p.predicted_price,
                "predicted_change_pct": p.predicted_change_pct,
                "current_price": p.current_price,
                "timestamp": p.timestamp.isoformat(),
            }
            for p in predictions
        ],
    }


@router.get("/predictions/quant")
async def get_quant_prediction(session: AsyncSession = Depends(get_session)):
    """Get latest quant theory prediction."""
    result = await session.execute(
        select(QuantPrediction).order_by(desc(QuantPrediction.timestamp)).limit(1)
    )
    qp = result.scalar_one_or_none()
    if not qp:
        return {"prediction": None}

    return {
        "prediction": {
            "direction": qp.direction,
            "action": qp.action,
            "composite_score": qp.composite_score,
            "confidence": qp.confidence,
            "current_price": qp.current_price,
            "predictions": {
                "1h": {"predicted_price": qp.pred_1h_price, "predicted_change_pct": qp.pred_1h_change_pct},
                "4h": {"predicted_price": qp.pred_4h_price, "predicted_change_pct": qp.pred_4h_change_pct},
                "24h": {"predicted_price": qp.pred_24h_price, "predicted_change_pct": qp.pred_24h_change_pct},
                "1w": {"predicted_price": qp.pred_1w_price, "predicted_change_pct": qp.pred_1w_change_pct},
                "1mo": {"predicted_price": qp.pred_1mo_price, "predicted_change_pct": qp.pred_1mo_change_pct},
            },
            "active_signals": qp.active_signals,
            "bullish_signals": qp.bullish_signals,
            "bearish_signals": qp.bearish_signals,
            "agreement_ratio": qp.agreement_ratio,
            "timestamp": qp.timestamp.isoformat(),
        },
    }


# ── Market ─────────────────────────────────────────────────────

@router.get("/market/macro")
async def get_macro(session: AsyncSession = Depends(get_session)):
    """Get latest macro market data (DXY, Gold, S&P500, Fear & Greed)."""
    cached = await cache_get("v1:macro")
    if cached is not None:
        return cached

    result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"error": "No macro data available"}

    data = {
        "dxy": row.dxy,
        "gold": row.gold,
        "sp500": row.sp500,
        "treasury_10y": row.treasury_10y,
        "fear_greed_index": row.fear_greed_index,
        "fear_greed_label": row.fear_greed_label,
        "timestamp": row.timestamp.isoformat(),
    }
    await cache_set("v1:macro", data, 60)
    return data


@router.get("/market/onchain")
async def get_onchain(session: AsyncSession = Depends(get_session)):
    """Get latest on-chain data (hash rate, mempool, active addresses)."""
    cached = await cache_get("v1:onchain")
    if cached is not None:
        return cached

    result = await session.execute(
        select(OnChainData).order_by(desc(OnChainData.timestamp)).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"error": "No on-chain data available"}

    data = {
        "hash_rate": row.hash_rate,
        "difficulty": row.difficulty,
        "mempool_size": row.mempool_size,
        "mempool_fees": row.mempool_fees,
        "tx_volume": row.tx_volume,
        "active_addresses": row.active_addresses,
        "large_tx_count": row.large_tx_count,
        "timestamp": row.timestamp.isoformat(),
    }
    await cache_set("v1:onchain", data, 60)
    return data


# ── Power Law ──────────────────────────────────────────────────

@router.get("/powerlaw")
async def get_power_law(session: AsyncSession = Depends(get_session)):
    """Get BTC Power Law fair value and corridor position."""
    cached = await cache_get("v1:powerlaw")
    if cached is not None:
        return cached

    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price_row = result.scalar_one_or_none()
    current_price = price_row.close if price_row else None

    now = datetime.utcnow()
    fair_value = power_law_fair_value(now)
    bands = {name: round(fair_value * mult, 2) for name, mult in CORRIDOR.items()}
    deviation_pct = ((current_price - fair_value) / fair_value * 100) if current_price and fair_value else 0

    data = {
        "current_price": current_price,
        "fair_value": round(fair_value, 2),
        "deviation_pct": round(deviation_pct, 2),
        "valuation": get_valuation_label(deviation_pct),
        "corridor": bands,
        "days_since_genesis": (now - BTC_GENESIS).days,
        "timestamp": now.isoformat(),
    }
    await cache_set("v1:powerlaw", data, 60)
    return data


# ── Usage ──────────────────────────────────────────────────────

@router.get("/usage")
async def get_usage(
    session: AsyncSession = Depends(get_session),
    request=None,
):
    """Get API usage stats for the current API key."""
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest

    # Get API key ID from request state (set by middleware)
    api_key_id = getattr(getattr(request, 'state', None), 'api_key_id', None) if request else None

    if not api_key_id:
        return {"error": "API key required to view usage stats"}

    # Get key info
    result = await session.execute(
        select(ApiKey).where(ApiKey.id == api_key_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return {"error": "API key not found"}

    # Count usage in last hour and last 24h
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    day_ago = datetime.utcnow() - timedelta(hours=24)

    from sqlalchemy import func
    result_1h = await session.execute(
        select(func.count(ApiUsageLog.id))
        .where(ApiUsageLog.api_key_id == api_key_id)
        .where(ApiUsageLog.timestamp >= hour_ago)
    )
    result_24h = await session.execute(
        select(func.count(ApiUsageLog.id))
        .where(ApiUsageLog.api_key_id == api_key_id)
        .where(ApiUsageLog.timestamp >= day_ago)
    )

    return {
        "tier": key.tier,
        "rate_limit": key.rate_limit,
        "requests_last_hour": result_1h.scalar() or 0,
        "requests_last_24h": result_24h.scalar() or 0,
        "is_active": key.is_active,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
    }
