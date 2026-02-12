from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, WhaleTransaction

router = APIRouter(prefix="/api/whales", tags=["whales"])


@router.get("/recent")
async def get_recent_whales(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
    direction: str = Query(None),
    min_btc: float = Query(None, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Get recent whale transactions with optional filters."""
    since = datetime.utcnow() - timedelta(hours=hours)

    query = select(WhaleTransaction).where(WhaleTransaction.timestamp >= since)

    if direction:
        query = query.where(WhaleTransaction.direction == direction)
    if min_btc is not None:
        query = query.where(WhaleTransaction.amount_btc >= min_btc)

    query = query.order_by(desc(WhaleTransaction.timestamp)).limit(limit)

    result = await session.execute(query)
    txs = result.scalars().all()

    return {
        "count": len(txs),
        "transactions": [
            {
                "id": tx.id,
                "tx_hash": tx.tx_hash,
                "timestamp": tx.timestamp.isoformat(),
                "amount_btc": tx.amount_btc,
                "amount_usd": tx.amount_usd,
                "direction": tx.direction,
                "from_entity": tx.from_entity,
                "to_entity": tx.to_entity,
                "severity": tx.severity,
                "btc_price_at_tx": tx.btc_price_at_tx,
                "change_pct_1h": tx.change_pct_1h,
                "change_pct_4h": tx.change_pct_4h,
                "change_pct_24h": tx.change_pct_24h,
                "direction_was_predictive": tx.direction_was_predictive,
            }
            for tx in txs
        ],
    }


@router.get("/stats")
async def get_whale_stats(
    session: AsyncSession = Depends(get_session),
):
    """Get whale transaction statistics for 24h and 7d."""
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    # 24h stats
    result_24h = await session.execute(
        select(WhaleTransaction).where(WhaleTransaction.timestamp >= since_24h)
    )
    txs_24h = result_24h.scalars().all()

    # 7d stats
    result_7d = await session.execute(
        select(WhaleTransaction).where(WhaleTransaction.timestamp >= since_7d)
    )
    txs_7d = result_7d.scalars().all()

    def compute_stats(txs):
        if not txs:
            return {
                "count": 0, "total_btc": 0, "avg_btc": 0,
                "exchange_in": 0, "exchange_out": 0,
                "whale_to_whale": 0, "unknown": 0,
                "net_flow_btc": 0, "top_exchanges": {},
            }

        directions = {"exchange_in": 0, "exchange_out": 0, "whale_to_whale": 0, "unknown": 0}
        exchange_counts = {}
        total_btc = 0
        net_flow = 0  # positive = net inflow (bearish), negative = net outflow (bullish)

        for tx in txs:
            total_btc += tx.amount_btc
            d = tx.direction or "unknown"
            directions[d] = directions.get(d, 0) + 1

            if d == "exchange_in":
                net_flow += tx.amount_btc
            elif d == "exchange_out":
                net_flow -= tx.amount_btc

            for entity in [tx.from_entity, tx.to_entity]:
                if entity and entity != "unknown":
                    exchange_counts[entity] = exchange_counts.get(entity, 0) + 1

        return {
            "count": len(txs),
            "total_btc": round(total_btc, 2),
            "avg_btc": round(total_btc / len(txs), 2) if txs else 0,
            "exchange_in": directions["exchange_in"],
            "exchange_out": directions["exchange_out"],
            "whale_to_whale": directions["whale_to_whale"],
            "unknown": directions["unknown"],
            "net_flow_btc": round(net_flow, 2),
            "top_exchanges": dict(sorted(exchange_counts.items(), key=lambda x: -x[1])[:5]),
        }

    # Predictive accuracy
    evaluated = await session.execute(
        select(WhaleTransaction).where(
            WhaleTransaction.evaluated_1h == True,
            WhaleTransaction.direction_was_predictive.isnot(None),
        )
    )
    eval_txs = evaluated.scalars().all()
    predictive_count = sum(1 for tx in eval_txs if tx.direction_was_predictive)
    accuracy = round(predictive_count / len(eval_txs) * 100, 1) if eval_txs else None

    return {
        "stats_24h": compute_stats(txs_24h),
        "stats_7d": compute_stats(txs_7d),
        "predictive_accuracy": accuracy,
        "total_evaluated": len(eval_txs),
    }


@router.get("/flow-history")
async def get_whale_flow_history(
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_session),
):
    """Get daily aggregated whale flow data for charting."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(WhaleTransaction).where(WhaleTransaction.timestamp >= since)
        .order_by(WhaleTransaction.timestamp)
    )
    txs = result.scalars().all()

    # Group by date
    daily = {}
    for tx in txs:
        date_key = tx.timestamp.strftime("%Y-%m-%d")
        if date_key not in daily:
            daily[date_key] = {
                "date": date_key, "count": 0, "total_btc": 0,
                "exchange_in_btc": 0, "exchange_out_btc": 0, "net_flow_btc": 0,
            }
        day = daily[date_key]
        day["count"] += 1
        day["total_btc"] += tx.amount_btc
        if tx.direction == "exchange_in":
            day["exchange_in_btc"] += tx.amount_btc
            day["net_flow_btc"] += tx.amount_btc
        elif tx.direction == "exchange_out":
            day["exchange_out_btc"] += tx.amount_btc
            day["net_flow_btc"] -= tx.amount_btc

    # Round values
    for day in daily.values():
        day["total_btc"] = round(day["total_btc"], 2)
        day["exchange_in_btc"] = round(day["exchange_in_btc"], 2)
        day["exchange_out_btc"] = round(day["exchange_out_btc"], 2)
        day["net_flow_btc"] = round(day["net_flow_btc"], 2)

    return {
        "days": days,
        "history": sorted(daily.values(), key=lambda x: x["date"]),
    }
