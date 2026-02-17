import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, NewListing, DexToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("/recent")
async def get_recent_listings(
    hours: int = Query(168, ge=1, le=720),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get recent new exchange listings."""
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await session.execute(
        select(NewListing)
        .where(NewListing.timestamp >= since)
        .order_by(desc(NewListing.timestamp))
        .limit(limit)
    )
    listings = result.scalars().all()

    return {
        "count": len(listings),
        "listings": [
            {
                "id": l.id,
                "exchange": l.exchange,
                "symbol": l.symbol,
                "listing_type": l.listing_type,
                "announcement_url": l.announcement_url,
                "price_at_listing": l.price_at_listing,
                "price_1h_after": l.price_1h_after,
                "price_24h_after": l.price_24h_after,
                "change_pct_1h": l.change_pct_1h,
                "change_pct_24h": l.change_pct_24h,
                "was_on_dex_first": l.was_on_dex_first,
                "timestamp": l.timestamp.isoformat(),
            }
            for l in listings
        ],
    }


@router.get("/dex-trending")
async def get_dex_trending(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get trending DEX tokens."""
    result = await session.execute(
        select(DexToken)
        .where(DexToken.volume_24h > 10000)
        .order_by(desc(DexToken.boosts), desc(DexToken.volume_24h))
        .limit(limit)
    )
    tokens = result.scalars().all()

    return {
        "count": len(tokens),
        "tokens": [
            {
                "id": t.id,
                "address": t.address,
                "chain": t.chain,
                "symbol": t.symbol,
                "name": t.name,
                "price_usd": t.price_usd,
                "volume_24h": t.volume_24h,
                "liquidity": t.liquidity,
                "holder_count": t.holder_count,
                "is_on_cex": t.is_on_cex,
                "boosts": t.boosts,
                "first_seen": t.first_seen.isoformat() if t.first_seen else None,
            }
            for t in tokens
        ],
    }


@router.get("/dex-to-cex")
async def get_dex_to_cex(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get tokens that migrated from DEX to CEX."""
    result = await session.execute(
        select(DexToken)
        .where(DexToken.is_on_cex == True)
        .order_by(desc(DexToken.updated_at))
        .limit(limit)
    )
    tokens = result.scalars().all()

    return {
        "count": len(tokens),
        "tokens": [
            {
                "id": t.id,
                "address": t.address,
                "chain": t.chain,
                "symbol": t.symbol,
                "name": t.name,
                "price_usd": t.price_usd,
                "volume_24h": t.volume_24h,
                "liquidity": t.liquidity,
                "first_seen": t.first_seen.isoformat() if t.first_seen else None,
            }
            for t in tokens
        ],
    }
