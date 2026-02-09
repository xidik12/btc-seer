import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, CoinInfo, CoinPrice
from app.collectors.coin_search import CoinSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coins", tags=["coins"])

_search_service = CoinSearchService()


@router.get("/tracked")
async def get_tracked_coins(session: AsyncSession = Depends(get_session)):
    """List tracked coins with latest prices."""
    result = await session.execute(
        select(CoinInfo).where(CoinInfo.is_tracked == True)
    )
    coins = result.scalars().all()

    tracked = []
    for coin in coins:
        # Get latest price
        price_result = await session.execute(
            select(CoinPrice)
            .where(CoinPrice.coin_id == coin.coin_id)
            .order_by(desc(CoinPrice.timestamp))
            .limit(1)
        )
        price = price_result.scalar_one_or_none()

        # Get mini sparkline (last 24 price points)
        sparkline_result = await session.execute(
            select(CoinPrice)
            .where(CoinPrice.coin_id == coin.coin_id)
            .order_by(desc(CoinPrice.timestamp))
            .limit(24)
        )
        sparkline_prices = sparkline_result.scalars().all()
        sparkline = [p.price_usd for p in reversed(sparkline_prices)] if sparkline_prices else []

        tracked.append({
            "coin_id": coin.coin_id,
            "symbol": coin.symbol,
            "name": coin.name,
            "image_url": coin.image_url,
            "price_usd": price.price_usd if price else None,
            "market_cap": price.market_cap if price else None,
            "volume_24h": price.volume_24h if price else None,
            "change_1h": price.change_1h if price else None,
            "change_24h": price.change_24h if price else None,
            "change_7d": price.change_7d if price else None,
            "sparkline": sparkline,
            "timestamp": price.timestamp.isoformat() if price else None,
        })

    return {"coins": tracked}


@router.get("/{coin_id}/detail")
async def get_coin_detail(coin_id: str, session: AsyncSession = Depends(get_session)):
    """Get full detail for one coin from CoinGecko, with DB fallback."""
    try:
        detail = await _search_service.get_coin_detail(coin_id)
        if detail:
            return detail
    except Exception as e:
        logger.warning(f"CoinGecko detail fetch failed for {coin_id}: {e}")

    # Fallback: build detail from our own DB (CoinInfo + CoinPrice)
    try:
        coin_result = await session.execute(
            select(CoinInfo).where(CoinInfo.coin_id == coin_id)
        )
        coin = coin_result.scalar_one_or_none()
        if not coin:
            return {"error": f"Coin '{coin_id}' not found"}

        price_result = await session.execute(
            select(CoinPrice)
            .where(CoinPrice.coin_id == coin_id)
            .order_by(desc(CoinPrice.timestamp))
            .limit(1)
        )
        price = price_result.scalar_one_or_none()

        return {
            "id": coin.coin_id,
            "symbol": coin.symbol,
            "name": coin.name,
            "image": coin.image_url,
            "description": "",
            "market_data": {
                "price_usd": price.price_usd if price else None,
                "market_cap": price.market_cap if price else None,
                "market_cap_rank": None,
                "volume_24h": price.volume_24h if price else None,
                "change_1h": price.change_1h if price else None,
                "change_24h": price.change_24h if price else None,
                "change_7d": price.change_7d if price else None,
                "change_30d": None,
                "ath": None, "ath_date": None, "ath_change_pct": None,
                "atl": None, "atl_date": None, "atl_change_pct": None,
                "circulating_supply": None,
                "total_supply": None,
                "max_supply": None,
                "fully_diluted_valuation": None,
            },
            "categories": [],
            "genesis_date": None,
            "platforms": {},
        }
    except Exception as e:
        logger.error(f"DB fallback also failed for {coin_id}: {e}")
        return {"error": f"Coin '{coin_id}' not found"}


@router.get("/{coin_id}/chart")
async def get_coin_chart(
    coin_id: str,
    days: int = Query(7, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    """Get price chart data for a coin, with DB fallback."""
    try:
        chart = await _search_service.get_chart_data(coin_id, days)
        if chart:
            return {"coin_id": coin_id, "days": days, "prices": chart}
    except Exception as e:
        logger.warning(f"CoinGecko chart fetch failed for {coin_id}: {e}")

    # Fallback: build chart from our own price snapshots
    try:
        since = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(CoinPrice)
            .where(CoinPrice.coin_id == coin_id)
            .where(CoinPrice.timestamp >= since)
            .order_by(CoinPrice.timestamp)
        )
        prices = result.scalars().all()
        chart = [
            {"timestamp": int(p.timestamp.timestamp() * 1000), "price": p.price_usd}
            for p in prices
            if p.price_usd
        ]
        return {"coin_id": coin_id, "days": days, "prices": chart}
    except Exception as e:
        logger.error(f"Chart DB fallback failed for {coin_id}: {e}")
        return {"coin_id": coin_id, "days": days, "prices": []}


@router.get("/search")
async def search_coins(q: str = Query(..., min_length=1)):
    """Search coins by name or symbol."""
    try:
        results = await _search_service.search_by_name(q)
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Error searching coins: {e}")
        return {"error": str(e)}


class AddressSearchRequest(BaseModel):
    address: str


@router.post("/search-address")
async def search_by_address(req: AddressSearchRequest):
    """Search for a token by its contract address."""
    try:
        result = await _search_service.search_by_address(req.address)
        return result
    except Exception as e:
        logger.error(f"Error searching address: {e}")
        return {"error": str(e)}


@router.get("/report/{address:path}")
async def get_coin_report(address: str):
    """Get or generate a detailed report for a contract address."""
    try:
        report = await _search_service.generate_report(address)
        return report
    except Exception as e:
        logger.error(f"Error generating report for {address}: {e}")
        return {"error": str(e)}
