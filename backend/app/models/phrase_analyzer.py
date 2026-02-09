"""Phrase/Word Correlation Analyzer for BTC Seer.

Tokenizes news headlines into words, bigrams, and trigrams,
tracks each phrase's correlation with price changes,
and feeds top predictive phrases as features into the model.
"""
import logging
import re
from datetime import datetime, timedelta
from collections import Counter

from sqlalchemy import select, desc

from app.database import async_session, News, Price, NewsPriceCorrelation

logger = logging.getLogger(__name__)

# Common stop words to filter out
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "about", "it", "its",
    "and", "but", "or", "if", "this", "that", "these", "those", "what",
    "which", "who", "whom", "his", "her", "he", "she", "they", "them",
    "we", "you", "i", "me", "my", "your", "our", "their",
}


def tokenize_headline(text: str) -> dict:
    """Tokenize a headline into words, bigrams, and trigrams."""
    # Clean and lowercase
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = [w for w in text.split() if len(w) > 2 and w not in STOP_WORDS]

    result = {"words": words, "bigrams": [], "trigrams": []}

    if len(words) >= 2:
        result["bigrams"] = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    if len(words) >= 3:
        result["trigrams"] = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)]

    return result


async def analyze_news_phrases():
    """Analyze recent news headlines and correlate phrases with price moves.

    Runs hourly. For each headline from the last hour:
    1. Tokenize into words, bigrams, trigrams
    2. Look up actual price change 1h/4h/24h later
    3. Update running correlations in NewsPriceCorrelation table
    """
    try:
        async with async_session() as session:
            # Get news from 1-25 hours ago (need at least 1h to have price data)
            since = datetime.utcnow() - timedelta(hours=25)
            until = datetime.utcnow() - timedelta(hours=1)
            result = await session.execute(
                select(News)
                .where(News.timestamp >= since)
                .where(News.timestamp <= until)
                .order_by(desc(News.timestamp))
                .limit(200)
            )
            news_items = result.scalars().all()

        if not news_items:
            return

        # Process each headline
        phrase_impacts = {}  # phrase -> list of {change_1h, change_4h, change_24h}

        for news_item in news_items:
            tokens = tokenize_headline(news_item.title)

            # Get price at news time
            async with async_session() as session:
                price_at_news = await _get_closest_price(session, news_item.timestamp)
                if not price_at_news:
                    continue

                # Get prices at +1h, +4h, +24h
                changes = {}
                for tf, hours in [("1h", 1), ("4h", 4), ("24h", 24)]:
                    target_time = news_item.timestamp + timedelta(hours=hours)
                    if target_time > datetime.utcnow():
                        continue
                    future_price = await _get_closest_price(session, target_time)
                    if future_price:
                        changes[tf] = (future_price - price_at_news) / price_at_news * 100

                if not changes:
                    continue

            # Track all phrases
            all_phrases = (
                [(w, "word") for w in tokens["words"]]
                + [(b, "bigram") for b in tokens["bigrams"]]
                + [(t, "trigram") for t in tokens["trigrams"]]
            )

            for phrase, ptype in all_phrases:
                if phrase not in phrase_impacts:
                    phrase_impacts[phrase] = {"type": ptype, "changes": []}
                phrase_impacts[phrase]["changes"].append(changes)

        if not phrase_impacts:
            return

        # Update database
        updated = 0
        async with async_session() as session:
            for phrase, data in phrase_impacts.items():
                changes_list = data["changes"]
                if len(changes_list) < 2:
                    continue

                avg_1h = sum(c.get("1h", 0) for c in changes_list) / len(changes_list)
                avg_4h = sum(c.get("4h", 0) for c in changes_list) / len(changes_list)
                avg_24h = sum(c.get("24h", 0) for c in changes_list) / len(changes_list)
                bullish_ratio = sum(1 for c in changes_list if c.get("1h", 0) > 0) / len(changes_list)

                # Correlation score: how consistently does this phrase predict direction?
                correlation = abs(bullish_ratio - 0.5) * 2  # 0 = random, 1 = perfect predictor

                # Upsert
                result = await session.execute(
                    select(NewsPriceCorrelation).where(NewsPriceCorrelation.phrase == phrase)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Exponential moving average update
                    alpha = 0.3
                    existing.avg_change_1h = existing.avg_change_1h * (1 - alpha) + avg_1h * alpha
                    existing.avg_change_4h = existing.avg_change_4h * (1 - alpha) + avg_4h * alpha
                    existing.avg_change_24h = existing.avg_change_24h * (1 - alpha) + avg_24h * alpha
                    existing.bullish_ratio = existing.bullish_ratio * (1 - alpha) + bullish_ratio * alpha
                    existing.occurrences += len(changes_list)
                    existing.correlation_score = existing.correlation_score * (1 - alpha) + correlation * alpha
                    existing.last_seen = datetime.utcnow()
                else:
                    new_corr = NewsPriceCorrelation(
                        phrase=phrase,
                        phrase_type=data["type"],
                        occurrences=len(changes_list),
                        avg_change_1h=avg_1h,
                        avg_change_4h=avg_4h,
                        avg_change_24h=avg_24h,
                        bullish_ratio=bullish_ratio,
                        correlation_score=correlation,
                        last_seen=datetime.utcnow(),
                    )
                    session.add(new_corr)

                updated += 1

            await session.commit()

        logger.info(f"Phrase analyzer: processed {len(news_items)} headlines, updated {updated} phrases")

    except Exception as e:
        logger.error(f"Phrase analysis error: {e}", exc_info=True)


async def get_phrase_features(headlines: list[str]) -> dict:
    """Get phrase-based features for current headlines.

    Looks up each phrase in the correlation table and returns
    the strongest bullish/bearish signals as features.
    """
    try:
        all_phrases = set()
        for headline in headlines:
            tokens = tokenize_headline(headline)
            all_phrases.update(tokens["words"])
            all_phrases.update(tokens["bigrams"])
            all_phrases.update(tokens["trigrams"])

        if not all_phrases:
            return {"top_bullish_score": 0, "top_bearish_score": 0, "net_signal": 0}

        # Look up correlations
        async with async_session() as session:
            result = await session.execute(
                select(NewsPriceCorrelation)
                .where(NewsPriceCorrelation.phrase.in_(list(all_phrases)))
                .where(NewsPriceCorrelation.occurrences >= 3)
                .where(NewsPriceCorrelation.correlation_score >= 0.3)
            )
            correlations = result.scalars().all()

        if not correlations:
            return {"top_bullish_score": 0, "top_bearish_score": 0, "net_signal": 0}

        bullish_scores = []
        bearish_scores = []

        for corr in correlations:
            weighted_score = corr.avg_change_1h * corr.correlation_score
            if weighted_score > 0:
                bullish_scores.append(weighted_score)
            else:
                bearish_scores.append(weighted_score)

        top_bullish = max(bullish_scores) if bullish_scores else 0
        top_bearish = min(bearish_scores) if bearish_scores else 0
        net_signal = sum(bullish_scores) + sum(bearish_scores)

        return {
            "top_bullish_score": round(top_bullish, 4),
            "top_bearish_score": round(abs(top_bearish), 4),
            "net_signal": round(net_signal, 4),
        }

    except Exception as e:
        logger.debug(f"Phrase features error: {e}")
        return {"top_bullish_score": 0, "top_bearish_score": 0, "net_signal": 0}


async def _get_closest_price(session, target_time: datetime) -> float | None:
    """Get price closest to target time within ±30 min."""
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= target_time - timedelta(minutes=30))
        .where(Price.timestamp <= target_time + timedelta(minutes=30))
        .order_by(Price.timestamp)
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row.close if row else None
