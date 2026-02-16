import logging
import re
from datetime import datetime
import aiohttp
import feedparser

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# INFLUENTIAL PEOPLE WHO AFFECT BTC & CRYPTO PRICES
# ══════════════════════════════════════════════════════════════════════════════
#
# Categories:
#   1. CEOs & Company Leaders
#   2. Investors & Fund Managers
#   3. Government & Regulators
#   4. Crypto Analysts & Educators
#   5. Developers & Protocol Leaders
#
# Since Nitter is dead, we use multiple alternative sources:
#   - RSS feeds from aggregators that track crypto influencer activity
#   - Google News filtered for specific influencer names
#   - CryptoQuant, Santiment, Glassnode social feeds
#   - Crypto-specific social monitoring RSS feeds
# ══════════════════════════════════════════════════════════════════════════════

INFLUENCERS = {
    # ── CEOs & Company Leaders ──
    "elonmusk": {
        "name": "Elon Musk",
        "role": "Tesla/SpaceX CEO",
        "category": "ceo",
        "weight": 10,
    },
    "saylor": {
        "name": "Michael Saylor",
        "role": "MicroStrategy Chairman",
        "category": "ceo",
        "weight": 9,
    },
    "brian_armstrong": {
        "name": "Brian Armstrong",
        "role": "Coinbase CEO",
        "category": "ceo",
        "weight": 8,
    },
    "cz_binance": {
        "name": "CZ (Changpeng Zhao)",
        "role": "Binance Founder",
        "category": "ceo",
        "weight": 8,
    },
    "jack": {
        "name": "Jack Dorsey",
        "role": "Block/Square CEO",
        "category": "ceo",
        "weight": 7,
    },

    # ── Investors & Fund Managers ──
    "cathiedwood": {
        "name": "Cathie Wood",
        "role": "ARK Invest CEO",
        "category": "investor",
        "weight": 8,
    },
    "APompliano": {
        "name": "Anthony Pompliano",
        "role": "Investor & Podcaster",
        "category": "investor",
        "weight": 7,
    },
    "RaoulGMI": {
        "name": "Raoul Pal",
        "role": "Real Vision CEO",
        "category": "investor",
        "weight": 7,
    },
    "BarrySilbert": {
        "name": "Barry Silbert",
        "role": "DCG Founder",
        "category": "investor",
        "weight": 6,
    },
    "novogratz": {
        "name": "Mike Novogratz",
        "role": "Galaxy Digital CEO",
        "category": "investor",
        "weight": 6,
    },

    # ── Government & Regulators ──
    "realDonaldTrump": {
        "name": "Donald Trump",
        "role": "US President",
        "category": "government",
        "weight": 10,
    },
    "GaryGensler": {
        "name": "Gary Gensler",
        "role": "SEC Chairman",
        "category": "regulator",
        "weight": 9,
    },
    "federalreserve": {
        "name": "Federal Reserve",
        "role": "US Central Bank",
        "category": "government",
        "weight": 9,
    },

    # ── Crypto Analysts & Educators ──
    "maxkeiser": {
        "name": "Max Keiser",
        "role": "Bitcoin Analyst",
        "category": "analyst",
        "weight": 6,
    },
    "santimentfeed": {
        "name": "Santiment",
        "role": "Crypto Analytics",
        "category": "analyst",
        "weight": 6,
    },
    "DocumentingBTC": {
        "name": "Documenting Bitcoin",
        "role": "Bitcoin News Aggregator",
        "category": "analyst",
        "weight": 5,
    },

    # ── Developers & Protocol Leaders ──
    "VitalikButerin": {
        "name": "Vitalik Buterin",
        "role": "Ethereum Co-Founder",
        "category": "developer",
        "weight": 8,
    },

    # ── Economists & Macro Analysts ──
    "PeterSchiff": {
        "name": "Peter Schiff",
        "role": "Economist (BTC Critic)",
        "category": "analyst",
        "weight": 5,
    },
    "LynAldenContact": {
        "name": "Lyn Alden",
        "role": "Investment Strategist",
        "category": "analyst",
        "weight": 7,
    },
}

# Influencer name variants for matching in news titles
INFLUENCER_NAME_PATTERNS = {
    "Elon Musk": ("elonmusk", 10, "ceo"),
    "Musk": ("elonmusk", 10, "ceo"),
    "Michael Saylor": ("saylor", 9, "ceo"),
    "Saylor": ("saylor", 9, "ceo"),
    "MicroStrategy": ("saylor", 9, "ceo"),
    "Brian Armstrong": ("brian_armstrong", 8, "ceo"),
    "Coinbase CEO": ("brian_armstrong", 8, "ceo"),
    "CZ": ("cz_binance", 8, "ceo"),
    "Changpeng Zhao": ("cz_binance", 8, "ceo"),
    "Binance CEO": ("cz_binance", 8, "ceo"),
    "Jack Dorsey": ("jack", 7, "ceo"),
    "Cathie Wood": ("cathiedwood", 8, "investor"),
    "ARK Invest": ("cathiedwood", 8, "investor"),
    "Pompliano": ("APompliano", 7, "investor"),
    "Raoul Pal": ("RaoulGMI", 7, "investor"),
    "Barry Silbert": ("BarrySilbert", 6, "investor"),
    "Novogratz": ("novogratz", 6, "investor"),
    "Galaxy Digital": ("novogratz", 6, "investor"),
    "Trump": ("realDonaldTrump", 10, "government"),
    "Gensler": ("GaryGensler", 9, "regulator"),
    "SEC Chair": ("GaryGensler", 9, "regulator"),
    "Federal Reserve": ("federalreserve", 9, "government"),
    "Jerome Powell": ("federalreserve", 9, "government"),
    "Powell": ("federalreserve", 9, "government"),
    "Vitalik": ("VitalikButerin", 8, "developer"),
    "Buterin": ("VitalikButerin", 8, "developer"),
    "Peter Schiff": ("PeterSchiff", 5, "analyst"),
    "Lyn Alden": ("LynAldenContact", 7, "analyst"),
    "Max Keiser": ("maxkeiser", 6, "analyst"),
    "Larry Fink": ("blackrock", 9, "investor"),
    "BlackRock": ("blackrock", 9, "investor"),
    "Grayscale": ("grayscale", 7, "investor"),
}

# RSS feeds that aggregate crypto influencer activity / social signals
SOCIAL_SIGNAL_FEEDS = {
    # Crypto Twitter aggregators via Google News
    "influencer_btc": "https://news.google.com/rss/search?q=%22Elon+Musk%22+OR+%22Michael+Saylor%22+OR+%22CZ%22+OR+%22Cathie+Wood%22+bitcoin+OR+crypto&hl=en-US&gl=US&ceid=US:en",
    "influencer_macro": "https://news.google.com/rss/search?q=%22Trump%22+OR+%22Powell%22+OR+%22Gensler%22+OR+%22SEC%22+bitcoin+OR+crypto+OR+regulation&hl=en-US&gl=US&ceid=US:en",
    "influencer_dev": "https://news.google.com/rss/search?q=%22Vitalik+Buterin%22+OR+%22Jack+Dorsey%22+crypto+OR+bitcoin+OR+ethereum&hl=en-US&gl=US&ceid=US:en",
    "influencer_investor": "https://news.google.com/rss/search?q=%22BlackRock%22+OR+%22Larry+Fink%22+OR+%22Grayscale%22+OR+%22ARK+Invest%22+bitcoin+OR+crypto+OR+ETF&hl=en-US&gl=US&ceid=US:en",

    # Crypto social aggregators
    "whale_alert": "https://news.google.com/rss/search?q=%22whale+alert%22+OR+%22whale+transaction%22+bitcoin+OR+BTC&hl=en-US&gl=US&ceid=US:en",

    # Specific influencer news
    "saylor_news": "https://news.google.com/rss/search?q=%22MicroStrategy%22+OR+%22Michael+Saylor%22+bitcoin&hl=en-US&gl=US&ceid=US:en",

    # ── International crypto opinion feeds ──
    "influencer_ru": "https://news.google.com/rss/search?q=%D0%B1%D0%B8%D1%82%D0%BA%D0%BE%D0%B8%D0%BD+%D0%BF%D1%80%D0%BE%D0%B3%D0%BD%D0%BE%D0%B7+OR+%D0%BA%D1%80%D0%B8%D0%BF%D1%82%D0%BE+%D0%BC%D0%BD%D0%B5%D0%BD%D0%B8%D0%B5&hl=ru&gl=RU&ceid=RU:ru",
    "influencer_cn": "https://news.google.com/rss/search?q=%E6%AF%94%E7%89%B9%E5%B8%81+%E5%88%86%E6%9E%90+OR+%E5%8A%A0%E5%AF%86%E8%B4%A7%E5%B8%81+%E4%B8%93%E5%AE%B6&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    "influencer_es": "https://news.google.com/rss/search?q=bitcoin+prediccion+OR+criptomoneda+analisis+OR+cripto+opinion&hl=es&gl=ES&ceid=ES:es",
}

SOCIAL_FEED_LANGUAGE_HINTS = {
    "influencer_ru": "ru",
    "influencer_cn": "zh-cn",
    "influencer_es": "es",
}


class InfluencerCollector(BaseCollector):
    """Monitors crypto influencer activity via news RSS feeds.

    Since Nitter/Twitter RSS is dead, this collector uses Google News RSS
    filtered for specific influencer names and crypto keywords. It extracts
    mentions of key figures from headlines and attributes them properly.
    """

    async def collect(self) -> dict:
        """Collect latest influencer-related news and social signals."""
        all_tweets = []
        failed_feeds = []

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BTCOracle/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

        for feed_name, feed_url in SOCIAL_SIGNAL_FEEDS.items():
            try:
                session = await self.get_session()
                async with session.get(
                    feed_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        logger.debug(f"Social feed {feed_name} returned HTTP {resp.status}")
                        failed_feeds.append(feed_name)
                        continue
                    content = await resp.text()

                feed = feedparser.parse(content)

                lang_hint = SOCIAL_FEED_LANGUAGE_HINTS.get(feed_name)

                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    published = getattr(entry, "published", "") or getattr(entry, "updated", "")

                    if not title:
                        continue

                    # For non-English feeds, accept all entries (skip English keyword check)
                    if lang_hint:
                        # Use a generic influencer entry for international feeds
                        all_tweets.append({
                            "source": f"news_{feed_name}",
                            "influencer": f"intl_{lang_hint}",
                            "username": f"intl_{lang_hint}",
                            "role": "International Crypto News",
                            "category": "analyst",
                            "weight": 5,
                            "text": title,
                            "url": link,
                            "published": published,
                            "sentiment_score": None,
                            "language": lang_hint,
                        })
                        continue

                    # Match influencer names in the title (English feeds)
                    matched_influencer = self._match_influencer(title)
                    if not matched_influencer:
                        continue

                    username, info = matched_influencer

                    all_tweets.append({
                        "source": f"news_{feed_name}",
                        "influencer": info["name"],
                        "username": username,
                        "role": info["role"],
                        "category": info["category"],
                        "weight": info["weight"],
                        "text": title,
                        "url": link,
                        "published": published,
                        "sentiment_score": None,
                    })

            except Exception as e:
                logger.debug(f"Error fetching social feed {feed_name}: {e}")
                failed_feeds.append(feed_name)

        return {
            "tweets": all_tweets,
            "count": len(all_tweets),
            "failed_users": failed_feeds,
            "timestamp": self.now().isoformat(),
        }

    def _match_influencer(self, title: str) -> tuple | None:
        """Match an influencer name in a news title.

        Returns (username, info_dict) or None if no match.
        """
        title_lower = title.lower()

        # Must be crypto-related
        crypto_keywords = [
            "bitcoin", "btc", "crypto", "ethereum", "eth", "blockchain",
            "regulation", "sec", "fed", "inflation", "interest rate",
            "tariff", "economy", "etf", "stablecoin", "digital asset",
            "token", "defi", "mining", "halving", "bull", "bear",
        ]
        is_crypto = any(kw in title_lower for kw in crypto_keywords)
        if not is_crypto:
            return None

        # Try to match influencer names (longest match first to avoid false positives)
        for name_pattern, (username, weight, category) in sorted(
            INFLUENCER_NAME_PATTERNS.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        ):
            if name_pattern.lower() in title_lower:
                # Get full info from INFLUENCERS dict, or build from pattern
                info = INFLUENCERS.get(username, {
                    "name": name_pattern,
                    "role": category.title(),
                    "category": category,
                    "weight": weight,
                })
                return (username, info)

        return None
