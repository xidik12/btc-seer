"""Pattern Learning Engine for BTC Seer.

Discovers accuracy patterns from PredictionAnalysis records and creates
LearnedPattern entries that modify future prediction confidence/direction.

Pattern types:
1. Model disagreement: "When LSTM disagrees with ensemble, accuracy drops to X%"
2. Volatility regime: "In high volatility, 4h predictions are only 40% accurate"
3. Feature threshold: "When RSI > 75, bullish predictions are wrong 70% of the time"
4. Confidence calibration: "When confidence is 80-90%, actual accuracy is only 55%"
5. Time patterns: "Predictions at 04:00 UTC are more accurate than 16:00"
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import (
    async_session, PredictionAnalysis, LearnedPattern, Prediction,
)

logger = logging.getLogger(__name__)

MIN_SAMPLE_SIZE = 20  # Minimum samples to form a pattern
SIGNIFICANCE_THRESHOLD = 0.10  # 10% accuracy difference to be significant


async def run_pattern_discovery():
    """Main entry point: discover patterns from prediction analyses (runs every 6h)."""
    try:
        logger.info("Pattern discovery: starting...")
        patterns_found = 0

        patterns_found += await _discover_volatility_patterns()
        patterns_found += await _discover_confidence_calibration()
        patterns_found += await _discover_model_disagreement()
        patterns_found += await _discover_feature_threshold_patterns()
        patterns_found += await _discover_time_patterns()

        logger.info(f"Pattern discovery: completed, {patterns_found} patterns updated/created")
    except Exception as e:
        logger.error(f"Pattern discovery error: {e}", exc_info=True)


async def _discover_volatility_patterns() -> int:
    """Discover accuracy differences across volatility regimes."""
    count = 0
    try:
        async with async_session() as session:
            for timeframe in ["1h", "4h", "24h"]:
                # Fetch all analyses for this timeframe in one query
                result = await session.execute(
                    select(PredictionAnalysis)
                    .where(PredictionAnalysis.timeframe == timeframe)
                    .where(PredictionAnalysis.direction_correct.isnot(None))
                )
                all_analyses = result.scalars().all()

                if len(all_analyses) < MIN_SAMPLE_SIZE:
                    continue

                total_all = len(all_analyses)
                correct_all = sum(1 for a in all_analyses if a.direction_correct)
                acc_all = correct_all / total_all

                for regime in ["low", "normal", "high", "extreme"]:
                    regime_analyses = [a for a in all_analyses if a.volatility_regime == regime]
                    total_regime = len(regime_analyses)

                    if total_regime < MIN_SAMPLE_SIZE:
                        continue

                    correct_regime = sum(1 for a in regime_analyses if a.direction_correct)
                    acc_regime = correct_regime / total_regime
                    diff = acc_regime - acc_all

                    if abs(diff) < SIGNIFICANCE_THRESHOLD:
                        continue

                    confidence_mod = min(1.2, max(0.5, acc_regime / max(acc_all, 0.01)))

                    await _upsert_pattern(
                        session,
                        pattern_type="volatility_regime",
                        timeframe=timeframe,
                        conditions={"volatility_regime": regime},
                        description=f"In {regime} volatility, {timeframe} accuracy is {acc_regime*100:.0f}% vs {acc_all*100:.0f}% overall",
                        sample_size=total_regime,
                        accuracy_when_pattern=acc_regime,
                        accuracy_when_not_pattern=acc_all,
                        confidence_modifier=round(confidence_mod, 3),
                    )
                    count += 1

            await session.commit()
    except Exception as e:
        logger.debug(f"Volatility pattern discovery error: {e}")
    return count


async def _discover_confidence_calibration() -> int:
    """Check if stated confidence matches actual accuracy."""
    count = 0
    try:
        async with async_session() as session:
            for timeframe in ["1h", "4h", "24h"]:
                # Bucket by confidence ranges
                buckets = [(50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
                for low, high in buckets:
                    result = await session.execute(
                        select(Prediction)
                        .where(Prediction.timeframe == timeframe)
                        .where(Prediction.was_correct.isnot(None))
                        .where(Prediction.confidence >= low)
                        .where(Prediction.confidence < high)
                    )
                    preds = result.scalars().all()

                    if len(preds) < MIN_SAMPLE_SIZE:
                        continue

                    actual_acc = sum(1 for p in preds if p.was_correct) / len(preds)
                    stated_conf = (low + high) / 2 / 100  # midpoint as fraction

                    # If actual accuracy is significantly different from stated confidence
                    if abs(actual_acc - stated_conf) > SIGNIFICANCE_THRESHOLD:
                        confidence_mod = actual_acc / max(stated_conf, 0.01)
                        confidence_mod = min(1.3, max(0.5, confidence_mod))

                        await _upsert_pattern(
                            session,
                            pattern_type="confidence_calibration",
                            timeframe=timeframe,
                            conditions={"confidence_range": [low, high]},
                            description=f"When confidence is {low}-{high}%, actual accuracy is {actual_acc*100:.0f}% for {timeframe}",
                            sample_size=len(preds),
                            accuracy_when_pattern=actual_acc,
                            accuracy_when_not_pattern=stated_conf,
                            confidence_modifier=round(confidence_mod, 3),
                        )
                        count += 1

            await session.commit()
    except Exception as e:
        logger.debug(f"Confidence calibration discovery error: {e}")
    return count


async def _discover_model_disagreement() -> int:
    """Find patterns where specific model disagreements predict accuracy."""
    count = 0
    try:
        async with async_session() as session:
            for timeframe in ["1h", "4h", "24h"]:
                # Get analyses with model agreement data
                result = await session.execute(
                    select(PredictionAnalysis)
                    .where(PredictionAnalysis.timeframe == timeframe)
                    .where(PredictionAnalysis.direction_correct.isnot(None))
                    .where(PredictionAnalysis.model_agreement_score.isnot(None))
                )
                analyses = result.scalars().all()

                if len(analyses) < MIN_SAMPLE_SIZE:
                    continue

                # High agreement (>= 0.75) vs low agreement (< 0.75)
                high_agree = [a for a in analyses if a.model_agreement_score >= 0.75]
                low_agree = [a for a in analyses if a.model_agreement_score < 0.75]

                if len(high_agree) >= MIN_SAMPLE_SIZE // 2 and len(low_agree) >= MIN_SAMPLE_SIZE // 2:
                    acc_high = sum(1 for a in high_agree if a.direction_correct) / len(high_agree)
                    acc_low = sum(1 for a in low_agree if a.direction_correct) / len(low_agree)

                    if abs(acc_high - acc_low) > SIGNIFICANCE_THRESHOLD:
                        await _upsert_pattern(
                            session,
                            pattern_type="model_disagreement",
                            timeframe=timeframe,
                            conditions={"agreement_threshold": 0.75},
                            description=f"High model agreement ({timeframe}): {acc_high*100:.0f}% vs low agreement: {acc_low*100:.0f}%",
                            sample_size=len(analyses),
                            accuracy_when_pattern=acc_low,  # "pattern" = low agreement
                            accuracy_when_not_pattern=acc_high,
                            confidence_modifier=round(min(1.2, max(0.5, acc_low / max(acc_high, 0.01))), 3),
                        )
                        count += 1

            await session.commit()
    except Exception as e:
        logger.debug(f"Model disagreement discovery error: {e}")
    return count


async def _discover_feature_threshold_patterns() -> int:
    """Find patterns like 'When RSI > 75, bullish predictions are wrong X% of the time'."""
    count = 0
    try:
        async with async_session() as session:
            for timeframe in ["1h", "4h", "24h"]:
                # RSI extremes
                result = await session.execute(
                    select(PredictionAnalysis)
                    .where(PredictionAnalysis.timeframe == timeframe)
                    .where(PredictionAnalysis.direction_correct.isnot(None))
                    .where(PredictionAnalysis.rsi_at_prediction.isnot(None))
                )
                analyses = result.scalars().all()

                if len(analyses) < MIN_SAMPLE_SIZE:
                    continue

                # RSI > 70 with bullish predictions
                high_rsi = [a for a in analyses if a.rsi_at_prediction > 70]
                if len(high_rsi) >= MIN_SAMPLE_SIZE // 2:
                    # Get corresponding predictions to check direction
                    pred_ids = [a.prediction_id for a in high_rsi]
                    pred_result = await session.execute(
                        select(Prediction).where(Prediction.id.in_(pred_ids))
                    )
                    pred_map = {p.id: p for p in pred_result.scalars().all()}

                    bullish_high_rsi = [
                        a for a in high_rsi
                        if pred_map.get(a.prediction_id) and pred_map[a.prediction_id].direction == "bullish"
                    ]
                    if len(bullish_high_rsi) >= MIN_SAMPLE_SIZE // 2:
                        acc = sum(1 for a in bullish_high_rsi if a.direction_correct) / len(bullish_high_rsi)
                        overall_acc = sum(1 for a in analyses if a.direction_correct) / len(analyses)

                        if abs(acc - overall_acc) > SIGNIFICANCE_THRESHOLD:
                            await _upsert_pattern(
                                session,
                                pattern_type="feature_threshold",
                                timeframe=timeframe,
                                conditions={"rsi_gt": 70, "direction": "bullish"},
                                description=f"When RSI > 70 & bullish ({timeframe}): {acc*100:.0f}% accurate vs {overall_acc*100:.0f}% overall",
                                sample_size=len(bullish_high_rsi),
                                accuracy_when_pattern=acc,
                                accuracy_when_not_pattern=overall_acc,
                                confidence_modifier=round(min(1.2, max(0.5, acc / max(overall_acc, 0.01))), 3),
                            )
                            count += 1

                # RSI < 30 with bearish predictions
                low_rsi = [a for a in analyses if a.rsi_at_prediction < 30]
                if len(low_rsi) >= MIN_SAMPLE_SIZE // 2:
                    pred_ids = [a.prediction_id for a in low_rsi]
                    pred_result = await session.execute(
                        select(Prediction).where(Prediction.id.in_(pred_ids))
                    )
                    pred_map = {p.id: p for p in pred_result.scalars().all()}

                    bearish_low_rsi = [
                        a for a in low_rsi
                        if pred_map.get(a.prediction_id) and pred_map[a.prediction_id].direction == "bearish"
                    ]
                    if len(bearish_low_rsi) >= MIN_SAMPLE_SIZE // 2:
                        acc = sum(1 for a in bearish_low_rsi if a.direction_correct) / len(bearish_low_rsi)
                        overall_acc = sum(1 for a in analyses if a.direction_correct) / len(analyses)

                        if abs(acc - overall_acc) > SIGNIFICANCE_THRESHOLD:
                            await _upsert_pattern(
                                session,
                                pattern_type="feature_threshold",
                                timeframe=timeframe,
                                conditions={"rsi_lt": 30, "direction": "bearish"},
                                description=f"When RSI < 30 & bearish ({timeframe}): {acc*100:.0f}% accurate vs {overall_acc*100:.0f}% overall",
                                sample_size=len(bearish_low_rsi),
                                accuracy_when_pattern=acc,
                                accuracy_when_not_pattern=overall_acc,
                                confidence_modifier=round(min(1.2, max(0.5, acc / max(overall_acc, 0.01))), 3),
                            )
                            count += 1

            await session.commit()
    except Exception as e:
        logger.debug(f"Feature threshold discovery error: {e}")
    return count


async def _discover_time_patterns() -> int:
    """Find patterns in prediction accuracy by hour of day."""
    count = 0
    try:
        async with async_session() as session:
            for timeframe in ["1h", "4h"]:
                result = await session.execute(
                    select(PredictionAnalysis)
                    .where(PredictionAnalysis.timeframe == timeframe)
                    .where(PredictionAnalysis.direction_correct.isnot(None))
                )
                analyses = result.scalars().all()

                if len(analyses) < MIN_SAMPLE_SIZE:
                    continue

                overall_acc = sum(1 for a in analyses if a.direction_correct) / len(analyses)

                # Get prediction timestamps to group by hour
                pred_ids = [a.prediction_id for a in analyses]
                pred_result = await session.execute(
                    select(Prediction).where(Prediction.id.in_(pred_ids))
                )
                pred_map = {p.id: p for p in pred_result.scalars().all()}

                # Group by 4-hour blocks (0-3, 4-7, 8-11, 12-15, 16-19, 20-23)
                blocks = {}
                for a in analyses:
                    p = pred_map.get(a.prediction_id)
                    if not p:
                        continue
                    block = (p.timestamp.hour // 4) * 4
                    if block not in blocks:
                        blocks[block] = {"correct": 0, "total": 0}
                    blocks[block]["total"] += 1
                    if a.direction_correct:
                        blocks[block]["correct"] += 1

                for block_hour, stats in blocks.items():
                    if stats["total"] < MIN_SAMPLE_SIZE // 2:
                        continue
                    block_acc = stats["correct"] / stats["total"]
                    if abs(block_acc - overall_acc) > SIGNIFICANCE_THRESHOLD:
                        confidence_mod = min(1.2, max(0.5, block_acc / max(overall_acc, 0.01)))
                        await _upsert_pattern(
                            session,
                            pattern_type="time_pattern",
                            timeframe=timeframe,
                            conditions={"hour_block": block_hour},
                            description=f"Predictions at {block_hour:02d}:00-{block_hour+3:02d}:59 UTC ({timeframe}): {block_acc*100:.0f}% vs {overall_acc*100:.0f}% overall",
                            sample_size=stats["total"],
                            accuracy_when_pattern=block_acc,
                            accuracy_when_not_pattern=overall_acc,
                            confidence_modifier=round(confidence_mod, 3),
                        )
                        count += 1

            await session.commit()
    except Exception as e:
        logger.debug(f"Time pattern discovery error: {e}")
    return count


async def _upsert_pattern(
    session, pattern_type: str, timeframe: str, conditions: dict,
    description: str, sample_size: int,
    accuracy_when_pattern: float, accuracy_when_not_pattern: float,
    confidence_modifier: float, direction_bias: float = 0.0,
):
    """Insert or update a learned pattern."""
    import json

    # Check if pattern already exists
    conditions_str = json.dumps(conditions, sort_keys=True)
    result = await session.execute(
        select(LearnedPattern)
        .where(LearnedPattern.pattern_type == pattern_type)
        .where(LearnedPattern.timeframe == timeframe)
    )
    existing = result.scalars().all()

    # Find match by conditions
    for pat in existing:
        if json.dumps(pat.conditions, sort_keys=True) == conditions_str:
            # Update existing
            pat.description = description
            pat.sample_size = sample_size
            pat.accuracy_when_pattern = accuracy_when_pattern
            pat.accuracy_when_not_pattern = accuracy_when_not_pattern
            pat.confidence_modifier = confidence_modifier
            pat.direction_bias = direction_bias
            pat.updated_at = datetime.utcnow()
            return

    # Create new
    session.add(LearnedPattern(
        pattern_type=pattern_type,
        timeframe=timeframe,
        description=description,
        conditions=conditions,
        sample_size=sample_size,
        accuracy_when_pattern=accuracy_when_pattern,
        accuracy_when_not_pattern=accuracy_when_not_pattern,
        confidence_modifier=confidence_modifier,
        direction_bias=direction_bias,
        is_active=True,
    ))


async def get_active_adjustments(
    timeframe: str, features: dict, model_outputs: dict
) -> dict:
    """Get confidence/direction adjustments from active learned patterns.

    Returns:
        {"confidence_modifier": float, "direction_bias": float}
    """
    result = {"confidence_modifier": 1.0, "direction_bias": 0.0}

    try:
        async with async_session() as session:
            res = await session.execute(
                select(LearnedPattern)
                .where(LearnedPattern.is_active == True)
                .where(
                    (LearnedPattern.timeframe == timeframe) |
                    (LearnedPattern.timeframe.is_(None))
                )
            )
            patterns = res.scalars().all()

        if not patterns:
            return result

        modifiers = []
        biases = []

        for pat in patterns:
            if _pattern_matches(pat, features, model_outputs):
                modifiers.append(pat.confidence_modifier)
                biases.append(pat.direction_bias)
                logger.debug(f"Pattern active: {pat.description} (modifier={pat.confidence_modifier})")

        if modifiers:
            # Combine modifiers multiplicatively
            combined_mod = 1.0
            for m in modifiers:
                combined_mod *= m
            result["confidence_modifier"] = max(0.3, min(1.5, combined_mod))

        if biases:
            result["direction_bias"] = sum(biases) / len(biases)

    except Exception as e:
        logger.debug(f"Pattern adjustment lookup error: {e}")

    return result


def _pattern_matches(pattern: "LearnedPattern", features: dict, model_outputs: dict) -> bool:
    """Check if current conditions match a learned pattern."""
    conditions = pattern.conditions or {}

    # Volatility regime
    if "volatility_regime" in conditions:
        vol = features.get("volatility_24h", 2.0)
        regime_map = {"low": (0, 1.0), "normal": (1.0, 3.0), "high": (3.0, 6.0), "extreme": (6.0, float("inf"))}
        low, high = regime_map.get(conditions["volatility_regime"], (0, float("inf")))
        if not (low <= vol < high):
            return False

    # Confidence range
    if "confidence_range" in conditions:
        # Can't check without current confidence — skip (applied post-prediction)
        return False

    # RSI thresholds
    if "rsi_gt" in conditions:
        rsi = features.get("rsi", 50)
        if rsi <= conditions["rsi_gt"]:
            return False

    if "rsi_lt" in conditions:
        rsi = features.get("rsi", 50)
        if rsi >= conditions["rsi_lt"]:
            return False

    # Direction check
    if "direction" in conditions:
        # Can't determine ensemble direction at this point in pre-prediction
        # This pattern type only activates during evaluation
        return False

    # Model agreement
    if "agreement_threshold" in conditions:
        if model_outputs:
            directions = []
            for model_data in model_outputs.values():
                if isinstance(model_data, dict):
                    directions.append(model_data.get("direction"))
            if directions:
                most_common = max(set(directions), key=directions.count)
                agreement = directions.count(most_common) / len(directions)
                if agreement >= conditions["agreement_threshold"]:
                    return False  # Pattern is for LOW agreement; high agreement = no match

    # Hour block
    if "hour_block" in conditions:
        current_hour = datetime.utcnow().hour
        block = (current_hour // 4) * 4
        if block != conditions["hour_block"]:
            return False

    return True
