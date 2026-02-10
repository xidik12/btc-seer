import asyncio
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select, desc, func

from app.config import settings
from app.database import (
    async_session, Price, News, Feature, Prediction, Signal,
    MacroData, OnChainData, InfluencerTweet, EventImpact, QuantPrediction,
    FundingRate, BtcDominance, IndicatorSnapshot, AlertLog, ModelVersion,
    PortfolioState, TradeAdvice, TradeResult, BotUser,
    PredictionContext, ModelPerformanceLog,
    timestamp_diff_order,
)
from app.collectors import (
    MarketCollector, NewsCollector, FearGreedCollector,
    MacroCollector, OnChainCollector, RedditCollector,
    BinanceNewsCollector, InfluencerCollector,
    ETFCollector, ExchangeFlowCollector,
    DerivativesExtendedCollector, StablecoinCollector,
)
from app.features.builder import FeatureBuilder
from app.features.sentiment import SentimentAnalyzer
from app.models.ensemble import EnsemblePredictor
from app.models.event_memory import EventClassifier, EventPatternMatcher
from app.models.quant_predictor import QuantPredictor
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
etf_collector = ETFCollector()
exchange_flow_collector = ExchangeFlowCollector()
derivatives_extended_collector = DerivativesExtendedCollector()
stablecoin_collector = StablecoinCollector()
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
            model_dir=settings.model_dir,
            num_features=len(feature_builder.ALL_FEATURES),
        )
    return _ensemble


async def backfill_historical_prices():
    """Backfill historical BTC price data from Binance on startup.

    Fetches hourly candles (1000 = ~41 days) and daily candles (1000 = ~2.7 years)
    so that charts have data for all timeframes immediately.
    Only runs if the DB has less than 7 days of data.
    """
    try:
        # Check how much data we already have
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(Price.timestamp).limit(1)
            )
            oldest = result.scalar_one_or_none()

            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            newest = result.scalar_one_or_none()

        # If we already have >7 days of data, skip backfill
        if oldest and newest:
            span = (newest.timestamp - oldest.timestamp).total_seconds()
            if span > 7 * 86400:
                logger.info(f"Backfill: DB already has {span / 86400:.1f} days of data, skipping")
                return

        logger.info("Backfill: Starting historical price data fetch from Binance...")

        # Fetch hourly klines (1000 = ~41 days) for short/medium timeframes
        hourly_klines = await market_collector.get_historical_klines(
            interval="1h", limit=1000
        )
        if hourly_klines:
            count = await _insert_klines(hourly_klines, source="binance_backfill_1h")
            logger.info(f"Backfill: Inserted {count} hourly candles")

        # Fetch daily klines (1000 = ~2.7 years) for long timeframes
        daily_klines = await market_collector.get_historical_klines(
            interval="1d", limit=1000
        )
        if daily_klines:
            count = await _insert_klines(daily_klines, source="binance_backfill_1d")
            logger.info(f"Backfill: Inserted {count} daily candles")

        total = (len(hourly_klines) if hourly_klines else 0) + (len(daily_klines) if daily_klines else 0)
        logger.info(f"Backfill: Complete — {total} total candles loaded")

    except Exception as e:
        logger.error(f"Backfill error: {e}", exc_info=True)


async def _insert_klines(klines: list[dict], source: str = "binance_backfill"):
    """Insert kline data into the Price table, skipping duplicates by timestamp."""
    async with async_session() as session:
        # Build set of existing timestamps (rounded to minute) for dedup
        result = await session.execute(select(Price.timestamp))
        existing_ts_minutes = set()
        for row in result.all():
            ts = row[0]
            # Round to nearest minute for comparison
            existing_ts_minutes.add(ts.replace(second=0, microsecond=0))

        inserted = 0
        for k in klines:
            ts = k["timestamp"]
            # Make naive UTC if timezone-aware
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)

            ts_minute = ts.replace(second=0, microsecond=0)
            if ts_minute in existing_ts_minutes:
                continue

            price = Price(
                timestamp=ts,
                open=k["open"],
                high=k["high"],
                low=k["low"],
                close=k["close"],
                volume=k["volume"],
                source=source,
            )
            session.add(price)
            existing_ts_minutes.add(ts_minute)
            inserted += 1

        await session.commit()
        return inserted


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

        dxy = macro_data.get("dxy", {}).get("price") if isinstance(macro_data.get("dxy"), dict) else None
        gold = macro_data.get("gold", {}).get("price") if isinstance(macro_data.get("gold"), dict) else None
        sp500 = macro_data.get("sp500", {}).get("price") if isinstance(macro_data.get("sp500"), dict) else None
        treasury_10y = macro_data.get("treasury_10y", {}).get("price") if isinstance(macro_data.get("treasury_10y"), dict) else None
        nasdaq = macro_data.get("nasdaq", {}).get("price") if isinstance(macro_data.get("nasdaq"), dict) else None
        vix = macro_data.get("vix", {}).get("price") if isinstance(macro_data.get("vix"), dict) else None
        eurusd = macro_data.get("eurusd", {}).get("price") if isinstance(macro_data.get("eurusd"), dict) else None
        fear_greed_index = fear_greed.get("value")
        fear_greed_label = fear_greed.get("label")

        # Don't save a row where ALL values are None
        if dxy is None and gold is None and sp500 is None and treasury_10y is None and nasdaq is None and vix is None and eurusd is None and fear_greed_index is None:
            logger.warning("Macro collection returned all None values, skipping DB save")
            return

        async with async_session() as session:
            macro = MacroData(
                timestamp=datetime.utcnow(),
                dxy=dxy,
                gold=gold,
                sp500=sp500,
                treasury_10y=treasury_10y,
                nasdaq=nasdaq,
                vix=vix,
                eurusd=eurusd,
                fear_greed_index=fear_greed_index,
                fear_greed_label=fear_greed_label,
            )
            session.add(macro)
            await session.commit()

        logger.info(f"Macro data collected: DXY={dxy}, Gold={gold}, SP500={sp500}, 10Y={treasury_10y}, NDQ={nasdaq}, VIX={vix}, EURUSD={eurusd}")

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

        if len(prices) < 5:
            logger.warning("Not enough price data for prediction (need at least 5)")
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

        # Get latest funding rate data
        funding_data = None
        try:
            async with async_session() as sess:
                result = await sess.execute(
                    select(FundingRate).order_by(desc(FundingRate.timestamp)).limit(1)
                )
                fr_row = result.scalar_one_or_none()
                if fr_row:
                    funding_data = {
                        "funding_rate": fr_row.funding_rate,
                        "open_interest": fr_row.open_interest,
                        "mark_price": fr_row.mark_price,
                        "index_price": fr_row.index_price,
                    }
        except Exception as e:
            logger.debug(f"Funding data query error: {e}")

        # Get latest dominance data
        dominance_data = None
        try:
            async with async_session() as sess:
                result = await sess.execute(
                    select(BtcDominance).order_by(desc(BtcDominance.timestamp)).limit(1)
                )
                dom_row = result.scalar_one_or_none()
                if dom_row:
                    dominance_data = {
                        "btc_dominance": dom_row.btc_dominance,
                        "eth_dominance": dom_row.eth_dominance,
                        "total_market_cap": dom_row.total_market_cap,
                        "market_cap_change_24h": dom_row.market_cap_change_24h,
                    }
        except Exception as e:
            logger.debug(f"Dominance data query error: {e}")

        # Get latest on-chain data for features
        onchain_raw = None
        try:
            async with async_session() as sess:
                result = await sess.execute(
                    select(OnChainData).order_by(desc(OnChainData.timestamp)).limit(1)
                )
                oc = result.scalar_one_or_none()
                if oc:
                    onchain_raw = {
                        "hash_rate": oc.hash_rate,
                        "mempool_size": oc.mempool_size,
                        "mempool_fees": oc.mempool_fees,
                        "tx_volume": oc.tx_volume,
                        "active_addresses": oc.active_addresses,
                        "difficulty": oc.difficulty,
                        "large_tx_count": oc.large_tx_count,
                    }
        except Exception as e:
            logger.debug(f"OnChain data query error: {e}")

        # Get supply/mining data from blockchain.info
        supply_data = None
        try:
            import aiohttp
            async with aiohttp.ClientSession() as http_sess:
                async with http_sess.get(
                    "https://api.blockchain.info/stats",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        stats = await resp.json(content_type=None)
                        total_btc = stats.get("totalbc", 0) / 1e8
                        n_blocks = stats.get("n_blocks_total", 0)
                        supply_data = {
                            "total_mined": total_btc if total_btc > 0 else 19_800_000,
                            "percent_mined": (total_btc / 21_000_000) * 100 if total_btc > 0 else 94.3,
                            "btc_mined_per_day": 144 * 3.125,
                            "blocks_until_halving": max(0, 1_050_000 - n_blocks) if n_blocks > 0 else 169_000,
                        }
        except Exception as e:
            logger.debug(f"Supply data fetch error: {e}")

        # Get latest influencer social media data
        influencer_data = None
        try:
            async with async_session() as sess:
                result = await sess.execute(
                    select(InfluencerTweet)
                    .where(InfluencerTweet.timestamp >= datetime.utcnow() - timedelta(hours=1))
                    .order_by(desc(InfluencerTweet.timestamp))
                    .limit(50)
                )
                tweets = result.scalars().all()
                if tweets:
                    influencer_data = [
                        {
                            "text": t.text,
                            "influencer": t.influencer,
                            "category": t.category,
                        }
                        for t in tweets
                    ]
        except Exception as e:
            logger.debug(f"Influencer data query error: {e}")

        # ── Collect new data sources (concurrently with 10s timeout) ──
        async def _safe_collect(collector, name):
            try:
                return await asyncio.wait_for(collector.collect(), timeout=10)
            except asyncio.TimeoutError:
                logger.debug(f"{name} collection timed out (10s)")
                return None
            except Exception as e:
                logger.debug(f"{name} collection error: {e}")
                return None

        derivatives_ext_data, etf_data, exchange_flow_data, stablecoin_data_raw = (
            await asyncio.gather(
                _safe_collect(derivatives_extended_collector, "Derivatives extended"),
                _safe_collect(etf_collector, "ETF"),
                _safe_collect(exchange_flow_collector, "Exchange flow"),
                _safe_collect(stablecoin_collector, "Stablecoin"),
            )
        )

        # Build features (including social media, event memory, funding, dominance)
        news_data = [{"title": n.title, "source": n.source} for n in news]
        features = feature_builder.build_features(
            price_df=price_df,
            news_data=news_data,
            influencer_data=influencer_data,
            event_memory=event_memory_data if event_memory_data else None,
            funding_data=funding_data,
            dominance_data=dominance_data,
            onchain_data=onchain_raw,
            supply_data=supply_data,
            derivatives_extended=derivatives_ext_data,
            etf_data=etf_data,
            exchange_flow_data=exchange_flow_data,
            stablecoin_data=stablecoin_data_raw,
        )

        # Build REAL feature sequence from Feature table history
        feature_array = feature_builder.features_to_array(features)

        async with async_session() as sess:
            result = await sess.execute(
                select(Feature)
                .order_by(desc(Feature.timestamp))
                .limit(168)
            )
            feature_history = list(reversed(result.scalars().all()))

        if len(feature_history) >= 10:
            # Use real historical feature snapshots
            sequence = feature_builder.build_sequence(
                [f.feature_data for f in feature_history], lookback=168
            )
        else:
            # Fallback: tile current features (first few hours after startup)
            sequence = np.tile(feature_array, (168, 1))

        # Collect price history for TimesFM (last 512 hours)
        price_history = [float(p.close) for p in prices[-512:]]

        # Run ensemble prediction with fallback
        try:
            ensemble = get_ensemble()
            predictions = ensemble.predict(
                feature_sequence=sequence,
                current_features=feature_array,
                news_data=news_data,
                price_history=price_history,
            )
        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}, using fallback")
            # Fallback: Use simple momentum-based predictions when ensemble fails
            recent_change = ((prices[-1].close - prices[-24].close) / prices[-24].close * 100) if len(prices) >= 24 else 0
            direction = "bullish" if recent_change > 0 else "bearish"
            predictions = {
                "1h": {"direction": direction, "confidence": 50, "magnitude_pct": recent_change * 0.1, "model_outputs": {}},
                "4h": {"direction": direction, "confidence": 45, "magnitude_pct": recent_change * 0.3, "model_outputs": {}},
                "24h": {"direction": direction, "confidence": 40, "magnitude_pct": recent_change * 0.8, "model_outputs": {}},
            }

        current_price = float(prices[-1].close)
        atr = features.get("atr", current_price * 0.02)
        volatility = features.get("volatility_24h", 2.0)

        # Generate signals
        signals = signal_generator.generate(predictions, current_price, atr, volatility)

        # Store predictions, signals, and context
        async with async_session() as session:
            prediction_ids = {}
            for timeframe, pred in predictions.items():
                # Ensemble now always produces a meaningful magnitude
                magnitude = pred.get("magnitude_pct", 0) or 0
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
                await session.flush()
                prediction_ids[timeframe] = prediction.id

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

            # Save full PredictionContext for training replay
            try:
                context = PredictionContext(
                    timestamp=datetime.utcnow(),
                    prediction_id=prediction_ids.get("1h"),
                    current_price=current_price,
                    features=features,
                    news_headlines=[{"title": n.get("title", ""), "source": n.get("source", "")} for n in news_data[:20]] if news_data else None,
                    macro_snapshot=None,
                    event_memory=event_memory_data if event_memory_data else None,
                    model_outputs={tf: p.get("model_outputs") for tf, p in predictions.items()},
                )
                session.add(context)
            except Exception as e:
                logger.debug(f"Context save error: {e}")

            await session.commit()

        summary = ", ".join(f"{tf}={p['direction']}" for tf, p in predictions.items())
        logger.info(f"Prediction generated: {summary}")

    except Exception as e:
        logger.error(f"Prediction generation error: {e}", exc_info=True)


async def generate_quant_prediction():
    """Generate quant theory-based prediction (runs every 30 min alongside ML).

    Uses 15+ proven BTC prediction theories: Pi Cycle, Rainbow Chart,
    Mayer Multiple, Halving Cycle, Mean Reversion, Momentum, Funding Rate, etc.
    """
    try:
        # Get price history
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1000)
            )
            prices = list(reversed(result.scalars().all()))

            # Get latest macro data
            result = await session.execute(
                select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
            )
            macro_row = result.scalar_one_or_none()

            # Get latest on-chain data
            result = await session.execute(
                select(OnChainData).order_by(desc(OnChainData.timestamp)).limit(1)
            )
            onchain_row = result.scalar_one_or_none()

        if len(prices) < 20:
            logger.warning("Not enough price data for quant prediction (need at least 20)")
            return

        current_price = float(prices[-1].close)

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

        # Prepare macro data
        macro_data = None
        if macro_row:
            # Calculate DXY 24h change (approximate from stored values)
            macro_data = {
                "dxy_change_24h": None,
            }
            if macro_row.dxy:
                # Get DXY from 24h ago
                async with async_session() as session:
                    result = await session.execute(
                        select(MacroData)
                        .where(MacroData.timestamp <= datetime.utcnow() - timedelta(hours=23))
                        .order_by(desc(MacroData.timestamp))
                        .limit(1)
                    )
                    old_macro = result.scalar_one_or_none()
                    if old_macro and old_macro.dxy and old_macro.dxy > 0:
                        macro_data["dxy_change_24h"] = (macro_row.dxy - old_macro.dxy) / old_macro.dxy

        # Fear & Greed value
        fear_greed_value = float(macro_row.fear_greed_index) if macro_row and macro_row.fear_greed_index else None

        # Funding rate from Binance
        funding_rate = None
        try:
            fr_data = await market_collector.get_funding_rate()
            if fr_data:
                funding_rate = fr_data.get("funding_rate")
        except Exception as e:
            logger.debug(f"Funding rate fetch for quant: {e}")

        # On-chain data
        onchain_data = None
        if onchain_row:
            onchain_data = {
                "tx_volume": onchain_row.tx_volume,
                "hash_rate": onchain_row.hash_rate,
                "active_addresses": onchain_row.active_addresses,
            }

        # Run quant predictor
        quant = QuantPredictor()
        result = quant.predict(
            price_df=price_df,
            current_price=current_price,
            macro_data=macro_data,
            fear_greed_value=fear_greed_value,
            funding_rate=funding_rate,
            onchain_data=onchain_data,
        )

        # Store in database
        preds = result.get("predictions", {})
        async with async_session() as session:
            qp = QuantPrediction(
                timestamp=datetime.utcnow(),
                current_price=current_price,
                composite_score=result.get("composite_score", 0),
                action=result.get("action", "NEUTRAL"),
                direction=result.get("direction", "neutral"),
                confidence=result.get("confidence", 0),
                pred_1h_price=preds.get("1h", {}).get("predicted_price"),
                pred_1h_change_pct=preds.get("1h", {}).get("predicted_change_pct"),
                pred_4h_price=preds.get("4h", {}).get("predicted_price"),
                pred_4h_change_pct=preds.get("4h", {}).get("predicted_change_pct"),
                pred_24h_price=preds.get("24h", {}).get("predicted_price"),
                pred_24h_change_pct=preds.get("24h", {}).get("predicted_change_pct"),
                pred_1w_price=preds.get("1w", {}).get("predicted_price"),
                pred_1w_change_pct=preds.get("1w", {}).get("predicted_change_pct"),
                pred_1mo_price=preds.get("1mo", {}).get("predicted_price"),
                pred_1mo_change_pct=preds.get("1mo", {}).get("predicted_change_pct"),
                active_signals=result.get("active_signals", 0),
                bullish_signals=result.get("bullish_signals", 0),
                bearish_signals=result.get("bearish_signals", 0),
                agreement_ratio=result.get("agreement_ratio", 0),
                signal_breakdown=result.get("signal_breakdown"),
            )
            session.add(qp)
            await session.commit()

        logger.info(
            f"Quant prediction: {result.get('direction')} "
            f"(score={result.get('composite_score'):.1f}, "
            f"confidence={result.get('confidence'):.0f}%, "
            f"action={result.get('action')}, "
            f"{result.get('bullish_signals')}B/{result.get('bearish_signals')}S signals)"
        )

    except Exception as e:
        logger.error(f"Quant prediction error: {e}", exc_info=True)


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

            evaluated_count = 0
            for pred in predictions:
                # Determine evaluation time based on timeframe
                hours = {"1h": 1, "4h": 4, "24h": 24, "1w": 168, "1mo": 720}.get(pred.timeframe, 1)
                eval_time = pred.timestamp + timedelta(hours=hours)

                if datetime.utcnow() < eval_time:
                    continue

                # Use wider window for finding price: ±30 min, pick closest to target
                window = timedelta(minutes=30)
                price_result = await session.execute(
                    select(Price)
                    .where(Price.timestamp >= eval_time - window)
                    .where(Price.timestamp <= eval_time + window)
                    .order_by(timestamp_diff_order(Price.timestamp, eval_time))
                    .limit(1)
                )
                actual_price_record = price_result.scalar_one_or_none()

                if not actual_price_record:
                    # Fallback: if no price in ±30min, get the latest price before eval_time + 1h
                    fallback_result = await session.execute(
                        select(Price)
                        .where(Price.timestamp <= eval_time + timedelta(hours=1))
                        .order_by(desc(Price.timestamp))
                        .limit(1)
                    )
                    actual_price_record = fallback_result.scalar_one_or_none()

                if not actual_price_record:
                    continue

                actual_price = actual_price_record.close
                actual_direction = "bullish" if actual_price > pred.current_price else "bearish"

                pred.actual_price = actual_price
                pred.actual_direction = actual_direction
                pred.was_correct = (pred.direction == actual_direction) or (
                    pred.direction == "neutral" and abs(actual_price - pred.current_price) / pred.current_price < 0.005
                )
                evaluated_count += 1

            await session.commit()

        logger.info(f"Evaluated {evaluated_count}/{len(predictions)} predictions")

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
    """Get BTC price closest to a target time (±30 min window, then fallback)."""
    # Try ±30 min window first, pick closest
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= target_time - timedelta(minutes=30))
        .where(Price.timestamp <= target_time + timedelta(minutes=30))
        .order_by(timestamp_diff_order(Price.timestamp, target_time))
        .limit(1)
    )
    price = result.scalar_one_or_none()
    if price:
        return price.close

    # Fallback: get latest price before target_time + 1h
    result = await session.execute(
        select(Price)
        .where(Price.timestamp <= target_time + timedelta(hours=1))
        .order_by(desc(Price.timestamp))
        .limit(1)
    )
    price = result.scalar_one_or_none()
    return price.close if price else None


async def collect_funding_data():
    """Collect and persist Binance perpetual funding rate & open interest (runs every 30 min)."""
    try:
        funding = await market_collector.get_funding_rate()
        oi_data = await market_collector.get_open_interest()

        if not funding and not oi_data:
            logger.debug("No funding/OI data received")
            return

        async with async_session() as session:
            record = FundingRate(
                timestamp=datetime.utcnow(),
                funding_rate=funding.get("funding_rate") if funding else None,
                mark_price=funding.get("mark_price") if funding else None,
                index_price=funding.get("index_price") if funding else None,
                next_funding_time=funding.get("next_funding_time") if funding else None,
                open_interest=oi_data.get("open_interest") if oi_data else None,
            )
            session.add(record)
            await session.commit()

        fr = funding.get("funding_rate", 0) if funding else 0
        oi = oi_data.get("open_interest", 0) if oi_data else 0
        logger.info(f"Funding data collected: rate={fr:.6f}, OI={oi:.2f} BTC")

    except Exception as e:
        logger.error(f"Funding data collection error: {e}")


async def collect_dominance_data():
    """Collect and persist BTC dominance & global market data (runs every hour)."""
    try:
        data = await market_collector.get_btc_dominance()

        if not data:
            logger.debug("No dominance data received")
            return

        async with async_session() as session:
            record = BtcDominance(
                timestamp=datetime.utcnow(),
                btc_dominance=data.get("btc_dominance"),
                eth_dominance=data.get("eth_dominance"),
                total_market_cap=data.get("total_market_cap"),
                total_volume=data.get("total_volume"),
                market_cap_change_24h=data.get("market_cap_change_24h"),
            )
            session.add(record)
            await session.commit()

        logger.info(f"BTC dominance collected: {data.get('btc_dominance', 0):.2f}%")

    except Exception as e:
        logger.error(f"Dominance collection error: {e}")


async def save_indicator_snapshot():
    """Compute and persist a full technical indicator snapshot (runs every hour).

    This saves the complete indicator state so historical indicator values
    are available for backtesting, model training, and trend analysis.
    """
    try:
        from app.features.technical import TechnicalFeatures

        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=400)
            result = await session.execute(
                select(Price).where(Price.timestamp >= since).order_by(Price.timestamp)
            )
            prices = result.scalars().all()

        if len(prices) < 30:
            logger.debug(f"Not enough price data for indicator snapshot ({len(prices)} candles)")
            return

        df = pd.DataFrame([
            {"open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume}
            for p in prices
        ])

        df = TechnicalFeatures.calculate_all(df)
        latest = df.iloc[-1]

        def safe(val):
            if pd.isna(val):
                return None
            v = float(val)
            return round(v, 6) if abs(v) < 1e12 else v

        indicators = {
            # Moving averages
            "ema_9": safe(latest.get("ema_9")),
            "ema_21": safe(latest.get("ema_21")),
            "ema_50": safe(latest.get("ema_50")),
            "ema_200": safe(latest.get("ema_200")),
            "sma_20": safe(latest.get("sma_20")),
            "sma_111": safe(latest.get("sma_111")),
            "sma_200": safe(latest.get("sma_200")),
            "sma_350": safe(latest.get("sma_350")),
            # Momentum
            "rsi": safe(latest.get("rsi")),
            "rsi_7": safe(latest.get("rsi_7")),
            "rsi_30": safe(latest.get("rsi_30")),
            "macd": safe(latest.get("macd")),
            "macd_signal": safe(latest.get("macd_signal")),
            "macd_hist": safe(latest.get("macd_hist")),
            "adx": safe(latest.get("adx")),
            "stoch_rsi_k": safe(latest.get("stoch_rsi_k")),
            "stoch_rsi_d": safe(latest.get("stoch_rsi_d")),
            "williams_r": safe(latest.get("williams_r")),
            "momentum_10": safe(latest.get("momentum_10")),
            "momentum_20": safe(latest.get("momentum_20")),
            # Volatility
            "bb_upper": safe(latest.get("bb_upper")),
            "bb_middle": safe(latest.get("bb_middle")),
            "bb_lower": safe(latest.get("bb_lower")),
            "bb_width": safe(latest.get("bb_width")),
            "bb_position": safe(latest.get("bb_position")),
            "atr": safe(latest.get("atr")),
            "volatility_24h": safe(latest.get("volatility_24h")),
            # Volume
            "obv": safe(latest.get("obv")),
            "vwap": safe(latest.get("vwap")),
            "volume_sma_20": safe(latest.get("volume_sma_20")),
            "volume_ratio": safe(latest.get("volume_ratio")),
            # Levels
            "pivot": safe(latest.get("pivot")),
            "support_1": safe(latest.get("support_1")),
            "resistance_1": safe(latest.get("resistance_1")),
            # Advanced
            "mayer_multiple": safe(latest.get("mayer_multiple")),
            "pi_cycle_ratio": safe(latest.get("pi_cycle_ratio")),
            "ema_cross": safe(latest.get("ema_cross")),
            "zscore_20": safe(latest.get("zscore_20")),
            # Ichimoku
            "ichimoku_tenkan": safe(latest.get("ichimoku_tenkan")),
            "ichimoku_kijun": safe(latest.get("ichimoku_kijun")),
            "ichimoku_senkou_a": safe(latest.get("ichimoku_senkou_a")),
            "ichimoku_senkou_b": safe(latest.get("ichimoku_senkou_b")),
            # Trend
            "trend_short": int(latest.get("trend_short", 0)),
            "trend_medium": int(latest.get("trend_medium", 0)),
            "trend_long": int(latest.get("trend_long", 0)),
            # ROC
            "roc_1": safe(latest.get("roc_1")),
            "roc_6": safe(latest.get("roc_6")),
            "roc_12": safe(latest.get("roc_12")),
            "roc_24": safe(latest.get("roc_24")),
            # Candlestick patterns
            "candle_doji": int(latest.get("candle_doji", 0)),
            "candle_hammer": int(latest.get("candle_hammer", 0)),
            "candle_inverted_hammer": int(latest.get("candle_inverted_hammer", 0)),
            "candle_bullish_engulfing": int(latest.get("candle_bullish_engulfing", 0)),
            "candle_bearish_engulfing": int(latest.get("candle_bearish_engulfing", 0)),
            "candle_morning_star": int(latest.get("candle_morning_star", 0)),
            "candle_evening_star": int(latest.get("candle_evening_star", 0)),
        }

        current_price = float(prices[-1].close)

        async with async_session() as session:
            snapshot = IndicatorSnapshot(
                timestamp=datetime.utcnow(),
                price=current_price,
                indicators=indicators,
            )
            session.add(snapshot)
            await session.commit()

        logger.info(f"Indicator snapshot saved (RSI={indicators.get('rsi')}, MACD={indicators.get('macd')})")

    except Exception as e:
        logger.error(f"Indicator snapshot error: {e}")


async def evaluate_quant_predictions():
    """Evaluate past quant predictions against actual prices (runs every hour)."""
    try:
        async with async_session() as session:
            # Find unevaluated quant predictions
            result = await session.execute(
                select(QuantPrediction)
                .where(
                    (QuantPrediction.was_correct_1h.is_(None)) |
                    (QuantPrediction.was_correct_24h.is_(None)) |
                    (QuantPrediction.was_correct_1w.is_(None)) |
                    (QuantPrediction.was_correct_1mo.is_(None))
                )
                .where(QuantPrediction.timestamp < datetime.utcnow() - timedelta(hours=1))
            )
            predictions = result.scalars().all()

            evaluated = 0
            for qp in predictions:
                # Evaluate each timeframe
                eval_configs = [
                    ("was_correct_1h", "actual_price_1h", timedelta(hours=1)),
                    ("was_correct_24h", "actual_price_24h", timedelta(hours=24)),
                    ("was_correct_1w", "actual_price_1w", timedelta(hours=168)),
                    ("was_correct_1mo", "actual_price_1mo", timedelta(hours=720)),
                ]
                for correct_field, price_field, delta in eval_configs:
                    if getattr(qp, correct_field) is not None:
                        continue
                    eval_time = qp.timestamp + delta
                    if datetime.utcnow() >= eval_time:
                        actual = await _get_price_at(session, eval_time)
                        if actual:
                            setattr(qp, price_field, actual)
                            actual_dir = "bullish" if actual > qp.current_price else "bearish"
                            was_correct = (qp.direction == actual_dir) or (
                                qp.direction == "neutral" and abs(actual - qp.current_price) / qp.current_price < 0.005
                            )
                            setattr(qp, correct_field, was_correct)
                            evaluated += 1

            await session.commit()

        if evaluated > 0:
            logger.info(f"Evaluated {evaluated} quant predictions")

    except Exception as e:
        logger.error(f"Quant prediction evaluation error: {e}")


async def cleanup_old_data():
    """Clean up old data with tiered retention policy (runs daily).

    Retention:
    - Predictions, Signals, QuantPredictions: NEVER deleted (core history)
    - EventImpacts: NEVER deleted (long-term memory)
    - PredictionContext, NewsPriceCorrelation: NEVER deleted (training data)
    - ModelPerformanceLog, FeatureImportanceLog: NEVER deleted (training data)
    - ApiKey, ApiUsageLog: NEVER deleted (billing data)
    - Price, News, Features: 90 days
    - Funding rates, Dominance, Indicators: 180 days
    - MacroData, OnChainData: 180 days
    - InfluencerTweets: 90 days
    - AlertLogs: 90 days
    """
    try:
        cutoff_90d = datetime.utcnow() - timedelta(days=90)
        cutoff_180d = datetime.utcnow() - timedelta(days=180)

        async with async_session() as session:
            # 90-day retention
            for model in [Price, News, Feature, InfluencerTweet, AlertLog]:
                await session.execute(
                    model.__table__.delete().where(model.timestamp < cutoff_90d)
                )

            # 180-day retention for less frequent data
            for model in [MacroData, OnChainData, FundingRate, BtcDominance, IndicatorSnapshot]:
                await session.execute(
                    model.__table__.delete().where(model.timestamp < cutoff_180d)
                )

            await session.commit()

        logger.info("Old data cleaned up (90d: price/news/features, 180d: macro/indicators)")

    except Exception as e:
        logger.error(f"Cleanup error: {e}")


async def auto_retrain_models():
    """Auto-retrain models when accuracy degrades or enough new data exists (runs every 6h).

    Triggers (more aggressive for continuous learning):
    - Accuracy dropped below 55% (was 52%)
    - More than 12 hours since last training (was 24h)
    - Never trained but have enough data (168+ feature snapshots)
    - Significant new data: 50+ new evaluated predictions since last train
    """
    try:
        from app.models.trainer import ModelTrainer
        trainer = ModelTrainer(model_dir=settings.model_dir)

        result = await trainer.evaluate_and_retrain_if_needed()

        if result.get("retrain"):
            # Hot-swap: reset ensemble so it reloads with new weights
            global _ensemble
            _ensemble = None  # Will reload on next prediction
            logger.info(f"Models retrained and ensemble reset: {result}")
        else:
            logger.info(f"Retrain check: {result.get('status')} (accuracy={result.get('accuracy', 'N/A')})")

    except Exception as e:
        logger.error(f"Auto-retrain error: {e}", exc_info=True)


# ────────────────────────────────────────────────────────────────
#  ADVISOR JOBS
# ────────────────────────────────────────────────────────────────

async def run_advisor_check():
    """Run advisor check after each prediction cycle (every 30 min).

    Fetches latest prediction, signal, quant, indicators, and price,
    then for each advisor user: detect new entries, size, plan, save, alert.
    """
    if not settings.advisor_enabled:
        return

    try:
        from app.advisor.entry_detector import check_entry
        from app.advisor.trade_planner import build_trade_plan, format_trade_plan_message
        from app.advisor.portfolio import get_or_create_portfolio

        # Fetch latest data
        async with async_session() as session:
            # Latest prediction (1h)
            result = await session.execute(
                select(Prediction)
                .where(Prediction.timeframe == "1h")
                .order_by(desc(Prediction.timestamp))
                .limit(1)
            )
            pred_row = result.scalar_one_or_none()

            # Latest signal (1h)
            result = await session.execute(
                select(Signal)
                .where(Signal.timeframe == "1h")
                .order_by(desc(Signal.timestamp))
                .limit(1)
            )
            signal_row = result.scalar_one_or_none()

            # Latest quant prediction
            result = await session.execute(
                select(QuantPrediction).order_by(desc(QuantPrediction.timestamp)).limit(1)
            )
            quant_row = result.scalar_one_or_none()

            # Latest indicator snapshot
            result = await session.execute(
                select(IndicatorSnapshot).order_by(desc(IndicatorSnapshot.timestamp)).limit(1)
            )
            ind_row = result.scalar_one_or_none()

            # Current price
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            price_row = result.scalar_one_or_none()

            # Recent high-severity events
            since_1h = datetime.utcnow() - timedelta(hours=1)
            result = await session.execute(
                select(EventImpact)
                .where(EventImpact.timestamp >= since_1h)
                .where(EventImpact.severity >= 7)
            )
            events = [
                {"severity": e.severity, "sentiment_score": e.sentiment_score, "category": e.category}
                for e in result.scalars().all()
            ]

        if not pred_row or not signal_row or not price_row:
            logger.info("Advisor: missing prediction/signal/price data")
            return

        current_price = float(price_row.close)
        atr_value = ind_row.indicators.get("atr", current_price * 0.02) if ind_row else current_price * 0.02

        # Build prediction dict
        prediction = {
            "direction": pred_row.direction,
            "confidence": pred_row.confidence,
            "model_outputs": pred_row.model_outputs or {},
            "magnitude_pct": pred_row.predicted_change_pct,
        }

        # Build signal dict
        signal = {
            "action": signal_row.action,
            "entry_price": signal_row.entry_price,
            "target_price": signal_row.target_price,
            "stop_loss": signal_row.stop_loss,
            "risk_rating": signal_row.risk_rating,
            "risk_reward_ratio": round(
                abs(signal_row.target_price - signal_row.entry_price)
                / max(abs(signal_row.entry_price - signal_row.stop_loss), 0.01), 2
            ),
        }

        # Build quant dict
        quant = None
        if quant_row:
            quant = {
                "direction": quant_row.direction,
                "confidence": quant_row.confidence,
                "composite_score": quant_row.composite_score,
                "action": quant_row.action,
                "agreement_ratio": quant_row.agreement_ratio or 0,
            }

        indicators = ind_row.indicators if ind_row else None

        # Auto-create portfolios for all registered users who don't have one yet
        async with async_session() as session:
            result = await session.execute(select(BotUser.telegram_id))
            all_user_ids = {r[0] for r in result.all()}

            result = await session.execute(select(PortfolioState.telegram_id))
            existing_portfolio_ids = {r[0] for r in result.all()}

        missing_ids = all_user_ids - existing_portfolio_ids
        if missing_ids:
            for uid in missing_ids:
                await get_or_create_portfolio(uid)
            logger.info(f"Advisor: auto-created portfolios for {len(missing_ids)} users")

        # Get all advisor users (all active portfolios)
        async with async_session() as session:
            result = await session.execute(select(PortfolioState).where(PortfolioState.is_active == True))
            portfolios = result.scalars().all()

        if not portfolios:
            logger.info("Advisor: no active portfolios")
            return

        # For each user with a portfolio, check for entry
        new_plans = 0
        for portfolio in portfolios:
            try:
                # Get user's open trades (exclude mock/paper trades)
                async with async_session() as session:
                    result = await session.execute(
                        select(TradeAdvice).where(
                            TradeAdvice.telegram_id == portfolio.telegram_id,
                            TradeAdvice.status.in_(["opened", "partial_tp", "pending"]),
                            TradeAdvice.is_mock == False,
                        )
                    )
                    open_trades = result.scalars().all()

                # Check for entry
                entry = check_entry(
                    portfolio=portfolio,
                    prediction=prediction,
                    signal=signal,
                    quant=quant,
                    indicators=indicators,
                    open_trades=open_trades,
                    events=events,
                )

                if not entry:
                    continue

                # Build trade plan
                plan = build_trade_plan(
                    entry=entry,
                    portfolio=portfolio,
                    current_price=current_price,
                    atr=atr_value,
                )

                # Save trade advice
                async with async_session() as session:
                    trade_advice = TradeAdvice(
                        telegram_id=portfolio.telegram_id,
                        direction=plan["direction"],
                        entry_price=plan["entry_price"],
                        entry_zone_low=plan["entry_zone_low"],
                        entry_zone_high=plan["entry_zone_high"],
                        stop_loss=plan["stop_loss"],
                        take_profit_1=plan["take_profit_1"],
                        take_profit_2=plan["take_profit_2"],
                        take_profit_3=plan["take_profit_3"],
                        leverage=plan["leverage"],
                        position_size_usdt=plan["position_size_usdt"],
                        position_size_pct=plan["position_size_pct"],
                        risk_amount_usdt=plan["risk_amount_usdt"],
                        risk_reward_ratio=plan["risk_reward_ratio"],
                        confidence=plan["confidence"],
                        risk_rating=plan["risk_rating"],
                        reasoning=plan["reasoning"],
                        models_agreeing=plan["models_agreeing"],
                        urgency=plan["urgency"],
                        timeframe=plan["timeframe"],
                        prediction_id=pred_row.id,
                        signal_id=signal_row.id,
                        quant_prediction_id=quant_row.id if quant_row else None,
                        status="pending",
                    )
                    session.add(trade_advice)
                    await session.commit()
                    await session.refresh(trade_advice)

                # Send Telegram alert
                try:
                    from app.advisor.trade_planner import format_trade_plan_message
                    from app.bot.keyboards import trade_action_keyboard

                    msg = format_trade_plan_message(trade_advice)
                    await _send_advisor_alert(
                        portfolio.telegram_id,
                        msg,
                        reply_markup=trade_action_keyboard(trade_advice.id),
                    )
                except Exception as e:
                    logger.error(f"Advisor alert send error: {e}")

                new_plans += 1

            except Exception as e:
                logger.error(f"Advisor check error for user {portfolio.telegram_id}: {e}")

        if new_plans > 0:
            logger.info(f"Advisor: generated {new_plans} new trade plans")

    except Exception as e:
        logger.error(f"Advisor check error: {e}", exc_info=True)


async def run_trade_management():
    """Monitor open trades for SL/TP/reversal alerts (runs every 5 min)."""
    if not settings.advisor_enabled:
        return

    try:
        from app.advisor.trade_manager import check_open_trades

        # Get current price
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            price_row = result.scalar_one_or_none()

            # Latest 1h prediction for reversal detection
            result = await session.execute(
                select(Prediction)
                .where(Prediction.timeframe == "1h")
                .order_by(desc(Prediction.timestamp))
                .limit(1)
            )
            pred_row = result.scalar_one_or_none()

        if not price_row:
            return

        current_price = float(price_row.close)
        prediction = None
        if pred_row:
            prediction = {
                "direction": pred_row.direction,
                "confidence": pred_row.confidence,
            }

        alerts = await check_open_trades(current_price, prediction)

        for alert in alerts:
            try:
                await _send_advisor_alert(
                    alert["telegram_id"],
                    alert["message"],
                )
            except Exception as e:
                logger.error(f"Trade management alert error: {e}")

        if alerts:
            logger.info(f"Trade management: sent {len(alerts)} alerts")

    except Exception as e:
        logger.error(f"Trade management error: {e}", exc_info=True)


async def _send_advisor_alert(telegram_id: int, text: str, reply_markup=None):
    """Send an advisor alert via Telegram bot."""
    try:
        if not settings.telegram_bot_token:
            logger.debug("No bot token, skipping advisor alert")
            return

        from aiogram import Bot
        bot = Bot(token=settings.telegram_bot_token)
        try:
            await bot.send_message(
                telegram_id,
                text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        finally:
            await bot.session.close()

    except Exception as e:
        logger.error(f"Advisor alert send error for {telegram_id}: {e}")


# ────────────────────────────────────────────────────────────────
#  SUBSCRIPTION EXPIRY CHECK
# ────────────────────────────────────────────────────────────────

async def check_subscription_expiry():
    """Notify users whose trial or subscription has expired (runs daily)."""
    if not settings.subscription_enabled:
        return

    try:
        from app.bot.subscription import is_premium

        now = datetime.utcnow()

        async with async_session() as session:
            # Users who had a trial or subscription that recently expired (last 25h)
            # and haven't renewed
            yesterday = now - timedelta(hours=25)

            result = await session.execute(
                select(BotUser).where(BotUser.subscribed == True)
            )
            users = result.scalars().all()

        expired_users = []
        for user in users:
            if is_premium(user):
                continue
            # Check if trial or sub expired recently (within last 25h)
            trial_just_expired = (
                user.trial_end
                and user.trial_end <= now
                and user.trial_end >= yesterday
            )
            sub_just_expired = (
                user.subscription_end
                and user.subscription_end <= now
                and user.subscription_end >= yesterday
            )
            if trial_just_expired or sub_just_expired:
                expired_users.append(user)

        if not expired_users:
            return

        if not settings.telegram_bot_token:
            return

        from aiogram import Bot
        bot = Bot(token=settings.telegram_bot_token)
        try:
            for user in expired_users:
                try:
                    await bot.send_message(
                        user.telegram_id,
                        "Your BTC Seer Premium access has expired.\n\n"
                        "Use /subscribe to continue getting AI predictions, "
                        "trading signals, and alerts.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.debug(f"Expiry notification failed for {user.telegram_id}: {e}")
        finally:
            await bot.session.close()

        logger.info(f"Subscription expiry: notified {len(expired_users)} users")

    except Exception as e:
        logger.error(f"Subscription expiry check error: {e}")
