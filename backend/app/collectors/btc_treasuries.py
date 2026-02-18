import logging
from datetime import datetime

from bs4 import BeautifulSoup
from sqlalchemy import select, desc

from app.collectors.base import BaseCollector
from app.database import async_session, InstitutionalHolding, WhaleTransaction

logger = logging.getLogger(__name__)

TREASURIES_URL = "https://bitcointreasuries.net/"


class BTCTreasuriesCollector(BaseCollector):
    """Scrapes bitcointreasuries.net for institutional BTC holdings."""

    def __init__(self):
        super().__init__()
        self._last_snapshot: dict[str, float] = {}  # company -> btc held

    async def collect(self) -> dict:
        """Fetch and parse the BitcoinTreasuries page."""
        holdings = await self._scrape_holdings()
        if not holdings:
            logger.warning("BTCTreasuries: no data scraped")
            return {"holdings": [], "count": 0, "changes": 0}

        changes = await self._store_and_detect_changes(holdings)

        logger.info(f"BTCTreasuries: {len(holdings)} companies scraped, {changes} changes detected")
        return {"holdings": holdings, "count": len(holdings), "changes": changes}

    async def _scrape_holdings(self) -> list[dict]:
        """Fetch and parse the HTML table from bitcointreasuries.net."""
        try:
            session = await self.get_session()
            async with session.get(TREASURIES_URL, headers={"User-Agent": "BTCSeer/1.0"}) as resp:
                if resp.status != 200:
                    logger.warning(f"BTCTreasuries HTTP {resp.status}")
                    return []
                html = await resp.text()
        except Exception as e:
            logger.error(f"BTCTreasuries fetch error: {e}")
            return []

        holdings = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table")
            if not table:
                logger.warning("BTCTreasuries: no table found in HTML")
                return []

            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                try:
                    company_name = cells[0].get_text(strip=True)
                    ticker = cells[1].get_text(strip=True) if len(cells) > 1 else None
                    country = cells[2].get_text(strip=True) if len(cells) > 2 else None

                    # Parse BTC amount (remove commas)
                    btc_text = cells[3].get_text(strip=True).replace(",", "").replace(" ", "")
                    total_btc = float(btc_text) if btc_text else 0

                    if not company_name or total_btc <= 0:
                        continue

                    holdings.append({
                        "company_name": company_name,
                        "ticker": ticker or None,
                        "country": country or None,
                        "total_btc": total_btc,
                    })
                except (ValueError, IndexError):
                    continue

        except Exception as e:
            logger.error(f"BTCTreasuries parse error: {e}")

        return holdings

    async def _store_and_detect_changes(self, holdings: list[dict]) -> int:
        """Store snapshots and detect significant changes (>100 BTC delta)."""
        import hashlib

        changes = 0
        now = datetime.utcnow()

        async with async_session() as session:
            for h in holdings:
                company = h["company_name"]
                total_btc = h["total_btc"]

                # Store snapshot
                holding = InstitutionalHolding(
                    company_name=company,
                    ticker=h.get("ticker"),
                    country=h.get("country"),
                    total_btc=total_btc,
                    source="bitcointreasuries",
                    snapshot_date=now,
                )
                session.add(holding)

                # Detect changes vs last known snapshot
                prev_btc = self._last_snapshot.get(company)
                if prev_btc is not None:
                    delta = total_btc - prev_btc
                    if abs(delta) >= 100:
                        changes += 1
                        # Create whale transaction for significant change
                        direction = "exchange_out" if delta > 0 else "exchange_in"
                        seed = f"treasuries_{company}_{now.strftime('%Y%m%d')}"
                        tx_hash = hashlib.sha256(seed.encode()).hexdigest()[:64]

                        existing = await session.execute(
                            select(WhaleTransaction.id).where(WhaleTransaction.tx_hash == tx_hash)
                        )
                        if existing.scalar_one_or_none() is None:
                            severity = 10 if abs(delta) >= 10000 else 9 if abs(delta) >= 5000 else 8 if abs(delta) >= 2000 else 7 if abs(delta) >= 1000 else 6

                            whale_tx = WhaleTransaction(
                                tx_hash=tx_hash,
                                timestamp=now,
                                amount_btc=abs(delta),
                                direction=direction,
                                from_entity=company,
                                to_entity=company,
                                entity_name=company,
                                entity_type="institution",
                                entity_wallet="treasury",
                                severity=severity,
                                source="bitcointreasuries",
                            )
                            session.add(whale_tx)
                            logger.info(f"BTCTreasuries: {company} changed by {delta:+,.0f} BTC")

                self._last_snapshot[company] = total_btc

            await session.commit()

        return changes


# Module-level instance
btc_treasuries_collector = BTCTreasuriesCollector()


async def scrape_btc_treasuries():
    """Scheduler entry point for BitcoinTreasuries scraping."""
    try:
        result = await btc_treasuries_collector.collect()
        logger.info(f"BTCTreasuries scrape done: {result.get('count', 0)} companies, {result.get('changes', 0)} changes")
    except Exception as e:
        logger.error(f"BTCTreasuries scrape failed: {e}", exc_info=True)
