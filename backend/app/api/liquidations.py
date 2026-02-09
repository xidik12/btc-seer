"""Liquidation Map API — estimates leveraged liquidation clusters by price level.

Uses Binance public endpoints (no API key needed):
- Open Interest
- Long/Short ratios
- Futures klines (volume profile for entry distribution)
- Funding rate (from existing FundingRate table)

Liquidation formula:
  Long liq  = entry * (1 - 1/leverage + mmr)
  Short liq = entry * (1 + 1/leverage - mmr)
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, FundingRate, Price
from app.collectors.market import MarketCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/liquidations", tags=["liquidations"])

# Hardcoded Binance BTCUSDT leverage brackets
LEVERAGE_TIERS = [
    {"leverage": 125, "mmr": 0.004},
    {"leverage": 100, "mmr": 0.005},
    {"leverage": 50,  "mmr": 0.010},
    {"leverage": 25,  "mmr": 0.025},
    {"leverage": 10,  "mmr": 0.050},
    {"leverage": 5,   "mmr": 0.100},
]

# Assumed leverage distribution (% of OI at each tier)
LEVERAGE_DISTRIBUTION = {
    5: 0.10,
    10: 0.20,
    25: 0.30,
    50: 0.20,
    100: 0.15,
    125: 0.05,
}

BIN_SIZE = 100  # $100 price bins


def _calc_long_liq(entry: float, leverage: int, mmr: float) -> float:
    return entry * (1 - 1 / leverage + mmr)


def _calc_short_liq(entry: float, leverage: int, mmr: float) -> float:
    return entry * (1 + 1 / leverage - mmr)


def _build_volume_profile(klines: list[dict]) -> list[dict]:
    """Build a volume profile from klines — weighted average price per candle."""
    profile = []
    for k in klines:
        vwap = (k["high"] + k["low"] + k["close"]) / 3
        profile.append({"price": vwap, "volume": k["quote_volume"]})
    return profile


def _compute_liquidation_bins(
    volume_profile: list[dict],
    long_oi_usd: float,
    short_oi_usd: float,
    current_price: float,
) -> list[dict]:
    """Compute liquidation volume bins from volume profile and OI split."""
    total_volume = sum(p["volume"] for p in volume_profile) or 1.0

    long_bins = defaultdict(float)
    short_bins = defaultdict(float)

    for point in volume_profile:
        weight = point["volume"] / total_volume

        for tier in LEVERAGE_TIERS:
            lev = tier["leverage"]
            mmr = tier["mmr"]
            dist = LEVERAGE_DISTRIBUTION.get(lev, 0)

            long_liq_price = _calc_long_liq(point["price"], lev, mmr)
            short_liq_price = _calc_short_liq(point["price"], lev, mmr)

            long_liq_volume = long_oi_usd * weight * dist
            short_liq_volume = short_oi_usd * weight * dist

            long_bin = int(long_liq_price / BIN_SIZE) * BIN_SIZE
            short_bin = int(short_liq_price / BIN_SIZE) * BIN_SIZE

            long_bins[long_bin] += long_liq_volume
            short_bins[short_bin] += short_liq_volume

    # Merge into sorted list, focus on bins near current price (+-20%)
    lower_bound = current_price * 0.80
    upper_bound = current_price * 1.20

    all_prices = set(long_bins.keys()) | set(short_bins.keys())
    bins = []
    for price in sorted(all_prices):
        if price < lower_bound or price > upper_bound:
            continue
        bins.append({
            "price": price,
            "long_liq_volume": round(long_bins.get(price, 0), 2),
            "short_liq_volume": round(short_bins.get(price, 0), 2),
            "total": round(long_bins.get(price, 0) + short_bins.get(price, 0), 2),
        })

    return bins


@router.get("/map")
async def get_liquidation_map(session: AsyncSession = Depends(get_session)):
    """Main liquidation heatmap data — bins of estimated liquidation volumes."""
    collector = MarketCollector()
    try:
        # Fetch data in parallel-ish (sequential but fast)
        oi_data = await collector.get_open_interest()
        ls_ratio = await collector.get_long_short_ratio()
        klines = await collector.get_futures_klines(interval="1h", limit=168)
        funding = await collector.get_funding_rate()

        # Current price from DB
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price_row = result.scalar_one_or_none()
        current_price = price_row.close if price_row else 0

        if not current_price or not oi_data or not klines:
            return {
                "current_price": current_price,
                "bins": [],
                "summary": {},
                "error": "Insufficient data",
            }

        # OI is in BTC, convert to USD
        oi_btc = oi_data["open_interest"]
        oi_usd = oi_btc * current_price

        # Split into long and short OI
        long_pct = ls_ratio["long_account"] if ls_ratio else 0.5
        short_pct = ls_ratio["short_account"] if ls_ratio else 0.5
        long_oi_usd = oi_usd * long_pct
        short_oi_usd = oi_usd * short_pct

        # Build volume profile and compute bins
        volume_profile = _build_volume_profile(klines)
        bins = _compute_liquidation_bins(volume_profile, long_oi_usd, short_oi_usd, current_price)

        # Find nearest clusters
        long_clusters = [b for b in bins if b["long_liq_volume"] > 0 and b["price"] < current_price]
        short_clusters = [b for b in bins if b["short_liq_volume"] > 0 and b["price"] > current_price]

        nearest_long = max(long_clusters, key=lambda b: b["long_liq_volume"]) if long_clusters else None
        nearest_short = max(short_clusters, key=lambda b: b["short_liq_volume"]) if short_clusters else None

        summary = {
            "total_oi_usd": round(oi_usd, 2),
            "long_oi_usd": round(long_oi_usd, 2),
            "short_oi_usd": round(short_oi_usd, 2),
            "long_pct": round(long_pct * 100, 1),
            "short_pct": round(short_pct * 100, 1),
            "funding_rate": funding["funding_rate"] if funding else None,
        }
        if nearest_long:
            summary["nearest_long_cluster"] = {
                "price": nearest_long["price"],
                "volume": nearest_long["long_liq_volume"],
                "distance_pct": round((current_price - nearest_long["price"]) / current_price * 100, 2),
            }
        if nearest_short:
            summary["nearest_short_cluster"] = {
                "price": nearest_short["price"],
                "volume": nearest_short["short_liq_volume"],
                "distance_pct": round((nearest_short["price"] - current_price) / current_price * 100, 2),
            }

        return {
            "current_price": current_price,
            "bins": bins,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        await collector.close()


@router.get("/levels")
async def get_liquidation_levels(session: AsyncSession = Depends(get_session)):
    """Simple table of liquidation prices for each leverage tier at current price."""
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price_row = result.scalar_one_or_none()
    current_price = price_row.close if price_row else 0

    if not current_price:
        return {"current_price": 0, "levels": []}

    levels = []
    for tier in LEVERAGE_TIERS:
        lev = tier["leverage"]
        mmr = tier["mmr"]
        long_liq = _calc_long_liq(current_price, lev, mmr)
        short_liq = _calc_short_liq(current_price, lev, mmr)
        levels.append({
            "leverage": f"{lev}x",
            "long_liq_price": round(long_liq, 2),
            "short_liq_price": round(short_liq, 2),
            "long_distance_pct": round((current_price - long_liq) / current_price * 100, 2),
            "short_distance_pct": round((short_liq - current_price) / current_price * 100, 2),
        })

    return {
        "current_price": round(current_price, 2),
        "levels": levels,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/stats")
async def get_liquidation_stats(session: AsyncSession = Depends(get_session)):
    """OI, long/short ratios, funding rate, and top trader ratios."""
    collector = MarketCollector()
    try:
        oi_data = await collector.get_open_interest()
        ls_ratio = await collector.get_long_short_ratio()
        top_ratio = await collector.get_top_position_ratio()
        funding = await collector.get_funding_rate()

        # Current price
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price_row = result.scalar_one_or_none()
        current_price = price_row.close if price_row else 0

        oi_btc = oi_data["open_interest"] if oi_data else 0
        oi_usd = oi_btc * current_price if current_price else 0

        # Recent funding from DB
        recent = await session.execute(
            select(FundingRate).order_by(desc(FundingRate.timestamp)).limit(1)
        )
        db_funding = recent.scalar_one_or_none()

        return {
            "current_price": round(current_price, 2),
            "open_interest_btc": round(oi_btc, 4),
            "open_interest_usd": round(oi_usd, 2),
            "long_short_ratio": ls_ratio,
            "top_trader_ratio": top_ratio,
            "funding_rate": funding["funding_rate"] if funding else (db_funding.funding_rate if db_funding else None),
            "mark_price": funding["mark_price"] if funding else (db_funding.mark_price if db_funding else None),
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        await collector.close()
