import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select, desc

from app.config import settings
from app.database import (
    async_session, Price, News, Feature, Prediction, Signal,
    MacroData, OnChainData,
)
from app.collectors import (
    MarketCollector, NewsCollector, FearGreedCollector,
    MacroCollector, OnChainCollector, RedditCollector,
)
from app.features.builder import FeatureBuilder
from app.features.sentiment import SentimentAnalyzer
from app.models.ensemble import EnsemblePredictor
from app.signals.generator import SignalGenerator

logger = logging.getLogger(__name__)

# Global instances (initialized once)
market_collector = MarketCollector()
news_collector = NewsCollector()
fear_greed_collector = FearGreedCollector()
macro_collector = MacroCollector()
onchain_collector = OnChainCollector()
reddit_collector = RedditCollector()
feature_builder = FeatureBuilder()
signal_generator = SignalGenerator()

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
    """Collect and store news data (runs every 5 minutes)."""
    try:
        data = await news_collector.collect()
        news_items = data.get("news", [])

        if not news_items:
            return

        analyzer = SentimentAnalyzer()

        async with async_session() as session:
            for item in news_items:
                # Score sentiment
                title = item.get("title", "")
                if title:
                    sentiment = analyzer.analyze_text(title)
                    score = sentiment["combined_score"]
                else:
                    score = None

                news = News(
                    timestamp=datetime.utcnow(),
                    source=item.get("source", "unknown"),
                    title=title,
                    url=item.get("url", ""),
                    sentiment_score=score,
                    raw_sentiment=item.get("raw_sentiment"),
                )
                session.add(news)

            await session.commit()

        logger.info(f"Collected {len(news_items)} news items")

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


async def generate_prediction():
    """Generate ML prediction (runs every hour)."""
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

        # Build features
        news_data = [{"title": n.title, "source": n.source} for n in news]
        features = feature_builder.build_features(
            price_df=price_df,
            news_data=news_data,
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
                prediction = Prediction(
                    timestamp=datetime.utcnow(),
                    timeframe=timeframe,
                    direction=pred["direction"],
                    confidence=pred["confidence"],
                    predicted_change_pct=pred.get("magnitude_pct"),
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


async def cleanup_old_data():
    """Clean up data older than 90 days (runs daily)."""
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
