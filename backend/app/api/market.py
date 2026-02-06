import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Price, MacroData, OnChainData
from app.collectors.market import MarketCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])

# Shared collector for Binance API fallback
_market_collector = MarketCollector()

# Minimum candles needed per timeframe to consider local data sufficient
_MIN_CANDLES = {"1m": 2, "5m": 2, "15m": 2, "1h": 5, "4h": 5, "1d": 10, "1w": 20, "1mo": 20, "1y": 50, "all": 50}

# Binance interval + limit for each timeframe (used as fallback)
_BINANCE_FALLBACK = {
    "1d": ("1h", 24),
    "1w": ("1h", 168),
    "1mo": ("4h", 180),
    "1y": ("1d", 365),
    "all": ("1d", 1000),
}


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


@router.get("/stats")
async def get_price_stats(
    timeframe: str = Query("1d", pattern="^(1m|5m|15m|1h|4h|1d|1w|1mo|1y|all)$"),
    session: AsyncSession = Depends(get_session),
):
    """Get price statistics for a specific timeframe.

    Timeframes: 1m, 5m, 15m, 1h, 4h, 1d (day), 1w (week), 1mo (month), 1y (year), all (lifetime)
    """
    # Map timeframe to timedelta
    timeframe_map = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1mo": timedelta(days=30),
        "1y": timedelta(days=365),
        "all": None,  # All time
    }

    # Get current price
    result_current = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    current = result_current.scalar_one_or_none()

    if not current:
        return {"error": "No price data available"}

    # Get historical data for timeframe
    delta = timeframe_map[timeframe]
    if delta:
        since = current.timestamp - delta
        result_historical = await session.execute(
            select(Price)
            .where(Price.timestamp >= since)
            .order_by(Price.timestamp)
        )
    else:
        # All time
        result_historical = await session.execute(
            select(Price).order_by(Price.timestamp)
        )

    prices = result_historical.scalars().all()

    min_needed = _MIN_CANDLES.get(timeframe, 5)

    # Fallback to Binance API if local data is insufficient
    if len(prices) < min_needed and timeframe in _BINANCE_FALLBACK:
        logger.info(f"Stats: Local data insufficient ({len(prices)} candles) for {timeframe}, fetching from Binance")
        try:
            binance_interval, binance_limit = _BINANCE_FALLBACK[timeframe]
            klines = await _market_collector.get_historical_klines(
                interval=binance_interval, limit=binance_limit
            )
            if klines and len(klines) > min_needed:
                current_price = current.close
                first_k = klines[0]
                open_price = first_k["open"]
                high_price = max(k["high"] for k in klines)
                low_price = min(k["low"] for k in klines)
                total_volume = sum(k["volume"] for k in klines)
                last_k = klines[-1]

                price_change = last_k["close"] - open_price
                price_change_pct = (price_change / open_price * 100) if open_price else 0

                max_candles = 500
                step = max(1, len(klines) // max_candles)
                candles = [
                    {
                        "timestamp": k["timestamp"].isoformat() if hasattr(k["timestamp"], "isoformat") else str(k["timestamp"]),
                        "open": k["open"],
                        "high": k["high"],
                        "low": k["low"],
                        "close": k["close"],
                        "volume": k["volume"],
                    }
                    for k in klines[::step]
                ]

                return {
                    "timeframe": timeframe,
                    "current_price": current_price,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "volume": total_volume,
                    "change": round(price_change, 2),
                    "change_pct": round(price_change_pct, 2),
                    "num_candles": len(klines),
                    "candles": candles,
                    "timestamp": current.timestamp.isoformat(),
                    "period_start": candles[0]["timestamp"],
                    "period_end": candles[-1]["timestamp"],
                    "source": "binance_api",
                }
        except Exception as e:
            logger.warning(f"Binance fallback failed: {e}")

    if not prices:
        return {"error": "No historical data available"}

    # Calculate stats from local DB data
    first_price = prices[0]
    current_price = current.close
    open_price = first_price.close
    high_price = max(p.high for p in prices)
    low_price = min(p.low for p in prices)
    total_volume = sum(p.volume for p in prices)

    price_change = current_price - open_price
    price_change_pct = (price_change / open_price * 100) if open_price else 0

    # Get candle data for chart (limit to reasonable number of points)
    max_candles = 1000
    step = max(1, len(prices) // max_candles)
    candles = [
        {
            "timestamp": p.timestamp.isoformat(),
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
        }
        for p in prices[::step]
    ]

    return {
        "timeframe": timeframe,
        "current_price": current_price,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "volume": total_volume,
        "change": round(price_change, 2),
        "change_pct": round(price_change_pct, 2),
        "num_candles": len(prices),
        "candles": candles,
        "timestamp": current.timestamp.isoformat(),
        "period_start": first_price.timestamp.isoformat(),
        "period_end": current.timestamp.isoformat(),
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
