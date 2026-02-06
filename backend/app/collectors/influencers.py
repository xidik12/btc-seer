import logging
from datetime import datetime
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
# We monitor their Twitter/X feeds via Nitter RSS (free, no API limits)
# ══════════════════════════════════════════════════════════════════════════════

INFLUENCERS = {
    # ── CEOs & Company Leaders ──
    "elonmusk": {
        "name": "Elon Musk",
        "role": "Tesla/SpaceX CEO",
        "category": "ceo",
        "weight": 10,  # Highest impact
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
    "JayClaytonCBDC": {
        "name": "Jay Clayton",
        "role": "Former SEC Chair",
        "category": "regulator",
        "weight": 5,
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
    "WhalePanda": {
        "name": "Whale Panda",
        "role": "Crypto Analyst",
        "category": "analyst",
        "weight": 5,
    },
    "CryptoCobain": {
        "name": "Crypto Cobain",
        "role": "Trader & Analyst",
        "category": "analyst",
        "weight": 5,
    },
    "TheMoonCarl": {
        "name": "The Moon",
        "role": "Crypto YouTuber",
        "category": "analyst",
        "weight": 4,
    },

    # ── Developers & Protocol Leaders ──
    "VitalikButerin": {
        "name": "Vitalik Buterin",
        "role": "Ethereum Co-Founder",
        "category": "developer",
        "weight": 8,
    },
    "aeyakovenko": {
        "name": "Anatoly Yakovenko",
        "role": "Solana Co-Founder",
        "category": "developer",
        "weight": 6,
    },
    "gavinandresen": {
        "name": "Gavin Andresen",
        "role": "Bitcoin Core Dev",
        "category": "developer",
        "weight": 5,
    },

    # ── Economists & Macro Analysts ──
    "PeterSchiff": {
        "name": "Peter Schiff",
        "role": "Economist (BTC Critic)",
        "category": "economist",
        "weight": 5,  # Contrarian view
    },
    "LynAldenContact": {
        "name": "Lyn Alden",
        "role": "Investment Strategist",
        "category": "analyst",
        "weight": 7,
    },
}

# Nitter instances (Twitter mirrors with RSS support)
# These rotate if one goes down
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.net",
]


class InfluencerCollector(BaseCollector):
    """Monitors Twitter/X feeds of influential crypto people via Nitter RSS.

    Tracks tweets about Bitcoin, crypto, regulations, macro economics from
    key figures who move markets. Sentiment and influence weighting applied.
    """

    def __init__(self):
        super().__init__()
        self.nitter_instance = NITTER_INSTANCES[0]
        self.instance_index = 0

    async def collect(self) -> dict:
        """Collect latest tweets from all influential people."""
        all_tweets = []
        failed_users = []

        for username, info in INFLUENCERS.items():
            tweets = await self._get_user_tweets(username, info)
            if tweets:
                all_tweets.extend(tweets)
            else:
                failed_users.append(username)

        # Rotate Nitter instance if many failures
        if len(failed_users) > len(INFLUENCERS) * 0.3:
            self._rotate_nitter_instance()
            logger.warning(f"Rotated Nitter instance to {self.nitter_instance}")

        return {
            "tweets": all_tweets,
            "count": len(all_tweets),
            "failed_users": failed_users,
            "timestamp": self.now().isoformat(),
        }

    async def _get_user_tweets(self, username: str, info: dict) -> list[dict] | None:
        """Get recent tweets from a user via Nitter RSS."""
        try:
            # Nitter RSS format: https://nitter.instance/username/rss
            rss_url = f"{self.nitter_instance}/{username}/rss"

            session = await self.get_session()
            async with session.get(rss_url, timeout=10) as resp:
                if resp.status != 200:
                    logger.debug(f"Nitter {resp.status} for @{username}")
                    return None

                content = await resp.text()

            # Parse RSS feed
            feed = feedparser.parse(content)

            tweets = []
            for entry in feed.entries[:5]:  # Last 5 tweets per user
                # Extract tweet text (Nitter puts it in title)
                text = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")

                # Filter: only tweets mentioning crypto-related keywords
                crypto_keywords = [
                    "bitcoin", "btc", "crypto", "ethereum", "eth",
                    "regulation", "sec", "fed", "inflation", "interest",
                    "market", "price", "tariff", "economy"
                ]
                text_lower = text.lower()
                is_relevant = any(kw in text_lower for kw in crypto_keywords)

                if is_relevant:
                    tweets.append({
                        "source": f"twitter_{username}",
                        "influencer": info["name"],
                        "username": username,
                        "role": info["role"],
                        "category": info["category"],
                        "weight": info["weight"],
                        "text": text,
                        "url": link,
                        "published": published,
                        "sentiment_score": None,  # Will be scored
                    })

            return tweets

        except Exception as e:
            logger.debug(f"Error fetching @{username}: {e}")
            return None

    def _rotate_nitter_instance(self):
        """Rotate to next Nitter instance if current one fails."""
        self.instance_index = (self.instance_index + 1) % len(NITTER_INSTANCES)
        self.nitter_instance = NITTER_INSTANCES[self.instance_index]
