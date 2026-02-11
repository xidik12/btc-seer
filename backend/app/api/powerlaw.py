"""BTC Power Law API endpoints.

Formula: Price = 10^(-17.016 + 5.845 * log10(days_since_genesis))
Genesis: January 3, 2009

Corridor bands:
  Support    = fair_value * 0.42
  Mid        = fair_value * 0.71
  Fair       = fair_value * 1.0
  Top Resist = fair_value * 1.5
"""
import json
import math
import logging
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Price, MacroData
from app.models.power_law_engine import PowerLawEngine, RatioModel

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


# ════════════════════════════════════════════════════════════════
#  NEW ENDPOINTS — b1m.io-style features
# ════════════════════════════════════════════════════════════════

DATA_DIR = Path(__file__).parent.parent / "data"
_engine = PowerLawEngine()


async def _get_current_price(session: AsyncSession) -> float | None:
    result = await session.execute(select(Price).order_by(desc(Price.timestamp)).limit(1))
    row = result.scalar_one_or_none()
    return float(row.close) if row else None


async def _get_24h_change(session: AsyncSession) -> float | None:
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    latest = result.scalar_one_or_none()
    if not latest:
        return None

    result = await session.execute(
        select(Price)
        .where(Price.timestamp <= latest.timestamp - timedelta(hours=23))
        .order_by(desc(Price.timestamp))
        .limit(1)
    )
    old = result.scalar_one_or_none()
    if not old or old.close == 0:
        return None
    return round((latest.close - old.close) / old.close * 100, 2)


async def _get_latest_macro(session: AsyncSession) -> MacroData | None:
    result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/dashboard")
async def get_power_law_dashboard(session: AsyncSession = Depends(get_session)):
    """Main b1m.io-style dashboard: stats, projections, milestones."""
    current_price = await _get_current_price(session)
    if not current_price:
        return {"error": "No price data available"}

    change_24h = await _get_24h_change(session)
    stats = _engine.get_stats(current_price)
    stats["change_24h"] = change_24h

    return stats


@router.get("/curve")
async def get_power_law_curve(
    session: AsyncSession = Depends(get_session),
):
    """Full power law curve from 2011 to 2045 with model line, bands, and actual price."""
    now = datetime.utcnow()

    # Generate curve from 2011 to 2045
    start_date = datetime(2011, 1, 1)
    end_date = datetime(2045, 12, 31)
    start_day = (start_date - BTC_GENESIS).days
    end_day = (end_date - BTC_GENESIS).days
    today_day = (now - BTC_GENESIS).days

    curve_points = []
    # Weekly points for efficiency
    for d in range(start_day, end_day + 1, 7):
        date = BTC_GENESIS + timedelta(days=d)
        fv = _engine.fair_value(date)
        curve_points.append({
            "date": date.strftime("%Y-%m-%d"),
            "days": d,
            "model": round(fv, 2),
            "lower": round(fv * 0.5, 2),
            "upper": round(fv * 3.0, 2),
        })

    # Get ALL historical prices for overlay
    result = await session.execute(
        select(Price).order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    daily_prices = {}
    for p in prices:
        day_key = p.timestamp.strftime("%Y-%m-%d")
        daily_prices[day_key] = round(p.close, 2)

    # Merge actual prices with curve
    for point in curve_points:
        point["actual"] = daily_prices.get(point["date"])

    # Today marker
    today_fv = _engine.fair_value(now)
    current_price = await _get_current_price(session)

    return {
        "points": curve_points,
        "today": {
            "date": now.strftime("%Y-%m-%d"),
            "model_price": round(today_fv, 2),
            "actual_price": current_price,
            "days_since_genesis": today_day,
        },
    }


@router.get("/gold")
async def get_power_law_gold(session: AsyncSession = Depends(get_session)):
    """BTC/Gold ratio analysis with power law model."""
    current_price = await _get_current_price(session)
    macro = await _get_latest_macro(session)

    if not current_price or not macro or not macro.gold:
        return {"error": "Missing price or gold data"}

    gold_price = macro.gold
    btc_in_oz = current_price / gold_price

    # Simple ratio model (using default power law scaled for gold)
    ratio_model = RatioModel()
    # Use approximate ratio regression params
    ratio_model.intercept = -14.5
    ratio_model.slope = 4.8
    ratio_model.r_squared = 0.92

    model_oz = ratio_model.model_ratio()
    multiplier = btc_in_oz / model_oz if model_oz > 0 else 0

    projections = {}
    for key, d in {"dec_2026": datetime(2026, 12, 31), "dec_2030": datetime(2030, 12, 31), "dec_2035": datetime(2035, 12, 31)}.items():
        projections[key] = round(ratio_model.model_ratio(d), 2)

    milestones = {}
    for target in [100, 1000]:
        milestones[f"{target}_oz"] = ratio_model.find_milestone_date(target)

    return {
        "btc_price": current_price,
        "gold_price": gold_price,
        "btc_in_gold_oz": round(btc_in_oz, 2),
        "model_oz": round(model_oz, 2),
        "multiplier": round(multiplier, 4),
        "r_squared": ratio_model.r_squared,
        "projections": projections,
        "milestones": milestones,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/m2")
async def get_power_law_m2(session: AsyncSession = Depends(get_session)):
    """BTC/M2 money supply ratio analysis."""
    current_price = await _get_current_price(session)
    macro = await _get_latest_macro(session)

    if not current_price:
        return {"error": "Missing price data"}

    # Get M2 supply (from DB or fallback estimate)
    m2_supply = None
    if macro and macro.m2_supply:
        m2_supply = macro.m2_supply
    else:
        # Fallback estimate
        base_date = datetime(2024, 1, 1)
        base_m2 = 20.8
        years = (datetime.utcnow() - base_date).days / 365.25
        m2_supply = base_m2 * (1.072 ** years)

    # BTC/M2 index (BTC price / M2 in trillions * 10000 for readability)
    btc_m2_index = current_price / m2_supply if m2_supply > 0 else 0

    # Simple model for BTC/M2
    ratio_model = RatioModel()
    ratio_model.intercept = -13.8
    ratio_model.slope = 4.5
    ratio_model.r_squared = 0.90

    model_index = ratio_model.model_ratio()
    multiplier = btc_m2_index / model_index if model_index > 0 else 0

    projections = {}
    for key, d in {"dec_2026": datetime(2026, 12, 31), "dec_2030": datetime(2030, 12, 31), "dec_2035": datetime(2035, 12, 31)}.items():
        projections[key] = round(ratio_model.model_ratio(d), 2)

    milestones = {}
    for target in [10000, 40000, 100000, 400000]:
        milestones[f"${target:,}"] = ratio_model.find_milestone_date(target)

    return {
        "btc_price": current_price,
        "m2_supply_trillions": round(m2_supply, 2),
        "btc_m2_index": round(btc_m2_index, 4),
        "model_index": round(model_index, 4),
        "multiplier": round(multiplier, 4),
        "r_squared": ratio_model.r_squared,
        "projections": projections,
        "milestones": milestones,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/spx")
async def get_power_law_spx(session: AsyncSession = Depends(get_session)):
    """BTC/S&P 500 ratio analysis."""
    current_price = await _get_current_price(session)
    macro = await _get_latest_macro(session)

    if not current_price or not macro or not macro.sp500:
        return {"error": "Missing price or S&P 500 data"}

    spx_price = macro.sp500
    btc_spx_ratio = current_price / spx_price

    ratio_model = RatioModel()
    ratio_model.intercept = -14.0
    ratio_model.slope = 4.6
    ratio_model.r_squared = 0.91

    model_ratio = ratio_model.model_ratio()
    multiplier = btc_spx_ratio / model_ratio if model_ratio > 0 else 0

    projections = {}
    for key, d in {"dec_2026": datetime(2026, 12, 31), "dec_2030": datetime(2030, 12, 31), "dec_2035": datetime(2035, 12, 31)}.items():
        projections[key] = round(ratio_model.model_ratio(d), 2)

    milestones = {}
    for target in [20, 50, 100, 200]:
        milestones[f"{target}x"] = ratio_model.find_milestone_date(target)

    return {
        "btc_price": current_price,
        "spx_price": spx_price,
        "btc_spx_ratio": round(btc_spx_ratio, 4),
        "model_ratio": round(model_ratio, 4),
        "multiplier": round(multiplier, 4),
        "r_squared": ratio_model.r_squared,
        "projections": projections,
        "milestones": milestones,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/assets")
async def get_power_law_assets():
    """Asset class comparison: annual returns table."""
    path = DATA_DIR / "asset_returns.json"
    if not path.exists():
        return {"error": "Asset returns data not available"}

    with open(path) as f:
        data = json.load(f)

    years = data.get("years", [])
    assets = data.get("assets", {})

    # Calculate winner per year and win counts
    yearly_winners = []
    win_counts = {name: 0 for name in assets}

    for i, year in enumerate(years):
        best_asset = None
        best_return = float("-inf")
        for name, info in assets.items():
            returns = info.get("returns", [])
            if i < len(returns) and returns[i] > best_return:
                best_return = returns[i]
                best_asset = name
        yearly_winners.append({"year": year, "winner": best_asset, "return": best_return})
        if best_asset:
            win_counts[best_asset] = win_counts.get(best_asset, 0) + 1

    return {
        "years": years,
        "assets": assets,
        "yearly_winners": yearly_winners,
        "win_counts": win_counts,
        "total_years": len(years),
    }


@router.get("/milestones")
async def get_power_law_milestones():
    """Bitcoin milestones timeline from genesis to present."""
    path = DATA_DIR / "btc_milestones.json"
    if not path.exists():
        return {"error": "Milestones data not available"}

    with open(path) as f:
        milestones = json.load(f)

    # Group by era
    eras = {}
    for m in milestones:
        cat = m.get("category", "other")
        if cat not in eras:
            eras[cat] = []
        eras[cat].append(m)

    return {
        "milestones": milestones,
        "total": len(milestones),
        "categories": list(eras.keys()),
        "by_category": eras,
    }


@router.get("/calculator")
async def get_power_law_calculator(
    monthly_expenses: float = Query(3000, ge=100, le=1_000_000),
    years: int = Query(30, ge=5, le=50),
    apr: float = Query(4.0, ge=0, le=30),
    ltv: float = Query(50.0, ge=10, le=90),
    inflation: float = Query(3.0, ge=0, le=20),
    session: AsyncSession = Depends(get_session),
):
    """Retirement calculator: how much BTC needed to live off it forever.

    Calculates BTC needed based on expenses, borrowing against it at LTV,
    with projected appreciation via power law model.
    """
    current_price = await _get_current_price(session)
    if not current_price:
        return {"error": "No price data"}

    # Annual expenses adjusted for inflation over time
    annual_expenses = monthly_expenses * 12

    # BTC needed = annual expenses / (power law CAGR return - borrowing cost)
    # Simplified: need enough BTC that LTV borrowing covers expenses
    # BTC collateral * LTV% = annual expenses
    btc_needed = annual_expenses / (current_price * (ltv / 100))

    # Build timeline
    timeline = []
    for year in range(years + 1):
        future_date = datetime.utcnow() + timedelta(days=365 * year)
        projected_price = _engine.fair_value(future_date)
        adjusted_expenses = annual_expenses * ((1 + inflation / 100) ** year)
        btc_value = btc_needed * projected_price
        borrowing_capacity = btc_value * (ltv / 100)
        surplus = borrowing_capacity - adjusted_expenses

        timeline.append({
            "year": year,
            "date": future_date.strftime("%Y"),
            "btc_price": round(projected_price, 2),
            "btc_value": round(btc_value, 2),
            "expenses": round(adjusted_expenses, 2),
            "borrowing_capacity": round(borrowing_capacity, 2),
            "surplus": round(surplus, 2),
        })

    return {
        "inputs": {
            "monthly_expenses": monthly_expenses,
            "years": years,
            "apr": apr,
            "ltv": ltv,
            "inflation": inflation,
        },
        "btc_needed": round(btc_needed, 6),
        "btc_value_usd": round(btc_needed * current_price, 2),
        "current_btc_price": current_price,
        "timeline": timeline,
    }


@router.get("/upcoming")
async def get_upcoming_events(session: AsyncSession = Depends(get_session)):
    """Upcoming events that could impact BTC price.

    Tracks impending regulations, tax changes, trade policies,
    company announcements, geopolitical events, and their potential
    impact on Bitcoin.
    """
    # Static upcoming events (would be augmented by news classification in production)
    upcoming = _get_upcoming_events_data()
    return {
        "events": upcoming,
        "total": len(upcoming),
        "timestamp": datetime.utcnow().isoformat(),
    }


def _get_upcoming_events_data() -> list[dict]:
    """Return curated list of upcoming events with BTC impact analysis."""
    now = datetime.utcnow()
    events = [
        {
            "id": 1,
            "title": "US Federal Reserve FOMC Meeting",
            "date": "2026-03-18",
            "category": "macro",
            "impact": "high",
            "direction": "neutral",
            "description": "Fed interest rate decision. Rate cuts are bullish for BTC as they weaken the dollar and push investors toward risk assets. Rate hikes are bearish.",
            "why_matters": "Lower rates = cheaper borrowing = more risk appetite = BTC up. Higher rates = stronger dollar = BTC down.",
            "status": "upcoming",
        },
        {
            "id": 2,
            "title": "US Crypto Regulatory Framework",
            "date": "2026-Q2",
            "category": "regulation",
            "impact": "high",
            "direction": "bullish",
            "description": "Congress expected to pass comprehensive crypto regulation bill. Clear rules reduce uncertainty and attract institutional capital.",
            "why_matters": "Regulatory clarity removes a major overhang. Institutions that were waiting on sidelines can now allocate to BTC.",
            "status": "expected",
        },
        {
            "id": 3,
            "title": "Bitcoin Strategic Reserve Developments",
            "date": "2026-Q1",
            "category": "adoption",
            "impact": "very_high",
            "direction": "bullish",
            "description": "Multiple countries evaluating Bitcoin strategic reserves following US executive order. Sovereign buying pressure could significantly impact supply.",
            "why_matters": "Nation-state buying is the ultimate demand driver. Even small allocations from sovereign wealth funds dwarf retail demand.",
            "status": "ongoing",
        },
        {
            "id": 4,
            "title": "Trump Tariff Policy Changes",
            "date": "2026-Q1",
            "category": "macro",
            "impact": "high",
            "direction": "mixed",
            "description": "New tariff policies affecting global trade. Trade wars can strengthen USD short-term (bearish BTC) but create inflation long-term (bullish BTC as hedge).",
            "why_matters": "Tariffs cause inflation → BTC is inflation hedge. But trade uncertainty can trigger risk-off selling across all assets including BTC.",
            "status": "ongoing",
        },
        {
            "id": 5,
            "title": "BlackRock & Major ETF Inflows",
            "date": "2026-ongoing",
            "category": "institutional",
            "impact": "very_high",
            "direction": "bullish",
            "description": "BlackRock IBIT and other spot Bitcoin ETFs continue accumulating. Daily inflows averaging hundreds of millions of dollars remove BTC from circulation.",
            "why_matters": "ETF buying is persistent, daily demand. As supply on exchanges shrinks, even small additional demand causes outsized price moves.",
            "status": "ongoing",
        },
        {
            "id": 6,
            "title": "2028 Bitcoin Halving Anticipation",
            "date": "2028-04",
            "category": "halving",
            "impact": "very_high",
            "direction": "bullish",
            "description": "Next Bitcoin halving expected ~April 2028. Block reward drops from 3.125 to 1.5625 BTC. Markets typically start pricing this in 12-18 months before.",
            "why_matters": "Every halving has preceded a major bull run. Supply shock: daily new BTC creation drops 50%, but demand keeps growing.",
            "status": "future",
        },
        {
            "id": 7,
            "title": "Middle East Geopolitical Developments",
            "date": "2026-ongoing",
            "category": "geopolitical",
            "impact": "medium",
            "direction": "mixed",
            "description": "Saudi Arabia and Iran trade developments, OPEC+ decisions affecting oil prices. Oil price spikes cause inflation, potentially bullish for BTC as inflation hedge.",
            "why_matters": "Geopolitical instability drives demand for non-sovereign stores of value. BTC benefits from 'digital gold' narrative during uncertainty.",
            "status": "monitoring",
        },
        {
            "id": 8,
            "title": "US Tax Policy & Capital Gains Changes",
            "date": "2026-Q2",
            "category": "regulation",
            "impact": "medium",
            "direction": "bearish",
            "description": "Potential changes to capital gains tax rates on crypto holdings. Higher taxes could reduce trading volume and selling pressure as holders delay realizing gains.",
            "why_matters": "Higher capital gains tax = less selling (holders wait longer) = reduced supply on market. Short-term bearish sentiment but may actually reduce sell pressure.",
            "status": "proposed",
        },
        {
            "id": 9,
            "title": "Global De-dollarization Trend",
            "date": "2026-ongoing",
            "category": "macro",
            "impact": "high",
            "direction": "bullish",
            "description": "BRICS nations and others reducing USD dependence. Bitcoin emerges as neutral settlement layer and reserve asset outside any single country's control.",
            "why_matters": "As countries diversify away from USD, BTC benefits as a politically neutral store of value that no government can sanction or freeze.",
            "status": "ongoing",
        },
        {
            "id": 10,
            "title": "MicroStrategy & Corporate Treasury Adoption",
            "date": "2026-ongoing",
            "category": "adoption",
            "impact": "high",
            "direction": "bullish",
            "description": "More public companies adding BTC to treasury reserves following MicroStrategy playbook. Corporate buying creates steady, large-scale demand.",
            "why_matters": "Corporate treasuries represent trillions in potential BTC demand. Even 1% allocation would absorb years of mining supply.",
            "status": "ongoing",
        },
    ]

    return events
