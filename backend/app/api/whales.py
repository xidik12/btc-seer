import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func, and_, case, literal_column, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, WhaleTransaction, AddressLabel
from app.cache import cache_get, cache_set

router = APIRouter(prefix="/api/whales", tags=["whales"])


@router.get("/recent")
async def get_recent_whales(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
    direction: str = Query(None),
    entity_type: str = Query(None),
    min_btc: float = Query(None, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Get recent whale transactions with optional filters."""
    since = datetime.utcnow() - timedelta(hours=hours)

    query = select(WhaleTransaction).where(WhaleTransaction.timestamp >= since)

    if direction:
        query = query.where(WhaleTransaction.direction == direction)
    if entity_type:
        query = query.where(WhaleTransaction.entity_type == entity_type)
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
                "entity_name": tx.entity_name,
                "entity_type": tx.entity_type,
                "entity_wallet": tx.entity_wallet,
                "severity": tx.severity,
                "btc_price_at_tx": tx.btc_price_at_tx,
                "change_pct_1h": tx.change_pct_1h,
                "change_pct_4h": tx.change_pct_4h,
                "change_pct_24h": tx.change_pct_24h,
                "direction_was_predictive": tx.direction_was_predictive,
                "from_address": tx.from_address,
                "to_address": tx.to_address,
                "chain": tx.chain,
            }
            for tx in txs
        ],
    }


@router.get("/entities")
async def get_entities(
    session: AsyncSession = Depends(get_session),
):
    """Get list of known entities with latest whale activity."""
    from app.collectors.known_entities import get_entities_summary

    entities = get_entities_summary()

    # Enrich with latest activity from DB — SQL aggregation instead of loading all rows
    now = datetime.utcnow()
    since_7d = now - timedelta(days=7)

    # Aggregate tx count and total BTC per entity in SQL
    agg_result = await session.execute(
        select(
            WhaleTransaction.entity_name,
            func.count().label("tx_count_7d"),
            func.sum(WhaleTransaction.amount_btc).label("total_btc_7d"),
            func.max(WhaleTransaction.timestamp).label("last_seen"),
        )
        .where(
            WhaleTransaction.timestamp >= since_7d,
            WhaleTransaction.entity_name.isnot(None),
        )
        .group_by(WhaleTransaction.entity_name)
    )
    agg_rows = agg_result.all()

    # Get last direction per entity (latest tx) using window function
    last_dir_sql = text("""
        SELECT entity_name, direction FROM (
            SELECT entity_name, direction,
                   ROW_NUMBER() OVER (PARTITION BY entity_name ORDER BY timestamp DESC) AS rn
            FROM whale_transactions
            WHERE timestamp >= :since AND entity_name IS NOT NULL
        ) sub WHERE rn = 1
    """)
    dir_result = await session.execute(last_dir_sql, {"since": since_7d})
    last_directions = {r.entity_name: r.direction for r in dir_result}

    entity_activity: dict[str, dict] = {}
    for row in agg_rows:
        entity_activity[row.entity_name] = {
            "tx_count_7d": row.tx_count_7d,
            "total_btc_7d": float(row.total_btc_7d or 0),
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            "last_direction": last_directions.get(row.entity_name),
        }

    # Merge
    for entity in entities:
        activity = entity_activity.get(entity["name"], {})
        entity["tx_count_7d"] = activity.get("tx_count_7d", 0)
        entity["total_btc_7d"] = round(activity.get("total_btc_7d", 0), 2)
        entity["last_seen"] = activity.get("last_seen")
        entity["last_direction"] = activity.get("last_direction")

    return {
        "entities": entities,
        "total": len(entities),
    }


@router.get("/stats")
async def get_whale_stats(
    session: AsyncSession = Depends(get_session),
):
    """Get whale transaction statistics for 24h and 7d (SQL aggregation)."""
    cached = await cache_get("whales:stats")
    if cached is not None:
        return cached

    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    async def _compute_stats_sql(since: datetime) -> dict:
        """Compute whale stats using SQL aggregation instead of loading all rows."""
        # Direction counts + totals in a single query
        dir_result = await session.execute(
            select(
                func.coalesce(WhaleTransaction.direction, "unknown").label("dir"),
                func.count().label("cnt"),
                func.sum(WhaleTransaction.amount_btc).label("total_btc"),
            )
            .where(WhaleTransaction.timestamp >= since)
            .group_by(func.coalesce(WhaleTransaction.direction, "unknown"))
        )
        dir_rows = dir_result.all()

        if not dir_rows:
            return {
                "count": 0, "total_btc": 0, "avg_btc": 0,
                "exchange_in": 0, "exchange_out": 0,
                "whale_to_whale": 0, "unknown": 0,
                "net_flow_btc": 0, "top_exchanges": {},
                "most_active_entity": None,
            }

        directions = {"exchange_in": 0, "exchange_out": 0, "whale_to_whale": 0, "unknown": 0}
        total_count = 0
        total_btc = 0.0
        net_flow = 0.0

        for row in dir_rows:
            d = row.dir
            directions[d] = directions.get(d, 0) + row.cnt
            total_count += row.cnt
            total_btc += row.total_btc or 0
            if d == "exchange_in":
                net_flow += row.total_btc or 0
            elif d == "exchange_out":
                net_flow -= row.total_btc or 0

        # Most active entity (single query)
        entity_result = await session.execute(
            select(
                WhaleTransaction.entity_name,
                func.count().label("cnt"),
            )
            .where(WhaleTransaction.timestamp >= since)
            .where(WhaleTransaction.entity_name.isnot(None))
            .group_by(WhaleTransaction.entity_name)
            .order_by(desc("cnt"))
            .limit(1)
        )
        entity_row = entity_result.first()
        most_active = entity_row.entity_name if entity_row else None

        # Top exchanges (from_entity and to_entity combined, single query)
        top_exch_sql = text("""
            SELECT entity, SUM(cnt) as total FROM (
                SELECT from_entity as entity, COUNT(*) as cnt
                FROM whale_transactions
                WHERE timestamp >= :since AND from_entity IS NOT NULL AND from_entity != 'unknown'
                GROUP BY from_entity
                UNION ALL
                SELECT to_entity as entity, COUNT(*) as cnt
                FROM whale_transactions
                WHERE timestamp >= :since AND to_entity IS NOT NULL AND to_entity != 'unknown'
                GROUP BY to_entity
            ) sub
            GROUP BY entity ORDER BY total DESC LIMIT 5
        """)
        exch_result = await session.execute(top_exch_sql, {"since": since})
        top_exchanges = {row.entity: row.total for row in exch_result}

        return {
            "count": total_count,
            "total_btc": round(total_btc, 2),
            "avg_btc": round(total_btc / total_count, 2) if total_count else 0,
            "exchange_in": directions["exchange_in"],
            "exchange_out": directions["exchange_out"],
            "whale_to_whale": directions["whale_to_whale"],
            "unknown": directions["unknown"],
            "net_flow_btc": round(net_flow, 2),
            "top_exchanges": top_exchanges,
            "most_active_entity": most_active,
        }

    stats_24h = await _compute_stats_sql(since_24h)
    stats_7d = await _compute_stats_sql(since_7d)

    # Predictive accuracy — SQL aggregation instead of loading all rows
    accuracy_result = await session.execute(
        select(
            func.count().label("total"),
            func.count().filter(WhaleTransaction.direction_was_predictive == True).label("predictive"),
        )
        .where(
            WhaleTransaction.evaluated_1h == True,
            WhaleTransaction.direction_was_predictive.isnot(None),
        )
    )
    acc_row = accuracy_result.first()
    total_evaluated = acc_row.total if acc_row else 0
    predictive_count = acc_row.predictive if acc_row else 0
    accuracy = round(predictive_count / total_evaluated * 100, 1) if total_evaluated else None

    response = {
        "stats_24h": stats_24h,
        "stats_7d": stats_7d,
        "predictive_accuracy": accuracy,
        "total_evaluated": total_evaluated,
    }
    await cache_set("whales:stats", response, 60)
    return response


@router.get("/flow-history")
async def get_whale_flow_history(
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_session),
):
    """Get daily aggregated whale flow data for charting (SQL aggregation)."""
    since = datetime.utcnow() - timedelta(days=days)

    flow_sql = text("""
        SELECT
            CAST(timestamp AS DATE) as date,
            COUNT(*) as count,
            ROUND(CAST(SUM(amount_btc) AS NUMERIC), 2) as total_btc,
            ROUND(CAST(SUM(CASE WHEN direction = 'exchange_in' THEN amount_btc ELSE 0 END) AS NUMERIC), 2) as exchange_in_btc,
            ROUND(CAST(SUM(CASE WHEN direction = 'exchange_out' THEN amount_btc ELSE 0 END) AS NUMERIC), 2) as exchange_out_btc,
            ROUND(CAST(
                SUM(CASE WHEN direction = 'exchange_in' THEN amount_btc ELSE 0 END) -
                SUM(CASE WHEN direction = 'exchange_out' THEN amount_btc ELSE 0 END)
            AS NUMERIC), 2) as net_flow_btc
        FROM whale_transactions
        WHERE timestamp >= :since
        GROUP BY CAST(timestamp AS DATE)
        ORDER BY date
    """)
    result = await session.execute(flow_sql, {"since": since})
    rows = result.mappings().all()

    history = [
        {
            "date": str(r["date"]),
            "count": r["count"],
            "total_btc": float(r["total_btc"] or 0),
            "exchange_in_btc": float(r["exchange_in_btc"] or 0),
            "exchange_out_btc": float(r["exchange_out_btc"] or 0),
            "net_flow_btc": float(r["net_flow_btc"] or 0),
        }
        for r in rows
    ]

    return {
        "days": days,
        "history": history,
    }


@router.get("/address/{address}")
async def get_address_transactions(
    address: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get all whale transactions involving a specific Bitcoin address, with entity label if known."""
    from app.collectors.known_entities import identify_entity
    from sqlalchemy import or_

    # Look up entity label
    label = identify_entity(address)

    # Check AddressLabel cache if not in static DB
    if not label:
        result = await session.execute(
            select(AddressLabel).where(AddressLabel.address == address)
        )
        cached = result.scalar_one_or_none()
        if cached and cached.entity_name:
            label = {
                "name": cached.entity_name,
                "type": cached.entity_type,
                "wallet": cached.wallet_type,
                "source": cached.source,
                "confidence": cached.confidence,
            }

    # Find all whale txs involving this address
    query = select(WhaleTransaction).where(
        or_(
            WhaleTransaction.from_address == address,
            WhaleTransaction.to_address == address,
        )
    ).order_by(desc(WhaleTransaction.timestamp)).limit(limit)

    result = await session.execute(query)
    txs = result.scalars().all()

    return {
        "address": address,
        "label": label,
        "transaction_count": len(txs),
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
                "from_address": tx.from_address,
                "to_address": tx.to_address,
                "entity_name": tx.entity_name,
                "entity_type": tx.entity_type,
                "severity": tx.severity,
                "role": "sender" if tx.from_address == address else "receiver",
            }
            for tx in txs
        ],
    }


@router.get("/institutional")
async def get_institutional_holdings(
    session: AsyncSession = Depends(get_session),
):
    """Get latest institutional BTC holdings with delta tracking."""
    from app.database import InstitutionalHolding
    from sqlalchemy import distinct

    # Get latest snapshot per company (most recent snapshot_date)
    subquery = (
        select(
            InstitutionalHolding.company_name,
            func.max(InstitutionalHolding.snapshot_date).label("latest")
        )
        .group_by(InstitutionalHolding.company_name)
        .subquery()
    )

    result = await session.execute(
        select(InstitutionalHolding).join(
            subquery,
            and_(
                InstitutionalHolding.company_name == subquery.c.company_name,
                InstitutionalHolding.snapshot_date == subquery.c.latest,
            )
        ).order_by(desc(InstitutionalHolding.total_btc))
    )
    holdings = result.scalars().all()

    return {
        "count": len(holdings),
        "holdings": [
            {
                "id": h.id,
                "company_name": h.company_name,
                "ticker": h.ticker,
                "country": h.country,
                "total_btc": h.total_btc,
                "entry_value_usd": h.entry_value_usd,
                "current_value_usd": h.current_value_usd,
                "change_btc": h.change_btc,
                "source": h.source,
                "snapshot_date": h.snapshot_date.isoformat() if h.snapshot_date else None,
            }
            for h in holdings
        ],
    }


@router.get("/institutional/{ticker}")
async def get_institutional_history(
    ticker: str,
    limit: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    """Get a single company's BTC holding history by ticker."""
    from app.database import InstitutionalHolding

    result = await session.execute(
        select(InstitutionalHolding)
        .where(InstitutionalHolding.ticker == ticker.upper())
        .order_by(desc(InstitutionalHolding.snapshot_date))
        .limit(limit)
    )
    holdings = result.scalars().all()

    if not holdings:
        return {"ticker": ticker.upper(), "history": [], "count": 0}

    return {
        "ticker": ticker.upper(),
        "company_name": holdings[0].company_name if holdings else None,
        "count": len(holdings),
        "history": [
            {
                "total_btc": h.total_btc,
                "change_btc": h.change_btc,
                "current_value_usd": h.current_value_usd,
                "snapshot_date": h.snapshot_date.isoformat() if h.snapshot_date else None,
                "source": h.source,
            }
            for h in holdings
        ],
    }


@router.post("/backfill")
async def trigger_whale_backfill():
    """Trigger whale transaction backfill from Blockchair (admin use)."""
    from app.scheduler.jobs import backfill_whale_transactions
    count = await backfill_whale_transactions()
    return {"status": "ok", "transactions_stored": count}


@router.post("/seed")
async def seed_whale_data(
    session: AsyncSession = Depends(get_session),
):
    """Seed verified whale transactions from on-chain news sources (Feb 5-12, 2026).

    Only includes transactions confirmed by multiple news sources with real amounts,
    exchanges, and directions. Price impacts left for the evaluator to fill from
    actual Price table data.

    Sources: Blockchain News, PANews, AMBCrypto, AInvest, Blockchain Reporter,
    BitcoinWorld, CoinDesk, Lookonchain.
    """
    import hashlib

    # Only verified individual transactions reported by news/on-chain trackers
    VERIFIED_WHALES = [
        # Garrett Jin (ex-BitForex CEO) — 5,000 BTC to Binance after $230M Hyperliquid liquidation
        {"time": "2026-02-07 14:30:00", "btc": 5000, "dir": "exchange_in",
         "from": "Garrett Jin", "to": "Binance", "price": 70200,
         "entity_name": "Binance", "entity_type": "exchange", "entity_wallet": "hot",
         "source": "blockchain.news / Lookonchain"},
        # Panic seller dumps 2,500 BTC on Binance
        {"time": "2026-02-08 09:20:00", "btc": 2500, "dir": "exchange_in",
         "from": "unknown", "to": "Binance", "price": 69100,
         "entity_name": "Binance", "entity_type": "exchange", "entity_wallet": "hot",
         "source": "ambcrypto / Lookonchain"},
        # Whale withdraws 2,786 BTC from Binance to cold storage
        {"time": "2026-02-08 16:45:00", "btc": 2786, "dir": "exchange_out",
         "from": "Binance", "to": "unknown", "price": 68500,
         "entity_name": "Binance", "entity_type": "exchange", "entity_wallet": "hot",
         "source": "blockchainreporter.net"},
        # Same whale also withdrew 630 BTC hours earlier
        {"time": "2026-02-08 14:10:00", "btc": 630, "dir": "exchange_out",
         "from": "Binance", "to": "unknown", "price": 68800,
         "entity_name": "Binance", "entity_type": "exchange", "entity_wallet": "hot",
         "source": "blockchainreporter.net"},
        # Institutional buyer withdraws 2,989 BTC from Coinbase Institutional
        {"time": "2026-02-06 20:30:00", "btc": 2989, "dir": "exchange_out",
         "from": "Coinbase", "to": "unknown", "price": 65200,
         "entity_name": "Coinbase", "entity_type": "exchange", "entity_wallet": "cold",
         "source": "bitcoinworld.co.in"},
        # Separate institutional withdrawal: 3,483 BTC from Coinbase Institutional
        {"time": "2026-02-07 03:15:00", "btc": 3483, "dir": "exchange_out",
         "from": "Coinbase", "to": "unknown", "price": 66800,
         "entity_name": "Coinbase", "entity_type": "exchange", "entity_wallet": "cold",
         "source": "bitcoinworld.co.in"},
    ]

    def _severity(btc: float) -> int:
        if btc >= 10000: return 10
        if btc >= 5000: return 9
        if btc >= 2000: return 8
        if btc >= 1000: return 7
        if btc >= 500: return 6
        if btc >= 200: return 5
        return 4

    try:
        stored = 0
        for w in VERIFIED_WHALES:
            # Deterministic hash so re-running is idempotent
            seed_str = f"{w['time']}-{w['btc']}-{w['dir']}-{w['from']}-{w['to']}"
            tx_hash = hashlib.sha256(seed_str.encode()).hexdigest()[:64]

            existing = await session.execute(
                select(WhaleTransaction.id).where(WhaleTransaction.tx_hash == tx_hash)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            ts = datetime.fromisoformat(w["time"])
            whale_tx = WhaleTransaction(
                tx_hash=tx_hash,
                timestamp=ts,
                amount_btc=w["btc"],
                amount_usd=round(w["btc"] * w["price"], 2),
                direction=w["dir"],
                from_entity=w["from"],
                to_entity=w["to"],
                entity_name=w.get("entity_name"),
                entity_type=w.get("entity_type"),
                entity_wallet=w.get("entity_wallet"),
                severity=_severity(w["btc"]),
                btc_price_at_tx=w["price"],
                source=w["source"],
            )
            session.add(whale_tx)
            stored += 1

        await session.commit()
        return {"status": "ok", "transactions_seeded": stored}
    except Exception as e:
        await session.rollback()
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}
