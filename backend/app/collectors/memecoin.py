"""Memecoin Collector — discovers early-stage memecoins from DexScreener,
assigns rug-pull risk scores, and marks dead tokens.

Reuses DexScreener trending + boosted token endpoints.

Risk scoring (0-100):
  - top_holder_pct > 50%       -> +30
  - contract not verified       -> +20
  - no liquidity lock           -> +15
  - volume acceleration > 10x   -> +10
  - (not all data available initially; score what is available)

Scheduled jobs:
  - discover_memecoins()             every 10 min
  - update_memecoin_risk_scores()    every 30 min
  - cleanup_dead_memecoins()         daily
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select

from app.collectors.base import BaseCollector
from app.database import async_session, MemeToken

logger = logging.getLogger(__name__)

# ── DexScreener Endpoints ────────────────────────────────────────────────────
DEXSCREENER_BOOSTS_LATEST = "https://api.dexscreener.com/token-boosts/latest/v1"
DEXSCREENER_BOOSTS_TOP = "https://api.dexscreener.com/token-boosts/top/v1"
DEXSCREENER_PROFILES_LATEST = "https://api.dexscreener.com/token-profiles/latest/v1"
DEXSCREENER_SEARCH = "https://api.dexscreener.com/latest/dex/search"

# Search queries to discover trending memecoins across chains
MEMECOIN_SEARCH_QUERIES = [
    "PEPE", "DOGE", "SHIB", "BONK", "WIF", "FLOKI",
    "MEME", "TRUMP", "BRETT", "POPCAT",
]

# Minimum thresholds for memecoins
MIN_VOLUME_24H = 10_000    # $10K
MIN_LIQUIDITY = 5_000      # $5K
MAX_AGE_DAYS = 7           # only tokens < 7 days old

# Dead token criteria — only mark dead after explicit 0 volume AND stale for 48h
DEAD_STALE_HOURS = 48


class MemecoinCollector(BaseCollector):
    """Discovers early-stage memecoins and tracks their risk profiles."""

    def __init__(self):
        super().__init__()

    async def collect(self) -> dict:
        """Primary collect — delegates to discover_memecoins."""
        return await self.discover_memecoins()

    # ── Job 1: Discover memecoins (every 10 min) ─────────────────────────────

    async def discover_memecoins(self) -> dict:
        """Fetch trending/boosted tokens from DexScreener + search, filter for young memecoins."""
        all_tokens: list[dict] = []

        # Source 1: Boost endpoints (paid promos — still useful but not sole source)
        boosts_latest = await self.fetch_json(DEXSCREENER_BOOSTS_LATEST)
        boosts_top = await self.fetch_json(DEXSCREENER_BOOSTS_TOP)
        profiles_latest = await self.fetch_json(DEXSCREENER_PROFILES_LATEST)

        for source_name, raw_data in [
            ("boosts_latest", boosts_latest),
            ("boosts_top", boosts_top),
            ("profiles_latest", profiles_latest),
        ]:
            tokens = self._parse_tokens(raw_data)
            all_tokens.extend(tokens)

        # Source 2: Search for popular memecoin names — finds genuinely trending tokens
        for query in MEMECOIN_SEARCH_QUERIES:
            search_data = await self.fetch_json(DEXSCREENER_SEARCH, params={"q": query})
            if search_data and "pairs" in search_data:
                for pair in search_data["pairs"][:10]:  # top 10 per query
                    token = self._normalize_pair(pair)
                    if token:
                        all_tokens.append(token)

        # Deduplicate by address + chain
        seen: set[tuple[str, str]] = set()
        unique: list[dict] = []
        for t in all_tokens:
            key = (t["address"].lower(), t["chain"])
            if key not in seen:
                seen.add(key)
                unique.append(t)

        # Enrich tokens from boost/profile endpoints with trading data
        unique = await self._enrich_tokens(unique)

        # Filter: volume >= $10K, liquidity >= $5K
        qualified = [
            t for t in unique
            if (t.get("volume_24h") or 0) >= MIN_VOLUME_24H
            and (t.get("liquidity") or 0) >= MIN_LIQUIDITY
        ]

        stored_count = 0
        async with async_session() as session:
            for token in qualified:
                created = await self._upsert_meme_token(session, token)
                if created:
                    stored_count += 1
            await session.commit()

        if stored_count:
            logger.info(
                f"MemecoinCollector: discovered {stored_count} new memecoins "
                f"(from {len(unique)} unique tokens)"
            )
        return {
            "scanned": len(all_tokens),
            "unique": len(unique),
            "qualified": len(qualified),
            "new": stored_count,
        }

    # ── Enrich tokens with trading data ────────────────────────────────────────

    async def _enrich_tokens(self, tokens: list[dict]) -> list[dict]:
        """Fetch trading data for tokens missing volume/liquidity from DexScreener pairs endpoint.

        Boost/profile endpoints only return metadata (address, chain, icon, description) —
        no volume, liquidity, or price. This method fetches that data so tokens can pass
        the qualified filter.
        """
        # Only enrich tokens that are missing trading data
        need_enrichment = [
            t for t in tokens
            if t.get("address") and t.get("chain")
            and (not t.get("volume_24h") or not t.get("liquidity"))
        ]

        if not need_enrichment:
            return tokens

        # Group by chain
        by_chain: dict[str, list[dict]] = defaultdict(list)
        for t in need_enrichment:
            by_chain[t["chain"]].append(t)

        # Batch: GET https://api.dexscreener.com/tokens/v1/{chainId}/{addr1},{addr2},...
        # Max 30 addresses per call
        for chain, chain_tokens in by_chain.items():
            for i in range(0, len(chain_tokens), 30):
                batch = chain_tokens[i:i + 30]
                addrs = ",".join(t["address"] for t in batch)
                url = f"https://api.dexscreener.com/tokens/v1/{chain}/{addrs}"
                data = await self.fetch_json(url)
                if not data:
                    continue

                pairs = data if isinstance(data, list) else data.get("pairs", [])

                # Build lookup: address -> best pair (highest volume)
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

                # Merge back into tokens
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
            logger.info(f"MemecoinCollector: enriched {enriched}/{len(need_enrichment)} tokens with trading data")

        return tokens

    # ── Job 2: Update risk scores (every 30 min) ─────────────────────────────

    async def update_memecoin_risk_scores(self) -> dict:
        """Recalculate rug-pull risk scores for all active meme tokens."""
        updated = 0

        async with async_session() as session:
            result = await session.execute(
                select(MemeToken).where(MemeToken.status == "active")
            )
            tokens = result.scalars().all()

            for token in tokens:
                old_score = token.rug_pull_score
                new_score = self._calculate_risk_score(token)
                token.rug_pull_score = new_score
                token.updated_at = datetime.utcnow()

                # Graduate tokens that have been around for a while with low risk
                age_days = (datetime.utcnow() - (token.first_seen or datetime.utcnow())).days
                if age_days > MAX_AGE_DAYS and new_score < 30:
                    token.status = "graduated"
                    logger.info(
                        f"MemecoinCollector: {token.symbol} graduated "
                        f"(age={age_days}d, risk={new_score})"
                    )

                if new_score != old_score:
                    updated += 1

            await session.commit()

        if updated:
            logger.info(f"MemecoinCollector: updated risk scores for {updated} tokens")
        return {"updated": updated, "total_active": len(tokens)}

    # ── Job 3: Cleanup dead memecoins (daily) ─────────────────────────────────

    async def cleanup_dead_memecoins(self) -> dict:
        """Mark tokens with 0 volume AND stale for >48h as 'dead'.

        Only marks dead if volume was explicitly fetched as 0 (not just
        'not refreshed'), preventing false positives from stale data.
        """
        cutoff = datetime.utcnow() - timedelta(hours=DEAD_STALE_HOURS)
        marked_dead = 0

        async with async_session() as session:
            result = await session.execute(
                select(MemeToken).where(
                    MemeToken.status == "active",
                    MemeToken.updated_at < cutoff,
                )
            )
            tokens = result.scalars().all()

            for token in tokens:
                # Only mark dead if volume is explicitly 0 AND stale for 48h+
                if token.volume_24h is not None and token.volume_24h == 0:
                    token.status = "dead"
                    token.updated_at = datetime.utcnow()
                    marked_dead += 1

            await session.commit()

        if marked_dead:
            logger.info(f"MemecoinCollector: marked {marked_dead} tokens as dead")
        return {"marked_dead": marked_dead}

    # ── Risk scoring ──────────────────────────────────────────────────────────

    @staticmethod
    def _calculate_risk_score(token: MemeToken) -> int:
        """Calculate rug-pull risk score (0-100). Higher = riskier.

        Scores what data is available; missing data does not add risk.
        """
        score = 0

        # Top holder concentration > 50% -> +30
        if token.top_holder_pct is not None and token.top_holder_pct > 50:
            score += 30

        # Contract not verified -> +20
        if token.contract_verified is not None and not token.contract_verified:
            score += 20

        # No liquidity lock -> +15
        if token.liquidity_locked is not None and not token.liquidity_locked:
            score += 15

        # Volume acceleration > 10x -> +10 (suspicious pump)
        if token.volume_acceleration is not None and token.volume_acceleration > 10:
            score += 10

        # Honeypot risk flag -> +25
        if token.honeypot_risk is not None and token.honeypot_risk:
            score += 25

        return min(score, 100)

    # ── Parsing helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _normalize_pair(pair: dict) -> dict | None:
        """Normalize a DexScreener pair result into a standard token dict."""
        base_token = pair.get("baseToken", {})
        address = base_token.get("address", "")
        if not address:
            return None

        chain = pair.get("chainId") or "unknown"

        def safe_float(v):
            if v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        volume_raw = pair.get("volume", {})
        volume_24h = safe_float(volume_raw.get("h24")) if isinstance(volume_raw, dict) else safe_float(volume_raw)

        liq_raw = pair.get("liquidity", {})
        liquidity = safe_float(liq_raw.get("usd")) if isinstance(liq_raw, dict) else safe_float(liq_raw)

        return {
            "address": address,
            "chain": chain,
            "symbol": base_token.get("symbol"),
            "name": base_token.get("name"),
            "price_usd": safe_float(pair.get("priceUsd")),
            "volume_24h": volume_24h,
            "liquidity": liquidity,
        }

    def _parse_tokens(self, data: dict | list | None) -> list[dict]:
        """Parse a DexScreener response into a flat token list."""
        if data is None:
            return []

        items = data if isinstance(data, list) else data.get("data", data.get("tokens", []))
        if not isinstance(items, list):
            return []

        tokens = []
        for item in items:
            token = self._normalize_item(item)
            if token:
                tokens.append(token)
        return tokens

    @staticmethod
    def _normalize_item(item: dict) -> dict | None:
        """Normalize a DexScreener item into a standard dict."""
        address = item.get("tokenAddress") or item.get("address") or ""
        if not address:
            return None

        chain = item.get("chainId") or item.get("chain") or "unknown"

        symbol = (
            item.get("symbol")
            or item.get("tokenSymbol")
            or item.get("header", {}).get("symbol")
        )
        name = (
            item.get("name")
            or item.get("tokenName")
            or item.get("description")
        )

        def safe_float(v):
            if v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        price_usd = safe_float(item.get("priceUsd") or item.get("price"))

        volume_raw = item.get("volume")
        if isinstance(volume_raw, dict):
            volume_24h = safe_float(volume_raw.get("h24"))
        else:
            volume_24h = safe_float(item.get("volume24h") or volume_raw)

        liq_raw = item.get("liquidity")
        if isinstance(liq_raw, dict):
            liquidity = safe_float(liq_raw.get("usd"))
        else:
            liquidity = safe_float(liq_raw)

        return {
            "address": address,
            "chain": chain,
            "symbol": symbol,
            "name": name,
            "price_usd": price_usd,
            "volume_24h": volume_24h,
            "liquidity": liquidity,
        }

    @staticmethod
    async def _upsert_meme_token(session, token: dict) -> bool:
        """Insert or update a MemeToken. Returns True if newly created."""
        address = token["address"].lower()
        chain = token["chain"]

        result = await session.execute(
            select(MemeToken).where(
                MemeToken.address == address,
                MemeToken.chain == chain,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Only update if token is still active
            if existing.status != "active":
                return False
            if token.get("price_usd") is not None:
                existing.price_usd = token["price_usd"]
            if token.get("volume_24h") is not None:
                # Calculate volume acceleration before overwriting
                old_vol = existing.volume_24h or 0
                new_vol = token["volume_24h"]
                if old_vol > 0:
                    existing.volume_acceleration = new_vol / old_vol
                existing.volume_24h = new_vol
            if token.get("liquidity") is not None:
                existing.liquidity = token["liquidity"]
            if token.get("symbol") and not existing.symbol:
                existing.symbol = token["symbol"]
            if token.get("name") and not existing.name:
                existing.name = token["name"]
            existing.updated_at = datetime.utcnow()
            return False

        session.add(MemeToken(
            address=address,
            chain=chain,
            symbol=token.get("symbol"),
            name=token.get("name"),
            price_usd=token.get("price_usd"),
            volume_24h=token.get("volume_24h"),
            liquidity=token.get("liquidity"),
            status="active",
            rug_pull_score=0,
            first_seen=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        return True


# ── Scheduled job entry points ────────────────────────────────────────────────

_collector: MemecoinCollector | None = None


def _get_collector() -> MemecoinCollector:
    global _collector
    if _collector is None:
        _collector = MemecoinCollector()
    return _collector


async def discover_memecoins():
    """Scheduled: every 10 min — discover new memecoins from DexScreener."""
    collector = _get_collector()
    try:
        await collector.discover_memecoins()
    except Exception as e:
        logger.error(f"discover_memecoins error: {e}", exc_info=True)


async def update_memecoin_risk_scores():
    """Scheduled: every 30 min — recalculate risk scores for active memecoins."""
    collector = _get_collector()
    try:
        await collector.update_memecoin_risk_scores()
    except Exception as e:
        logger.error(f"update_memecoin_risk_scores error: {e}", exc_info=True)


async def cleanup_dead_memecoins():
    """Scheduled: daily — mark 0-volume tokens as dead."""
    collector = _get_collector()
    try:
        await collector.cleanup_dead_memecoins()
    except Exception as e:
        logger.error(f"cleanup_dead_memecoins error: {e}", exc_info=True)
