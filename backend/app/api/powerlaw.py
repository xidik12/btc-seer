"""BTC Power Law API endpoints.

Formula: Price = 10^(intercept + slope * log10(days_since_genesis))
Genesis: January 3, 2009
All parameters computed from historical data via OLS regression.

Corridor bands:
  Support    = fair_value * 0.42
  Mid        = fair_value * 0.71
  Fair       = fair_value * 1.0
  Top Resist = fair_value * 1.5
"""
import json
import math
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Price, MacroData
from app.models.power_law_engine import PowerLawEngine, RatioModel
from app.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/powerlaw", tags=["powerlaw"])

BTC_GENESIS = datetime(2009, 1, 3)

# Corridor multipliers
CORRIDOR = {
    "support": 0.42,
    "mid": 0.71,
    "fair": 1.0,
    "top_resistance": 1.5,
}

# ── Cached engine (fitted from data, refreshed every 6 hours) ──
_engine_cache = {"engine": None, "fitted_at": 0}
_ratio_cache = {"gold": None, "m2": None, "spx": None, "fitted_at": 0}
CACHE_TTL = 6 * 3600  # 6 hours


async def _get_engine(session: AsyncSession) -> PowerLawEngine:
    """Get or create cached PowerLawEngine fitted from DB + early price data."""
    now = time.time()
    if _engine_cache["engine"] and (now - _engine_cache["fitted_at"]) < CACHE_TTL:
        return _engine_cache["engine"]

    try:
        # Get daily prices from DB (one per day, deduplicated)
        result = await session.execute(
            select(Price).order_by(Price.timestamp)
        )
        db_prices = result.scalars().all()
        engine = PowerLawEngine.from_db_prices(db_prices)
        logger.info(f"PowerLawEngine fitted: slope={engine.slope}, intercept={engine.intercept}, R²={engine.r_squared}")
    except Exception as e:
        logger.warning(f"Failed to fit from DB ({e}), using early prices only")
        engine = PowerLawEngine.from_early_prices()

    _engine_cache["engine"] = engine
    _engine_cache["fitted_at"] = now
    return engine


def _load_early_ratios() -> tuple[list, list, list]:
    """Load historical BTC ratios from static early price + macro data.

    Returns (gold_ratios, m2_ratios, spx_ratios) as lists of (datetime, ratio).
    Sources: LBMA gold fix, S&P 500 monthly close, FRED M2 money supply.
    """
    btc_path = DATA_DIR / "btc_early_prices.json"
    macro_path = DATA_DIR / "macro_early_data.json"
    if not btc_path.exists() or not macro_path.exists():
        return [], [], []

    with open(btc_path) as f:
        btc_data = json.load(f)
    with open(macro_path) as f:
        macro_data = json.load(f)

    # Build macro lookup by YYYY-MM
    macro_by_month = {}
    for m in macro_data:
        key = m["date"][:7]  # "2011-01"
        macro_by_month[key] = m

    gold_ratios, m2_ratios, spx_ratios = [], [], []
    for item in btc_data:
        btc_price = item["price"]
        if btc_price <= 0:
            continue
        d = datetime.fromisoformat(item["date"])
        month_key = item["date"][:7]
        m = macro_by_month.get(month_key)
        if not m:
            continue
        if m["gold"] and m["gold"] > 0:
            gold_ratios.append((d, btc_price / m["gold"]))
        if m["sp500"] and m["sp500"] > 0:
            spx_ratios.append((d, btc_price / m["sp500"]))
        if m["m2_supply"] and m["m2_supply"] > 0:
            m2_ratios.append((d, btc_price / m["m2_supply"]))

    return gold_ratios, m2_ratios, spx_ratios


async def _get_ratio_models(session: AsyncSession) -> dict:
    """Fit Gold, M2, SPX ratio models from historical data."""
    now_ts = time.time()
    if _ratio_cache["gold"] and (now_ts - _ratio_cache["fitted_at"]) < CACHE_TTL:
        return _ratio_cache

    # Start with full historical ratios from static data
    gold_ratios, m2_ratios, spx_ratios = _load_early_ratios()

    # Supplement with DB prices + macro data
    price_result = await session.execute(select(Price).order_by(Price.timestamp))
    prices = price_result.scalars().all()

    macro_result = await session.execute(select(MacroData).order_by(MacroData.timestamp))
    macros = macro_result.scalars().all()

    macro_by_date = {}
    for m in macros:
        day_key = m.timestamp.strftime("%Y-%m-%d")
        macro_by_date[day_key] = m

    for p in prices:
        if not p.close or p.close <= 0:
            continue
        day_key = p.timestamp.strftime("%Y-%m-%d")
        m = macro_by_date.get(day_key)
        if m:
            if m.gold and m.gold > 0:
                gold_ratios.append((p.timestamp, p.close / m.gold))
            if m.sp500 and m.sp500 > 0:
                spx_ratios.append((p.timestamp, p.close / m.sp500))
            if hasattr(m, 'm2_supply') and m.m2_supply and m.m2_supply > 0:
                m2_ratios.append((p.timestamp, p.close / m.m2_supply))

    try:
        _ratio_cache["gold"] = RatioModel.fit(gold_ratios) if len(gold_ratios) >= 20 else None
    except Exception as e:
        logger.warning(f"Gold ratio fit failed: {e}")
        _ratio_cache["gold"] = None

    try:
        _ratio_cache["spx"] = RatioModel.fit(spx_ratios) if len(spx_ratios) >= 20 else None
    except Exception as e:
        logger.warning(f"SPX ratio fit failed: {e}")
        _ratio_cache["spx"] = None

    try:
        _ratio_cache["m2"] = RatioModel.fit(m2_ratios) if len(m2_ratios) >= 20 else None
    except Exception as e:
        logger.warning(f"M2 ratio fit failed: {e}")
        _ratio_cache["m2"] = None

    _ratio_cache["fitted_at"] = now_ts
    logger.info(f"Ratio models fitted — gold:{_ratio_cache['gold'] is not None}, spx:{_ratio_cache['spx'] is not None}, m2:{_ratio_cache['m2'] is not None}")
    return _ratio_cache


def power_law_fair_value(target_date: datetime = None) -> float:
    """Calculate BTC Power Law fair value using cached engine.
    Fallback to early-prices-only engine if cache is empty.
    """
    engine = _engine_cache.get("engine")
    if engine is None:
        engine = PowerLawEngine.from_early_prices()
    return engine.fair_value(target_date)


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


def _build_dashboard_calculations(engine, current_price: float, stats: dict) -> dict:
    """Build calculation explanations for each dashboard stat."""
    days = stats["days_since_genesis"]
    fv = stats["model_price"]
    result = {
        "model_price": {
            "formula": "10^(intercept + slope * log10(days_since_genesis))",
            "inputs": {
                "intercept": engine.intercept,
                "slope": engine.slope,
                "days_since_genesis": days,
                "log10_days": round(math.log10(days), 4) if days > 0 else 0,
            },
            "steps": [
                f"log10({days}) = {math.log10(days):.4f}" if days > 0 else "N/A",
                f"{engine.intercept} + {engine.slope} * {math.log10(days):.4f} = {engine.intercept + engine.slope * math.log10(days):.4f}" if days > 0 else "N/A",
                f"10^{engine.intercept + engine.slope * math.log10(days):.4f} = ${fv:,.2f}" if days > 0 else "N/A",
            ],
            "explanation": "The Power Law model fits a straight line in log-log space to Bitcoin's entire price history. The model price is calculated by taking 10 raised to the power of (intercept + slope * log10 of days since Bitcoin genesis on Jan 3, 2009).",
        },
        "multiplier": {
            "formula": "current_price / model_price",
            "inputs": {"current_price": current_price, "model_price": fv},
            "steps": [f"${current_price:,.2f} / ${fv:,.2f} = {stats['multiplier']:.4f}x"],
            "explanation": "The multiplier shows how far the actual price is from the model's fair value. Below 1.0x means undervalued relative to the power law trend. Above 1.0x means overvalued.",
        },
        "deviation_pct": {
            "formula": "((current_price - model_price) / model_price) * 100",
            "inputs": {"current_price": current_price, "model_price": fv},
            "steps": [
                f"({current_price:,.2f} - {fv:,.2f}) / {fv:,.2f} * 100",
                f"= {stats['deviation_pct']:.2f}%",
            ],
            "explanation": "Percentage deviation from the power law fair value. Negative means BTC is trading below the model's expected price. Historically, BTC oscillates between -60% and +150% of the model.",
        },
        "slope": {
            "formula": "OLS regression slope in log10-log10 space",
            "inputs": {"n_data_points": "All daily prices since 2010"},
            "steps": [
                "1. Convert all (date, price) pairs to (log10(days), log10(price))",
                "2. Run Ordinary Least Squares (OLS) linear regression",
                f"3. Fitted slope B = {engine.slope}",
            ],
            "explanation": "The slope (B) of the power law regression represents Bitcoin's growth rate in log-log space. A slope of ~5.5 means that for every 10x increase in time, price increases by 10^5.5 = ~316,000x. Computed via OLS regression on all historical daily prices.",
        },
        "r_squared": {
            "formula": "R2 = 1 - (SS_residual / SS_total)",
            "inputs": {"SS_res": "Sum of squared residuals", "SS_tot": "Total sum of squares"},
            "steps": [
                "1. For each data point: residual = actual_log_price - predicted_log_price",
                "2. SS_res = sum(residuals^2)",
                "3. SS_tot = sum((log_price - mean_log_price)^2)",
                f"4. R2 = 1 - SS_res/SS_tot = {engine.r_squared}",
            ],
            "explanation": "R-squared measures how well the power law model fits the data. A value of 0.95+ means the model explains over 95% of Bitcoin's price variance in log-log space. Computed from OLS regression residuals.",
        },
        "log_volatility": {
            "formula": "sigma = sqrt(SS_residual / (n - 2))",
            "inputs": {"description": "Standard deviation of residuals in log10 space"},
            "steps": [
                "1. Compute residuals: actual_log_price - predicted_log_price for each point",
                "2. Sum of squared residuals (SS_res)",
                f"3. sigma = sqrt(SS_res / (n-2)) = {engine.log_volatility}",
            ],
            "explanation": "Log volatility measures the typical scatter of actual prices around the model line in log space. Lower values mean prices track the model more closely. A value of 0.20 means prices typically deviate by +/-10^0.20 = +/-58% from the model.",
        },
        "cagr": {
            "formula": "((model_price_now / genesis_value)^(1/years) - 1) * 100",
            "inputs": {"years_since_genesis": round(days / 365.25, 1) if days > 0 else 0},
            "steps": [
                f"Model price today: ${fv:,.2f}",
                f"Years since genesis: {days / 365.25:.1f}" if days > 0 else "N/A",
                f"CAGR = {stats['cagr']}%",
            ],
            "explanation": "Compound Annual Growth Rate of the power law model from genesis to today. This represents the model's implied average yearly return. Note: actual CAGR varies depending on entry date.",
        },
    }

    # Projection calculations
    projection_targets = {
        "dec_2026": datetime(2026, 12, 31),
        "dec_2030": datetime(2030, 12, 31),
        "dec_2035": datetime(2035, 12, 31),
        "dec_2045": datetime(2045, 12, 31),
    }
    for key, target_date in projection_targets.items():
        target_days = (target_date - datetime(2009, 1, 3)).days
        log_days = math.log10(target_days)
        log_price = engine.intercept + engine.slope * log_days
        projected = 10 ** log_price
        result[f"proj_{key}"] = {
            "formula": "10^(intercept + slope * log10(days_to_target))",
            "inputs": {
                "target_date": target_date.strftime("%Y-%m-%d"),
                "days_since_genesis": target_days,
                "intercept": engine.intercept,
                "slope": engine.slope,
            },
            "steps": [
                f"Days from genesis to {target_date.strftime('%b %Y')}: {target_days}",
                f"log10({target_days}) = {log_days:.4f}",
                f"{engine.intercept} + {engine.slope} * {log_days:.4f} = {log_price:.4f}",
                f"10^{log_price:.4f} = ${projected:,.2f}",
            ],
            "explanation": f"Projected price for {target_date.strftime('%B %Y')} based on the power law trendline — not a prediction, but where the model's fair value line will be at that date.",
        }

    # Milestone calculations
    for target in [1_000_000, 10_000_000]:
        label = f"${target:,.0f}"
        # Trendline date: solve for date where model = target
        log_target = math.log10(target)
        log_days_ms = (log_target - engine.intercept) / engine.slope
        days_ms = 10 ** log_days_ms
        ms_date = engine.find_milestone_date(target)
        sanitized = str(target)
        result[f"milestone_{sanitized}_trendline"] = {
            "formula": "days = 10^((log10(target_price) - intercept) / slope)",
            "inputs": {
                "target_price": f"${target:,.0f}",
                "intercept": engine.intercept,
                "slope": engine.slope,
            },
            "steps": [
                f"log10({target:,.0f}) = {log_target:.4f}",
                f"({log_target:.4f} - {engine.intercept}) / {engine.slope} = {log_days_ms:.4f}",
                f"10^{log_days_ms:.4f} = {days_ms:,.0f} days from genesis",
                f"Genesis + {days_ms:,.0f} days = {ms_date}",
            ],
            "explanation": f"The date when the power law trendline (fair value) reaches {label}. This is when the model's central estimate equals the target price.",
        }
        # Earliest date: solve for date where model * 4 = target (upper band)
        earliest_target = target / 4.0
        log_target_e = math.log10(earliest_target)
        log_days_e = (log_target_e - engine.intercept) / engine.slope
        days_e = 10 ** log_days_e
        earliest_date = engine.find_milestone_date(earliest_target)
        result[f"milestone_{sanitized}_earliest"] = {
            "formula": "days = 10^((log10(target_price / 4) - intercept) / slope)",
            "inputs": {
                "target_price": f"${target:,.0f}",
                "at_4x_multiplier": f"${earliest_target:,.0f}",
                "intercept": engine.intercept,
                "slope": engine.slope,
            },
            "steps": [
                f"{label} / 4 = ${earliest_target:,.0f} (model needs to reach this for price to hit {label} at 4x upper band)",
                f"log10({earliest_target:,.0f}) = {log_target_e:.4f}",
                f"({log_target_e:.4f} - {engine.intercept}) / {engine.slope} = {log_days_e:.4f}",
                f"10^{log_days_e:.4f} = {days_e:,.0f} days from genesis",
                f"Genesis + {days_e:,.0f} days = {earliest_date}",
            ],
            "explanation": f"The earliest possible date for {label} BTC, assuming price reaches 4x above the trendline (the historical upper band). This is when the model's fair value equals {label}/4 = ${earliest_target:,.0f}.",
        }

    return result


def _build_ratio_calculations(asset: str, model, actual_ratio: float, model_ratio: float, asset_price: float, btc_price: float) -> dict:
    """Build calculation explanations for ratio model stats."""
    asset_labels = {
        "gold": {"name": "Gold", "unit": "oz", "ratio_label": "BTC/Gold (oz)"},
        "m2": {"name": "M2 Money Supply", "unit": "$T", "ratio_label": "BTC/M2 Index"},
        "spx": {"name": "S&P 500", "unit": "x", "ratio_label": "BTC/SPX Ratio"},
    }
    info = asset_labels.get(asset, {"name": asset, "unit": "", "ratio_label": f"BTC/{asset}"})
    now = datetime.utcnow()
    days = (now - BTC_GENESIS).days

    return {
        "ratio": {
            "formula": f"BTC_price / {info['name']}_price",
            "inputs": {"btc_price": btc_price, f"{asset}_price": asset_price},
            "steps": [f"${btc_price:,.2f} / ${asset_price:,.2f} = {actual_ratio:.4f}"],
            "explanation": f"The actual {info['ratio_label']} calculated by dividing the current Bitcoin price by the current {info['name']} price. Shows how many units of {info['name']} one Bitcoin is worth.",
        },
        "model_ratio": {
            "formula": f"10^(intercept + slope * log10(days_since_genesis))",
            "inputs": {
                "intercept": model.intercept,
                "slope": model.slope,
                "days_since_genesis": days,
            },
            "steps": [
                f"log10({days}) = {math.log10(days):.4f}" if days > 0 else "N/A",
                f"{model.intercept} + {model.slope} * {math.log10(days):.4f} = {model.intercept + model.slope * math.log10(days):.4f}" if days > 0 else "N/A",
                f"10^{model.intercept + model.slope * math.log10(days):.4f} = {model_ratio:.4f}" if days > 0 else "N/A",
            ],
            "explanation": f"The power law model for {info['ratio_label']} fitted via OLS regression in log-log space on all historical ratio data points. Predicts the expected ratio based on Bitcoin's age.",
        },
        "multiplier": {
            "formula": "actual_ratio / model_ratio",
            "inputs": {"actual": actual_ratio, "model": model_ratio},
            "steps": [f"{actual_ratio:.4f} / {model_ratio:.4f} = {actual_ratio / model_ratio:.4f}x" if model_ratio > 0 else "N/A"],
            "explanation": f"How far the actual {info['ratio_label']} is from the model prediction. Below 1.0x means the ratio is below trend (BTC undervalued relative to {info['name']}). Above 1.0x means above trend.",
        },
        "r_squared": {
            "formula": "R2 = 1 - (SS_residual / SS_total)",
            "inputs": {"value": model.r_squared},
            "steps": [f"R2 = {model.r_squared} ({model.r_squared * 100:.1f}% of variance explained)"],
            "explanation": f"How well the power law fits the historical {info['ratio_label']} data. Computed from OLS regression in log-log space on all available ratio data points.",
        },
        "slope": {
            "formula": "OLS regression slope B in log10-log10 space",
            "inputs": {"value": model.slope},
            "steps": [f"B = {model.slope}"],
            "explanation": f"The growth rate of {info['ratio_label']} in log-log space. Higher slope means Bitcoin is gaining value against {info['name']} faster over time.",
        },
        "log_volatility": {
            "formula": "sigma = sqrt(SS_residual / (n - 2))",
            "inputs": {"value": model.log_volatility},
            "steps": [f"sigma = {model.log_volatility}"],
            "explanation": f"Standard deviation of the residuals in log space. Shows how much the actual ratio typically deviates from the model prediction.",
        },
        "cagr": {
            "formula": "((ratio_now / ratio_start)^(1/years) - 1) * 100",
            "inputs": {"value": model.cagr},
            "steps": [f"CAGR = {model.cagr}%"],
            "explanation": f"Compound Annual Growth Rate of the {info['ratio_label']} model. Shows how fast Bitcoin is outpacing {info['name']} per year on average.",
        },
    }


@router.get("/current")
async def get_power_law_current(session: AsyncSession = Depends(get_session)):
    """Current BTC price vs Power Law fair value."""
    cached = await cache_get("pl:current")
    if cached is not None:
        return cached

    engine = await _get_engine(session)

    # Get latest price
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price_row = result.scalar_one_or_none()
    current_price = price_row.close if price_row else None

    now = datetime.utcnow()
    days_since_genesis = (now - BTC_GENESIS).days
    fair_value = engine.fair_value(now)

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

    data = {
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
            "intercept": engine.intercept,
            "slope": engine.slope,
            "r_squared": engine.r_squared,
            "genesis": BTC_GENESIS.isoformat(),
        },
        "timestamp": now.isoformat(),
    }
    await cache_set("pl:current", data, 60)
    return data


@router.get("/historical")
async def get_power_law_historical(
    days: int = Query(365, ge=30, le=3650),
    session: AsyncSession = Depends(get_session),
):
    """Historical Power Law curve + actual BTC price for charting."""
    cache_key = f"pl:hist:{days}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    engine = await _get_engine(session)
    now = datetime.utcnow()

    # Generate power law curve points (daily)
    curve_points = []
    for d in range(max(1, (now - BTC_GENESIS).days - days), (now - BTC_GENESIS).days + 1):
        date = BTC_GENESIS + timedelta(days=d)
        fv = engine.fair_value(date)
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

    data = {
        "days": days,
        "points": curve_points,
        "parameters": {
            "intercept": engine.intercept,
            "slope": engine.slope,
            "r_squared": engine.r_squared,
            "genesis": BTC_GENESIS.isoformat(),
            "corridor_multipliers": CORRIDOR,
        },
    }
    await cache_set(cache_key, data, 300)
    return data


# ════════════════════════════════════════════════════════════════
#  NEW ENDPOINTS — b1m.io-style features
# ════════════════════════════════════════════════════════════════

DATA_DIR = Path(__file__).parent.parent / "data"


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
    cached = await cache_get("pl:dashboard")
    if cached is not None:
        return cached

    current_price = await _get_current_price(session)
    if not current_price:
        return {"error": "No price data available"}

    engine = await _get_engine(session)
    change_24h = await _get_24h_change(session)
    stats = engine.get_stats(current_price)
    stats["change_24h"] = change_24h
    stats["calculations"] = _build_dashboard_calculations(engine, current_price, stats)

    await cache_set("pl:dashboard", stats, 60)
    return stats


@router.get("/curve")
async def get_power_law_curve(
    session: AsyncSession = Depends(get_session),
):
    """Full power law curve from 2011 to 2045 with model line, bands, and actual price."""
    cached = await cache_get("pl:curve")
    if cached is not None:
        return cached

    engine = await _get_engine(session)
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
        fv = engine.fair_value(date)
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
    today_fv = engine.fair_value(now)
    current_price = await _get_current_price(session)

    data = {
        "points": curve_points,
        "today": {
            "date": now.strftime("%Y-%m-%d"),
            "model_price": round(today_fv, 2),
            "actual_price": current_price,
            "days_since_genesis": today_day,
        },
    }
    await cache_set("pl:curve", data, 300)
    return data


@router.get("/gold")
async def get_power_law_gold(session: AsyncSession = Depends(get_session)):
    """BTC/Gold ratio analysis with power law model fitted from data."""
    cached = await cache_get("pl:gold")
    if cached is not None:
        return cached

    current_price = await _get_current_price(session)
    macro = await _get_latest_macro(session)

    if not current_price or not macro or not macro.gold:
        return {"error": "Missing price or gold data"}

    gold_price = macro.gold
    btc_in_oz = current_price / gold_price

    ratios = await _get_ratio_models(session)
    ratio_model = ratios.get("gold")
    if not ratio_model:
        return {"error": "Not enough data to fit BTC/Gold model"}

    model_oz = ratio_model.model_ratio()
    multiplier = btc_in_oz / model_oz if model_oz > 0 else 0

    projections = {}
    for key, d in {"dec_2026": datetime(2026, 12, 31), "dec_2030": datetime(2030, 12, 31), "dec_2035": datetime(2035, 12, 31), "dec_2045": datetime(2045, 12, 31)}.items():
        projections[key] = round(ratio_model.model_ratio(d), 1)

    milestones = {}
    for target in [100, 1000]:
        milestones[f"{target}_oz"] = ratio_model.find_milestone_date(target)

    response = {
        "btc_price": current_price,
        "gold_price": gold_price,
        "btc_in_gold_oz": round(btc_in_oz, 2),
        "model_oz": round(model_oz, 2),
        "multiplier": round(multiplier, 4),
        "slope": ratio_model.slope,
        "r_squared": ratio_model.r_squared,
        "log_volatility": ratio_model.log_volatility,
        "cagr": ratio_model.cagr,
        "projections": projections,
        "milestones": milestones,
        "timestamp": datetime.utcnow().isoformat(),
    }
    response["calculations"] = _build_ratio_calculations("gold", ratio_model, btc_in_oz, model_oz, gold_price, current_price)
    await cache_set("pl:gold", response, 300)
    return response


@router.get("/m2")
async def get_power_law_m2(session: AsyncSession = Depends(get_session)):
    """BTC/M2 money supply ratio analysis fitted from data."""
    cached = await cache_get("pl:m2")
    if cached is not None:
        return cached

    current_price = await _get_current_price(session)
    macro = await _get_latest_macro(session)

    if not current_price:
        return {"error": "Missing price data"}

    # Get M2 supply from DB
    m2_supply = None
    if macro and hasattr(macro, 'm2_supply') and macro.m2_supply:
        m2_supply = macro.m2_supply

    if not m2_supply:
        return {"error": "Missing M2 supply data"}

    btc_m2_index = current_price / m2_supply if m2_supply > 0 else 0

    ratios = await _get_ratio_models(session)
    ratio_model = ratios.get("m2")
    if not ratio_model:
        return {"error": "Not enough data to fit BTC/M2 model"}

    model_index = ratio_model.model_ratio()
    multiplier = btc_m2_index / model_index if model_index > 0 else 0

    projections = {}
    for key, d in {"dec_2026": datetime(2026, 12, 31), "dec_2030": datetime(2030, 12, 31), "dec_2035": datetime(2035, 12, 31), "dec_2045": datetime(2045, 12, 31)}.items():
        projections[key] = round(ratio_model.model_ratio(d))

    milestones = {}
    for target in [10000, 40000, 100000, 400000]:
        milestones[f"${target:,}"] = ratio_model.find_milestone_date(target)

    response = {
        "btc_price": current_price,
        "m2_supply_trillions": round(m2_supply, 2),
        "btc_m2_index": round(btc_m2_index, 4),
        "model_index": round(model_index, 4),
        "multiplier": round(multiplier, 4),
        "slope": ratio_model.slope,
        "r_squared": ratio_model.r_squared,
        "log_volatility": ratio_model.log_volatility,
        "cagr": ratio_model.cagr,
        "projections": projections,
        "milestones": milestones,
        "timestamp": datetime.utcnow().isoformat(),
    }
    response["calculations"] = _build_ratio_calculations("m2", ratio_model, btc_m2_index, model_index, m2_supply, current_price)
    await cache_set("pl:m2", response, 300)
    return response


@router.get("/spx")
async def get_power_law_spx(session: AsyncSession = Depends(get_session)):
    """BTC/S&P 500 ratio analysis fitted from data."""
    cached = await cache_get("pl:spx")
    if cached is not None:
        return cached

    current_price = await _get_current_price(session)
    macro = await _get_latest_macro(session)

    if not current_price or not macro or not macro.sp500:
        return {"error": "Missing price or S&P 500 data"}

    spx_price = macro.sp500
    btc_spx_ratio = current_price / spx_price

    ratios = await _get_ratio_models(session)
    ratio_model = ratios.get("spx")
    if not ratio_model:
        return {"error": "Not enough data to fit BTC/SPX model"}

    model_ratio = ratio_model.model_ratio()
    multiplier = btc_spx_ratio / model_ratio if model_ratio > 0 else 0

    projections = {}
    for key, d in {"dec_2026": datetime(2026, 12, 31), "dec_2030": datetime(2030, 12, 31), "dec_2035": datetime(2035, 12, 31), "dec_2045": datetime(2045, 12, 31)}.items():
        projections[key] = round(ratio_model.model_ratio(d), 1)

    milestones = {}
    for target in [20, 50, 100, 200]:
        milestones[f"{target}x"] = ratio_model.find_milestone_date(target)

    response = {
        "btc_price": current_price,
        "spx_price": spx_price,
        "btc_spx_ratio": round(btc_spx_ratio, 4),
        "model_ratio": round(model_ratio, 4),
        "multiplier": round(multiplier, 4),
        "slope": ratio_model.slope,
        "r_squared": ratio_model.r_squared,
        "log_volatility": ratio_model.log_volatility,
        "cagr": ratio_model.cagr,
        "projections": projections,
        "milestones": milestones,
        "timestamp": datetime.utcnow().isoformat(),
    }
    response["calculations"] = _build_ratio_calculations("spx", ratio_model, btc_spx_ratio, model_ratio, spx_price, current_price)
    await cache_set("pl:spx", response, 300)
    return response


@router.get("/assets")
async def get_power_law_assets():
    """Asset class comparison: annual returns table."""
    cached = await cache_get("pl:assets")
    if cached is not None:
        return cached

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

    data = {
        "years": years,
        "assets": assets,
        "yearly_winners": yearly_winners,
        "win_counts": win_counts,
        "total_years": len(years),
    }
    await cache_set("pl:assets", data, 3600)
    return data


@router.get("/milestones")
async def get_power_law_milestones():
    """Bitcoin milestones timeline from genesis to present."""
    cached = await cache_get("pl:milestones")
    if cached is not None:
        return cached

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

    data = {
        "milestones": milestones,
        "total": len(milestones),
        "categories": list(eras.keys()),
        "by_category": eras,
    }
    await cache_set("pl:milestones", data, 3600)
    return data


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

    engine = await _get_engine(session)

    # Build timeline
    timeline = []
    for year in range(years + 1):
        future_date = datetime.utcnow() + timedelta(days=365 * year)
        projected_price = engine.fair_value(future_date)
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
