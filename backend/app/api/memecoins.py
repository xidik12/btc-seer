import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, MemeToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memecoins", tags=["memecoins"])


@router.get("/trending")
async def get_trending_memecoins(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get trending memecoins with risk scores. Includes both active and graduated tokens."""
    result = await session.execute(
        select(MemeToken)
        .where(MemeToken.status.in_(["active", "graduated"]))
        .where(MemeToken.volume_24h > 0)
        .order_by(desc(MemeToken.volume_24h))
        .limit(limit)
    )
    tokens = result.scalars().all()

    return {
        "count": len(tokens),
        "tokens": [_format_meme(t) for t in tokens],
    }


@router.get("/{address}/risk")
async def get_memecoin_risk(
    address: str,
    session: AsyncSession = Depends(get_session),
):
    """Deep risk analysis for a specific token."""
    result = await session.execute(
        select(MemeToken).where(MemeToken.address == address)
    )
    token = result.scalar_one_or_none()

    if not token:
        return {"error": "Token not found", "address": address}

    risk_breakdown = []
    score = token.rug_pull_score or 0

    if token.top_holder_pct and token.top_holder_pct > 50:
        risk_breakdown.append({"factor": "Top holder concentration >50%", "points": 30, "severity": "high"})
    if token.contract_verified is False:
        risk_breakdown.append({"factor": "Unverified contract", "points": 20, "severity": "high"})
    if token.liquidity_locked is False:
        risk_breakdown.append({"factor": "No liquidity lock", "points": 15, "severity": "medium"})
    if token.volume_acceleration and token.volume_acceleration > 10:
        risk_breakdown.append({"factor": "Volume acceleration >10x", "points": 10, "severity": "medium"})
    if token.honeypot_risk:
        risk_breakdown.append({"factor": "Honeypot risk detected", "points": 25, "severity": "critical"})

    risk_level = "low" if score < 25 else "medium" if score < 50 else "high" if score < 75 else "critical"

    return {
        "address": address,
        "token": _format_meme(token),
        "risk_score": score,
        "risk_level": risk_level,
        "risk_breakdown": risk_breakdown,
    }


@router.get("/leaderboard")
async def get_memecoin_leaderboard(
    session: AsyncSession = Depends(get_session),
):
    """Top performers and biggest losers among memecoins."""
    # Top by volume
    result = await session.execute(
        select(MemeToken)
        .where(MemeToken.status == "active")
        .where(MemeToken.volume_24h > 0)
        .order_by(desc(MemeToken.volume_24h))
        .limit(10)
    )
    top_volume = result.scalars().all()

    # Safest (lowest risk score with good volume)
    result = await session.execute(
        select(MemeToken)
        .where(MemeToken.status == "active")
        .where(MemeToken.volume_24h > 10000)
        .order_by(MemeToken.rug_pull_score)
        .limit(10)
    )
    safest = result.scalars().all()

    # Recently dead
    result = await session.execute(
        select(MemeToken)
        .where(MemeToken.status == "dead")
        .order_by(desc(MemeToken.updated_at))
        .limit(10)
    )
    dead = result.scalars().all()

    return {
        "top_volume": [_format_meme(t) for t in top_volume],
        "safest": [_format_meme(t) for t in safest],
        "recently_dead": [_format_meme(t) for t in dead],
    }


def _format_meme(t: MemeToken) -> dict:
    return {
        "id": t.id,
        "address": t.address,
        "chain": t.chain,
        "symbol": t.symbol,
        "name": t.name,
        "price_usd": t.price_usd,
        "volume_24h": t.volume_24h,
        "liquidity": t.liquidity,
        "volume_acceleration": t.volume_acceleration,
        "rug_pull_score": t.rug_pull_score,
        "top_holder_pct": t.top_holder_pct,
        "liquidity_locked": t.liquidity_locked,
        "contract_verified": t.contract_verified,
        "honeypot_risk": t.honeypot_risk,
        "status": t.status,
        "first_seen": t.first_seen.isoformat() if t.first_seen else None,
    }
