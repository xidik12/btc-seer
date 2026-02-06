from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Price, MacroData, OnChainData

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/price")
async def get_current_price(session: AsyncSession = Depends(get_session)):
    """Get latest BTC price data."""
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price = result.scalar_one_or_none()

    if not price:
        return {"price": None, "message": "No price data available"}

    # Get 24h ago price for change calculation
    yesterday = price.timestamp - timedelta(hours=24)
    result_24h = await session.execute(
        select(Price)
        .where(Price.timestamp <= yesterday)
        .order_by(desc(Price.timestamp))
        .limit(1)
    )
    price_24h = result_24h.scalar_one_or_none()

    change_24h = None
    change_24h_pct = None
    if price_24h:
        change_24h = price.close - price_24h.close
        change_24h_pct = (change_24h / price_24h.close) * 100

    return {
        "price": price.close,
        "open": price.open,
        "high": price.high,
        "low": price.low,
        "volume": price.volume,
        "change_24h": round(change_24h, 2) if change_24h else None,
        "change_24h_pct": round(change_24h_pct, 2) if change_24h_pct else None,
        "timestamp": price.timestamp.isoformat(),
    }


@router.get("/candles")
async def get_candles(
    hours: int = Query(168, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    """Get historical candle data."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    return {
        "count": len(prices),
        "candles": [
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


@router.get("/macro")
async def get_macro_data(session: AsyncSession = Depends(get_session)):
    """Get latest macro market data."""
    result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    macro = result.scalar_one_or_none()

    if not macro:
        return {"macro": None, "message": "No macro data available"}

    return {
        "dxy": macro.dxy,
        "gold": macro.gold,
        "sp500": macro.sp500,
        "treasury_10y": macro.treasury_10y,
        "fear_greed_index": macro.fear_greed_index,
        "fear_greed_label": macro.fear_greed_label,
        "timestamp": macro.timestamp.isoformat(),
    }


@router.get("/onchain")
async def get_onchain_data(session: AsyncSession = Depends(get_session)):
    """Get latest on-chain metrics."""
    result = await session.execute(
        select(OnChainData).order_by(desc(OnChainData.timestamp)).limit(1)
    )
    onchain = result.scalar_one_or_none()

    if not onchain:
        return {"onchain": None, "message": "No on-chain data available"}

    return {
        "hash_rate": onchain.hash_rate,
        "difficulty": onchain.difficulty,
        "mempool_size": onchain.mempool_size,
        "mempool_fees": onchain.mempool_fees,
        "tx_volume": onchain.tx_volume,
        "active_addresses": onchain.active_addresses,
        "exchange_reserve": onchain.exchange_reserve,
        "large_tx_count": onchain.large_tx_count,
        "timestamp": onchain.timestamp.isoformat(),
    }
