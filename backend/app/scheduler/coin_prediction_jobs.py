"""Scheduled jobs for multi-coin prediction pipeline.

Generates predictions, signals, and features for the 19 tracked altcoins
(Bitcoin keeps its existing heavyweight pipeline).  Also evaluates past
predictions once their target timeframe has elapsed.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc, and_

from app.config import settings
from app.database import (
    async_session,
    CoinOHLCV,
    CoinPrediction,
    CoinSignal,
    CoinFeature,
    CoinPrice,
    CoinSentiment,
)
from app.collectors.coins import TRACKED_COINS
from app.features.coin_feature_builder import CoinFeatureBuilder
from app.models.coin_ensemble import CoinEnsemblePredictor

logger = logging.getLogger(__name__)

# Singleton instances — created on first use
_feature_builder: CoinFeatureBuilder | None = None
_ensemble: CoinEnsemblePredictor | None = None

# Timeframe -> hours mapping for evaluation
TIMEFRAME_HOURS = {"1h": 1, "4h": 4, "24h": 24}


def _get_feature_builder() -> CoinFeatureBuilder:
    global _feature_builder
    if _feature_builder is None:
        _feature_builder = CoinFeatureBuilder()
    return _feature_builder


def _get_ensemble() -> CoinEnsemblePredictor:
    global _ensemble
    if _ensemble is None:
        _ensemble = CoinEnsemblePredictor()
    return _ensemble


# ======================================================================
#  Main prediction generator
# ======================================================================

async def generate_coin_predictions(timeframe: str = "1h") -> None:
    """Generate predictions for all tracked altcoins (skip Bitcoin).

    For each coin:
      1. Build features via CoinFeatureBuilder
      2. Get current price
      3. Run CoinEnsemblePredictor
      4. Store CoinPrediction, CoinSignal, CoinFeature rows

    Sleeps 1 second between coins to avoid DB contention.
    """
    builder = _get_feature_builder()
    ensemble = _get_ensemble()
    now = datetime.utcnow()

    altcoins = [c for c in TRACKED_COINS if c["coin_id"] != "bitcoin"]
    success_count = 0
    error_count = 0

    logger.info(f"[CoinPredictions] Starting {timeframe} predictions for {len(altcoins)} altcoins")

    for coin in altcoins:
        coin_id = coin["coin_id"]
        symbol = coin["symbol"]

        try:
            # 1. Build features
            features = await builder.build_features(coin_id)
            if features is None:
                logger.debug(f"[CoinPredictions] Skipping {symbol}: no features")
                continue

            # 2. Get current price
            current_price = await _get_current_price(coin_id)
            if current_price is None or current_price <= 0:
                logger.debug(f"[CoinPredictions] Skipping {symbol}: no price")
                continue

            # 3. Get price history for momentum component
            price_history = await _get_price_history(coin_id, limit=200)

            # 4. Predict
            prediction = ensemble.predict(
                features=features,
                price_history=price_history,
                coin_id=coin_id,
                timeframe=timeframe,
            )

            # 5. Compute predicted price
            predicted_change_pct = prediction["predicted_change_pct"]
            predicted_price = current_price * (1 + predicted_change_pct / 100)

            # 6. Derive trading signal
            signal_data = _derive_signal(
                direction=prediction["direction"],
                confidence=prediction["confidence"],
                current_price=current_price,
                predicted_change_pct=predicted_change_pct,
                timeframe=timeframe,
            )

            # 7. Store everything
            async with async_session() as session:
                # CoinPrediction
                pred_row = CoinPrediction(
                    coin_id=coin_id,
                    timestamp=now,
                    timeframe=timeframe,
                    direction=prediction["direction"],
                    confidence=prediction["confidence"],
                    predicted_price=predicted_price,
                    predicted_change_pct=predicted_change_pct,
                    current_price=current_price,
                    model_outputs=prediction["model_outputs"],
                )
                session.add(pred_row)

                # CoinSignal
                session.add(CoinSignal(
                    coin_id=coin_id,
                    timestamp=now,
                    action=signal_data["action"],
                    direction=prediction["direction"],
                    confidence=prediction["confidence"],
                    entry_price=current_price,
                    target_price=signal_data["target_price"],
                    stop_loss=signal_data["stop_loss"],
                    risk_rating=signal_data["risk_rating"],
                    timeframe=timeframe,
                    reasoning=signal_data["reasoning"],
                ))

                # CoinFeature
                session.add(CoinFeature(
                    coin_id=coin_id,
                    timestamp=now,
                    feature_data=features,
                ))

                await session.commit()

            success_count += 1
            logger.debug(
                f"[CoinPredictions] {symbol} {timeframe}: "
                f"{prediction['direction']} ({prediction['confidence']:.0%}), "
                f"change={predicted_change_pct:+.2f}%"
            )

        except Exception as e:
            error_count += 1
            logger.error(
                f"[CoinPredictions] Error processing {symbol}: {e}",
                exc_info=True,
            )

        # Gentle throttle between coins
        await asyncio.sleep(1)

    logger.info(
        f"[CoinPredictions] {timeframe} complete: "
        f"{success_count} ok, {error_count} errors, "
        f"{len(altcoins) - success_count - error_count} skipped"
    )


# ======================================================================
#  Convenience wrappers (registered with APScheduler)
# ======================================================================

async def generate_coin_predictions_1h() -> None:
    """Generate 1-hour altcoin predictions."""
    await generate_coin_predictions("1h")


async def generate_coin_predictions_4h() -> None:
    """Generate 4-hour altcoin predictions."""
    await generate_coin_predictions("4h")


async def generate_coin_predictions_24h() -> None:
    """Generate 24-hour altcoin predictions."""
    await generate_coin_predictions("24h")


# ======================================================================
#  Prediction evaluator
# ======================================================================

async def evaluate_coin_predictions() -> None:
    """Evaluate past CoinPredictions whose timeframe has elapsed.

    For each unevaluated prediction:
      1. Check if enough time has passed since the prediction timestamp.
      2. Find the actual price at (timestamp + timeframe hours).
      3. Compute was_correct and error_pct, then update the row.
    """
    now = datetime.utcnow()
    evaluated = 0
    errors = 0

    for tf, hours in TIMEFRAME_HOURS.items():
        cutoff = now - timedelta(hours=hours)

        try:
            async with async_session() as session:
                # Fetch unevaluated predictions whose timeframe has elapsed
                result = await session.execute(
                    select(CoinPrediction).where(
                        and_(
                            CoinPrediction.timeframe == tf,
                            CoinPrediction.was_correct.is_(None),
                            CoinPrediction.timestamp <= cutoff,
                        )
                    )
                    .order_by(CoinPrediction.timestamp)
                    .limit(100)  # Process in batches to limit DB load
                )
                predictions = result.scalars().all()

                if not predictions:
                    continue

                for pred in predictions:
                    try:
                        # Target time = prediction time + timeframe
                        target_time = pred.timestamp + timedelta(hours=hours)
                        actual_price = await _get_price_at_time(
                            pred.coin_id, target_time
                        )

                        if actual_price is None:
                            continue

                        # Compute direction correctness
                        actual_direction = (
                            "bullish" if actual_price > pred.current_price else "bearish"
                        )
                        was_correct = pred.direction == actual_direction

                        # Error percentage
                        if pred.predicted_price and pred.predicted_price > 0:
                            error_pct = (
                                (actual_price - pred.predicted_price)
                                / pred.predicted_price
                                * 100
                            )
                        else:
                            error_pct = 0.0

                        # Update
                        pred.actual_price = actual_price
                        pred.actual_direction = actual_direction
                        pred.was_correct = was_correct
                        pred.error_pct = round(error_pct, 4)

                        evaluated += 1

                    except Exception as e:
                        errors += 1
                        logger.warning(
                            f"[CoinEval] Error evaluating prediction {pred.id}: {e}"
                        )

                await session.commit()

        except Exception as e:
            errors += 1
            logger.error(f"[CoinEval] Batch error for {tf}: {e}", exc_info=True)

    if evaluated > 0 or errors > 0:
        logger.info(
            f"[CoinEval] Evaluated {evaluated} predictions, {errors} errors"
        )


# ======================================================================
#  Helper functions
# ======================================================================

async def _get_current_price(coin_id: str) -> float | None:
    """Get the latest price for a coin from CoinPrice or CoinOHLCV."""
    async with async_session() as session:
        # Try CoinPrice first (more recent snapshots)
        result = await session.execute(
            select(CoinPrice.price_usd)
            .where(CoinPrice.coin_id == coin_id)
            .order_by(desc(CoinPrice.timestamp))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return float(row)

        # Fallback to latest OHLCV close
        result = await session.execute(
            select(CoinOHLCV.close)
            .where(CoinOHLCV.coin_id == coin_id)
            .order_by(desc(CoinOHLCV.timestamp))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return float(row) if row is not None else None


async def _get_price_history(coin_id: str, limit: int = 200) -> list[float]:
    """Get recent close prices for the momentum component."""
    async with async_session() as session:
        result = await session.execute(
            select(CoinOHLCV.close)
            .where(CoinOHLCV.coin_id == coin_id, CoinOHLCV.interval == "1h")
            .order_by(desc(CoinOHLCV.timestamp))
            .limit(limit)
        )
        rows = result.scalars().all()

    # Oldest-first
    return [float(p) for p in reversed(rows)]


async def _get_price_at_time(coin_id: str, target_time: datetime) -> float | None:
    """Find the price closest to *target_time* for evaluation.

    Looks within a 2-hour window around the target.
    """
    window = timedelta(hours=2)
    low = target_time - window
    high = target_time + window

    async with async_session() as session:
        # Try CoinOHLCV first (most precise)
        result = await session.execute(
            select(CoinOHLCV)
            .where(
                and_(
                    CoinOHLCV.coin_id == coin_id,
                    CoinOHLCV.interval == "1h",
                    CoinOHLCV.timestamp >= low,
                    CoinOHLCV.timestamp <= high,
                )
            )
            .order_by(CoinOHLCV.timestamp)
            .limit(1)
        )
        ohlcv = result.scalar_one_or_none()
        if ohlcv is not None:
            return float(ohlcv.close)

        # Fallback to CoinPrice
        result = await session.execute(
            select(CoinPrice)
            .where(
                and_(
                    CoinPrice.coin_id == coin_id,
                    CoinPrice.timestamp >= low,
                    CoinPrice.timestamp <= high,
                )
            )
            .order_by(CoinPrice.timestamp)
            .limit(1)
        )
        price_row = result.scalar_one_or_none()
        if price_row is not None:
            return float(price_row.price_usd)

    return None


def _derive_signal(
    direction: str,
    confidence: float,
    current_price: float,
    predicted_change_pct: float,
    timeframe: str,
) -> dict:
    """Convert a prediction into a trading signal (action + targets).

    Returns a dict with keys: action, target_price, stop_loss, risk_rating, reasoning.
    """
    # Action mapping based on direction and confidence
    if direction == "bullish":
        if confidence >= 0.75:
            action = "strong_buy"
        elif confidence >= 0.55:
            action = "buy"
        else:
            action = "hold"
    elif direction == "bearish":
        if confidence >= 0.75:
            action = "strong_sell"
        elif confidence >= 0.55:
            action = "sell"
        else:
            action = "hold"
    else:
        action = "hold"

    # Target and stop-loss based on predicted change and timeframe
    tf_atr_mult = {"1h": 0.5, "4h": 1.0, "24h": 2.0}
    atr_mult = tf_atr_mult.get(timeframe, 1.0)

    # Default stop-loss = 1.5% * atr_mult; target = predicted price
    stop_loss_pct = 1.5 * atr_mult / 100
    target_price = current_price * (1 + predicted_change_pct / 100)

    if direction == "bearish":
        stop_loss = current_price * (1 + stop_loss_pct)
    else:
        stop_loss = current_price * (1 - stop_loss_pct)

    # Risk rating 1-10 (higher = riskier)
    if confidence >= 0.75:
        risk_rating = 3
    elif confidence >= 0.55:
        risk_rating = 5
    else:
        risk_rating = 7

    # Reasoning summary
    reasoning = (
        f"{timeframe} {direction} signal (confidence {confidence:.0%}). "
        f"Predicted change: {predicted_change_pct:+.2f}%. "
        f"Action: {action}."
    )

    return {
        "action": action,
        "target_price": round(target_price, 8),
        "stop_loss": round(stop_loss, 8),
        "risk_rating": risk_rating,
        "reasoning": reasoning,
    }
