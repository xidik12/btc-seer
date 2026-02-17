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

    # ── Russian crypto news ──
    "bits_media_ru": "https://bits.media/rss2/",
    "forklog_ru": "https://forklog.com/feed/",
    "coinspot_ru": "https://coinspot.io/feed/",
    "google_news_btc_ru": "https://news.google.com/rss/search?q=bitcoin+OR+%D0%B1%D0%B8%D1%82%D0%BA%D0%BE%D0%B8%D0%BD+OR+%D0%BA%D1%80%D0%B8%D0%BF%D1%82%D0%BE&hl=ru&gl=RU&ceid=RU:ru",
    "google_news_rbc_ru": "https://news.google.com/rss/search?q=site:rbc.ru+%D0%B1%D0%B8%D1%82%D0%BA%D0%BE%D0%B8%D0%BD+OR+%D0%BA%D1%80%D0%B8%D0%BF%D1%82%D0%BE%D0%B2%D0%B0%D0%BB%D1%8E%D1%82%D0%B0&hl=ru&gl=RU&ceid=RU:ru",

    # ── Chinese crypto news ──
    "8btc_cn": "https://www.8btc.com/feed",
    "google_news_btc_cn": "https://news.google.com/rss/search?q=%E6%AF%94%E7%89%B9%E5%B8%81+OR+%E5%8A%A0%E5%AF%86%E8%B4%A7%E5%B8%81+OR+bitcoin&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # ── Spanish crypto news ──
    "criptonoticias_es": "https://www.criptonoticias.com/feed/",
    "beincrypto_es": "https://es.beincrypto.com/feed/",
    "cointelegraph_es": "https://es.cointelegraph.com/rss",
    "diariobitcoin_es": "https://www.diariobitcoin.com/feed/",
    "google_news_btc_es": "https://news.google.com/rss/search?q=bitcoin+OR+criptomoneda+OR+cripto&hl=es&gl=ES&ceid=ES:es",

    # ── Arabic crypto news ──
    "cointelegraph_ar": "https://ar.cointelegraph.com/rss",
    "google_news_btc_ar": "https://news.google.com/rss/search?q=%D8%A8%D9%8A%D8%AA%D9%83%D9%88%D9%8A%D9%86+OR+%D8%B9%D9%85%D9%84%D8%A9+%D8%B1%D9%82%D9%85%D9%8A%D8%A9+OR+bitcoin&hl=ar&gl=AE&ceid=AE:ar",
    "google_news_saudi_btc": "https://news.google.com/rss/search?q=%D8%A8%D9%8A%D8%AA%D9%83%D9%88%D9%8A%D9%86+OR+%D8%A7%D9%84%D8%B3%D8%B9%D9%88%D8%AF%D9%8A%D8%A9+%D9%83%D8%B1%D9%8A%D8%A8%D8%AA%D9%88+OR+bitcoin+saudi&hl=ar&gl=SA&ceid=SA:ar",

    # ── Japanese crypto news ──
    "cointelegraph_jp": "https://jp.cointelegraph.com/rss",
    "google_news_btc_jp": "https://news.google.com/rss/search?q=%E3%83%93%E3%83%83%E3%83%88%E3%82%B3%E3%82%A4%E3%83%B3+OR+%E4%BB%AE%E6%83%B3%E9%80%9A%E8%B2%A8+OR+bitcoin&hl=ja&gl=JP&ceid=JP:ja",

    # ── Korean crypto news ──
    "google_news_btc_kr": "https://news.google.com/rss/search?q=%EB%B9%84%ED%8A%B8%EC%BD%94%EC%9D%B8+OR+%EC%95%94%ED%98%B8%ED%99%94%ED%8F%90+OR+bitcoin&hl=ko&gl=KR&ceid=KR:ko",

    # ── Turkish crypto news ──
    "cointelegraph_tr": "https://tr.cointelegraph.com/rss",
    "google_news_btc_tr": "https://news.google.com/rss/search?q=bitcoin+OR+kripto+para+OR+kripto&hl=tr&gl=TR&ceid=TR:tr",

    # ── Portuguese / Brazilian crypto news ──
    "cointelegraph_br": "https://br.cointelegraph.com/rss",
    "beincrypto_br": "https://br.beincrypto.com/feed/",
    "google_news_btc_br": "https://news.google.com/rss/search?q=bitcoin+OR+criptomoeda+OR+cripto&hl=pt-BR&gl=BR&ceid=BR:pt-419",

    # ── Hindi / Indian crypto news ──
    "google_news_btc_in": "https://news.google.com/rss/search?q=bitcoin+OR+%E0%A4%AC%E0%A4%BF%E0%A4%9F%E0%A4%95%E0%A5%89%E0%A4%87%E0%A4%A8+OR+crypto+india&hl=hi&gl=IN&ceid=IN:hi",

    # ── Italian crypto news ──
    "cointelegraph_it": "https://it.cointelegraph.com/rss",

    # ── German crypto news ──
    "cointelegraph_de": "https://de.cointelegraph.com/rss",

    # ── Country adoption / sovereign BTC (English, multi-region) ──
    "google_news_btc_reserve": "https://news.google.com/rss/search?q=bitcoin+reserve+OR+strategic+bitcoin+OR+sovereign+bitcoin+OR+country+bitcoin&hl=en-US&gl=US&ceid=US:en",
    "google_news_mideast_btc": "https://news.google.com/rss/search?q=bitcoin+OR+crypto+saudi+OR+uae+OR+qatar+OR+dubai+OR+bahrain+OR+israel&hl=en-US&gl=US&ceid=US:en",
}

# Map feed source names to language codes
FEED_LANGUAGE_HINTS = {
    # Russian
    "bits_media_ru": "ru",
    "forklog_ru": "ru",
    "coinspot_ru": "ru",
    "google_news_btc_ru": "ru",
    "google_news_rbc_ru": "ru",
    # Chinese
    "8btc_cn": "zh-cn",
    "google_news_btc_cn": "zh-cn",
    # Spanish
    "criptonoticias_es": "es",
    "beincrypto_es": "es",
    "cointelegraph_es": "es",
    "diariobitcoin_es": "es",
    "google_news_btc_es": "es",
    # Arabic
    "cointelegraph_ar": "ar",
    "google_news_btc_ar": "ar",
    "google_news_saudi_btc": "ar",
    # Japanese
    "cointelegraph_jp": "ja",
    "google_news_btc_jp": "ja",
    # Korean
    "google_news_btc_kr": "ko",
    # Turkish
    "cointelegraph_tr": "tr",
    "google_news_btc_tr": "tr",
    # Portuguese
    "cointelegraph_br": "pt",
    "beincrypto_br": "pt",
    "google_news_btc_br": "pt",
    # Hindi
    "google_news_btc_in": "hi",
    # Italian
    "cointelegraph_it": "it",
    # German
    "cointelegraph_de": "de",
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

                lang_hint = FEED_LANGUAGE_HINTS.get(source)

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
                        "language": lang_hint,
                    })

            except Exception as e:
                logger.debug(f"Error parsing RSS feed {source}: {e}")

        return all_news
