import logging
import re
from datetime import datetime

from app.collectors.base import BaseCollector
from app.database import async_session, WhaleTransaction, InstitutionalHolding
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Known BTC treasury company CIKs
TREASURY_COMPANIES = {
    "0001050446": {"name": "Strategy Inc", "ticker": "MSTR"},
    "0001318605": {"name": "Tesla Inc", "ticker": "TSLA"},
    "0001507605": {"name": "Marathon Digital", "ticker": "MARA"},
    "0001167419": {"name": "Riot Platforms", "ticker": "RIOT"},
    "0001828937": {"name": "Hut 8 Corp", "ticker": "HUT"},
    "0001725134": {"name": "CleanSpark", "ticker": "CLSK"},
    "0001091818": {"name": "Coinbase", "ticker": "COIN"},
    "0001538978": {"name": "Metaplanet", "ticker": "METAP"},
    "0001946573": {"name": "Nakamoto Inc", "ticker": "NAKA"},
}

# Regex patterns for parsing 8-K filing text for BTC acquisition info
BTC_AMOUNT_PATTERNS = [
    re.compile(r'(?:acquired|purchased|bought)\s+(?:approximately\s+)?([0-9,]+(?:\.\d+)?)\s*(?:bitcoin|btc)', re.IGNORECASE),
    re.compile(r'([0-9,]+(?:\.\d+)?)\s*(?:bitcoin|btc)\s+(?:were|was)\s+(?:acquired|purchased)', re.IGNORECASE),
]

USD_AMOUNT_PATTERNS = [
    re.compile(r'(?:aggregate\s+)?(?:purchase\s+)?price\s+of\s+(?:approximately\s+)?\$([0-9,.]+)\s*(million|billion|m|b)', re.IGNORECASE),
    re.compile(r'\$([0-9,.]+)\s*(million|billion|m|b)\s+(?:in\s+)?(?:bitcoin|btc)', re.IGNORECASE),
]

EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filename}"

# SEC requires User-Agent header
SEC_HEADERS = {
    "User-Agent": "BTCSeer/1.0 (info@btcseer.com)",
    "Accept-Encoding": "gzip, deflate",
}


class SECEdgarCollector(BaseCollector):
    """Polls SEC EDGAR for 8-K filings from known BTC treasury companies."""

    def __init__(self):
        super().__init__()
        self._seen_accessions: set = set()

    async def collect(self) -> dict:
        """Check all treasury companies for new 8-K filings."""
        results = []

        for cik, company in TREASURY_COMPANIES.items():
            try:
                filings = await self._check_company_filings(cik, company)
                results.extend(filings)
            except Exception as e:
                logger.debug(f"SEC EDGAR error for {company['name']}: {e}")

        if results:
            await self._store_results(results)
            logger.info(f"SEC EDGAR: {len(results)} new institutional BTC events detected")

        return {"events": results, "count": len(results)}

    async def _check_company_filings(self, cik: str, company: dict) -> list[dict]:
        """Check a single company's recent filings for 8-K forms."""
        url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
        data = await self.fetch_json(url, headers=SEC_HEADERS)
        if not data:
            return []

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])

        events = []

        for i, form in enumerate(forms[:20]):  # Check last 20 filings
            if form != "8-K":
                continue

            accession = accessions[i] if i < len(accessions) else ""
            if not accession or accession in self._seen_accessions:
                continue

            # Only process filings from last 7 days
            filing_date = filing_dates[i] if i < len(filing_dates) else ""
            if filing_date:
                try:
                    fd = datetime.strptime(filing_date, "%Y-%m-%d")
                    if (datetime.utcnow() - fd).days > 7:
                        continue
                except ValueError:
                    pass

            self._seen_accessions.add(accession)

            # Try to fetch and parse the filing document
            primary_doc = primary_docs[i] if i < len(primary_docs) else ""
            if primary_doc:
                btc_info = await self._parse_filing(cik, accession, primary_doc)
                if btc_info:
                    events.append({
                        "company_name": company["name"],
                        "ticker": company["ticker"],
                        "cik": cik,
                        "accession": accession,
                        "filing_date": filing_date,
                        "btc_amount": btc_info.get("btc_amount"),
                        "usd_amount": btc_info.get("usd_amount"),
                    })

        return events

    async def _parse_filing(self, cik: str, accession: str, filename: str) -> dict | None:
        """Fetch and parse an 8-K filing for BTC purchase information."""
        clean_accession = accession.replace("-", "")
        url = EDGAR_FILING_URL.format(cik=cik.lstrip("0"), accession=clean_accession, filename=filename)

        try:
            session = await self.get_session()
            async with session.get(url, headers=SEC_HEADERS) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        # Search for BTC purchase amounts
        btc_amount = None
        for pattern in BTC_AMOUNT_PATTERNS:
            match = pattern.search(text)
            if match:
                btc_amount = float(match.group(1).replace(",", ""))
                break

        usd_amount = None
        for pattern in USD_AMOUNT_PATTERNS:
            match = pattern.search(text)
            if match:
                amount = float(match.group(1).replace(",", ""))
                multiplier = match.group(2).lower()
                if multiplier in ("billion", "b"):
                    usd_amount = amount * 1e9
                else:
                    usd_amount = amount * 1e6
                break

        if btc_amount or usd_amount:
            return {"btc_amount": btc_amount, "usd_amount": usd_amount}
        return None

    async def _store_results(self, events: list[dict]) -> None:
        """Store detected institutional BTC acquisitions as WhaleTransactions."""
        import hashlib

        async with async_session() as session:
            for event in events:
                # Create deterministic hash
                seed = f"sec_edgar_{event['accession']}_{event['company_name']}"
                tx_hash = hashlib.sha256(seed.encode()).hexdigest()[:64]

                existing = await session.execute(
                    select(WhaleTransaction.id).where(WhaleTransaction.tx_hash == tx_hash)
                )
                if existing.scalar_one_or_none() is not None:
                    continue

                btc_amount = event.get("btc_amount") or 0
                usd_amount = event.get("usd_amount") or 0

                # Estimate BTC from USD if we only have USD
                if not btc_amount and usd_amount:
                    btc_amount = usd_amount / 97000  # rough estimate

                if btc_amount < 10:
                    continue  # Skip tiny amounts

                severity = 10 if btc_amount >= 10000 else 9 if btc_amount >= 5000 else 8 if btc_amount >= 2000 else 7 if btc_amount >= 1000 else 6

                whale_tx = WhaleTransaction(
                    tx_hash=tx_hash,
                    timestamp=datetime.utcnow(),
                    amount_btc=btc_amount,
                    amount_usd=usd_amount or None,
                    direction="exchange_out",  # acquisition = bullish
                    from_entity=event["company_name"],
                    to_entity=event["company_name"],
                    entity_name=event["company_name"],
                    entity_type="institution",
                    entity_wallet="treasury",
                    severity=severity,
                    source="sec_edgar",
                )
                session.add(whale_tx)

            await session.commit()


# Module-level instance
sec_edgar_collector = SECEdgarCollector()


async def collect_sec_filings():
    """Scheduler entry point for SEC EDGAR collection."""
    try:
        result = await sec_edgar_collector.collect()
        logger.info(f"SEC EDGAR collection done: {result.get('count', 0)} events")
    except Exception as e:
        logger.error(f"SEC EDGAR collection failed: {e}", exc_info=True)
