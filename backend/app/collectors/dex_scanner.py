"""DEX Scanner Collector — monitors DexScreener for trending/boosted tokens and
tracks which DEX tokens later migrate to centralized exchanges.

Endpoints (free, no auth):
  - GET  /token-boosts/latest/v1
  - GET  /token-boosts/top/v1
  - GET  /token-profiles/latest/v1

Scheduled jobs:
  - scan_dex_tokens()               every 5 min
  - check_dex_to_cex_migrations()   every 30 min
"""

import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select, or_

from app.collectors.base import BaseCollector
from app.database import async_session, DexToken, CoinInfo

logger = logging.getLogger(__name__)

# ── DexScreener Endpoints ────────────────────────────────────────────────────
DEXSCREENER_BOOSTS_LATEST = "https://api.dexscreener.com/token-boosts/latest/v1"
DEXSCREENER_BOOSTS_TOP = "https://api.dexscreener.com/token-boosts/top/v1"
DEXSCREENER_PROFILES_LATEST = "https://api.dexscreener.com/token-profiles/latest/v1"

# Binance exchangeInfo for CEX cross-reference
EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"

# Minimum thresholds to store a token
MIN_VOLUME_24H = 10_000  # $10K
MIN_LIQUIDITY = 5_000    # $5K


class DexScannerCollector(BaseCollector):
    """Scans DexScreener for boosted/trending DEX tokens and tracks CEX migrations."""

    def __init__(self):
        super().__init__()

    async def collect(self) -> dict:
        """Primary collect — delegates to scan_dex_tokens."""
        return await self.scan_dex_tokens()

    # ── Job 1: Scan DEX tokens (every 5 min) ─────────────────────────────────

    async def scan_dex_tokens(self) -> dict:
        """Fetch boosted and trending tokens from DexScreener, store qualifying ones."""
        all_tokens: list[dict] = []

        # Fetch from all three endpoints in parallel-friendly manner
        boosts_latest = await self.fetch_json(DEXSCREENER_BOOSTS_LATEST)
        boosts_top = await self.fetch_json(DEXSCREENER_BOOSTS_TOP)
        profiles_latest = await self.fetch_json(DEXSCREENER_PROFILES_LATEST)

        for source_name, raw_data in [
            ("boosts_latest", boosts_latest),
            ("boosts_top", boosts_top),
            ("profiles_latest", profiles_latest),
        ]:
            tokens = self._parse_dexscreener_response(raw_data, source_name)
            all_tokens.extend(tokens)

        # Deduplicate by address + chain
        seen = set()
        unique_tokens = []
        for t in all_tokens:
            key = (t["address"].lower(), t["chain"])
            if key not in seen:
                seen.add(key)
                unique_tokens.append(t)

        # Enrich tokens from boost/profile endpoints with trading data
        unique_tokens = await self._enrich_tokens(unique_tokens)

        # Filter by volume and liquidity thresholds
        qualified = [
            t for t in unique_tokens
            if (t.get("volume_24h") or 0) >= MIN_VOLUME_24H
            and (t.get("liquidity") or 0) >= MIN_LIQUIDITY
        ]

        stored_count = 0
        async with async_session() as session:
            for token in qualified:
                stored = await self._upsert_dex_token(session, token)
                if stored:
                    stored_count += 1
            await session.commit()

        if stored_count:
            logger.info(
                f"DexScanner: stored/updated {stored_count} tokens "
                f"(from {len(unique_tokens)} unique, {len(all_tokens)} total)"
            )
        return {
            "scanned": len(all_tokens),
            "unique": len(unique_tokens),
            "qualified": len(qualified),
            "stored": stored_count,
        }

    # ── Enrich tokens with trading data ────────────────────────────────────────

    async def _enrich_tokens(self, tokens: list[dict]) -> list[dict]:
        """Fetch trading data for tokens missing volume/liquidity from DexScreener pairs endpoint.

        Boost/profile endpoints only return metadata — no volume, liquidity, or price.
        """
        need_enrichment = [
            t for t in tokens
            if t.get("address") and t.get("chain")
            and (not t.get("volume_24h") or not t.get("liquidity"))
        ]

        if not need_enrichment:
            return tokens

        by_chain: dict[str, list[dict]] = defaultdict(list)
        for t in need_enrichment:
            by_chain[t["chain"]].append(t)

        for chain, chain_tokens in by_chain.items():
            for i in range(0, len(chain_tokens), 30):
                batch = chain_tokens[i:i + 30]
                addrs = ",".join(t["address"] for t in batch)
                url = f"https://api.dexscreener.com/tokens/v1/{chain}/{addrs}"
                data = await self.fetch_json(url)
                if not data:
                    continue

                pairs = data if isinstance(data, list) else data.get("pairs", [])

                best: dict[str, dict] = {}
                for pair in pairs:
                    addr = (pair.get("baseToken", {}).get("address") or "").lower()
                    vol = float(pair.get("volume", {}).get("h24", 0) or 0)
                    if addr and (addr not in best or vol > best[addr].get("vol", 0)):
                        best[addr] = {
                            "vol": vol,
                            "liq": float(pair.get("liquidity", {}).get("usd", 0) or 0),
                            "price": float(pair.get("priceUsd", 0) or 0),
                            "symbol": pair.get("baseToken", {}).get("symbol"),
                            "name": pair.get("baseToken", {}).get("name"),
                        }

                for t in batch:
                    info = best.get(t["address"].lower())
                    if info:
                        t["volume_24h"] = t.get("volume_24h") or info["vol"]
                        t["liquidity"] = t.get("liquidity") or info["liq"]
                        t["price_usd"] = t.get("price_usd") or info["price"]
                        t["symbol"] = t.get("symbol") or info["symbol"]
                        t["name"] = t.get("name") or info["name"]

        enriched = len([t for t in need_enrichment if t.get("volume_24h")])
        if enriched:
            logger.info(f"DexScanner: enriched {enriched}/{len(need_enrichment)} tokens with trading data")

        return tokens

    # ── Job 2: DEX-to-CEX migration check (every 30 min) ─────────────────────

    async def check_dex_to_cex_migrations(self) -> dict:
        """Cross-reference DexToken addresses against CoinInfo in DB + Binance symbols."""
        migrations_found = 0

        # Get all DEX tokens not yet flagged as on-CEX
        async with async_session() as session:
            result = await session.execute(
                select(DexToken).where(DexToken.is_on_cex == False)  # noqa: E712
            )
            dex_tokens = result.scalars().all()

            if not dex_tokens:
                return {"migrations_found": 0}

            # Method 1: Cross-reference against CoinInfo symbols already in DB
            dex_symbols_upper = {
                t.symbol.upper(): t
                for t in dex_tokens
                if t.symbol
            }

            if dex_symbols_upper:
                coin_result = await session.execute(
                    select(CoinInfo).where(
                        CoinInfo.symbol.in_(list(dex_symbols_upper.keys()))
                    )
                )
                matched_coins = coin_result.scalars().all()

                for coin in matched_coins:
                    dex_token = dex_symbols_upper.get(coin.symbol.upper())
                    if dex_token:
                        dex_token.is_on_cex = True
                        dex_token.updated_at = datetime.utcnow()
                        migrations_found += 1
                        logger.info(
                            f"DexScanner: {dex_token.symbol} ({dex_token.chain}) "
                            f"found on CEX (matched CoinInfo: {coin.coin_id})"
                        )

            # Method 2: Check Binance exchangeInfo for symbols
            exchange_data = await self.fetch_json(EXCHANGE_INFO_URL)
            if exchange_data and "symbols" in exchange_data:
                binance_base_assets = {
                    s.get("baseAsset", "").upper()
                    for s in exchange_data["symbols"]
                    if s.get("status") == "TRADING"
                }

                for dex_token in dex_tokens:
                    if dex_token.is_on_cex:
                        continue
                    if dex_token.symbol and dex_token.symbol.upper() in binance_base_assets:
                        dex_token.is_on_cex = True
                        dex_token.updated_at = datetime.utcnow()
                        migrations_found += 1
                        logger.info(
                            f"DexScanner: {dex_token.symbol} ({dex_token.chain}) "
                            f"found on Binance"
                        )

            await session.commit()

        if migrations_found:
            logger.info(f"DexScanner: {migrations_found} DEX-to-CEX migrations detected")
        return {"migrations_found": migrations_found}

    # ── Parsing helpers ───────────────────────────────────────────────────────

    def _parse_dexscreener_response(
        self, data: dict | list | None, source: str
    ) -> list[dict]:
        """Normalize DexScreener response into a flat list of token dicts."""
        if data is None:
            return []

        tokens = []

        # DexScreener returns a list of token objects
        items = data if isinstance(data, list) else data.get("data", data.get("tokens", []))
        if not isinstance(items, list):
            logger.debug(f"DexScanner: unexpected {source} response type: {type(items)}")
            return []

        for item in items:
            token = self._normalize_token(item, source)
            if token:
                tokens.append(token)

        return tokens

    @staticmethod
    def _normalize_token(item: dict, source: str) -> dict | None:
        """Extract a normalized token dict from a DexScreener item."""
        address = item.get("tokenAddress") or item.get("address") or ""
        if not address:
            return None

        chain = item.get("chainId") or item.get("chain") or "unknown"

        # Token boosts/profiles may have different field names
        symbol = (
            item.get("symbol")
            or item.get("tokenSymbol")
            or item.get("header", {}).get("symbol")
            or None
        )
        name = (
            item.get("name")
            or item.get("tokenName")
            or item.get("description")
            or None
        )

        # Price data might be nested
        price_usd = item.get("priceUsd") or item.get("price")
        volume_24h = item.get("volume", {}).get("h24") if isinstance(item.get("volume"), dict) else item.get("volume24h")
        liquidity = item.get("liquidity", {}).get("usd") if isinstance(item.get("liquidity"), dict) else item.get("liquidity")

        # Convert to float safely
        def safe_float(v):
            if v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        boosts = item.get("amount") or item.get("totalAmount") or 0
        try:
            boosts = int(boosts)
        except (ValueError, TypeError):
            boosts = 0

        return {
            "address": address,
            "chain": chain,
            "symbol": symbol,
            "name": name,
            "price_usd": safe_float(price_usd),
            "volume_24h": safe_float(volume_24h),
            "liquidity": safe_float(liquidity),
            "boosts": boosts,
            "source": source,
        }

    @staticmethod
    async def _upsert_dex_token(session, token: dict) -> bool:
        """Insert or update a DexToken row. Returns True if a new row was created."""
        address = token["address"].lower()
        chain = token["chain"]

        result = await session.execute(
            select(DexToken).where(
                DexToken.address == address,
                DexToken.chain == chain,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update mutable fields if new data is available
            if token.get("price_usd") is not None:
                existing.price_usd = token["price_usd"]
            if token.get("volume_24h") is not None:
                existing.volume_24h = token["volume_24h"]
            if token.get("liquidity") is not None:
                existing.liquidity = token["liquidity"]
            if token.get("boosts") and token["boosts"] > (existing.boosts or 0):
                existing.boosts = token["boosts"]
            if token.get("symbol") and not existing.symbol:
                existing.symbol = token["symbol"]
            if token.get("name") and not existing.name:
                existing.name = token["name"]
            existing.updated_at = datetime.utcnow()
            return False

        session.add(DexToken(
            address=address,
            chain=chain,
            symbol=token.get("symbol"),
            name=token.get("name"),
            price_usd=token.get("price_usd"),
            volume_24h=token.get("volume_24h"),
            liquidity=token.get("liquidity"),
            boosts=token.get("boosts", 0),
            first_seen=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        return True


# ── Scheduled job entry points ────────────────────────────────────────────────

_collector: DexScannerCollector | None = None


def _get_collector() -> DexScannerCollector:
    global _collector
    if _collector is None:
        _collector = DexScannerCollector()
    return _collector


async def scan_dex_tokens():
    """Scheduled: every 5 min — scan DexScreener for trending/boosted tokens."""
    collector = _get_collector()
    try:
        await collector.scan_dex_tokens()
    except Exception as e:
        logger.error(f"scan_dex_tokens error: {e}", exc_info=True)


async def check_dex_to_cex_migrations():
    """Scheduled: every 30 min — cross-reference DEX tokens vs CEX listings."""
    collector = _get_collector()
    try:
        await collector.check_dex_to_cex_migrations()
    except Exception as e:
        logger.error(f"check_dex_to_cex_migrations error: {e}", exc_info=True)
