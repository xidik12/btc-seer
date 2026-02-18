"""
Arbitrage API — exposes current and historical cross-exchange arbitrage
opportunities for tracked coins.

Routes:
    GET /api/arbitrage/current    — all opportunities from the last 5 minutes
    GET /api/arbitrage/history    — historical data with optional filters
    GET /api/arbitrage/{coin_id}  — per-coin prices across exchanges + best opp
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, ExchangeTicker, ArbitrageOpportunity
from app.collectors.arbitrage import EXCHANGE_FEES, DEFAULT_FEE_PCT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/arbitrage", tags=["arbitrage"])


# ---------------------------------------------------------------------------
# GET /api/arbitrage/current
# ---------------------------------------------------------------------------
@router.get("/current")
async def get_current_opportunities(
    session: AsyncSession = Depends(get_session),
):
    """Return all arbitrage opportunities detected in the last 5 minutes,
    sorted by net_profit_pct descending."""
    cutoff = datetime.utcnow() - timedelta(minutes=5)

    result = await session.execute(
        select(ArbitrageOpportunity)
        .where(ArbitrageOpportunity.timestamp >= cutoff)
        .order_by(desc(ArbitrageOpportunity.net_profit_pct))
    )
    rows = result.scalars().all()

    opportunities = []
    for row in rows:
        opportunities.append({
            "id": row.id,
            "coin_id": row.coin_id,
            "buy_exchange": row.buy_exchange,
            "buy_price": row.buy_price,
            "sell_exchange": row.sell_exchange,
            "sell_price": row.sell_price,
            "spread_pct": row.spread_pct,
            "net_profit_pct": row.net_profit_pct,
            "estimated_fees_pct": row.estimated_fees_pct,
            "is_actionable": row.is_actionable,
            "exchange_prices": row.exchange_prices,
            "timestamp": row.timestamp.isoformat(),
        })

    return {
        "count": len(opportunities),
        "actionable": sum(1 for o in opportunities if o["is_actionable"]),
        "opportunities": opportunities,
    }


# ---------------------------------------------------------------------------
# GET /api/arbitrage/history
# ---------------------------------------------------------------------------
@router.get("/history")
async def get_arbitrage_history(
    coin_id: str | None = Query(None, description="Filter by coin_id (e.g. 'bitcoin')"),
    hours: int = Query(24, ge=1, le=168, description="Lookback window in hours (1-168)"),
    actionable_only: bool = Query(False, description="Only return actionable opportunities"),
    limit: int = Query(200, ge=1, le=1000, description="Max rows to return"),
    session: AsyncSession = Depends(get_session),
):
    """Return historical arbitrage opportunities with optional filters."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    query = (
        select(ArbitrageOpportunity)
        .where(ArbitrageOpportunity.timestamp >= cutoff)
    )

    if coin_id:
        query = query.where(ArbitrageOpportunity.coin_id == coin_id)

    if actionable_only:
        query = query.where(ArbitrageOpportunity.is_actionable == True)  # noqa: E712

    query = query.order_by(desc(ArbitrageOpportunity.timestamp)).limit(limit)

    result = await session.execute(query)
    rows = result.scalars().all()

    history = []
    for row in rows:
        history.append({
            "id": row.id,
            "coin_id": row.coin_id,
            "buy_exchange": row.buy_exchange,
            "buy_price": row.buy_price,
            "sell_exchange": row.sell_exchange,
            "sell_price": row.sell_price,
            "spread_pct": row.spread_pct,
            "net_profit_pct": row.net_profit_pct,
            "estimated_fees_pct": row.estimated_fees_pct,
            "is_actionable": row.is_actionable,
            "exchange_prices": row.exchange_prices,
            "timestamp": row.timestamp.isoformat(),
        })

    return {
        "count": len(history),
        "coin_id": coin_id,
        "hours": hours,
        "history": history,
    }


# ---------------------------------------------------------------------------
# GET /api/arbitrage/calculate
# ---------------------------------------------------------------------------
@router.get("/calculate")
async def calculate_arbitrage_profit(
    coin_id: str = Query(..., description="Coin ID (e.g. 'bitcoin')"),
    amount_usd: float = Query(1000, ge=10, le=1_000_000, description="Trade amount in USD"),
    session: AsyncSession = Depends(get_session),
):
    """Calculate detailed profit breakdown for each exchange pair including fees."""
    cutoff = datetime.utcnow() - timedelta(minutes=5)

    result = await session.execute(
        select(ArbitrageOpportunity)
        .where(
            ArbitrageOpportunity.coin_id == coin_id,
            ArbitrageOpportunity.timestamp >= cutoff,
        )
        .order_by(desc(ArbitrageOpportunity.net_profit_pct))
        .limit(1)
    )
    opp = result.scalar_one_or_none()

    if not opp:
        return {"coin_id": coin_id, "amount_usd": amount_usd, "opportunities": []}

    # Calculate for the best opportunity
    buy_fee_pct = EXCHANGE_FEES.get(opp.buy_exchange, DEFAULT_FEE_PCT)
    sell_fee_pct = EXCHANGE_FEES.get(opp.sell_exchange, DEFAULT_FEE_PCT)

    # Buy side
    buy_fee_usd = amount_usd * buy_fee_pct / 100
    coins_bought = (amount_usd - buy_fee_usd) / opp.buy_price if opp.buy_price > 0 else 0

    # Sell side
    gross_sell = coins_bought * opp.sell_price
    sell_fee_usd = gross_sell * sell_fee_pct / 100
    net_sell = gross_sell - sell_fee_usd

    net_profit_usd = net_sell - amount_usd
    net_profit_pct = (net_profit_usd / amount_usd * 100) if amount_usd > 0 else 0

    return {
        "coin_id": coin_id,
        "amount_usd": amount_usd,
        "best_opportunity": {
            "buy_exchange": opp.buy_exchange,
            "sell_exchange": opp.sell_exchange,
            "buy_price": opp.buy_price,
            "sell_price": opp.sell_price,
            "buy_fee_pct": buy_fee_pct,
            "sell_fee_pct": sell_fee_pct,
            "buy_fee_usd": round(buy_fee_usd, 2),
            "sell_fee_usd": round(sell_fee_usd, 2),
            "coins_bought": round(coins_bought, 8),
            "gross_sell_usd": round(gross_sell, 2),
            "net_profit_usd": round(net_profit_usd, 2),
            "net_profit_pct": round(net_profit_pct, 4),
            "spread_pct": opp.spread_pct,
            "is_profitable": net_profit_usd > 0,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/arbitrage/analytics
# ---------------------------------------------------------------------------
@router.get("/analytics")
async def get_arbitrage_analytics(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
):
    """Analytics: average spread by coin, best exchange pairs, opportunity frequency."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(ArbitrageOpportunity)
        .where(ArbitrageOpportunity.timestamp >= cutoff)
        .order_by(desc(ArbitrageOpportunity.timestamp))
        .limit(2000)
    )
    rows = result.scalars().all()

    if not rows:
        return {"hours": hours, "coins": [], "exchange_pairs": [], "total_opportunities": 0}

    # Aggregate by coin
    coin_stats: dict[str, dict] = {}
    pair_stats: dict[str, dict] = {}

    for row in rows:
        # Per-coin stats
        cs = coin_stats.setdefault(row.coin_id, {
            "coin_id": row.coin_id,
            "count": 0,
            "actionable_count": 0,
            "total_spread": 0,
            "best_spread": 0,
        })
        cs["count"] += 1
        if row.is_actionable:
            cs["actionable_count"] += 1
        cs["total_spread"] += row.spread_pct or 0
        cs["best_spread"] = max(cs["best_spread"], row.net_profit_pct or 0)

        # Per exchange-pair stats
        pair_key = f"{row.buy_exchange}->{row.sell_exchange}"
        ps = pair_stats.setdefault(pair_key, {
            "pair": pair_key,
            "buy_exchange": row.buy_exchange,
            "sell_exchange": row.sell_exchange,
            "count": 0,
            "actionable_count": 0,
            "avg_profit": 0,
            "total_profit": 0,
        })
        ps["count"] += 1
        if row.is_actionable:
            ps["actionable_count"] += 1
        ps["total_profit"] += row.net_profit_pct or 0

    # Compute averages
    coins = []
    for cs in coin_stats.values():
        cs["avg_spread"] = round(cs["total_spread"] / cs["count"], 4) if cs["count"] else 0
        cs["best_spread"] = round(cs["best_spread"], 4)
        del cs["total_spread"]
        coins.append(cs)
    coins.sort(key=lambda x: x["best_spread"], reverse=True)

    pairs = []
    for ps in pair_stats.values():
        ps["avg_profit"] = round(ps["total_profit"] / ps["count"], 4) if ps["count"] else 0
        del ps["total_profit"]
        pairs.append(ps)
    pairs.sort(key=lambda x: x["avg_profit"], reverse=True)

    return {
        "hours": hours,
        "total_opportunities": len(rows),
        "total_actionable": sum(1 for r in rows if r.is_actionable),
        "coins": coins[:20],
        "exchange_pairs": pairs[:20],
        "exchange_fees": EXCHANGE_FEES,
    }


# ---------------------------------------------------------------------------
# GET /api/arbitrage/{coin_id}
# ---------------------------------------------------------------------------
@router.get("/{coin_id}")
async def get_coin_arbitrage(
    coin_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Return current exchange prices and the best arbitrage opportunity for
    a single coin.

    Prices come from ExchangeTicker rows in the last 5 minutes.
    The best opportunity comes from ArbitrageOpportunity in the same window.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=5)

    # --- Exchange prices (most recent ticker per exchange) ---
    ticker_result = await session.execute(
        select(ExchangeTicker)
        .where(
            ExchangeTicker.coin_id == coin_id,
            ExchangeTicker.timestamp >= cutoff,
        )
        .order_by(desc(ExchangeTicker.timestamp))
    )
    ticker_rows = ticker_result.scalars().all()

    # Deduplicate: keep only the latest row per exchange
    seen_exchanges: set[str] = set()
    exchange_prices: list[dict] = []
    for row in ticker_rows:
        if row.exchange in seen_exchanges:
            continue
        seen_exchanges.add(row.exchange)
        exchange_prices.append({
            "exchange": row.exchange,
            "bid": row.bid,
            "ask": row.ask,
            "last": row.last,
            "volume_24h": row.volume_24h,
            "timestamp": row.timestamp.isoformat(),
        })

    # --- Best opportunity ---
    opp_result = await session.execute(
        select(ArbitrageOpportunity)
        .where(
            ArbitrageOpportunity.coin_id == coin_id,
            ArbitrageOpportunity.timestamp >= cutoff,
        )
        .order_by(desc(ArbitrageOpportunity.net_profit_pct))
        .limit(1)
    )
    best_opp = opp_result.scalar_one_or_none()

    best_opportunity = None
    if best_opp:
        best_opportunity = {
            "id": best_opp.id,
            "buy_exchange": best_opp.buy_exchange,
            "buy_price": best_opp.buy_price,
            "sell_exchange": best_opp.sell_exchange,
            "sell_price": best_opp.sell_price,
            "spread_pct": best_opp.spread_pct,
            "net_profit_pct": best_opp.net_profit_pct,
            "estimated_fees_pct": best_opp.estimated_fees_pct,
            "is_actionable": best_opp.is_actionable,
            "timestamp": best_opp.timestamp.isoformat(),
        }

    return {
        "coin_id": coin_id,
        "exchanges_count": len(exchange_prices),
        "exchange_prices": exchange_prices,
        "best_opportunity": best_opportunity,
    }
