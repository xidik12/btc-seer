"""New Listing Collector — detects new Binance spot listings via exchangeInfo diff
and announcements feed.  Tracks post-listing price performance.

Scheduled jobs:
  - check_new_listings()            every 30s
  - check_listing_announcements()   every 2 min
  - evaluate_listing_performance()  every hour
"""

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import select

from app.collectors.base import BaseCollector
from app.database import async_session, NewListing

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
ANNOUNCEMENTS_URL = (
    "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
)
TICKER_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"

# Regex to pull 2-10 letter uppercase symbols from announcement titles
_SYMBOL_RE = re.compile(r"\b([A-Z]{2,10})\b")

# Common English words that look like ticker symbols — skip these
_NOISE_WORDS = frozenset({
    "THE", "AND", "FOR", "NEW", "NOW", "HOW", "HAS", "ITS", "WAS", "ARE",
    "NOT", "BUT", "ALL", "CAN", "HAD", "HER", "ONE", "OUR", "OUT", "YOU",
    "DAY", "GET", "HIS", "MAY", "OLD", "SEE", "WAY", "WHO", "DID", "LET",
    "SAY", "SHE", "TOO", "USE", "BIG", "SET", "TRY", "ASK", "MEN", "RUN",
    "PUT", "END", "WHY", "FAR", "FEW", "GOT", "MAN", "OWN", "WILL", "WITH",
    "FROM", "THIS", "THAT", "HAVE", "BEEN", "THEY", "WHAT", "YOUR", "THAN",
    "EACH", "MAKE", "LIKE", "LONG", "LOOK", "MANY", "THEM", "THEN", "VERY",
    "LIST", "SPOT", "USD", "USDT", "BUSD", "TUSD", "USDC", "BNB", "PAIR",
    "ZONE", "OPEN", "ADDS", "WILL", "FIAT", "SEED", "TAG", "UPDATE",
    "TRADING", "BINANCE", "TOKEN", "COIN", "MARGIN", "FUTURES",
})


class NewListingCollector(BaseCollector):
    """Detects new Binance listings by diffing exchangeInfo and scraping announcements."""

    _known_symbols: set = set()
    _db_seeded: bool = False

    def __init__(self):
        super().__init__()

    async def collect(self) -> dict:
        """Primary collect — delegates to check_new_listings."""
        return await self.check_new_listings()

    async def _seed_from_db(self):
        """Restore known symbols from DB on first run (survives restarts)."""
        if self._db_seeded:
            return
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(NewListing.symbol).distinct()
                )
                db_symbols = {row[0] for row in result.all() if row[0]}
                if db_symbols:
                    self._known_symbols.update(db_symbols)
                    logger.info(
                        f"NewListingCollector: restored {len(db_symbols)} known symbols from DB"
                    )
        except Exception as e:
            logger.error(f"NewListingCollector: DB seed error: {e}")
        self._db_seeded = True

    # ── Job 1: exchangeInfo diff (every 30s) ─────────────────────────────────

    async def check_new_listings(self) -> dict:
        """Poll Binance exchangeInfo, diff against cached symbols, detect new ones."""
        # Ensure we've restored known symbols from DB
        await self._seed_from_db()

        data = await self.fetch_json(EXCHANGE_INFO_URL)
        if not data or "symbols" not in data:
            logger.warning("NewListingCollector: exchangeInfo returned no data")
            return {"new_symbols": [], "total_symbols": len(self._known_symbols)}

        current_symbols = {
            s["symbol"]
            for s in data["symbols"]
            if s.get("status") == "TRADING"
        }

        # First run — seed the cache, nothing to report
        if not self._known_symbols:
            self._known_symbols = current_symbols
            logger.info(
                f"NewListingCollector: seeded {len(current_symbols)} symbols from exchangeInfo"
            )
            return {"new_symbols": [], "total_symbols": len(current_symbols)}

        new_symbols = current_symbols - self._known_symbols
        self._known_symbols = current_symbols

        if not new_symbols:
            return {"new_symbols": [], "total_symbols": len(current_symbols)}

        logger.info(f"NewListingCollector: detected {len(new_symbols)} new symbols: {new_symbols}")

        stored = []
        for sym in new_symbols:
            listing = await self._store_listing(
                symbol=sym,
                exchange="binance",
                listing_type="spot",
                announcement_url=None,
            )
            if listing:
                stored.append(sym)

        return {"new_symbols": stored, "total_symbols": len(current_symbols)}

    async def backfill_recent_announcements(self) -> dict:
        """Scrape last 5 Binance listing announcements to populate initial data."""
        try:
            session = await self.get_session()
            payload = {"catalogId": 48, "pageNo": 1, "pageSize": 5}
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            }

            async with session.post(
                ANNOUNCEMENTS_URL, json=payload, headers=headers, timeout=15
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        f"NewListingCollector: backfill announcements HTTP {resp.status}"
                    )
                    return {"backfilled": 0}
                data = await resp.json()

        except Exception as e:
            logger.error(
                f"NewListingCollector: backfill announcements error: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return {"backfilled": 0}

        catalogs = data.get("data", {}).get("catalogs", [])
        articles = catalogs[0].get("articles", []) if catalogs else []

        backfilled = 0
        for art in articles:
            title = art.get("title", "")
            code = art.get("code", "")
            url = (
                f"https://www.binance.com/en/support/announcement/{code}"
                if code
                else None
            )
            symbols = self._extract_symbols(title)
            for sym in symbols:
                listing = await self._store_listing(
                    symbol=sym,
                    exchange="binance",
                    listing_type="spot",
                    announcement_url=url,
                )
                if listing:
                    backfilled += 1

        if backfilled:
            logger.info(f"NewListingCollector: backfilled {backfilled} recent announcements")
        return {"backfilled": backfilled}

    # ── Job 2: Announcements feed (every 2 min) ──────────────────────────────

    async def check_listing_announcements(self) -> dict:
        """Poll Binance CMS for new-listing announcements (catalog 48)."""
        try:
            session = await self.get_session()
            payload = {"catalogId": 48, "pageNo": 1, "pageSize": 10}
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            }

            async with session.post(
                ANNOUNCEMENTS_URL, json=payload, headers=headers, timeout=15
            ) as resp:
                if resp.status != 200:
                    body_preview = ""
                    try:
                        body_preview = (await resp.text())[:200]
                    except Exception:
                        pass
                    logger.warning(
                        f"NewListingCollector: announcements HTTP {resp.status} "
                        f"url={ANNOUNCEMENTS_URL} body={body_preview}"
                    )
                    return {"announcements": []}
                data = await resp.json()

        except Exception as e:
            logger.error(
                f"NewListingCollector: announcements fetch error: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return {"announcements": []}

        catalogs = data.get("data", {}).get("catalogs", [])
        articles = catalogs[0].get("articles", []) if catalogs else []

        extracted = []
        for art in articles:
            title = art.get("title", "")
            code = art.get("code", "")
            url = (
                f"https://www.binance.com/en/support/announcement/{code}"
                if code
                else None
            )

            symbols = self._extract_symbols(title)
            for sym in symbols:
                listing = await self._store_listing(
                    symbol=sym,
                    exchange="binance",
                    listing_type="spot",
                    announcement_url=url,
                )
                if listing:
                    extracted.append(sym)

        if extracted:
            logger.info(
                f"NewListingCollector: extracted {len(extracted)} symbols from announcements"
            )
        return {"announcements": extracted}

    # ── Job 3: Performance evaluation (every hour) ────────────────────────────

    async def evaluate_listing_performance(self) -> dict:
        """For listings >1h old with no price_1h_after, fetch current price."""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        evaluated = []

        async with async_session() as session:
            result = await session.execute(
                select(NewListing).where(
                    NewListing.price_1h_after.is_(None),
                    NewListing.timestamp < cutoff,
                    NewListing.price_at_listing.isnot(None),
                )
            )
            listings = result.scalars().all()

            if not listings:
                return {"evaluated": 0}

            for listing in listings:
                current_price = await self._fetch_price(listing.symbol)
                if current_price is None:
                    continue

                listing.price_1h_after = current_price
                if listing.price_at_listing and listing.price_at_listing > 0:
                    listing.change_pct_1h = (
                        (current_price - listing.price_at_listing)
                        / listing.price_at_listing
                        * 100
                    )
                evaluated.append(listing.symbol)

            # Also check 24h performance for listings >24h old
            cutoff_24h = datetime.utcnow() - timedelta(hours=24)
            result_24h = await session.execute(
                select(NewListing).where(
                    NewListing.price_24h_after.is_(None),
                    NewListing.timestamp < cutoff_24h,
                    NewListing.price_at_listing.isnot(None),
                )
            )
            listings_24h = result_24h.scalars().all()

            for listing in listings_24h:
                current_price = await self._fetch_price(listing.symbol)
                if current_price is None:
                    continue

                listing.price_24h_after = current_price
                if listing.price_at_listing and listing.price_at_listing > 0:
                    listing.change_pct_24h = (
                        (current_price - listing.price_at_listing)
                        / listing.price_at_listing
                        * 100
                    )

            await session.commit()

        if evaluated:
            logger.info(
                f"NewListingCollector: evaluated 1h performance for {len(evaluated)} listings"
            )
        return {"evaluated": len(evaluated)}

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _store_listing(
        self,
        symbol: str,
        exchange: str,
        listing_type: str,
        announcement_url: str | None,
    ) -> NewListing | None:
        """Store a new listing if it does not already exist."""
        async with async_session() as session:
            # Check for duplicate (same symbol + exchange within last 24h)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            result = await session.execute(
                select(NewListing).where(
                    NewListing.symbol == symbol,
                    NewListing.exchange == exchange,
                    NewListing.timestamp > cutoff,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return None

            # Fetch listing price
            price = await self._fetch_price(symbol)

            listing = NewListing(
                exchange=exchange,
                symbol=symbol,
                listing_type=listing_type,
                announcement_url=announcement_url,
                price_at_listing=price,
                timestamp=datetime.utcnow(),
            )
            session.add(listing)
            await session.commit()
            logger.info(
                f"NewListingCollector: stored listing {symbol} on {exchange} "
                f"(price={price})"
            )
            return listing

    async def _fetch_price(self, symbol: str) -> float | None:
        """Fetch current price for a symbol from Binance ticker."""
        # Try common USDT pair first
        for quote in ("USDT", "BUSD", "BTC"):
            pair = symbol.replace("USDT", "").replace("BUSD", "") + quote
            if pair == symbol:
                # Already a pair like BTCUSDT
                pair = symbol
            data = await self.fetch_json(TICKER_PRICE_URL, params={"symbol": pair})
            if data and "price" in data:
                try:
                    return float(data["price"])
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _extract_symbols(title: str) -> list[str]:
        """Extract likely token symbols from an announcement title."""
        matches = _SYMBOL_RE.findall(title)
        symbols = []
        for m in matches:
            if m not in _NOISE_WORDS and len(m) >= 2:
                symbols.append(m)
        return symbols


# ── Scheduled job entry points ────────────────────────────────────────────────

_collector: NewListingCollector | None = None


def _get_collector() -> NewListingCollector:
    global _collector
    if _collector is None:
        _collector = NewListingCollector()
    return _collector


async def check_new_listings():
    """Scheduled: every 30s — diff exchangeInfo for new symbols."""
    collector = _get_collector()
    try:
        await collector.check_new_listings()
    except Exception as e:
        logger.error(f"check_new_listings error: {e}", exc_info=True)


async def check_listing_announcements():
    """Scheduled: every 2 min — parse Binance listing announcements."""
    collector = _get_collector()
    try:
        await collector.check_listing_announcements()
    except Exception as e:
        logger.error(f"check_listing_announcements error: {e}", exc_info=True)


async def evaluate_listing_performance():
    """Scheduled: every hour — fill in price_1h_after / price_24h_after."""
    collector = _get_collector()
    try:
        await collector.evaluate_listing_performance()
    except Exception as e:
        logger.error(f"evaluate_listing_performance error: {e}", exc_info=True)


async def backfill_recent_announcements():
    """Startup: backfill last 5 Binance listing announcements."""
    collector = _get_collector()
    try:
        await collector.backfill_recent_announcements()
    except Exception as e:
        logger.error(f"backfill_recent_announcements error: {e}", exc_info=True)
