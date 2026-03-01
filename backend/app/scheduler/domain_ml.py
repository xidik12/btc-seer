"""ML prediction jobs: ensemble predictions, quant predictions, evaluation, retraining."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import select, desc

from app.config import settings
from app.database import (
    async_session, Price, News, Feature, Prediction, Signal,
    MacroData, OnChainData, InfluencerTweet, EventImpact, QuantPrediction,
    FundingRate, BtcDominance, WhaleTransaction,
    PredictionContext, ModelPerformanceLog, PredictionAnalysis,
    timestamp_diff_order,
)
logger = logging.getLogger(__name__)

from app.scheduler._singletons import (
    get_market_collector, get_etf_collector, get_exchange_flow_collector,
    get_derivatives_extended_collector, get_stablecoin_collector,
    get_feature_builder, get_signal_generator, get_event_pattern_matcher,
    get_ensemble,
)


async def _get_price_at(session, target_time: datetime) -> float | None:
    """Get BTC price closest to a target time (+-30 min window, then fallback)."""
    # Try +-30 min window first, pick closest
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

            # -- Event Memory: query ALL recent events and combine their expected impacts --
            event_memory_data = {}
            try:
                # Get active events from last 2 hours (wider window for multi-event combining)
                since_2h = datetime.utcnow() - timedelta(hours=2)
                result = await session.execute(
                    select(EventImpact)
                    .where(EventImpact.timestamp >= since_2h)
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
                        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    }
                    for e in historical_events
                ]

                if recent_events:
                    # Process ALL active events, not just the top one
                    matcher = get_event_pattern_matcher()
                    events_with_impacts = []
                    for evt in recent_events:
                        similar = matcher.find_similar_events(
                            category=evt.category,
                            keywords=evt.keywords or "",
                            past_events=historical_dicts,
                            severity=evt.severity,
                        )
                        expected = matcher.get_expected_impact(
                            similar, current_severity=evt.severity
                        )
                        events_with_impacts.append({
                            "category": evt.category,
                            "severity": evt.severity,
                            "expected_impact": expected,
                            "event_id": evt.id,
                        })

                    # Combine all events
                    if len(events_with_impacts) == 1:
                        # Single event — use directly
                        expected = events_with_impacts[0]["expected_impact"]
                        top_event = recent_events[0]
                        event_memory_data = {
                            "expected_1h": expected["expected_1h"],
                            "expected_4h": expected["expected_4h"],
                            "expected_24h": expected["expected_24h"],
                            "confidence": expected["confidence"],
                            "severity": top_event.severity / 10.0,
                            "avg_sentiment_predictive": expected["avg_sentiment_predictive"],
                            "active_event_count": 1.0,
                            "sample_size": expected["sample_size"],
                        }
                    else:
                        # Multiple events — combine with the multi-event combiner
                        combined = matcher.combine_multiple_events(events_with_impacts)
                        top_severity = max(e.severity for e in recent_events)
                        event_memory_data = {
                            "expected_1h": combined["expected_1h"],
                            "expected_4h": combined["expected_4h"],
                            "expected_24h": combined["expected_24h"],
                            "confidence": combined["confidence"],
                            "severity": top_severity / 10.0,
                            "avg_sentiment_predictive": 0.5,
                            "active_event_count": float(combined["active_event_count"]),
                            "sample_size": sum(e["expected_impact"]["sample_size"] for e in events_with_impacts),
                        }

                    if event_memory_data.get("sample_size", 0) > 0:
                        cats = list(set(e.category for e in recent_events))
                        logger.info(
                            f"Event memory: {len(recent_events)} events ({', '.join(cats)}) — "
                            f"combined 1h={event_memory_data['expected_1h']:+.2f}%, "
                            f"24h={event_memory_data['expected_24h']:+.2f}% "
                            f"(from {event_memory_data['sample_size']} historical samples)"
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

        # Get latest macro data (M2 supply, gold, sp500 for ratio features)
        macro_raw = None
        try:
            async with async_session() as sess:
                result = await sess.execute(
                    select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
                )
                macro_row = result.scalar_one_or_none()
                if macro_row:
                    macro_raw = {
                        "gold": macro_row.gold,
                        "sp500": macro_row.sp500,
                        "m2_supply": macro_row.m2_supply,
                        "dxy": macro_row.dxy,
                        "treasury_10y": macro_row.treasury_10y,
                    }
        except Exception as e:
            logger.debug(f"Macro data query error: {e}")

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

        # -- Collect new data sources (concurrently with 10s timeout) --
        async def _safe_collect(collector, name):
            try:
                return await asyncio.wait_for(collector.collect(), timeout=10)
            except asyncio.TimeoutError:
                logger.debug(f"{name} collection timed out (10s)")
                return None
            except Exception as e:
                logger.debug(f"{name} collection error: {e}")
                return None

        deriv = get_derivatives_extended_collector()
        etf = get_etf_collector()
        flow = get_exchange_flow_collector()
        stable = get_stablecoin_collector()
        derivatives_ext_data, etf_data, exchange_flow_data, stablecoin_data_raw = (
            await asyncio.gather(
                _safe_collect(deriv, "Derivatives extended"),
                _safe_collect(etf, "ETF"),
                _safe_collect(flow, "Exchange flow"),
                _safe_collect(stable, "Stablecoin"),
            )
        )

        # -- Whale data aggregation --
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
        news_data = [{"title": n.title, "source": n.source, "timestamp": n.timestamp.isoformat() if n.timestamp else None} for n in news]
        fb = get_feature_builder()
        features = fb.build_features(
            price_df=price_df,
            news_data=news_data,
            influencer_data=influencer_data,
            macro_data=macro_raw,
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
        feature_array = fb.features_to_array(features)

        async with async_session() as sess:
            result = await sess.execute(
                select(Feature)
                .order_by(desc(Feature.timestamp))
                .limit(168)
            )
            feature_history = list(reversed(result.scalars().all()))

        if len(feature_history) >= 10:
            # Use real historical feature snapshots
            sequence = fb.build_sequence(
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
                        f"Pattern adjustment [{tf}]: confidence {original_conf:.0f}->{pred['confidence']:.0f} "
                        f"(modifier={adjustments['confidence_modifier']:.2f}, "
                        f"bias={adjustments['direction_bias']:+.3f})"
                    )
        except Exception as e:
            logger.debug(f"Pattern adjustment error (non-critical): {e}")

        # Generate signals
        signals = get_signal_generator().generate(predictions, current_price, atr, volatility)

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


# -- Time-aligned prediction wrappers --

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
            fr_data = await get_market_collector().get_funding_rate()
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
        from app.models.quant_predictor import QuantPredictor
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


# -- Time-aligned quant prediction wrappers --

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

                # Use wider window for finding price: +-30 min, pick closest to target
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
                    # Fallback: if no price in +-30min, get the latest price before eval_time + 1h
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

                # -- Compute error metrics --
                if pred.predicted_price and pred.predicted_price > 0:
                    pred.error_pct = (actual_price - pred.predicted_price) / pred.predicted_price * 100
                else:
                    pred.error_pct = None

                # -- Classify volatility regime --
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

                    # -- Classify trend state --
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

                    # -- Per-model results analysis --
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

                        # -- Populate ModelPerformanceLog (critical fix) --
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

                    # -- Create PredictionAnalysis record --
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

                logger.info(f"Dedup [{timeframe}]: {len(preds)} -> {len(windows)} (removed {len(preds) - len(windows)})")

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
                logger.info(f"Dedup [quant]: {len(quants)} -> {len(q_windows)} (removed {q_deleted})")
                total_deleted += q_deleted

            await session.commit()
            logger.info(f"Deduplication complete: removed {total_deleted} duplicate predictions")

    except Exception as e:
        logger.error(f"Deduplication error: {e}", exc_info=True)


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
            # Hot-swap: clear cached ensemble so it reloads with new weights
            get_ensemble.cache_clear()
            logger.info(f"Models retrained and ensemble reset: {result}")
        else:
            logger.info(f"Retrain check: {result.get('status')} (accuracy={result.get('accuracy', 'N/A')})")

    except Exception as e:
        logger.error(f"Auto-retrain error: {e}", exc_info=True)
