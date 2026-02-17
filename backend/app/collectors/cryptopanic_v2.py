import logging
from datetime import datetime, timedelta

from app.collectors.base import BaseCollector
from app.config import settings
from app.database import async_session, News

logger = logging.getLogger(__name__)

CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/"

# Coin filter -- BTC plus major alts
CURRENCIES = "BTC,ETH,SOL"


class CryptoPanicV2Collector(BaseCollector):
    """Collects coin-specific crypto news from CryptoPanic API with community sentiment.

    Unlike the existing NewsCollector's CryptoPanic integration (BTC-only, important filter),
    this collector:
    - Fetches news for BTC, ETH, and SOL simultaneously
    - Extracts community vote sentiment (bullish/bearish/important/toxic counts)
    - Does NOT filter by 'important' -- captures all news for broader sentiment signal
    - Stores per-coin data using the coin_id field on News table

    Requires: settings.cryptopanic_api_key
    """

    # Map CryptoPanic currency codes to our internal coin IDs
    CURRENCY_TO_COIN_ID = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }

    async def collect(self) -> dict:
        """Fetch latest news for BTC, ETH, SOL from CryptoPanic with sentiment votes."""
        if not settings.cryptopanic_api_key:
            logger.debug("CryptoPanicV2: API key not set, skipping")
            return {"news": [], "count": 0}

        params = {
            "auth_token": settings.cryptopanic_api_key,
            "currencies": CURRENCIES,
            "kind": "news",
            "public": "true",
        }

        data = await self.fetch_json(CRYPTOPANIC_API_URL, params=params)
        if not data or "results" not in data:
            logger.warning("CryptoPanicV2: no results from API")
            return {"news": [], "count": 0}

        news_items: list[dict] = []

        for item in data["results"]:
            title = item.get("title", "").strip()
            if not title:
                continue

            url = item.get("url", "")
            published_at = item.get("published_at", "")
            source_info = item.get("source", {})
            source_name = source_info.get("title", "cryptopanic") if isinstance(source_info, dict) else "cryptopanic"

            # Extract community votes
            votes = item.get("votes", {})
            positive = votes.get("positive", 0)
            negative = votes.get("negative", 0)
            important = votes.get("important", 0)
            liked = votes.get("liked", 0)
            disliked = votes.get("disliked", 0)
            toxic = votes.get("toxic", 0)

            # Compute sentiment score from votes (-1 to +1)
            bullish_weight = positive + liked
            bearish_weight = negative + disliked + toxic
            total_votes = bullish_weight + bearish_weight + important
            if total_votes > 0:
                sentiment_score = (bullish_weight - bearish_weight) / total_votes
            else:
                sentiment_score = 0.0

            # Determine raw sentiment label
            if sentiment_score > 0.2:
                raw_sentiment = "bullish"
            elif sentiment_score < -0.2:
                raw_sentiment = "bearish"
            else:
                raw_sentiment = "neutral"

            # Extract associated currencies to map to coin_id
            currencies = item.get("currencies", [])
            coin_ids = []
            if currencies:
                for curr in currencies:
                    code = curr.get("code", "")
                    cid = self.CURRENCY_TO_COIN_ID.get(code)
                    if cid:
                        coin_ids.append(cid)

            # If no recognized currency, default to "bitcoin"
            if not coin_ids:
                coin_ids = ["bitcoin"]

            news_items.append({
                "title": title,
                "url": url,
                "published_at": published_at,
                "source": f"cryptopanic_{source_name}",
                "sentiment_score": round(sentiment_score, 4),
                "raw_sentiment": raw_sentiment,
                "coin_ids": coin_ids,
                "votes": {
                    "positive": positive,
                    "negative": negative,
                    "important": important,
                    "liked": liked,
                    "disliked": disliked,
                    "toxic": toxic,
                },
            })

        logger.info(f"CryptoPanicV2: fetched {len(news_items)} news items for {CURRENCIES}")
        return {"news": news_items, "count": len(news_items)}


async def collect_cryptopanic_v2():
    """Scheduled job: collect multi-coin CryptoPanic news every 5 minutes.

    Deduplicates by title within a 24-hour window to avoid storing
    the same headline multiple times.
    """
    collector = CryptoPanicV2Collector()
    try:
        result = await collector.collect()
        news_items = result.get("news", [])

        if not news_items:
            return

        # Load existing titles from last 24h for deduplication
        from sqlalchemy import select

        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=24)
            existing_result = await session.execute(
                select(News.title)
                .where(News.timestamp >= since)
                .where(News.source.like("cryptopanic_%"))
            )
            existing_titles = {row[0].lower().strip() for row in existing_result.all()}

        # Store new items
        async with async_session() as session:
            stored = 0
            for item in news_items:
                title = item["title"]
                if title.lower().strip() in existing_titles:
                    continue

                # Parse published_at timestamp
                published_at = item.get("published_at", "")
                if published_at:
                    try:
                        # CryptoPanic uses ISO format: 2026-02-17T12:34:56Z
                        ts = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        ts = ts.replace(tzinfo=None)  # Store as naive UTC
                    except (ValueError, TypeError):
                        ts = datetime.utcnow()
                else:
                    ts = datetime.utcnow()

                # Create one News row per coin_id
                for coin_id in item.get("coin_ids", ["bitcoin"]):
                    news_row = News(
                        timestamp=ts,
                        source=item["source"],
                        title=title,
                        url=item.get("url"),
                        sentiment_score=item["sentiment_score"],
                        raw_sentiment=item["raw_sentiment"],
                        language="en",
                        coin_id=coin_id,
                    )
                    session.add(news_row)

                stored += 1
                existing_titles.add(title.lower().strip())

            await session.commit()

        if stored:
            logger.info(f"CryptoPanicV2: stored {stored} new news items")

    except Exception as e:
        logger.error(f"CryptoPanicV2 collection error: {e}")
    finally:
        await collector.close()
