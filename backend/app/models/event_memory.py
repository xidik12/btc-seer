"""Event Impact Memory — classifies news events and recalls historical price impact.

This module gives the prediction system a 'memory' of how past events
(war, politics, Fed decisions, hacks, ETF news, etc.) have affected BTC price,
so it can anticipate the impact of similar new events.
"""
import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# ── Event categories and their keyword mappings ──

EVENT_CATEGORIES = {
    "war_conflict": {
        "keywords": [
            "war", "invasion", "military", "missile", "strike", "bomb",
            "conflict", "troops", "army", "attack", "hostage", "ceasefire",
            "nato", "nuclear", "weapons", "sanctions military", "drone strike",
            "escalation", "tension", "geopolitical", "territorial",
        ],
        "severity_boost": 2,  # War events get +2 severity
    },
    "politics_regulation": {
        "keywords": [
            "regulation", "ban", "crackdown", "sec", "cftc", "congress",
            "senate", "legislation", "law", "executive order", "policy",
            "tax", "compliance", "kyc", "aml", "enforcement", "subpoena",
            "stablecoin bill", "framework", "gensler", "warren",
            "trump", "biden", "white house", "treasury department",
        ],
        "severity_boost": 1,
    },
    "monetary_policy": {
        "keywords": [
            "federal reserve", "fed", "interest rate", "rate hike", "rate cut",
            "fomc", "powell", "inflation", "cpi", "ppi", "employment",
            "jobs report", "nonfarm", "gdp", "recession", "quantitative",
            "tightening", "easing", "dovish", "hawkish", "yield curve",
            "debt ceiling", "treasury", "bond", "basis points",
        ],
        "severity_boost": 2,
    },
    "tariff_trade": {
        "keywords": [
            "tariff", "trade war", "import duty", "export ban", "trade deal",
            "sanctions", "embargo", "trade deficit", "customs", "wto",
            "retaliatory", "trade policy", "protectionism", "free trade",
        ],
        "severity_boost": 1,
    },
    "stock_market": {
        "keywords": [
            "s&p 500", "nasdaq", "dow jones", "stock market", "wall street",
            "equity", "stock crash", "correction", "bear market", "bull market",
            "earnings", "tech stocks", "magnificent 7", "ipo", "buyback",
            "market cap", "index", "futures", "options expiry",
        ],
        "severity_boost": 0,
    },
    "etf_institutional": {
        "keywords": [
            "etf", "bitcoin etf", "spot etf", "etf approval", "etf filing",
            "etf inflow", "etf outflow", "grayscale", "blackrock", "fidelity",
            "ark invest", "institutional", "custody", "asset manager",
            "fund", "investment vehicle", "ibit", "gbtc",
        ],
        "severity_boost": 2,
    },
    "exchange_hack": {
        "keywords": [
            "hack", "exploit", "breach", "stolen", "drained", "vulnerability",
            "rug pull", "scam", "phishing", "flash loan", "oracle attack",
            "bridge hack", "defi exploit", "funds stolen", "security incident",
        ],
        "severity_boost": 2,
    },
    "company_announcement": {
        "keywords": [
            "partnership", "acquisition", "merger", "launch", "listing",
            "delisting", "bankruptcy", "insolvency", "layoff", "restructuring",
            "revenue", "profit", "loss", "quarterly", "annual report",
            "tesla", "microstrategy", "coinbase", "binance", "kraken",
        ],
        "severity_boost": 0,
    },
    "whale_movement": {
        "keywords": [
            "whale", "large transfer", "whale alert", "dormant", "moved",
            "exchange deposit", "exchange withdrawal", "accumulation",
            "distribution", "on-chain", "wallet", "cold storage",
        ],
        "severity_boost": 1,
    },
    "technology": {
        "keywords": [
            "halving", "upgrade", "fork", "taproot", "lightning network",
            "layer 2", "protocol", "mining", "hash rate", "difficulty",
            "ordinals", "inscription", "brc-20", "runes", "segwit",
        ],
        "severity_boost": 1,
    },
    "macro_economic": {
        "keywords": [
            "dollar", "dxy", "gold", "oil", "commodity", "currency",
            "euro", "yen", "yuan", "emerging market", "sovereign debt",
            "banking crisis", "liquidity", "money supply", "m2",
            "real estate", "housing", "consumer confidence",
        ],
        "severity_boost": 0,
    },
}


class EventClassifier:
    """Classifies news headlines into event categories with severity scoring."""

    def classify(self, title: str, sentiment_score: float = 0.0) -> dict | None:
        """Classify a news headline into an event category.

        Returns None if the headline doesn't match any significant category.
        Returns dict with category, subcategory, keywords, severity.
        """
        title_lower = title.lower()

        best_category = None
        best_score = 0
        matched_keywords = []

        for category, config in EVENT_CATEGORIES.items():
            cat_keywords = []
            cat_score = 0

            for kw in config["keywords"]:
                # Use word boundary matching for short keywords to avoid
                # false positives like "war" in "rewards"
                if len(kw) <= 4:
                    if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
                        cat_keywords.append(kw)
                        cat_score += len(kw.split()) * 2
                else:
                    if kw in title_lower:
                        cat_keywords.append(kw)
                        cat_score += len(kw.split()) * 2

            if cat_score > best_score:
                best_score = cat_score
                best_category = category
                matched_keywords = cat_keywords

        if not best_category or best_score < 2:
            return None  # Not significant enough to track

        # Calculate severity (1-10)
        config = EVENT_CATEGORIES[best_category]
        severity = min(10, max(1,
            3  # base
            + config["severity_boost"]
            + len(matched_keywords)  # more keywords = more relevant
            + int(abs(sentiment_score) * 3)  # strong sentiment = more impactful
        ))

        return {
            "category": best_category,
            "subcategory": matched_keywords[0] if matched_keywords else None,
            "keywords": ",".join(matched_keywords),
            "severity": severity,
        }


class EventPatternMatcher:
    """Finds similar past events and returns their average price impact."""

    def find_similar_events(
        self,
        category: str,
        keywords: str,
        past_events: list[dict],
        min_similarity: float = 0.3,
    ) -> list[dict]:
        """Find past events in the same category with similar keywords."""
        current_kw_set = set(keywords.lower().split(",")) if keywords else set()
        similar = []

        for event in past_events:
            if event.get("category") != category:
                continue

            past_kw_set = set(
                (event.get("keywords") or "").lower().split(",")
            )

            # Jaccard similarity on keywords
            intersection = current_kw_set & past_kw_set
            union = current_kw_set | past_kw_set
            if not union:
                continue

            similarity = len(intersection) / len(union)
            if similarity >= min_similarity:
                event["similarity"] = similarity
                similar.append(event)

        # Sort by similarity (highest first)
        similar.sort(key=lambda x: -x.get("similarity", 0))
        return similar[:20]  # Top 20 most similar

    def get_expected_impact(self, similar_events: list[dict]) -> dict:
        """Calculate expected price impact from similar past events.

        Returns weighted average of historical impacts, with more similar
        events weighted higher.
        """
        if not similar_events:
            return {
                "expected_1h": 0.0,
                "expected_4h": 0.0,
                "expected_24h": 0.0,
                "confidence": 0.0,
                "sample_size": 0,
                "avg_sentiment_predictive": 0.5,
            }

        total_weight = 0.0
        weighted_1h = 0.0
        weighted_4h = 0.0
        weighted_24h = 0.0
        predictive_count = 0
        total_predictive = 0

        for event in similar_events:
            sim = event.get("similarity", 0.5)
            weight = sim * sim  # Quadratic weighting — very similar events matter more

            c1h = event.get("change_pct_1h")
            c4h = event.get("change_pct_4h")
            c24h = event.get("change_pct_24h")

            if c1h is not None:
                weighted_1h += c1h * weight
                total_weight += weight

            if c4h is not None:
                weighted_4h += c4h * weight

            if c24h is not None:
                weighted_24h += c24h * weight

            if event.get("sentiment_was_predictive") is not None:
                total_predictive += 1
                if event["sentiment_was_predictive"]:
                    predictive_count += 1

        if total_weight == 0:
            return {
                "expected_1h": 0.0,
                "expected_4h": 0.0,
                "expected_24h": 0.0,
                "confidence": 0.0,
                "sample_size": 0,
                "avg_sentiment_predictive": 0.5,
            }

        avg_1h = weighted_1h / total_weight
        avg_4h = weighted_4h / total_weight
        avg_24h = weighted_24h / total_weight

        # Confidence: more events + higher similarity = higher confidence
        confidence = min(1.0,
            (len(similar_events) / 10)  # More events = more confident
            * (sum(e.get("similarity", 0) for e in similar_events) / len(similar_events))  # Avg similarity
        )

        avg_predictive = (predictive_count / total_predictive) if total_predictive > 0 else 0.5

        return {
            "expected_1h": round(avg_1h, 4),
            "expected_4h": round(avg_4h, 4),
            "expected_24h": round(avg_24h, 4),
            "confidence": round(confidence, 4),
            "sample_size": len(similar_events),
            "avg_sentiment_predictive": round(avg_predictive, 4),
        }

    def get_category_stats(self, past_events: list[dict]) -> dict:
        """Get average impact stats per event category.

        Returns dict like: {"war_conflict": {"avg_1h": -0.5, "avg_24h": -2.1, "count": 15}, ...}
        """
        stats = {}

        for event in past_events:
            cat = event.get("category")
            if not cat:
                continue

            if cat not in stats:
                stats[cat] = {
                    "impacts_1h": [], "impacts_4h": [], "impacts_24h": [],
                    "count": 0
                }

            stats[cat]["count"] += 1
            if event.get("change_pct_1h") is not None:
                stats[cat]["impacts_1h"].append(event["change_pct_1h"])
            if event.get("change_pct_4h") is not None:
                stats[cat]["impacts_4h"].append(event["change_pct_4h"])
            if event.get("change_pct_24h") is not None:
                stats[cat]["impacts_24h"].append(event["change_pct_24h"])

        result = {}
        for cat, data in stats.items():
            result[cat] = {
                "count": data["count"],
                "avg_1h": round(sum(data["impacts_1h"]) / len(data["impacts_1h"]), 4) if data["impacts_1h"] else 0.0,
                "avg_4h": round(sum(data["impacts_4h"]) / len(data["impacts_4h"]), 4) if data["impacts_4h"] else 0.0,
                "avg_24h": round(sum(data["impacts_24h"]) / len(data["impacts_24h"]), 4) if data["impacts_24h"] else 0.0,
            }
        return result
