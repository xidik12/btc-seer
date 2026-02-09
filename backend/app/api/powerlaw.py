"""BTC Power Law API endpoints.

Formula: Price = 10^(-17.016 + 5.845 * log10(days_since_genesis))
Genesis: January 3, 2009

Corridor bands:
  Support    = fair_value * 0.42
  Mid        = fair_value * 0.71
  Fair       = fair_value * 1.0
  Top Resist = fair_value * 1.5
"""
import math
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Price

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/powerlaw", tags=["powerlaw"])

BTC_GENESIS = datetime(2009, 1, 3)
PL_INTERCEPT = -17.016
PL_SLOPE = 5.845

# Corridor multipliers
CORRIDOR = {
    "support": 0.42,
    "mid": 0.71,
    "fair": 1.0,
    "top_resistance": 1.5,
}


def power_law_fair_value(target_date: datetime = None) -> float:
    """Calculate BTC Power Law fair value for a given date."""
    if target_date is None:
        target_date = datetime.utcnow()
    days = (target_date - BTC_GENESIS).days
    if days <= 0:
        return 0
    log_price = PL_INTERCEPT + PL_SLOPE * math.log10(days)
    return 10 ** log_price


def get_valuation_label(deviation_pct: float) -> str:
    """Return a valuation label based on deviation from fair value."""
    if deviation_pct < -58:
        return "Extremely Undervalued"
    elif deviation_pct < -29:
        return "Undervalued"
    elif deviation_pct < 0:
        return "Below Fair Value"
    elif deviation_pct < 50:
        return "Above Fair Value"
    else:
        return "Overvalued"


@router.get("/current")
async def get_power_law_current(session: AsyncSession = Depends(get_session)):
    """Current BTC price vs Power Law fair value."""
    # Get latest price
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price_row = result.scalar_one_or_none()
    current_price = price_row.close if price_row else None

    now = datetime.utcnow()
    days_since_genesis = (now - BTC_GENESIS).days
    fair_value = power_law_fair_value(now)

    # Corridor bands
    bands = {name: round(fair_value * mult, 2) for name, mult in CORRIDOR.items()}

    # Deviation
    deviation_pct = ((current_price - fair_value) / fair_value * 100) if current_price and fair_value else 0

    # Where in the corridor (0 = support, 1 = top resistance)
    corridor_range = bands["top_resistance"] - bands["support"]
    corridor_position = (
        (current_price - bands["support"]) / corridor_range
        if current_price and corridor_range > 0 else 0.5
    )
    corridor_position = max(0, min(1, corridor_position))

    return {
        "current_price": current_price,
        "fair_value": round(fair_value, 2),
        "deviation_pct": round(deviation_pct, 2),
        "valuation": get_valuation_label(deviation_pct),
        "days_since_genesis": days_since_genesis,
        "corridor": bands,
        "corridor_position": round(corridor_position, 4),
        "distance_to_support_pct": round(
            ((current_price - bands["support"]) / current_price * 100) if current_price else 0, 2
        ),
        "distance_to_resistance_pct": round(
            ((bands["top_resistance"] - current_price) / current_price * 100) if current_price else 0, 2
        ),
        "parameters": {
            "intercept": PL_INTERCEPT,
            "slope": PL_SLOPE,
            "genesis": BTC_GENESIS.isoformat(),
        },
        "timestamp": now.isoformat(),
    }


@router.get("/historical")
async def get_power_law_historical(
    days: int = Query(365, ge=30, le=3650),
    session: AsyncSession = Depends(get_session),
):
    """Historical Power Law curve + actual BTC price for charting."""
    now = datetime.utcnow()

    # Generate power law curve points (daily)
    curve_points = []
    for d in range(max(1, (now - BTC_GENESIS).days - days), (now - BTC_GENESIS).days + 1):
        date = BTC_GENESIS + timedelta(days=d)
        fv = power_law_fair_value(date)
        curve_points.append({
            "date": date.strftime("%Y-%m-%d"),
            "days_since_genesis": d,
            "fair_value": round(fv, 2),
            "support": round(fv * CORRIDOR["support"], 2),
            "mid": round(fv * CORRIDOR["mid"], 2),
            "top_resistance": round(fv * CORRIDOR["top_resistance"], 2),
        })

    # Get actual price data for overlay
    since = now - timedelta(days=days)
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    # Downsample prices to daily for charting (take last price each day)
    daily_prices = {}
    for p in prices:
        day_key = p.timestamp.strftime("%Y-%m-%d")
        daily_prices[day_key] = round(p.close, 2)

    # Merge curve with actual prices
    for point in curve_points:
        point["actual_price"] = daily_prices.get(point["date"])

    return {
        "days": days,
        "points": curve_points,
        "parameters": {
            "intercept": PL_INTERCEPT,
            "slope": PL_SLOPE,
            "genesis": BTC_GENESIS.isoformat(),
            "corridor_multipliers": CORRIDOR,
        },
    }
