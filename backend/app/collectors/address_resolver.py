"""Online Bitcoin address resolution using WalletExplorer + Blockchair APIs.

Resolution cascade:
1. Static lookup: KNOWN_ENTITIES dict (instant)
2. Cache lookup: AddressLabel table (DB query)
3. WalletExplorer API (FREE, primary)
4. Blockchair API (fallback, 1K free/day)

Negative caching: when no label found, store with entity_name=None, source="api_miss".
Cache TTL = 7 days before re-querying.
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta

import aiohttp
import ssl
import certifi

from app.collectors.known_entities import KNOWN_ENTITIES

logger = logging.getLogger(__name__)

# Rate limiting: max 1 request/sec globally
_last_api_call: float = 0.0
_RATE_LIMIT_SECS = 1.0

# Known WalletExplorer entity name patterns → entity type mapping
_EXCHANGE_PATTERNS = re.compile(
    r"(binance|coinbase|kraken|bitfinex|bitstamp|gemini|huobi|okx|bybit|"
    r"bitget|kucoin|gate\.io|crypto\.com|robinhood|upbit|bithumb|deribit|"
    r"mexc|bitflyer|poloniex|hitbtc|bittrex|coincheck|korbit|bitvavo|luno|"
    r"blockchain\.com|swissborg|mtgox|mt\.gox|btc-e|wex|localbitcoins|"
    r"paxful|bisq|changelly|shapeshift|sideshift)",
    re.IGNORECASE,
)
_POOL_PATTERNS = re.compile(
    r"(f2pool|antpool|foundry|viabtc|slush|braiins|btc\.com|poolin|"
    r"luxor|spiderpool|ocean|sbi.crypto|mara|binance.pool|btc\.top)",
    re.IGNORECASE,
)
_GAMBLING_PATTERNS = re.compile(
    r"(satoshi.?dice|primedice|stake\.com|bustabit|cloudbet|fortunejack|"
    r"1xbit|betcoin|nitrogen|bitcasino)",
    re.IGNORECASE,
)


def _classify_wallet_id(wallet_id: str) -> dict | None:
    """Parse a WalletExplorer wallet_id into entity info."""
    if not wallet_id:
        return None

    # Hex hash = unknown wallet cluster
    if re.match(r"^[0-9a-f]{32}$", wallet_id, re.IGNORECASE):
        return None

    # Clean up the name
    name = wallet_id.replace(".net", "").replace(".com", "").replace(".io", "")
    name = name.strip()

    if _EXCHANGE_PATTERNS.search(wallet_id):
        return {"name": wallet_id, "type": "exchange", "wallet": "hot"}
    if _POOL_PATTERNS.search(wallet_id):
        return {"name": wallet_id, "type": "mining_pool", "wallet": "hot"}
    if _GAMBLING_PATTERNS.search(wallet_id):
        return {"name": wallet_id, "type": "exchange", "wallet": "hot"}

    # If it has a readable name but doesn't match patterns, it's still identified
    return {"name": wallet_id, "type": "exchange", "wallet": "hot"}


async def _rate_limit():
    """Enforce global rate limit of 1 req/sec."""
    global _last_api_call
    now = time.monotonic()
    elapsed = now - _last_api_call
    if elapsed < _RATE_LIMIT_SECS:
        await asyncio.sleep(_RATE_LIMIT_SECS - elapsed)
    _last_api_call = time.monotonic()


class AddressResolver:
    """Resolves Bitcoin addresses to entity labels using APIs and caching."""

    WALLETEXPLORER_URL = "http://www.walletexplorer.com/api/1/address-lookup"
    BLOCKCHAIR_URL = "https://api.blockchair.com/bitcoin/dashboards/address/{addr}"
    CACHE_TTL_DAYS = 7

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                connector=aiohttp.TCPConnector(ssl=ssl_ctx),
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def resolve(self, address: str, db_session) -> dict | None:
        """Resolve an address to entity info.

        Returns: {"name": ..., "type": ..., "wallet": ...} or None
        """
        from app.database import AddressLabel

        # 1. Static lookup
        static = KNOWN_ENTITIES.get(address)
        if static:
            return static

        # 2. Cache lookup
        from sqlalchemy import select
        result = await db_session.execute(
            select(AddressLabel).where(AddressLabel.address == address)
        )
        cached = result.scalar_one_or_none()

        if cached:
            # Check if cache is still fresh
            if cached.last_checked and (datetime.utcnow() - cached.last_checked) < timedelta(days=self.CACHE_TTL_DAYS):
                if cached.entity_name:
                    return {
                        "name": cached.entity_name,
                        "type": cached.entity_type or "exchange",
                        "wallet": cached.wallet_type or "hot",
                    }
                return None  # Negative cache hit

        # 3. WalletExplorer API
        label = await self._try_walletexplorer(address)

        # 4. Blockchair fallback
        if label is None:
            label = await self._try_blockchair(address)

        # 5. Cache the result (positive or negative)
        await self._cache_result(address, label, db_session)

        return label

    async def _try_walletexplorer(self, address: str) -> dict | None:
        """Query WalletExplorer API for address label."""
        try:
            await _rate_limit()
            session = await self._get_session()
            params = {"address": address, "caller": "btc-oracle"}
            async with session.get(self.WALLETEXPLORER_URL, params=params) as resp:
                if resp.status != 200:
                    logger.debug(f"WalletExplorer returned {resp.status} for {address[:12]}...")
                    return None
                data = await resp.json()
                wallet_id = data.get("wallet_id")
                if wallet_id:
                    return _classify_wallet_id(wallet_id)
        except Exception as e:
            logger.debug(f"WalletExplorer error for {address[:12]}...: {e}")
        return None

    async def _try_blockchair(self, address: str) -> dict | None:
        """Query Blockchair API for address label (fallback)."""
        try:
            await _rate_limit()
            session = await self._get_session()
            url = self.BLOCKCHAIR_URL.format(addr=address)
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                addr_data = data.get("data", {}).get(address, {})
                addr_info = addr_data.get("address", {})
                # Blockchair may have labels in premium responses
                label = addr_info.get("type")
                if label and label not in ("pubkeyhash", "scripthash", "witness_v0_keyhash", "witness_v1_taproot"):
                    return {"name": label, "type": "exchange", "wallet": "hot"}
        except Exception as e:
            logger.debug(f"Blockchair error for {address[:12]}...: {e}")
        return None

    async def _cache_result(self, address: str, label: dict | None, db_session):
        """Upsert an AddressLabel cache row."""
        from app.database import AddressLabel
        from sqlalchemy import select

        try:
            result = await db_session.execute(
                select(AddressLabel).where(AddressLabel.address == address)
            )
            existing = result.scalar_one_or_none()

            now = datetime.utcnow()
            if existing:
                existing.entity_name = label["name"] if label else None
                existing.entity_type = label.get("type") if label else None
                existing.wallet_type = label.get("wallet") if label else None
                existing.source = "walletexplorer" if label else "api_miss"
                existing.confidence = 0.7 if label else 0.0
                existing.last_checked = now
            else:
                new_label = AddressLabel(
                    address=address,
                    entity_name=label["name"] if label else None,
                    entity_type=label.get("type") if label else None,
                    wallet_type=label.get("wallet") if label else None,
                    source="walletexplorer" if label else "api_miss",
                    confidence=0.7 if label else 0.0,
                    last_checked=now,
                    created_at=now,
                )
                db_session.add(new_label)

            await db_session.commit()
        except Exception as e:
            logger.debug(f"Cache write error for {address[:12]}...: {e}")
            await db_session.rollback()
