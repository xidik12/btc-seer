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
