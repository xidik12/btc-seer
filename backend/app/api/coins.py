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
async def get_coin_detail(coin_id: str):
    """Get full detail for one coin from CoinGecko."""
    try:
        detail = await _search_service.get_coin_detail(coin_id)
        if not detail:
            return {"error": f"Coin '{coin_id}' not found"}
        return detail
    except Exception as e:
        logger.error(f"Error fetching coin detail for {coin_id}: {e}")
        return {"error": str(e)}
    finally:
        await _search_service.close()


@router.get("/{coin_id}/chart")
async def get_coin_chart(
    coin_id: str,
    days: int = Query(7, ge=1, le=365),
):
    """Get price chart data for a coin."""
    try:
        chart = await _search_service.get_chart_data(coin_id, days)
        return {"coin_id": coin_id, "days": days, "prices": chart}
    except Exception as e:
        logger.error(f"Error fetching chart for {coin_id}: {e}")
        return {"error": str(e)}
    finally:
        await _search_service.close()


@router.get("/search")
async def search_coins(q: str = Query(..., min_length=1)):
    """Search coins by name or symbol."""
    try:
        results = await _search_service.search_by_name(q)
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Error searching coins: {e}")
        return {"error": str(e)}
    finally:
        await _search_service.close()


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
    finally:
        await _search_service.close()


@router.get("/report/{address:path}")
async def get_coin_report(address: str):
    """Get or generate a detailed report for a contract address."""
    try:
        report = await _search_service.generate_report(address)
        return report
    except Exception as e:
        logger.error(f"Error generating report for {address}: {e}")
        return {"error": str(e)}
    finally:
        await _search_service.close()
