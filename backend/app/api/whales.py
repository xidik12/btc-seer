import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, WhaleTransaction, AddressLabel

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

    # Enrich with latest activity from DB
    now = datetime.utcnow()
    since_7d = now - timedelta(days=7)

    result = await session.execute(
        select(WhaleTransaction).where(
            WhaleTransaction.timestamp >= since_7d,
            WhaleTransaction.entity_name.isnot(None),
        ).order_by(desc(WhaleTransaction.timestamp))
    )
    txs = result.scalars().all()

    # Group activity by entity
    entity_activity: dict[str, dict] = {}
    for tx in txs:
        name = tx.entity_name
        if name not in entity_activity:
            entity_activity[name] = {
                "tx_count_7d": 0,
                "total_btc_7d": 0.0,
                "last_seen": tx.timestamp.isoformat(),
                "last_direction": tx.direction,
            }
        entity_activity[name]["tx_count_7d"] += 1
        entity_activity[name]["total_btc_7d"] += tx.amount_btc

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
                "most_active_entity": None,
            }

        directions = {"exchange_in": 0, "exchange_out": 0, "whale_to_whale": 0, "unknown": 0}
        exchange_counts = {}
        entity_counts = {}
        total_btc = 0
        net_flow = 0

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

            if tx.entity_name:
                entity_counts[tx.entity_name] = entity_counts.get(tx.entity_name, 0) + 1

        most_active = max(entity_counts, key=entity_counts.get) if entity_counts else None

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
            "most_active_entity": most_active,
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
