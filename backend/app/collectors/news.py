import logging
from datetime import datetime

import feedparser

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "bitcoin_magazine": "https://bitcoinmagazine.com/feed",
    "google_news_btc": "https://news.google.com/rss/search?q=bitcoin+OR+BTC+OR+crypto&hl=en-US&gl=US&ceid=US:en",
}

CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"


class NewsCollector(BaseCollector):
    """Collects crypto news from CryptoPanic API and RSS feeds."""

    async def collect(self) -> dict:
        """Collect news from all sources."""
        cryptopanic_news = await self._get_cryptopanic()
        rss_news = await self._get_rss_feeds()

        all_news = []
        if cryptopanic_news:
            all_news.extend(cryptopanic_news)
        if rss_news:
            all_news.extend(rss_news)

        return {
            "news": all_news,
            "count": len(all_news),
            "timestamp": self.now().isoformat(),
        }

    async def _get_cryptopanic(self) -> list[dict] | None:
        """Get news from CryptoPanic API."""
        if not settings.cryptopanic_api_key:
            logger.debug("CryptoPanic API key not set, skipping")
            return None

        data = await self.fetch_json(
            CRYPTOPANIC_URL,
            params={
                "auth_token": settings.cryptopanic_api_key,
                "currencies": "BTC",
                "filter": "important",
                "public": "true",
            },
        )

        if not data or "results" not in data:
            return None

        news = []
        for item in data["results"]:
            votes = item.get("votes", {})
            positive = votes.get("positive", 0)
            negative = votes.get("negative", 0)
            total = positive + negative
            sentiment = (positive - negative) / total if total > 0 else 0

            news.append({
                "source": "cryptopanic",
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "published": item.get("published_at", ""),
                "sentiment_score": sentiment,
                "raw_sentiment": item.get("metadata", {}).get("sentiment"),
            })

        return news

    async def _get_rss_feeds(self) -> list[dict]:
        """Parse RSS feeds for crypto news."""
        all_news = []

        for source, url in RSS_FEEDS.items():
            try:
                session = await self.get_session()
                async with session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    content = await resp.text()

                feed = feedparser.parse(content)

                for entry in feed.entries[:10]:  # Last 10 per source
                    published = ""
                    if hasattr(entry, "published"):
                        published = entry.published
                    elif hasattr(entry, "updated"):
                        published = entry.updated

                    all_news.append({
                        "source": source,
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "published": published,
                        "sentiment_score": None,  # Will be scored by sentiment analyzer
                        "raw_sentiment": None,
                    })

            except Exception as e:
                logger.error(f"Error parsing RSS feed {source}: {e}")

        return all_news
