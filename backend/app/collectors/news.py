import logging
from datetime import datetime

import aiohttp
import feedparser

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# RSS / Atom feeds — crypto-native + mainstream financial press
# ──────────────────────────────────────────────────────────────
RSS_FEEDS = {
    # ── Crypto-native outlets ──
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "bitcoin_magazine": "https://bitcoinmagazine.com/feed",
    "theblock": "https://www.theblock.co/rss.xml",
    "decrypt": "https://decrypt.co/feed",
    "newsbtc": "https://www.newsbtc.com/feed/",
    "bitcoinist": "https://bitcoinist.com/feed/",
    "cryptoslate": "https://cryptoslate.com/feed/",
    "utoday": "https://u.today/rss",
    "beincrypto": "https://beincrypto.com/feed/",
    "ambcrypto": "https://ambcrypto.com/feed/",
    "cryptonews": "https://cryptonews.com/news/feed/",
    "dailycoin": "https://dailycoin.com/feed/",
    "cryptopotato": "https://cryptopotato.com/feed/",
    "coingape": "https://coingape.com/feed/",
    "blockonomi": "https://blockonomi.com/feed/",
    "cryptobriefing": "https://cryptobriefing.com/feed/",
    "protos": "https://protos.com/feed/",
    "watcherguru": "https://watcher.guru/news/feed",
    "binance_blog": "https://www.binance.com/en/feed/rss",

    # ── Mainstream finance (crypto coverage) ──
    "google_news_btc": "https://news.google.com/rss/search?q=bitcoin+OR+BTC+OR+crypto&hl=en-US&gl=US&ceid=US:en",
    "google_news_macro": "https://news.google.com/rss/search?q=federal+reserve+OR+interest+rate+OR+inflation+OR+tariff+crypto&hl=en-US&gl=US&ceid=US:en",
    "yahoo_crypto": "https://finance.yahoo.com/news/topic/crypto-news/.rss",
    "cnbc_crypto": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=33002080",

    # ── Bitcoin-specific feeds ──
    "bitcoin_optech": "https://bitcoinops.org/feed.xml",

    # ── Politics, war, geopolitics ──
    "google_news_war": "https://news.google.com/rss/search?q=war+OR+conflict+OR+military+OR+sanctions+bitcoin+OR+crypto&hl=en-US&gl=US&ceid=US:en",
    "google_news_politics": "https://news.google.com/rss/search?q=congress+OR+senate+OR+regulation+cryptocurrency+OR+bitcoin&hl=en-US&gl=US&ceid=US:en",
    "google_news_tariff": "https://news.google.com/rss/search?q=tariff+OR+trade+war+OR+sanctions+economy&hl=en-US&gl=US&ceid=US:en",

    # ── Central banks & monetary policy ──
    "google_news_fed": "https://news.google.com/rss/search?q=federal+reserve+OR+rate+decision+OR+FOMC+OR+powell&hl=en-US&gl=US&ceid=US:en",

    # ── Stock market & corporate ──
    "google_news_stocks": "https://news.google.com/rss/search?q=stock+market+OR+S%26P+500+OR+nasdaq+crash+OR+rally&hl=en-US&gl=US&ceid=US:en",
    "google_news_tech": "https://news.google.com/rss/search?q=tesla+OR+apple+OR+nvidia+earnings+OR+stock&hl=en-US&gl=US&ceid=US:en",

    # ── Financial news outlets ──
    "reuters_business": "https://news.google.com/rss/search?q=site:reuters.com+bitcoin+OR+crypto+OR+federal+reserve&hl=en-US&gl=US&ceid=US:en",
    "ft_crypto": "https://news.google.com/rss/search?q=site:ft.com+bitcoin+OR+cryptocurrency+OR+digital+asset&hl=en-US&gl=US&ceid=US:en",
    "bloomberg_crypto": "https://news.google.com/rss/search?q=site:bloomberg.com+bitcoin+OR+crypto+OR+stablecoin&hl=en-US&gl=US&ceid=US:en",
}

CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"


class NewsCollector(BaseCollector):
    """Collects crypto news from CryptoPanic API and 25+ RSS feeds."""

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
        """Parse RSS feeds for crypto news — all sources in parallel-ish loop."""
        all_news = []
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BTCOracle/1.0; +https://btc-oracle.app)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

        for source, url in RSS_FEEDS.items():
            try:
                session = await self.get_session()
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status != 200:
                        logger.debug(f"RSS {source} returned HTTP {resp.status}")
                        continue
                    content = await resp.text()

                feed = feedparser.parse(content)

                for entry in feed.entries[:15]:  # Last 15 per source
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
                        "sentiment_score": None,
                        "raw_sentiment": None,
                    })

            except Exception as e:
                logger.debug(f"Error parsing RSS feed {source}: {e}")

        return all_news
