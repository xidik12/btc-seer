"""Smart Money Feed API — aggregated whale, institutional, arbitrage events."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, desc, and_

from app.database import (
    async_session, WhaleTransaction, InstitutionalHolding,
    ArbitrageOpportunity, BotUser,
)
from app.api.admin import _verify_telegram_init_data
from app.bot.subscription import is_premium
from app.dependencies import standard_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/smart-money", tags=["smart-money"], dependencies=[Depends(standard_rate_limit)])


def _whale_impact(tx) -> str:
    """Assess whale transaction impact."""
    if tx.direction == "exchange_in":
        return "bearish"
    elif tx.direction == "exchange_out":
        return "bullish"
    return "neutral"


def _whale_event(tx) -> dict:
    impact = _whale_impact(tx)
    direction_label = {
        "exchange_in": "Exchange Inflow",
        "exchange_out": "Exchange Outflow",
        "whale_to_whale": "Whale Transfer",
    }.get(tx.direction, "Unknown Transfer")

    return {
        "id": f"whale_{tx.id}",
        "type": "whale",
        "timestamp": tx.timestamp.isoformat() if tx.timestamp else None,
        "title": f"{direction_label}: {tx.amount_btc:,.1f} BTC",
        "description": f"From {tx.from_entity} to {tx.to_entity}",
        "amount_usd": tx.amount_usd,
        "amount_btc": tx.amount_btc,
        "impact": impact,
        "severity": tx.severity,
        "entity_name": tx.entity_name or tx.from_entity,
    }


def _institutional_event(holding, prev_btc: float | None) -> dict | None:
    if prev_btc is None:
        return None
    delta = holding.total_btc - prev_btc
    if abs(delta) < 1:
        return None
    impact = "bullish" if delta > 0 else "bearish"
    action = "accumulated" if delta > 0 else "reduced"
    return {
        "id": f"inst_{holding.id}",
        "type": "institutional",
        "timestamp": holding.snapshot_date.isoformat() if holding.snapshot_date else None,
        "title": f"{holding.company_name} {action} {abs(delta):,.0f} BTC",
        "description": f"Total: {holding.total_btc:,.0f} BTC | {holding.ticker or ''}",
        "amount_usd": abs(delta) * (holding.current_value_usd / holding.total_btc) if holding.total_btc else 0,
        "amount_btc": abs(delta),
        "impact": impact,
        "severity": min(10, max(1, int(abs(delta) / 100))),
        "entity_name": holding.company_name,
    }


def _arb_event(arb) -> dict:
    return {
        "id": f"arb_{arb.id}",
        "type": "arbitrage",
        "timestamp": arb.timestamp.isoformat() if arb.timestamp else None,
        "title": f"{arb.coin_id.upper()[:6]} Arb: {arb.net_profit_pct:.2f}% profit",
        "description": f"Buy {arb.buy_exchange} @ ${arb.buy_price:,.2f} → Sell {arb.sell_exchange} @ ${arb.sell_price:,.2f}",
        "amount_usd": None,
        "amount_btc": None,
        "impact": "neutral",
        "severity": min(10, max(1, int(arb.net_profit_pct * 5))),
        "entity_name": None,
    }


@router.get("/feed")
async def get_smart_money_feed(
    request: Request,
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(50, ge=1, le=200),
    event_type: str = "all",
    direction: str = "all",
):
    """Unified smart money event feed."""
    # Check premium for full feed
    is_user_premium = False
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if init_data:
        try:
            user_data = _verify_telegram_init_data(init_data, max_age=86400)
            telegram_id = user_data.get("id")
            if telegram_id:
                async with async_session() as session:
                    result = await session.execute(
                        select(BotUser).where(BotUser.telegram_id == telegram_id)
                    )
                    user = result.scalar_one_or_none()
                    is_user_premium = is_premium(user) if user else False
        except Exception:
            pass

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    events = []

    async with async_session() as session:
        # Whale transactions
        if event_type in ("all", "whale"):
            query = (
                select(WhaleTransaction)
                .where(WhaleTransaction.timestamp >= cutoff)
                .order_by(desc(WhaleTransaction.timestamp))
                .limit(100)
            )
            result = await session.execute(query)
            whales = result.scalars().all()
            for tx in whales:
                evt = _whale_event(tx)
                if direction == "all" or evt["impact"] == direction:
                    events.append(evt)

        # Institutional holding changes
        if event_type in ("all", "institutional"):
            result = await session.execute(
                select(InstitutionalHolding)
                .where(InstitutionalHolding.snapshot_date >= cutoff)
                .order_by(desc(InstitutionalHolding.snapshot_date))
                .limit(100)
            )
            holdings = result.scalars().all()

            # Group by company to detect deltas
            company_holdings = {}
            for h in holdings:
                key = h.company_name
                if key not in company_holdings:
                    company_holdings[key] = []
                company_holdings[key].append(h)

            for company, snapshots in company_holdings.items():
                if len(snapshots) >= 2:
                    latest = snapshots[0]
                    previous = snapshots[1]
                    evt = _institutional_event(latest, previous.total_btc)
                    if evt and (direction == "all" or evt["impact"] == direction):
                        events.append(evt)

        # Arbitrage opportunities
        if event_type in ("all", "arbitrage"):
            result = await session.execute(
                select(ArbitrageOpportunity)
                .where(
                    ArbitrageOpportunity.timestamp >= cutoff,
                    ArbitrageOpportunity.is_actionable == True,
                )
                .order_by(desc(ArbitrageOpportunity.net_profit_pct))
                .limit(20)
            )
            arbs = result.scalars().all()
            for arb in arbs:
                evt = _arb_event(arb)
                if direction == "all" or evt["impact"] == direction:
                    events.append(evt)

    # Sort all events by timestamp descending
    events.sort(key=lambda e: e["timestamp"] or "", reverse=True)

    # Free users: limit to 5 events
    if not is_user_premium:
        events = events[:5]
    else:
        events = events[:limit]

    return {"events": events, "is_premium": is_user_premium}


@router.get("/score")
async def get_smart_money_score():
    """24h weighted smart money sentiment score (-100 to +100)."""
    cutoff = datetime.utcnow() - timedelta(hours=24)

    whale_bullish = 0
    whale_bearish = 0
    inst_bullish = 0
    inst_bearish = 0

    async with async_session() as session:
        # Whale score
        result = await session.execute(
            select(WhaleTransaction)
            .where(WhaleTransaction.timestamp >= cutoff)
        )
        whales = result.scalars().all()

        for tx in whales:
            weight = tx.amount_usd or (tx.amount_btc * 95000)  # fallback price estimate
            if tx.direction == "exchange_out":
                whale_bullish += weight
            elif tx.direction == "exchange_in":
                whale_bearish += weight

        # Institutional score (compare latest vs previous snapshot)
        result = await session.execute(
            select(InstitutionalHolding)
            .where(InstitutionalHolding.snapshot_date >= cutoff)
            .order_by(desc(InstitutionalHolding.snapshot_date))
        )
        holdings = result.scalars().all()

        company_latest = {}
        for h in holdings:
            if h.company_name not in company_latest:
                company_latest[h.company_name] = h

        for h in company_latest.values():
            if h.change_btc and h.change_btc > 0:
                inst_bullish += abs(h.change_btc)
            elif h.change_btc and h.change_btc < 0:
                inst_bearish += abs(h.change_btc)

    whale_total = whale_bullish + whale_bearish
    whale_score = ((whale_bullish - whale_bearish) / whale_total * 100) if whale_total else 0

    inst_total = inst_bullish + inst_bearish
    inst_score = ((inst_bullish - inst_bearish) / inst_total * 100) if inst_total else 0

    # Composite: whales 60%, institutional 40%
    composite = whale_score * 0.6 + inst_score * 0.4

    # Label
    if composite > 50:
        label = "Strong Bullish"
    elif composite > 20:
        label = "Bullish"
    elif composite > -20:
        label = "Neutral"
    elif composite > -50:
        label = "Bearish"
    else:
        label = "Strong Bearish"

    return {
        "score": round(composite, 1),
        "label": label,
        "whale_score": round(whale_score, 1),
        "institutional_score": round(inst_score, 1),
        "whale_bullish_usd": whale_bullish,
        "whale_bearish_usd": whale_bearish,
        "institutional_buy_btc": inst_bullish,
        "institutional_sell_btc": inst_bearish,
    }
