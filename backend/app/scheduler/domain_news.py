"""News collection jobs: news, influencer tweets, event classification, sentiment aggregation."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc

from app.database import (
    async_session, Price, News, InfluencerTweet, EventImpact,
)
from app.collectors import (
    NewsCollector, RedditCollector, BinanceNewsCollector, InfluencerCollector,
)
from app.features.sentiment import SentimentAnalyzer
from app.models.event_memory import EventClassifier

logger = logging.getLogger(__name__)

# Global instances (initialized once)
news_collector = NewsCollector()
reddit_collector = RedditCollector()
binance_news_collector = BinanceNewsCollector()
influencer_collector = InfluencerCollector()
event_classifier = EventClassifier()


async def collect_news_data():
    """Collect news from ALL sources: RSS feeds, CryptoPanic, Reddit, Binance.

    Runs every 2 minutes. De-duplicates by title to avoid storing the same
    headline twice within a 6-hour window.
    """
    try:
        # -- Gather news from all collectors in parallel-ish fashion --
        all_items: list[dict] = []

        # 1. RSS + CryptoPanic (25+ feeds)
        rss_data = await news_collector.collect()
        all_items.extend(rss_data.get("news", []))

        # 2. Reddit posts
        try:
            reddit_data = await reddit_collector.collect()
            for post in reddit_data.get("posts", []):
                all_items.append({
                    "source": f"reddit_{post.get('subreddit', 'unknown')}",
                    "title": post.get("title", ""),
                    "url": post.get("url", ""),
                    "published": "",
                    "sentiment_score": None,
                    "raw_sentiment": None,
                })
        except Exception as e:
            logger.debug(f"Reddit collection failed: {e}")

        # 3. Binance announcements (listings, delistings, airdrops)
        try:
            binance_data = await binance_news_collector.collect()
            all_items.extend(binance_data.get("news", []))
        except Exception as e:
            logger.debug(f"Binance news collection failed: {e}")

        if not all_items:
            return

        # -- De-duplicate: skip titles already stored in the last 6 hours --
        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=6)
            result = await session.execute(
                select(News.title).where(News.timestamp >= since)
            )
            existing_titles = {row[0].lower().strip() for row in result.all()}

        analyzer = SentimentAnalyzer()
        analyzer.load_multilingual()
        new_count = 0

        async with async_session() as session:
            for item in all_items:
                title = item.get("title", "").strip()
                if not title:
                    continue

                # Skip duplicates
                if title.lower() in existing_titles:
                    continue
                existing_titles.add(title.lower())

                # Detect language (from hint or auto-detect)
                language = item.get("language")
                if not language:
                    language = analyzer.detect_language(title)

                # Score sentiment with language awareness
                sentiment = analyzer.analyze_text(title, language=language)
                score = sentiment["combined_score"]

                # Tag with coin_id
                from app.features.coin_tagger import CoinTagger
                primary_coin = CoinTagger.tag_primary(title)

                news = News(
                    timestamp=datetime.utcnow(),
                    source=item.get("source", "unknown"),
                    title=title,
                    url=item.get("url", ""),
                    sentiment_score=score,
                    raw_sentiment=item.get("raw_sentiment"),
                    language=language,
                    coin_id=primary_coin,
                )
                session.add(news)
                new_count += 1

            await session.commit()

        logger.info(f"News: {len(all_items)} fetched, {new_count} new (deduped)")

    except Exception as e:
        logger.error(f"News collection error: {e}")


async def collect_influencer_tweets():
    """Collect tweets from influential crypto people (runs every 10 minutes).

    Monitors Twitter/X feeds of key figures who affect BTC price:
    - CEOs (Elon, Saylor, CZ, etc.)
    - Investors (Cathie Wood, Raoul Pal, etc.)
    - Regulators (SEC, Fed, politicians)
    - Analysts and developers
    """
    try:
        data = await influencer_collector.collect()
        tweets = data.get("tweets", [])

        if not tweets:
            logger.debug("No new influencer tweets")
            return

        # Deduplicate by text (same tweet not stored twice in 24h)
        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=24)
            result = await session.execute(
                select(InfluencerTweet.text)
                .where(InfluencerTweet.timestamp >= since)
            )
            existing_texts = {row[0].lower().strip() for row in result.all()}

        analyzer = SentimentAnalyzer()
        analyzer.load_multilingual()
        new_count = 0

        async with async_session() as session:
            for tweet in tweets:
                text = tweet.get("text", "").strip()
                if not text or text.lower() in existing_texts:
                    continue
                existing_texts.add(text.lower())

                # Detect language (from hint or auto-detect)
                language = tweet.get("language")
                if not language:
                    language = analyzer.detect_language(text)

                # Analyze sentiment with language awareness
                sentiment = analyzer.analyze_text(text, language=language)
                score = sentiment["combined_score"]

                # Weight score by influencer's impact (1-10), clamped to [-1, 1]
                weight = tweet.get("weight", 5)
                weighted_score = max(-1.0, min(1.0, score * (weight / 5)))

                tweet_record = InfluencerTweet(
                    timestamp=datetime.utcnow(),
                    influencer_name=tweet.get("influencer", "Unknown"),
                    username=tweet.get("username", ""),
                    role=tweet.get("role", ""),
                    category=tweet.get("category", ""),
                    weight=weight,
                    text=text,
                    url=tweet.get("url", ""),
                    sentiment_score=weighted_score,
                    published_at=tweet.get("published", ""),
                    language=language,
                )
                session.add(tweet_record)
                new_count += 1

            await session.commit()

        logger.info(
            f"Influencer tweets: {len(tweets)} fetched, {new_count} new "
            f"(failed: {len(data.get('failed_users', []))})"
        )

    except Exception as e:
        logger.error(f"Influencer collection error: {e}")


async def classify_news_events():
    """Classify recent news into event categories and record them (runs every 5 min).

    This is the 'learning' step -- it identifies significant events and starts
    tracking their price impact. Over time, this builds a historical memory
    of how different event types affect BTC.
    """
    try:
        async with async_session() as session:
            # Get news from last 10 minutes that haven't been classified yet
            since = datetime.utcnow() - timedelta(minutes=10)
            result = await session.execute(
                select(News).where(News.timestamp >= since)
            )
            recent_news = result.scalars().all()

            # Get already-classified news IDs (from last hour to avoid re-processing)
            since_1h = datetime.utcnow() - timedelta(hours=1)
            result = await session.execute(
                select(EventImpact.news_id).where(
                    EventImpact.timestamp >= since_1h
                )
            )
            already_classified = {row[0] for row in result.all() if row[0]}

            # Get current BTC price
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            current_price_row = result.scalar_one_or_none()
            if not current_price_row:
                return
            current_price = current_price_row.close

        new_events = 0

        async with async_session() as session:
            for news_item in recent_news:
                if news_item.id in already_classified:
                    continue

                classification = event_classifier.classify(
                    news_item.title,
                    sentiment_score=news_item.sentiment_score or 0.0,
                )

                if classification is None:
                    continue  # Not a significant event

                event = EventImpact(
                    timestamp=news_item.timestamp,
                    news_id=news_item.id,
                    title=news_item.title,
                    source=news_item.source,
                    category=classification["category"],
                    subcategory=classification["subcategory"],
                    keywords=classification["keywords"],
                    severity=classification["severity"],
                    sentiment_score=news_item.sentiment_score,
                    price_at_event=current_price,
                )
                session.add(event)
                new_events += 1

            await session.commit()

        if new_events > 0:
            logger.info(f"Event memory: {new_events} new events classified")

    except Exception as e:
        logger.error(f"Event classification error: {e}")


async def evaluate_event_impacts():
    """Measure actual BTC price impact of past events (runs every 30 min).

    For each event that hasn't been fully evaluated, check if enough time has
    passed and record the actual price change. This builds the historical
    'memory' that the pattern matcher uses.
    """
    from app.scheduler.domain_ml import _get_price_at

    try:
        async with async_session() as session:
            # Get events that need evaluation
            result = await session.execute(
                select(EventImpact).where(
                    (EventImpact.evaluated_1h == False) |
                    (EventImpact.evaluated_4h == False) |
                    (EventImpact.evaluated_24h == False) |
                    (EventImpact.evaluated_7d == False)
                )
            )
            events = result.scalars().all()

            if not events:
                return

            now = datetime.utcnow()
            evaluated_count = 0

            for event in events:
                base_price = event.price_at_event
                if not base_price:
                    continue

                # Evaluate 1h impact
                if not event.evaluated_1h and now >= event.timestamp + timedelta(hours=1):
                    price_1h = await _get_price_at(session, event.timestamp + timedelta(hours=1))
                    if price_1h:
                        event.price_1h = price_1h
                        event.change_pct_1h = round((price_1h - base_price) / base_price * 100, 4)
                        event.evaluated_1h = True
                        evaluated_count += 1

                        # Check if sentiment was predictive for 1h
                        if event.sentiment_score is not None:
                            sent_predicted_up = event.sentiment_score > 0
                            actually_went_up = event.change_pct_1h > 0
                            event.sentiment_was_predictive = (sent_predicted_up == actually_went_up)

                # Evaluate 4h impact
                if not event.evaluated_4h and now >= event.timestamp + timedelta(hours=4):
                    price_4h = await _get_price_at(session, event.timestamp + timedelta(hours=4))
                    if price_4h:
                        event.price_4h = price_4h
                        event.change_pct_4h = round((price_4h - base_price) / base_price * 100, 4)
                        event.evaluated_4h = True
                        evaluated_count += 1

                # Evaluate 24h impact
                if not event.evaluated_24h and now >= event.timestamp + timedelta(hours=24):
                    price_24h = await _get_price_at(session, event.timestamp + timedelta(hours=24))
                    if price_24h:
                        event.price_24h = price_24h
                        event.change_pct_24h = round((price_24h - base_price) / base_price * 100, 4)
                        event.evaluated_24h = True
                        evaluated_count += 1

                # Evaluate 7d impact
                if not event.evaluated_7d and now >= event.timestamp + timedelta(days=7):
                    price_7d = await _get_price_at(session, event.timestamp + timedelta(days=7))
                    if price_7d:
                        event.price_7d = price_7d
                        event.change_pct_7d = round((price_7d - base_price) / base_price * 100, 4)
                        event.evaluated_7d = True
                        evaluated_count += 1

            await session.commit()

        if evaluated_count > 0:
            logger.info(f"Event memory: evaluated {evaluated_count} impact measurements")

    except Exception as e:
        logger.error(f"Event impact evaluation error: {e}")


async def aggregate_coin_sentiments():
    """Aggregate per-coin sentiment from tagged news and Reddit posts.

    Runs every 5 minutes. For each tracked coin, queries tagged news + Reddit posts
    from the last hour and computes average sentiment/volume.
    """
    from app.collectors.coins import TRACKED_COINS
    from app.database import CoinSentiment

    try:
        since_1h = datetime.utcnow() - timedelta(hours=1)
        since_24h = datetime.utcnow() - timedelta(hours=24)

        async with async_session() as session:
            for coin in TRACKED_COINS:
                coin_id = coin["coin_id"]

                # Get news tagged with this coin in last 1h
                result_1h = await session.execute(
                    select(News.sentiment_score).where(
                        News.coin_id == coin_id,
                        News.timestamp >= since_1h,
                        News.sentiment_score.isnot(None),
                    )
                )
                scores_1h = [row[0] for row in result_1h.all()]

                # Get news tagged with this coin in last 24h
                result_24h = await session.execute(
                    select(News.sentiment_score).where(
                        News.coin_id == coin_id,
                        News.timestamp >= since_24h,
                        News.sentiment_score.isnot(None),
                    )
                )
                scores_24h = [row[0] for row in result_24h.all()]

                # Compute averages
                news_avg = sum(scores_1h) / len(scores_1h) if scores_1h else None
                news_vol = len(scores_24h)

                # Reddit posts mentioning this coin (from news table with reddit_ source)
                reddit_result = await session.execute(
                    select(News.sentiment_score).where(
                        News.coin_id == coin_id,
                        News.source.like("reddit_%"),
                        News.timestamp >= since_24h,
                        News.sentiment_score.isnot(None),
                    )
                )
                reddit_scores = [row[0] for row in reddit_result.all()]
                reddit_avg = sum(reddit_scores) / len(reddit_scores) if reddit_scores else None

                # Overall sentiment: weighted average of available sources
                components = []
                if news_avg is not None:
                    components.append(news_avg)
                if reddit_avg is not None:
                    components.append(reddit_avg)
                overall = sum(components) / len(components) if components else None

                # Only store if we have any data
                if overall is not None or news_vol > 0:
                    session.add(CoinSentiment(
                        coin_id=coin_id,
                        timestamp=datetime.utcnow(),
                        news_sentiment_avg=news_avg,
                        news_volume=news_vol,
                        social_sentiment_avg=None,
                        social_volume=0,
                        reddit_sentiment_avg=reddit_avg,
                        reddit_volume=len(reddit_scores),
                        overall_sentiment=overall,
                    ))

            await session.commit()
            logger.info(f"Aggregated sentiment for {len(TRACKED_COINS)} coins")

    except Exception as e:
        logger.error(f"Sentiment aggregation error: {e}", exc_info=True)
