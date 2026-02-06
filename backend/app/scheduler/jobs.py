import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select, desc

from app.config import settings
from app.database import (
    async_session, Price, News, Feature, Prediction, Signal,
    MacroData, OnChainData, InfluencerTweet, EventImpact,
)
from app.collectors import (
    MarketCollector, NewsCollector, FearGreedCollector,
    MacroCollector, OnChainCollector, RedditCollector,
    BinanceNewsCollector, InfluencerCollector,
)
from app.features.builder import FeatureBuilder
from app.features.sentiment import SentimentAnalyzer
from app.models.ensemble import EnsemblePredictor
from app.models.event_memory import EventClassifier, EventPatternMatcher
from app.signals.generator import SignalGenerator

logger = logging.getLogger(__name__)

# Global instances (initialized once)
market_collector = MarketCollector()
news_collector = NewsCollector()
fear_greed_collector = FearGreedCollector()
macro_collector = MacroCollector()
onchain_collector = OnChainCollector()
reddit_collector = RedditCollector()
binance_news_collector = BinanceNewsCollector()
influencer_collector = InfluencerCollector()
feature_builder = FeatureBuilder()
signal_generator = SignalGenerator()
event_classifier = EventClassifier()
event_pattern_matcher = EventPatternMatcher()

# Lazy-loaded ensemble predictor
_ensemble: EnsemblePredictor | None = None


def get_ensemble() -> EnsemblePredictor:
    global _ensemble
    if _ensemble is None:
        _ensemble = EnsemblePredictor(
            num_features=len(feature_builder.ALL_FEATURES),
        )
    return _ensemble


async def collect_price_data():
    """Collect and store BTC price data (runs every minute)."""
    try:
        data = await market_collector.collect()
        ticker = data.get("ticker")

        if not ticker:
            logger.warning("No ticker data received")
            return

        async with async_session() as session:
            price = Price(
                timestamp=datetime.utcnow(),
                open=float(ticker.get("openPrice", 0)),
                high=float(ticker.get("highPrice", 0)),
                low=float(ticker.get("lowPrice", 0)),
                close=float(ticker.get("lastPrice", 0)),
                volume=float(ticker.get("volume", 0)),
                source="binance",
            )
            session.add(price)
            await session.commit()

        logger.info(f"Price collected: ${ticker.get('lastPrice')}")

    except Exception as e:
        logger.error(f"Price collection error: {e}")


async def collect_news_data():
    """Collect news from ALL sources: RSS feeds, CryptoPanic, Reddit, Binance.

    Runs every 2 minutes. De-duplicates by title to avoid storing the same
    headline twice within a 6-hour window.
    """
    try:
        # ── Gather news from all collectors in parallel-ish fashion ──
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

        # ── De-duplicate: skip titles already stored in the last 6 hours ──
        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=6)
            result = await session.execute(
                select(News.title).where(News.timestamp >= since)
            )
            existing_titles = {row[0].lower().strip() for row in result.all()}

        analyzer = SentimentAnalyzer()
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

                # Score sentiment
                sentiment = analyzer.analyze_text(title)
                score = sentiment["combined_score"]

                news = News(
                    timestamp=datetime.utcnow(),
                    source=item.get("source", "unknown"),
                    title=title,
                    url=item.get("url", ""),
                    sentiment_score=score,
                    raw_sentiment=item.get("raw_sentiment"),
                )
                session.add(news)
                new_count += 1

            await session.commit()

        logger.info(f"News: {len(all_items)} fetched, {new_count} new (deduped)")

    except Exception as e:
        logger.error(f"News collection error: {e}")


async def collect_macro_data():
    """Collect and store macro market data (runs every hour)."""
    try:
        macro_data = await macro_collector.collect()
        fear_greed = await fear_greed_collector.collect()

        async with async_session() as session:
            macro = MacroData(
                timestamp=datetime.utcnow(),
                dxy=macro_data.get("dxy", {}).get("price") if isinstance(macro_data.get("dxy"), dict) else None,
                gold=macro_data.get("gold", {}).get("price") if isinstance(macro_data.get("gold"), dict) else None,
                sp500=macro_data.get("sp500", {}).get("price") if isinstance(macro_data.get("sp500"), dict) else None,
                treasury_10y=macro_data.get("treasury_10y", {}).get("price") if isinstance(macro_data.get("treasury_10y"), dict) else None,
                fear_greed_index=fear_greed.get("value"),
                fear_greed_label=fear_greed.get("label"),
            )
            session.add(macro)
            await session.commit()

        logger.info("Macro data collected")

    except Exception as e:
        logger.error(f"Macro collection error: {e}")


async def collect_onchain_data():
    """Collect and store on-chain data (runs every hour)."""
    try:
        data = await onchain_collector.collect()

        async with async_session() as session:
            onchain = OnChainData(
                timestamp=datetime.utcnow(),
                hash_rate=data.get("hash_rate"),
                difficulty=data.get("difficulty"),
                mempool_size=data.get("mempool_size"),
                mempool_fees=data.get("mempool_fees"),
                tx_volume=data.get("tx_volume"),
                active_addresses=data.get("active_addresses"),
                large_tx_count=data.get("large_tx_count"),
            )
            session.add(onchain)
            await session.commit()

        logger.info("On-chain data collected")

    except Exception as e:
        logger.error(f"On-chain collection error: {e}")


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
        new_count = 0

        async with async_session() as session:
            for tweet in tweets:
                text = tweet.get("text", "").strip()
                if not text or text.lower() in existing_texts:
                    continue
                existing_texts.add(text.lower())

                # Analyze sentiment
                sentiment = analyzer.analyze_text(text)
                score = sentiment["combined_score"]

                # Weight score by influencer's impact (1-10)
                weight = tweet.get("weight", 5)
                weighted_score = score * (weight / 5)  # Normalize around weight=5

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


async def generate_prediction():
    """Generate ML prediction (runs every hour).

    Incorporates event memory: queries historical event impacts to understand
    how similar past events affected BTC price, and feeds this as features
    to the prediction model.
    """
    try:
        # Get recent price data
        async with async_session() as session:
            result = await session.execute(
                select(Price)
                .order_by(desc(Price.timestamp))
                .limit(200)
            )
            prices = list(reversed(result.scalars().all()))

            # Get recent news
            result = await session.execute(
                select(News)
                .order_by(desc(News.timestamp))
                .limit(50)
            )
            news = result.scalars().all()

            # ── Event Memory: query recent events and historical patterns ──
            event_memory_data = {}
            try:
                # Get active events from last hour
                since_1h = datetime.utcnow() - timedelta(hours=1)
                result = await session.execute(
                    select(EventImpact)
                    .where(EventImpact.timestamp >= since_1h)
                    .order_by(desc(EventImpact.severity))
                )
                recent_events = result.scalars().all()

                # Get all historical evaluated events for pattern matching
                result = await session.execute(
                    select(EventImpact)
                    .where(EventImpact.evaluated_1h == True)
                    .order_by(desc(EventImpact.timestamp))
                    .limit(500)
                )
                historical_events = result.scalars().all()
                historical_dicts = [
                    {
                        "category": e.category,
                        "keywords": e.keywords,
                        "severity": e.severity,
                        "sentiment_score": e.sentiment_score,
                        "change_pct_1h": e.change_pct_1h,
                        "change_pct_4h": e.change_pct_4h,
                        "change_pct_24h": e.change_pct_24h,
                        "sentiment_was_predictive": e.sentiment_was_predictive,
                    }
                    for e in historical_events
                ]

                if recent_events:
                    # Use the most severe recent event for pattern matching
                    top_event = recent_events[0]
                    similar = event_pattern_matcher.find_similar_events(
                        category=top_event.category,
                        keywords=top_event.keywords or "",
                        past_events=historical_dicts,
                    )
                    expected = event_pattern_matcher.get_expected_impact(similar)

                    event_memory_data = {
                        "expected_1h": expected["expected_1h"],
                        "expected_4h": expected["expected_4h"],
                        "expected_24h": expected["expected_24h"],
                        "confidence": expected["confidence"],
                        "severity": top_event.severity / 10.0,  # Normalize to 0-1
                        "avg_sentiment_predictive": expected["avg_sentiment_predictive"],
                        "active_event_count": float(len(recent_events)),
                        "sample_size": expected["sample_size"],
                    }

                    if expected["sample_size"] > 0:
                        logger.info(
                            f"Event memory: {top_event.category} "
                            f"(severity={top_event.severity}) — "
                            f"expected 1h={expected['expected_1h']:+.2f}%, "
                            f"24h={expected['expected_24h']:+.2f}% "
                            f"(from {expected['sample_size']} similar events)"
                        )
            except Exception as e:
                logger.debug(f"Event memory query error: {e}")

        if len(prices) < 10:
            logger.warning("Not enough price data for prediction")
            return

        # Build price DataFrame
        price_df = pd.DataFrame([
            {
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices
        ])

        # Build features (including event memory)
        news_data = [{"title": n.title, "source": n.source} for n in news]
        features = feature_builder.build_features(
            price_df=price_df,
            news_data=news_data,
            event_memory=event_memory_data if event_memory_data else None,
        )

        # Build feature sequence for LSTM
        feature_array = feature_builder.features_to_array(features)
        sequence = np.tile(feature_array, (168, 1))  # Simplified: repeat current features
        # In production, we'd use historical feature snapshots

        # Run ensemble prediction
        ensemble = get_ensemble()
        predictions = ensemble.predict(
            feature_sequence=sequence,
            current_features=feature_array,
            news_data=news_data,
        )

        current_price = float(prices[-1].close)
        atr = features.get("atr", current_price * 0.02)
        volatility = features.get("volatility_24h", 2.0)

        # Generate signals
        signals = signal_generator.generate(predictions, current_price, atr, volatility)

        # Store predictions and signals
        async with async_session() as session:
            for timeframe, pred in predictions.items():
                # Always compute a numeric predicted price
                magnitude = pred.get("magnitude_pct", 0) or 0
                bullish_prob = pred.get("bullish_prob", 0.5)

                # If magnitude is 0 (heuristic fallback), estimate from probability
                if abs(magnitude) < 0.01:
                    # Map probability to a % change estimate:
                    # 0.0 → -3%, 0.5 → 0%, 1.0 → +3%
                    tf_multiplier = {"1h": 0.5, "4h": 1.5, "24h": 3.0}.get(timeframe, 1.0)
                    magnitude = (bullish_prob - 0.5) * 2 * tf_multiplier

                predicted_price = current_price * (1 + magnitude / 100)

                prediction = Prediction(
                    timestamp=datetime.utcnow(),
                    timeframe=timeframe,
                    direction=pred["direction"],
                    confidence=pred["confidence"],
                    predicted_change_pct=round(magnitude, 4),
                    predicted_price=round(predicted_price, 2),
                    current_price=current_price,
                    model_outputs=pred.get("model_outputs"),
                )
                session.add(prediction)

            for timeframe, sig in signals.items():
                signal = Signal(
                    timestamp=datetime.utcnow(),
                    action=sig["action"],
                    direction=sig["direction"],
                    confidence=sig["confidence"],
                    entry_price=sig["entry_price"],
                    target_price=sig["target_price"],
                    stop_loss=sig["stop_loss"],
                    risk_rating=sig["risk_rating"],
                    timeframe=timeframe,
                    reasoning=sig["reasoning"],
                )
                session.add(signal)

            # Store features
            feature_record = Feature(
                timestamp=datetime.utcnow(),
                feature_data=features,
            )
            session.add(feature_record)

            await session.commit()

        summary = ", ".join(f"{tf}={p['direction']}" for tf, p in predictions.items())
        logger.info(f"Prediction generated: {summary}")

    except Exception as e:
        logger.error(f"Prediction generation error: {e}", exc_info=True)


async def evaluate_predictions():
    """Evaluate past predictions against actual prices (runs every hour)."""
    try:
        async with async_session() as session:
            # Find unevaluated predictions older than their timeframe
            result = await session.execute(
                select(Prediction)
                .where(Prediction.was_correct.is_(None))
                .where(Prediction.timestamp < datetime.utcnow() - timedelta(hours=1))
            )
            predictions = result.scalars().all()

            for pred in predictions:
                # Determine evaluation time based on timeframe
                hours = {"1h": 1, "4h": 4, "24h": 24}.get(pred.timeframe, 1)
                eval_time = pred.timestamp + timedelta(hours=hours)

                if datetime.utcnow() < eval_time:
                    continue

                # Get actual price at evaluation time
                price_result = await session.execute(
                    select(Price)
                    .where(Price.timestamp >= eval_time - timedelta(minutes=5))
                    .where(Price.timestamp <= eval_time + timedelta(minutes=5))
                    .order_by(Price.timestamp)
                    .limit(1)
                )
                actual_price_record = price_result.scalar_one_or_none()

                if not actual_price_record:
                    continue

                actual_price = actual_price_record.close
                actual_direction = "bullish" if actual_price > pred.current_price else "bearish"

                pred.actual_price = actual_price
                pred.actual_direction = actual_direction
                pred.was_correct = (pred.direction == actual_direction) or (
                    pred.direction == "neutral" and abs(actual_price - pred.current_price) / pred.current_price < 0.005
                )

            await session.commit()

        logger.info(f"Evaluated {len(predictions)} predictions")

    except Exception as e:
        logger.error(f"Prediction evaluation error: {e}")


async def classify_news_events():
    """Classify recent news into event categories and record them (runs every 5 min).

    This is the 'learning' step — it identifies significant events and starts
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


async def _get_price_at(session, target_time: datetime) -> float | None:
    """Get BTC price closest to a target time (±10 min window)."""
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= target_time - timedelta(minutes=10))
        .where(Price.timestamp <= target_time + timedelta(minutes=10))
        .order_by(Price.timestamp)
        .limit(1)
    )
    price = result.scalar_one_or_none()
    return price.close if price else None


async def cleanup_old_data():
    """Clean up data older than 90 days (runs daily).
    Note: EventImpact is kept indefinitely for long-term memory.
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=90)

        async with async_session() as session:
            for model in [Price, News, Feature]:
                await session.execute(
                    model.__table__.delete().where(model.timestamp < cutoff)
                )
            await session.commit()

        logger.info("Old data cleaned up")

    except Exception as e:
        logger.error(f"Cleanup error: {e}")
