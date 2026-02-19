"""On-chain / whale tracking jobs: whale transactions, entity monitoring, impact evaluation."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, desc

from app.database import (
    async_session, Price, WhaleTransaction, EventImpact,
    timestamp_diff_order,
)
from app.collectors import WhaleCollector

logger = logging.getLogger(__name__)

# Global instances
whale_collector = WhaleCollector()


async def _store_whale_transactions(transactions: list[dict], source_label: str):
    """Shared helper to store whale transaction dicts into the database."""
    if not transactions:
        return 0

    async with async_session() as session:
        price_row = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price = price_row.scalar_one_or_none()
        current_price = price.close if price else None

        stored = 0
        for tx_data in transactions:
            existing = await session.execute(
                select(WhaleTransaction.id).where(
                    WhaleTransaction.tx_hash == tx_data["tx_hash"]
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            amount_usd = tx_data["amount_btc"] * current_price if current_price else None

            whale_tx = WhaleTransaction(
                tx_hash=tx_data["tx_hash"],
                timestamp=datetime.fromisoformat(tx_data["timestamp"]) if tx_data.get("timestamp") else datetime.utcnow(),
                amount_btc=tx_data["amount_btc"],
                amount_usd=amount_usd,
                direction=tx_data["direction"],
                from_entity=tx_data["from_entity"],
                to_entity=tx_data["to_entity"],
                entity_name=tx_data.get("entity_name"),
                entity_type=tx_data.get("entity_type"),
                entity_wallet=tx_data.get("entity_wallet"),
                severity=tx_data["severity"],
                btc_price_at_tx=current_price,
                from_address=tx_data.get("from_address"),
                to_address=tx_data.get("to_address"),
                source=tx_data.get("source", source_label),
                raw_data=tx_data.get("raw_data"),
            )
            session.add(whale_tx)
            stored += 1

            # For severity >= 9, also create EventImpact
            if tx_data["severity"] >= 9 and current_price:
                entity_label = tx_data.get("entity_name") or tx_data["from_entity"]
                if entity_label == "unknown":
                    entity_label = tx_data["to_entity"]
                direction_label = tx_data["direction"].replace("_", " ")
                title = f"Whale {direction_label}: {tx_data['amount_btc']:.0f} BTC"
                if entity_label and entity_label != "unknown":
                    title += f" ({entity_label})"
                if amount_usd:
                    title += f" ${amount_usd:,.0f}"

                event = EventImpact(
                    timestamp=whale_tx.timestamp,
                    title=title,
                    source="whale_tracker",
                    category="whale_movement",
                    subcategory=tx_data["direction"],
                    keywords=f"whale,{tx_data['direction']},{tx_data['from_entity']},{tx_data['to_entity']}",
                    severity=tx_data["severity"],
                    sentiment_score=-0.5 if tx_data["direction"] == "exchange_in" else 0.5 if tx_data["direction"] == "exchange_out" else 0.0,
                    price_at_event=current_price,
                )
                session.add(event)

        await session.commit()

    if stored:
        logger.info(f"Whale transactions stored ({source_label}): {stored} new")
    return stored


async def resolve_unknown_whale_addresses():
    """Resolve unknown whale addresses using WalletExplorer + Blockchair APIs (runs every 30 min).

    Finds whale txs where entity_name IS NULL and from_address/to_address exist,
    resolves them via online APIs, and updates entity info on the transaction.
    Limited to 20 addresses per run to stay within rate limits.
    """
    from app.collectors.address_resolver import AddressResolver

    resolver = AddressResolver()
    try:
        async with async_session() as session:
            # Find txs with unknown entities but known addresses
            result = await session.execute(
                select(WhaleTransaction).where(
                    WhaleTransaction.entity_name.is_(None),
                    (WhaleTransaction.from_address.isnot(None)) | (WhaleTransaction.to_address.isnot(None)),
                ).order_by(desc(WhaleTransaction.timestamp)).limit(40)
            )
            txs = result.scalars().all()

            if not txs:
                return

            resolved_count = 0
            addresses_checked = 0
            max_addresses = 20

            for tx in txs:
                if addresses_checked >= max_addresses:
                    break

                from_label = None
                to_label = None

                # Try resolving from_address
                if tx.from_address and addresses_checked < max_addresses:
                    from_label = await resolver.resolve(tx.from_address, session)
                    addresses_checked += 1

                # Try resolving to_address
                if tx.to_address and addresses_checked < max_addresses:
                    to_label = await resolver.resolve(tx.to_address, session)
                    addresses_checked += 1

                # Update transaction if we found labels
                if from_label or to_label:
                    if from_label:
                        tx.from_entity = from_label["name"]
                    if to_label:
                        tx.to_entity = to_label["name"]

                    # Determine primary entity and direction
                    primary = to_label or from_label
                    tx.entity_name = primary["name"]
                    tx.entity_type = primary.get("type")
                    tx.entity_wallet = primary.get("wallet")

                    # Re-classify direction
                    if from_label and not to_label:
                        tx.direction = "exchange_out"
                    elif not from_label and to_label:
                        tx.direction = "exchange_in"
                    elif from_label and to_label:
                        tx.direction = "exchange_in"

                    resolved_count += 1

            await session.commit()

            if resolved_count:
                logger.info(f"Address resolver: resolved {resolved_count} whale txs ({addresses_checked} addresses checked)")

    except Exception as e:
        logger.error(f"Address resolution error: {e}")
    finally:
        await resolver.close()


async def collect_whale_transactions():
    """Collect and store large BTC transactions (runs every 10 min).

    Uses Blockchair for discovery + BTCScan for address details + mempool.space fallback.
    """
    try:
        result = await whale_collector.collect()
        await _store_whale_transactions(result.get("transactions", []), "blockchair+btcscan")
    except Exception as e:
        logger.error(f"Whale collection error: {e}")


async def monitor_entity_wallets():
    """Monitor known entity wallets for new large transactions (runs every 10 min, offset by 5 min)."""
    try:
        result = await whale_collector.monitor_known_addresses()
        await _store_whale_transactions(result.get("transactions", []), "entity_monitor")
    except Exception as e:
        logger.error(f"Entity wallet monitor error: {e}")


async def evaluate_whale_impacts():
    """Evaluate price impact of whale transactions (runs every 30 min)."""
    try:
        async with async_session() as session:
            now = datetime.utcnow()

            # Find unevaluated whale txs older than the timeframe
            for timeframe, hours, eval_col, change_col in [
                ("1h", 1, "evaluated_1h", "change_pct_1h"),
                ("4h", 4, "evaluated_4h", "change_pct_4h"),
                ("24h", 24, "evaluated_24h", "change_pct_24h"),
            ]:
                cutoff = now - timedelta(hours=hours)
                result = await session.execute(
                    select(WhaleTransaction).where(
                        getattr(WhaleTransaction, eval_col) == False,
                        WhaleTransaction.timestamp <= cutoff,
                        WhaleTransaction.btc_price_at_tx.isnot(None),
                    ).limit(50)
                )
                txs = result.scalars().all()

                for tx in txs:
                    target_time = tx.timestamp + timedelta(hours=hours)
                    price_result = await session.execute(
                        select(Price)
                        .order_by(timestamp_diff_order(Price.timestamp, target_time))
                        .limit(1)
                    )
                    price_row = price_result.scalar_one_or_none()

                    if price_row and tx.btc_price_at_tx:
                        change_pct = ((price_row.close - tx.btc_price_at_tx) / tx.btc_price_at_tx) * 100
                        setattr(tx, change_col, round(change_pct, 4))
                        setattr(tx, eval_col, True)

                        # For 1h evaluation, also determine if direction was predictive
                        if timeframe == "1h":
                            if tx.direction == "exchange_in":
                                # Exchange deposits should be bearish
                                tx.direction_was_predictive = change_pct < 0
                            elif tx.direction == "exchange_out":
                                # Exchange withdrawals should be bullish
                                tx.direction_was_predictive = change_pct > 0
                            else:
                                tx.direction_was_predictive = None

            await session.commit()
            logger.info("Whale impact evaluation completed")

    except Exception as e:
        logger.error(f"Whale evaluation error: {e}")


async def backfill_whale_transactions():
    """Backfill whale transactions by scanning recent blocks via mempool.space.

    Scans the last 10 blocks (~100 min) for large BTC transactions (>100 BTC).
    Each block is paginated (25 txs/page), scanning first 200 txs per block.
    Called once at startup or via admin endpoint.
    """
    import aiohttp
    import ssl
    import certifi
    from app.collectors.whale import calculate_severity
    from app.collectors.known_entities import identify_any

    logger.info("Backfilling whale transactions via mempool.space block scan...")

    try:
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        timeout = aiohttp.ClientTimeout(total=30)

        # Get current BTC price
        async with async_session() as session:
            price_row = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            price = price_row.scalar_one_or_none()
            current_price = price.close if price else 68000.0

        stored_total = 0

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as http:
            # Get recent blocks
            async with http.get("https://mempool.space/api/blocks") as resp:
                if resp.status != 200:
                    logger.warning(f"mempool.space /blocks returned {resp.status}")
                    return 0
                blocks = await resp.json()

            for block in blocks[:10]:  # last 10 blocks
                block_hash = block.get("id", "")
                block_ts = block.get("timestamp")
                if not block_hash:
                    continue

                # Scan pages of txs in this block
                for page_start in range(0, 200, 25):
                    try:
                        url = f"https://mempool.space/api/block/{block_hash}/txs/{page_start}"
                        async with http.get(url) as resp:
                            if resp.status != 200:
                                break
                            page_txs = await resp.json()

                        if not page_txs:
                            break

                        async with async_session() as session:
                            for tx in page_txs:
                                tx_hash = tx.get("txid", "")
                                if not tx_hash:
                                    continue

                                existing = await session.execute(
                                    select(WhaleTransaction.id).where(
                                        WhaleTransaction.tx_hash == tx_hash
                                    )
                                )
                                if existing.scalar_one_or_none() is not None:
                                    continue

                                total_out = sum(v.get("value", 0) for v in tx.get("vout", []))
                                amount_btc = total_out / 1e8
                                if amount_btc < 100:
                                    continue

                                # Extract addresses (already in mempool.space response)
                                input_addrs = []
                                for vin in tx.get("vin", []):
                                    prevout = vin.get("prevout") or {}
                                    addr = prevout.get("scriptpubkey_address")
                                    if addr:
                                        input_addrs.append(addr)

                                output_addrs = []
                                for vout in tx.get("vout", []):
                                    addr = vout.get("scriptpubkey_address")
                                    if addr:
                                        output_addrs.append(addr)

                                # Classify
                                from_info = identify_any(input_addrs)
                                to_info = identify_any(output_addrs)
                                from_name = from_info["name"] if from_info else "unknown"
                                to_name = to_info["name"] if to_info else "unknown"

                                if from_info and not to_info:
                                    direction, primary = "exchange_out", from_info
                                elif not from_info and to_info:
                                    direction, primary = "exchange_in", to_info
                                elif from_info and to_info:
                                    direction, primary = "exchange_in", to_info
                                else:
                                    direction, primary = "unknown", None

                                ts = datetime.fromtimestamp(block_ts, tz=timezone.utc) if block_ts else datetime.now(timezone.utc)

                                whale_tx = WhaleTransaction(
                                    tx_hash=tx_hash,
                                    timestamp=ts,
                                    amount_btc=round(amount_btc, 4),
                                    amount_usd=round(amount_btc * current_price, 2),
                                    direction=direction,
                                    from_entity=from_name,
                                    to_entity=to_name,
                                    entity_name=primary["name"] if primary else None,
                                    entity_type=primary["type"] if primary else None,
                                    entity_wallet=primary["wallet"] if primary else None,
                                    severity=calculate_severity(amount_btc),
                                    btc_price_at_tx=current_price,
                                    source="mempool_backfill",
                                )
                                session.add(whale_tx)
                                stored_total += 1

                            await session.commit()

                        if len(page_txs) < 25:
                            break

                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning(f"Block scan error at {block_hash[:12]} offset {page_start}: {e}")
                        break

        logger.info(f"Whale backfill complete: {stored_total} transactions stored")
        return stored_total

    except Exception as e:
        logger.error(f"Whale backfill error: {e}")
        return 0
