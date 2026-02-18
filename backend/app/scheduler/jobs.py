import asyncio
import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import select, desc, func

from app.config import settings
from app.database import (
    async_session, Price, News, Feature, Prediction, Signal,
    MacroData, OnChainData, InfluencerTweet, EventImpact, QuantPrediction,
    FundingRate, BtcDominance, IndicatorSnapshot, AlertLog, ModelVersion,
    PortfolioState, TradeAdvice, TradeResult, BotUser,
    PredictionContext, ModelPerformanceLog, WhaleTransaction,
    PredictionAnalysis, MarketingMetrics, SupportTicket,
    PaymentHistory, ApiUsageLog, Referral,
    timestamp_diff_order,
)
from app.collectors import (
    MarketCollector, NewsCollector, FearGreedCollector,
    MacroCollector, OnChainCollector, RedditCollector,
    BinanceNewsCollector, InfluencerCollector,
    ETFCollector, ExchangeFlowCollector,
    DerivativesExtendedCollector, StablecoinCollector,
    WhaleCollector,
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
whale_collector = WhaleCollector()
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


async def deep_backfill_historical_prices():
    """Deep backfill: fetch full BTC price history from 2009 to present.

    Runs once on startup when oldest Price row > 2014.
    Uses HistoricalBTCCollector to fetch from early JSON + CoinGecko + Binance.
    """
    try:
        from app.collectors.historical_btc import HistoricalBTCCollector

        # Check if we need deep backfill
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(Price.timestamp).limit(1)
            )
            oldest = result.scalar_one_or_none()

        if oldest and oldest.timestamp.year <= 2014:
            logger.info("Deep backfill: Already have pre-2014 data, skipping")
            return

        logger.info("Deep backfill: Starting comprehensive historical price fetch...")
        collector = HistoricalBTCCollector()

        try:
            all_prices = await collector.fetch_all_historical()
        finally:
            await collector.close()

        if not all_prices:
            logger.warning("Deep backfill: No historical prices fetched")
            return

        # Insert into Price table, skipping existing dates
        async with async_session() as session:
            result = await session.execute(select(Price.timestamp))
            existing_dates = set()
            for row in result.all():
                existing_dates.add(row[0].strftime("%Y-%m-%d"))

            inserted = 0
            for p in all_prices:
                day_key = p["timestamp"].strftime("%Y-%m-%d")
                if day_key in existing_dates:
                    continue

                price = Price(
                    timestamp=p["timestamp"],
                    open=p["open"],
                    high=p["high"],
                    low=p["low"],
                    close=p["close"],
                    volume=p["volume"],
                    source="historical_backfill",
                )
                session.add(price)
                existing_dates.add(day_key)
                inserted += 1

            await session.commit()

        logger.info(f"Deep backfill: Inserted {inserted} historical price records")

        # Trigger ML retrain with extended features after backfill
        if inserted > 100:
            try:
                from app.models.trainer import ModelTrainer
                trainer = ModelTrainer()
                result = await trainer.train_all()
                logger.info(f"Deep backfill: Post-backfill retrain result: {result.get('status')}")
            except Exception as e:
                logger.warning(f"Deep backfill: Post-backfill retrain failed (non-critical): {e}")

    except Exception as e:
        logger.error(f"Deep backfill error: {e}", exc_info=True)


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
    """Collect and store BTC price data (runs every minute).

    Uses Binance klines endpoint for proper per-candle OHLC instead of the
    24hr ticker (which returns rolling 24h open/high/low — wrong for candle
    resampling in Elliott Wave etc.).
    """
    try:
        # Fetch latest closed 1-minute kline for proper OHLC
        kline_data = await market_collector.fetch_json(
            market_collector.BINANCE_KLINES_URL,
            params={"symbol": "BTCUSDT", "interval": "1m", "limit": 2},
        )

        if not kline_data or len(kline_data) < 2:
            logger.warning("No kline data received")
            return

        # Use the second-to-last candle (last closed candle)
        k = kline_data[-2]
        from datetime import timezone
        candle_ts = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).replace(tzinfo=None)

        async with async_session() as session:
            price = Price(
                timestamp=candle_ts,
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
                source="binance",
            )
            session.add(price)
            await session.commit()

        logger.info(f"Price collected: ${k[4]} (kline OHLC)")

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

        # Fetch M2 money supply
        m2_supply = None
        try:
            m2_supply = await macro_collector.fetch_m2_supply()
        except Exception as e:
            logger.debug(f"M2 supply fetch error: {e}")

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
                m2_supply=m2_supply,
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


async def generate_prediction(timeframes: list[str] | None = None):
    """Generate ML prediction for specified timeframes.

    If timeframes is None, generates for all timeframes (used on startup).
    Otherwise filters ensemble output to only the requested timeframes.

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

        # ── Whale data aggregation ──
        whale_raw = None
        try:
            now_wh = datetime.utcnow()
            since_1h_wh = now_wh - timedelta(hours=1)
            since_24h_wh = now_wh - timedelta(hours=24)

            async with async_session() as sess_wh:
                r1h = await sess_wh.execute(
                    select(WhaleTransaction).where(WhaleTransaction.timestamp >= since_1h_wh)
                )
                txs_1h = r1h.scalars().all()

                r24h = await sess_wh.execute(
                    select(WhaleTransaction).where(WhaleTransaction.timestamp >= since_24h_wh)
                )
                txs_24h = r24h.scalars().all()

                # Historical accuracy
                r_eval = await sess_wh.execute(
                    select(WhaleTransaction).where(
                        WhaleTransaction.evaluated_1h == True,
                        WhaleTransaction.direction_was_predictive.isnot(None),
                    )
                )
                eval_txs = r_eval.scalars().all()

            def _count_dir(txs, d):
                return sum(1 for t in txs if t.direction == d)

            in_1h = _count_dir(txs_1h, "exchange_in")
            out_1h = _count_dir(txs_1h, "exchange_out")
            in_24h = _count_dir(txs_24h, "exchange_in")
            out_24h = _count_dir(txs_24h, "exchange_out")
            net_1h = sum(t.amount_btc for t in txs_1h if t.direction == "exchange_in") - sum(t.amount_btc for t in txs_1h if t.direction == "exchange_out")
            net_24h = sum(t.amount_btc for t in txs_24h if t.direction == "exchange_in") - sum(t.amount_btc for t in txs_24h if t.direction == "exchange_out")

            total_dir_1h = in_1h + out_1h
            directional_signal = (out_1h - in_1h) / total_dir_1h if total_dir_1h > 0 else 0.0
            accuracy = sum(1 for t in eval_txs if t.direction_was_predictive) / len(eval_txs) if eval_txs else 0.5

            whale_raw = {
                "whale_tx_1h_count": len(txs_1h),
                "whale_tx_24h_count": len(txs_24h),
                "whale_exchange_in_1h": in_1h,
                "whale_exchange_out_1h": out_1h,
                "whale_exchange_in_24h": in_24h,
                "whale_exchange_out_24h": out_24h,
                "whale_net_flow_1h_btc": round(net_1h, 2),
                "whale_net_flow_24h_btc": round(net_24h, 2),
                "whale_avg_severity_1h": sum(t.severity for t in txs_1h) / len(txs_1h) if txs_1h else 0,
                "whale_avg_severity_24h": sum(t.severity for t in txs_24h) / len(txs_24h) if txs_24h else 0,
                "whale_directional_signal": round(directional_signal, 4),
                "whale_historical_accuracy": round(accuracy, 4),
            }
        except Exception as e:
            logger.debug(f"Whale data aggregation error: {e}")

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
            whale_data=whale_raw,
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
            logger.error(f"Ensemble prediction failed: {e}", exc_info=True)
            # Fallback: Use simple momentum-based predictions when ensemble fails
            recent_change = ((prices[-1].close - prices[-24].close) / prices[-24].close * 100) if len(prices) >= 24 else 0
            direction = "bullish" if recent_change > 0 else "bearish"
            predictions = {
                "1h": {"direction": direction, "confidence": 50, "magnitude_pct": recent_change * 0.1, "model_outputs": {}},
                "4h": {"direction": direction, "confidence": 45, "magnitude_pct": recent_change * 0.3, "model_outputs": {}},
                "24h": {"direction": direction, "confidence": 40, "magnitude_pct": recent_change * 0.8, "model_outputs": {}},
                "1w": {"direction": direction, "confidence": 35, "magnitude_pct": recent_change * 1.5, "model_outputs": {}},
                "1mo": {"direction": direction, "confidence": 30, "magnitude_pct": recent_change * 3.0, "model_outputs": {}},
            }

        current_price = float(prices[-1].close)
        atr = features.get("atr", current_price * 0.02)
        volatility = features.get("volatility_24h", 2.0)

        # Filter to requested timeframes only
        if timeframes is not None:
            predictions = {tf: pred for tf, pred in predictions.items() if tf in timeframes}

        if not predictions:
            logger.warning(f"No predictions for requested timeframes: {timeframes}")
            return

        # Apply learned pattern adjustments
        try:
            from app.models.pattern_learner import get_active_adjustments
            for tf, pred in predictions.items():
                adjustments = await get_active_adjustments(tf, features, pred.get("model_outputs", {}))
                if adjustments["confidence_modifier"] != 1.0 or adjustments["direction_bias"] != 0.0:
                    original_conf = pred["confidence"]
                    pred["confidence"] = max(10, min(95, pred["confidence"] * adjustments["confidence_modifier"]))
                    logger.info(
                        f"Pattern adjustment [{tf}]: confidence {original_conf:.0f}→{pred['confidence']:.0f} "
                        f"(modifier={adjustments['confidence_modifier']:.2f}, "
                        f"bias={adjustments['direction_bias']:+.3f})"
                    )
        except Exception as e:
            logger.debug(f"Pattern adjustment error (non-critical): {e}")

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


# ── Time-aligned prediction wrappers ──

async def generate_prediction_1h():
    """Generate ML prediction for 1h timeframe only (runs every hour at :00)."""
    await generate_prediction(timeframes=["1h"])


async def generate_prediction_4h():
    """Generate ML prediction for 4h timeframe only (runs every 4h at :02)."""
    await generate_prediction(timeframes=["4h"])


async def generate_prediction_24h():
    """Generate ML prediction for 24h/1w/1mo timeframes (runs daily at 00:04)."""
    await generate_prediction(timeframes=["24h", "1w", "1mo"])


async def generate_quant_prediction(timeframes: list[str] | None = None):
    """Generate quant theory-based prediction for specified timeframes.

    If timeframes is None, generates for all timeframes (used on startup).

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


# ── Time-aligned quant prediction wrappers ──

async def generate_quant_prediction_1h():
    """Generate quant prediction for 1h timeframe (runs every hour at :01)."""
    await generate_quant_prediction(timeframes=["1h"])


async def generate_quant_prediction_4h():
    """Generate quant prediction for 4h timeframe (runs every 4h at :03)."""
    await generate_quant_prediction(timeframes=["4h"])


async def generate_quant_prediction_24h():
    """Generate quant prediction for 24h/1w/1mo timeframes (runs daily at 00:05)."""
    await generate_quant_prediction(timeframes=["24h", "1w", "1mo"])


async def evaluate_predictions(timeframe_filter: str | None = None):
    """Evaluate past predictions against actual prices with deep error analysis.

    Args:
        timeframe_filter: If set, only evaluate predictions for this timeframe (e.g. "1h", "4h", "24h").
    """
    try:
        async with async_session() as session:
            # Find unevaluated predictions older than their timeframe
            query = (
                select(Prediction)
                .where(Prediction.was_correct.is_(None))
                .where(Prediction.timestamp < datetime.utcnow() - timedelta(hours=1))
            )
            if timeframe_filter:
                query = query.where(Prediction.timeframe == timeframe_filter)

            result = await session.execute(query)
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

                # ── Compute error metrics ──
                if pred.predicted_price and pred.predicted_price > 0:
                    pred.error_pct = (actual_price - pred.predicted_price) / pred.predicted_price * 100
                else:
                    pred.error_pct = None

                # ── Classify volatility regime ──
                try:
                    # Look up PredictionContext for features at prediction time
                    ctx_result = await session.execute(
                        select(PredictionContext)
                        .where(PredictionContext.prediction_id == pred.id)
                        .limit(1)
                    )
                    ctx = ctx_result.scalar_one_or_none()

                    features_snapshot = ctx.features if ctx else {}
                    vol_24h = features_snapshot.get("volatility_24h", 2.0) if features_snapshot else 2.0
                    rsi_val = features_snapshot.get("rsi", 50.0) if features_snapshot else 50.0

                    if vol_24h < 1.0:
                        pred.volatility_regime = "low"
                    elif vol_24h < 3.0:
                        pred.volatility_regime = "normal"
                    elif vol_24h < 6.0:
                        pred.volatility_regime = "high"
                    else:
                        pred.volatility_regime = "extreme"

                    # ── Classify trend state ──
                    sma_20 = features_snapshot.get("sma_20", 0) if features_snapshot else 0
                    sma_50 = features_snapshot.get("sma_50", 0) if features_snapshot else 0
                    if sma_20 and sma_50 and sma_20 > 0 and sma_50 > 0:
                        ratio = sma_20 / sma_50
                        if ratio > 1.01:
                            pred.trend_state = "trending_up"
                        elif ratio < 0.99:
                            pred.trend_state = "trending_down"
                        else:
                            pred.trend_state = "ranging"
                    else:
                        pred.trend_state = "ranging"

                    # ── Per-model results analysis ──
                    per_model = {}
                    model_outputs = pred.model_outputs or {}
                    model_count = 0
                    agree_count = 0
                    dissenting = []

                    for model_name, model_data in model_outputs.items():
                        if not isinstance(model_data, dict):
                            continue
                        model_dir = model_data.get("direction", "neutral")
                        model_prob = model_data.get("bullish_prob", model_data.get("prob"))
                        model_correct = (model_dir == actual_direction)

                        per_model[model_name] = {
                            "predicted": model_dir,
                            "correct": model_correct,
                            "prob": model_prob,
                        }

                        model_count += 1
                        if model_dir == pred.direction:
                            agree_count += 1
                        else:
                            dissenting.append(model_name)

                        # ── Populate ModelPerformanceLog (critical fix) ──
                        session.add(ModelPerformanceLog(
                            prediction_id=pred.id,
                            model_name=model_name,
                            timeframe=pred.timeframe,
                            predicted_direction=model_dir,
                            predicted_prob=model_prob,
                            actual_direction=actual_direction,
                            was_correct=model_correct,
                            confidence=pred.confidence,
                        ))

                    # Also log ensemble result
                    session.add(ModelPerformanceLog(
                        prediction_id=pred.id,
                        model_name="ensemble",
                        timeframe=pred.timeframe,
                        predicted_direction=pred.direction,
                        predicted_prob=None,
                        actual_direction=actual_direction,
                        was_correct=pred.was_correct,
                        confidence=pred.confidence,
                    ))

                    agreement_score = agree_count / model_count if model_count > 0 else 0.0

                    # Extract top features
                    top_features = None
                    if features_snapshot:
                        # Get features with highest absolute values (normalized)
                        feature_items = {
                            k: v for k, v in features_snapshot.items()
                            if isinstance(v, (int, float)) and not np.isnan(v)
                        }
                        if feature_items:
                            sorted_features = sorted(feature_items.items(), key=lambda x: abs(x[1]), reverse=True)
                            top_features = dict(sorted_features[:10])

                    # ── Create PredictionAnalysis record ──
                    analysis = PredictionAnalysis(
                        prediction_id=pred.id,
                        timeframe=pred.timeframe,
                        error_pct=pred.error_pct,
                        abs_error_pct=abs(pred.error_pct) if pred.error_pct is not None else None,
                        direction_correct=pred.was_correct,
                        per_model_results=per_model if per_model else None,
                        volatility_regime=pred.volatility_regime,
                        trend_state=pred.trend_state,
                        rsi_at_prediction=rsi_val,
                        top_features=top_features,
                        model_agreement_score=agreement_score,
                        dissenting_models=",".join(dissenting) if dissenting else None,
                    )
                    session.add(analysis)

                    pred.evaluation_notes = {
                        "error_pct": round(pred.error_pct, 4) if pred.error_pct is not None else None,
                        "volatility": pred.volatility_regime,
                        "trend": pred.trend_state,
                        "agreement": round(agreement_score, 2),
                        "dissenting": dissenting,
                    }

                except Exception as e:
                    logger.debug(f"Error analysis for prediction {pred.id}: {e}")

                evaluated_count += 1

            await session.commit()

        tf_label = f" [{timeframe_filter}]" if timeframe_filter else ""
        logger.info(f"Evaluated{tf_label} {evaluated_count}/{len(predictions)} predictions")

    except Exception as e:
        logger.error(f"Prediction evaluation error: {e}", exc_info=True)


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


async def _store_whale_transactions(transactions: list[dict], source_label: str):
    """Shared helper to store whale transaction dicts into the database."""
    if not transactions:
        return 0

    async with async_session() as session:
        price_row = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price = price_row.scalar_one_or_none()
        current_price = price.close if price else None

        stored = 0
        for tx_data in transactions:
            existing = await session.execute(
                select(WhaleTransaction.id).where(
                    WhaleTransaction.tx_hash == tx_data["tx_hash"]
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            amount_usd = tx_data["amount_btc"] * current_price if current_price else None

            whale_tx = WhaleTransaction(
                tx_hash=tx_data["tx_hash"],
                timestamp=datetime.fromisoformat(tx_data["timestamp"]) if tx_data.get("timestamp") else datetime.utcnow(),
                amount_btc=tx_data["amount_btc"],
                amount_usd=amount_usd,
                direction=tx_data["direction"],
                from_entity=tx_data["from_entity"],
                to_entity=tx_data["to_entity"],
                entity_name=tx_data.get("entity_name"),
                entity_type=tx_data.get("entity_type"),
                entity_wallet=tx_data.get("entity_wallet"),
                severity=tx_data["severity"],
                btc_price_at_tx=current_price,
                from_address=tx_data.get("from_address"),
                to_address=tx_data.get("to_address"),
                source=tx_data.get("source", source_label),
                raw_data=tx_data.get("raw_data"),
            )
            session.add(whale_tx)
            stored += 1

            # For severity >= 9, also create EventImpact
            if tx_data["severity"] >= 9 and current_price:
                entity_label = tx_data.get("entity_name") or tx_data["from_entity"]
                if entity_label == "unknown":
                    entity_label = tx_data["to_entity"]
                direction_label = tx_data["direction"].replace("_", " ")
                title = f"Whale {direction_label}: {tx_data['amount_btc']:.0f} BTC"
                if entity_label and entity_label != "unknown":
                    title += f" ({entity_label})"
                if amount_usd:
                    title += f" ${amount_usd:,.0f}"

                event = EventImpact(
                    timestamp=whale_tx.timestamp,
                    title=title,
                    source="whale_tracker",
                    category="whale_movement",
                    subcategory=tx_data["direction"],
                    keywords=f"whale,{tx_data['direction']},{tx_data['from_entity']},{tx_data['to_entity']}",
                    severity=tx_data["severity"],
                    sentiment_score=-0.5 if tx_data["direction"] == "exchange_in" else 0.5 if tx_data["direction"] == "exchange_out" else 0.0,
                    price_at_event=current_price,
                )
                session.add(event)

        await session.commit()

    if stored:
        logger.info(f"Whale transactions stored ({source_label}): {stored} new")
    return stored


async def resolve_unknown_whale_addresses():
    """Resolve unknown whale addresses using WalletExplorer + Blockchair APIs (runs every 30 min).

    Finds whale txs where entity_name IS NULL and from_address/to_address exist,
    resolves them via online APIs, and updates entity info on the transaction.
    Limited to 20 addresses per run to stay within rate limits.
    """
    from app.collectors.address_resolver import AddressResolver

    resolver = AddressResolver()
    try:
        async with async_session() as session:
            # Find txs with unknown entities but known addresses
            result = await session.execute(
                select(WhaleTransaction).where(
                    WhaleTransaction.entity_name.is_(None),
                    (WhaleTransaction.from_address.isnot(None)) | (WhaleTransaction.to_address.isnot(None)),
                ).order_by(desc(WhaleTransaction.timestamp)).limit(40)
            )
            txs = result.scalars().all()

            if not txs:
                return

            resolved_count = 0
            addresses_checked = 0
            max_addresses = 20

            for tx in txs:
                if addresses_checked >= max_addresses:
                    break

                from_label = None
                to_label = None

                # Try resolving from_address
                if tx.from_address and addresses_checked < max_addresses:
                    from_label = await resolver.resolve(tx.from_address, session)
                    addresses_checked += 1

                # Try resolving to_address
                if tx.to_address and addresses_checked < max_addresses:
                    to_label = await resolver.resolve(tx.to_address, session)
                    addresses_checked += 1

                # Update transaction if we found labels
                if from_label or to_label:
                    if from_label:
                        tx.from_entity = from_label["name"]
                    if to_label:
                        tx.to_entity = to_label["name"]

                    # Determine primary entity and direction
                    primary = to_label or from_label
                    tx.entity_name = primary["name"]
                    tx.entity_type = primary.get("type")
                    tx.entity_wallet = primary.get("wallet")

                    # Re-classify direction
                    if from_label and not to_label:
                        tx.direction = "exchange_out"
                    elif not from_label and to_label:
                        tx.direction = "exchange_in"
                    elif from_label and to_label:
                        tx.direction = "exchange_in"

                    resolved_count += 1

            await session.commit()

            if resolved_count:
                logger.info(f"Address resolver: resolved {resolved_count} whale txs ({addresses_checked} addresses checked)")

    except Exception as e:
        logger.error(f"Address resolution error: {e}")
    finally:
        await resolver.close()


async def collect_whale_transactions():
    """Collect and store large BTC transactions (runs every 10 min).

    Uses Blockchair for discovery + BTCScan for address details + mempool.space fallback.
    """
    try:
        result = await whale_collector.collect()
        await _store_whale_transactions(result.get("transactions", []), "blockchair+btcscan")
    except Exception as e:
        logger.error(f"Whale collection error: {e}")


async def monitor_entity_wallets():
    """Monitor known entity wallets for new large transactions (runs every 10 min, offset by 5 min)."""
    try:
        result = await whale_collector.monitor_known_addresses()
        await _store_whale_transactions(result.get("transactions", []), "entity_monitor")
    except Exception as e:
        logger.error(f"Entity wallet monitor error: {e}")


async def evaluate_whale_impacts():
    """Evaluate price impact of whale transactions (runs every 30 min)."""
    try:
        async with async_session() as session:
            now = datetime.utcnow()

            # Find unevaluated whale txs older than the timeframe
            for timeframe, hours, eval_col, change_col in [
                ("1h", 1, "evaluated_1h", "change_pct_1h"),
                ("4h", 4, "evaluated_4h", "change_pct_4h"),
                ("24h", 24, "evaluated_24h", "change_pct_24h"),
            ]:
                cutoff = now - timedelta(hours=hours)
                result = await session.execute(
                    select(WhaleTransaction).where(
                        getattr(WhaleTransaction, eval_col) == False,
                        WhaleTransaction.timestamp <= cutoff,
                        WhaleTransaction.btc_price_at_tx.isnot(None),
                    ).limit(50)
                )
                txs = result.scalars().all()

                for tx in txs:
                    target_time = tx.timestamp + timedelta(hours=hours)
                    price_result = await session.execute(
                        select(Price)
                        .order_by(timestamp_diff_order(Price.timestamp, target_time))
                        .limit(1)
                    )
                    price_row = price_result.scalar_one_or_none()

                    if price_row and tx.btc_price_at_tx:
                        change_pct = ((price_row.close - tx.btc_price_at_tx) / tx.btc_price_at_tx) * 100
                        setattr(tx, change_col, round(change_pct, 4))
                        setattr(tx, eval_col, True)

                        # For 1h evaluation, also determine if direction was predictive
                        if timeframe == "1h":
                            if tx.direction == "exchange_in":
                                # Exchange deposits should be bearish
                                tx.direction_was_predictive = change_pct < 0
                            elif tx.direction == "exchange_out":
                                # Exchange withdrawals should be bullish
                                tx.direction_was_predictive = change_pct > 0
                            else:
                                tx.direction_was_predictive = None

            await session.commit()
            logger.info("Whale impact evaluation completed")

    except Exception as e:
        logger.error(f"Whale evaluation error: {e}")


async def backfill_whale_transactions():
    """Backfill whale transactions by scanning recent blocks via mempool.space.

    Scans the last 10 blocks (~100 min) for large BTC transactions (>100 BTC).
    Each block is paginated (25 txs/page), scanning first 200 txs per block.
    Called once at startup or via admin endpoint.
    """
    import aiohttp
    import ssl
    import certifi
    from app.collectors.whale import calculate_severity
    from app.collectors.known_entities import identify_any

    logger.info("Backfilling whale transactions via mempool.space block scan...")

    try:
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        timeout = aiohttp.ClientTimeout(total=30)

        # Get current BTC price
        async with async_session() as session:
            price_row = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            price = price_row.scalar_one_or_none()
            current_price = price.close if price else 68000.0

        stored_total = 0

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as http:
            # Get recent blocks
            async with http.get("https://mempool.space/api/blocks") as resp:
                if resp.status != 200:
                    logger.warning(f"mempool.space /blocks returned {resp.status}")
                    return 0
                blocks = await resp.json()

            for block in blocks[:10]:  # last 10 blocks
                block_hash = block.get("id", "")
                block_ts = block.get("timestamp")
                if not block_hash:
                    continue

                # Scan pages of txs in this block
                for page_start in range(0, 200, 25):
                    try:
                        url = f"https://mempool.space/api/block/{block_hash}/txs/{page_start}"
                        async with http.get(url) as resp:
                            if resp.status != 200:
                                break
                            page_txs = await resp.json()

                        if not page_txs:
                            break

                        async with async_session() as session:
                            for tx in page_txs:
                                tx_hash = tx.get("txid", "")
                                if not tx_hash:
                                    continue

                                existing = await session.execute(
                                    select(WhaleTransaction.id).where(
                                        WhaleTransaction.tx_hash == tx_hash
                                    )
                                )
                                if existing.scalar_one_or_none() is not None:
                                    continue

                                total_out = sum(v.get("value", 0) for v in tx.get("vout", []))
                                amount_btc = total_out / 1e8
                                if amount_btc < 100:
                                    continue

                                # Extract addresses (already in mempool.space response)
                                input_addrs = []
                                for vin in tx.get("vin", []):
                                    prevout = vin.get("prevout") or {}
                                    addr = prevout.get("scriptpubkey_address")
                                    if addr:
                                        input_addrs.append(addr)

                                output_addrs = []
                                for vout in tx.get("vout", []):
                                    addr = vout.get("scriptpubkey_address")
                                    if addr:
                                        output_addrs.append(addr)

                                # Classify
                                from_info = identify_any(input_addrs)
                                to_info = identify_any(output_addrs)
                                from_name = from_info["name"] if from_info else "unknown"
                                to_name = to_info["name"] if to_info else "unknown"

                                if from_info and not to_info:
                                    direction, primary = "exchange_out", from_info
                                elif not from_info and to_info:
                                    direction, primary = "exchange_in", to_info
                                elif from_info and to_info:
                                    direction, primary = "exchange_in", to_info
                                else:
                                    direction, primary = "unknown", None

                                ts = datetime.fromtimestamp(block_ts, tz=timezone.utc) if block_ts else datetime.now(timezone.utc)

                                whale_tx = WhaleTransaction(
                                    tx_hash=tx_hash,
                                    timestamp=ts,
                                    amount_btc=round(amount_btc, 4),
                                    amount_usd=round(amount_btc * current_price, 2),
                                    direction=direction,
                                    from_entity=from_name,
                                    to_entity=to_name,
                                    entity_name=primary["name"] if primary else None,
                                    entity_type=primary["type"] if primary else None,
                                    entity_wallet=primary["wallet"] if primary else None,
                                    severity=calculate_severity(amount_btc),
                                    btc_price_at_tx=current_price,
                                    source="mempool_backfill",
                                )
                                session.add(whale_tx)
                                stored_total += 1

                            await session.commit()

                        if len(page_txs) < 25:
                            break

                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning(f"Block scan error at {block_hash[:12]} offset {page_start}: {e}")
                        break

        logger.info(f"Whale backfill complete: {stored_total} transactions stored")
        return stored_total

    except Exception as e:
        logger.error(f"Whale backfill error: {e}")
        return 0


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
            # 90-day retention (but preserve daily historical prices forever)
            for model in [News, Feature, InfluencerTweet, AlertLog]:
                await session.execute(
                    model.__table__.delete().where(model.timestamp < cutoff_90d)
                )

            # Price: only clean hourly data >90 days, keep daily backfill forever
            from sqlalchemy import and_
            await session.execute(
                Price.__table__.delete().where(
                    and_(
                        Price.timestamp < cutoff_90d,
                        Price.source != "historical_backfill",
                    )
                )
            )

            # 180-day retention for less frequent data
            for model in [MacroData, OnChainData, FundingRate, BtcDominance, IndicatorSnapshot, WhaleTransaction]:
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


async def deduplicate_predictions():
    """Remove duplicate predictions created by the old 30-min-all-timeframes scheduler.

    Keeps at most 1 prediction per timeframe per time window:
      - 1h: 1 per hour
      - 4h: 1 per 4-hour block
      - 24h / 1w / 1mo: 1 per calendar day

    Within each window, keeps the evaluated prediction (was_correct IS NOT NULL)
    or the earliest one if none are evaluated.
    """
    try:
        async with async_session() as session:
            total_deleted = 0

            for timeframe in ["1h", "4h", "24h", "1w", "1mo"]:
                result = await session.execute(
                    select(Prediction)
                    .where(Prediction.timeframe == timeframe)
                    .order_by(Prediction.timestamp)
                )
                preds = result.scalars().all()

                if not preds:
                    continue

                # Group predictions by their time window
                windows: dict[str, list] = {}
                for p in preds:
                    ts = p.timestamp
                    if timeframe == "1h":
                        key = ts.strftime("%Y-%m-%d-%H")
                    elif timeframe == "4h":
                        block = (ts.hour // 4) * 4
                        key = f"{ts.strftime('%Y-%m-%d')}-{block:02d}"
                    else:  # 24h, 1w, 1mo
                        key = ts.strftime("%Y-%m-%d")
                    windows.setdefault(key, []).append(p)

                # Keep the best prediction per window, delete the rest
                for window_key, group in windows.items():
                    if len(group) <= 1:
                        continue

                    # Prefer evaluated predictions, then earliest
                    evaluated = [p for p in group if p.was_correct is not None]
                    if evaluated:
                        keep = evaluated[0]
                    else:
                        keep = group[0]

                    for p in group:
                        if p.id != keep.id:
                            await session.delete(p)
                            total_deleted += 1

                logger.info(f"Dedup [{timeframe}]: {len(preds)} → {len(windows)} (removed {len(preds) - len(windows)})")

            # Also deduplicate QuantPrediction (1 per hour max)
            qresult = await session.execute(
                select(QuantPrediction).order_by(QuantPrediction.timestamp)
            )
            quants = qresult.scalars().all()
            if quants:
                q_windows: dict[str, list] = {}
                for q in quants:
                    key = q.timestamp.strftime("%Y-%m-%d-%H")
                    q_windows.setdefault(key, []).append(q)

                q_deleted = 0
                for window_key, group in q_windows.items():
                    if len(group) <= 1:
                        continue
                    keep = group[0]
                    for q in group[1:]:
                        await session.delete(q)
                        q_deleted += 1
                logger.info(f"Dedup [quant]: {len(quants)} → {len(q_windows)} (removed {q_deleted})")
                total_deleted += q_deleted

            await session.commit()
            logger.info(f"Deduplication complete: removed {total_deleted} duplicate predictions")

    except Exception as e:
        logger.error(f"Deduplication error: {e}", exc_info=True)


async def snapshot_daily_metrics():
    """Capture daily KPIs into MarketingMetrics table (runs at 23:55 UTC)."""
    try:
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_ago = now - timedelta(hours=24)

        async with async_session() as session:
            # Check if already snapshotted today
            existing = await session.execute(
                select(MarketingMetrics).where(MarketingMetrics.date == today)
            )
            if existing.scalar_one_or_none():
                logger.info(f"Metrics already snapshotted for {today}")
                return

            # Users
            total_users = (await session.execute(
                select(func.count(BotUser.id))
            )).scalar() or 0

            premium_users = (await session.execute(
                select(func.count(BotUser.id)).where(
                    BotUser.subscription_end.isnot(None),
                    BotUser.subscription_end > now,
                )
            )).scalar() or 0

            trial_users = (await session.execute(
                select(func.count(BotUser.id)).where(
                    BotUser.trial_end.isnot(None),
                    BotUser.trial_end > now,
                    BotUser.subscription_tier == "free",
                )
            )).scalar() or 0

            new_users_today = (await session.execute(
                select(func.count(BotUser.id)).where(BotUser.joined_at >= today_start)
            )).scalar() or 0

            # Revenue
            stars_today = (await session.execute(
                select(func.sum(PaymentHistory.stars_amount))
                .where(PaymentHistory.created_at >= today_start)
            )).scalar() or 0

            # Predictions
            preds_made = (await session.execute(
                select(func.count(Prediction.id))
                .where(Prediction.timestamp >= today_start)
            )).scalar() or 0

            preds_correct = (await session.execute(
                select(func.count(Prediction.id))
                .where(Prediction.timestamp >= today_start)
                .where(Prediction.was_correct == True)
            )).scalar() or 0

            accuracy = round(preds_correct / preds_made * 100, 1) if preds_made > 0 else 0.0

            # Signals
            signals_gen = (await session.execute(
                select(func.count(Signal.id))
                .where(Signal.timestamp >= today_start)
            )).scalar() or 0

            # Support
            tickets_opened = (await session.execute(
                select(func.count(SupportTicket.id))
                .where(SupportTicket.created_at >= today_start)
            )).scalar() or 0

            tickets_resolved = (await session.execute(
                select(func.count(SupportTicket.id))
                .where(SupportTicket.resolved_at >= today_start)
            )).scalar() or 0

            # Referrals
            referrals_today = (await session.execute(
                select(func.count(Referral.id))
                .where(Referral.created_at >= today_start)
            )).scalar() or 0

            total_referrals = (await session.execute(
                select(func.count(Referral.id))
            )).scalar() or 0

            # API usage
            api_requests = (await session.execute(
                select(func.count(ApiUsageLog.id))
                .where(ApiUsageLog.timestamp >= today_start)
            )).scalar() or 0

            api_errors = (await session.execute(
                select(func.count(ApiUsageLog.id))
                .where(ApiUsageLog.timestamp >= today_start)
                .where(ApiUsageLog.status_code >= 500)
            )).scalar() or 0

            # Save snapshot
            metrics = MarketingMetrics(
                date=today,
                total_users=total_users,
                premium_users=premium_users,
                trial_users=trial_users,
                new_users_today=new_users_today,
                active_users_24h=0,  # Would need activity tracking
                stars_revenue_today=stars_today,
                trial_conversions_today=0,
                predictions_made=preds_made,
                predictions_correct=preds_correct,
                accuracy_pct=accuracy,
                signals_generated=signals_gen,
                signals_profitable=0,
                tickets_opened=tickets_opened,
                tickets_resolved=tickets_resolved,
                referrals_today=referrals_today,
                total_referrals=total_referrals,
                api_requests=api_requests,
                api_errors=api_errors,
            )
            session.add(metrics)
            await session.commit()
            logger.info(f"Daily metrics snapshot saved for {today}: {total_users} users, {premium_users} premium, {preds_made} predictions ({accuracy}%)")

    except Exception as e:
        logger.error(f"Metrics snapshot error: {e}", exc_info=True)


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
