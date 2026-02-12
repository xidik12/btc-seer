"""Training feedback loop: analyze mock trade outcomes vs AI predictions.

Includes adaptive weight learning that adjusts ensemble model weights
based on per-model accuracy from recent predictions.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc, func

from app.database import (
    async_session, TradeAdvice, TradeResult, Prediction, ModelFeedback,
    ModelPerformanceLog,
)

logger = logging.getLogger(__name__)


async def run_training_feedback():
    """Analyze closed mock trades vs predictions for model improvement.

    Runs daily. Correlates trade outcomes with the prediction that was active
    at entry time, then stores aggregated feedback metrics.
    """
    try:
        since = datetime.utcnow() - timedelta(hours=24)

        # 1. Get all closed mock trades from last 24h
        async with async_session() as session:
            result = await session.execute(
                select(TradeResult)
                .join(TradeAdvice, TradeResult.trade_advice_id == TradeAdvice.id)
                .where(
                    TradeAdvice.is_mock == True,
                    TradeResult.timestamp >= since,
                )
                .order_by(desc(TradeResult.timestamp))
            )
            trade_results = result.scalars().all()

        if not trade_results:
            logger.info("Training feedback: no closed mock trades in last 24h")
            return

        # 2. For each trade, look up the prediction at entry time
        direction_correct = 0
        total = len(trade_results)
        confidences = []
        predicted_rrs = []
        achieved_rrs = []
        pnl_pcts = []
        per_trade_details = []

        for tr in trade_results:
            # Get the trade advice to find prediction_id
            async with async_session() as session:
                result = await session.execute(
                    select(TradeAdvice).where(TradeAdvice.id == tr.trade_advice_id)
                )
                advice = result.scalar_one_or_none()

            if not advice:
                continue

            # Find prediction closest to trade entry time
            entry_time = advice.opened_at or advice.timestamp
            async with async_session() as session:
                if advice.prediction_id:
                    result = await session.execute(
                        select(Prediction).where(Prediction.id == advice.prediction_id)
                    )
                else:
                    result = await session.execute(
                        select(Prediction)
                        .where(Prediction.timestamp <= entry_time)
                        .order_by(desc(Prediction.timestamp))
                        .limit(1)
                    )
                pred = result.scalar_one_or_none()

            # Compare prediction direction vs actual outcome
            pred_direction = pred.direction if pred else None
            actual_won = tr.was_winner
            trade_direction = tr.direction  # LONG or SHORT

            # Check if prediction direction matched trade outcome
            if pred:
                pred_was_right = (
                    (pred_direction == "bullish" and trade_direction == "LONG" and actual_won) or
                    (pred_direction == "bearish" and trade_direction == "SHORT" and actual_won) or
                    (pred_direction == "bullish" and trade_direction == "SHORT" and not actual_won) or
                    (pred_direction == "bearish" and trade_direction == "LONG" and not actual_won)
                )
                if pred_was_right:
                    direction_correct += 1
                confidences.append(pred.confidence)

            # Track R:R
            if advice.risk_reward_ratio:
                predicted_rrs.append(advice.risk_reward_ratio)

            # Actual achieved R:R
            if advice.risk_amount_usdt and advice.risk_amount_usdt > 0:
                achieved_rr = abs(tr.pnl_usdt) / advice.risk_amount_usdt
                if not tr.was_winner:
                    achieved_rr = -achieved_rr
                achieved_rrs.append(achieved_rr)

            pnl_pcts.append(tr.pnl_pct_leveraged or tr.pnl_pct or 0)

            per_trade_details.append({
                "trade_id": tr.trade_advice_id,
                "direction": trade_direction,
                "was_winner": actual_won,
                "pnl_pct": round(tr.pnl_pct_leveraged or 0, 2),
                "pred_direction": pred_direction,
                "pred_confidence": round(pred.confidence, 1) if pred else None,
            })

        # 3. Aggregate metrics
        direction_accuracy = (direction_correct / total * 100) if total > 0 else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        avg_predicted_rr = sum(predicted_rrs) / len(predicted_rrs) if predicted_rrs else 0
        avg_achieved_rr = sum(achieved_rrs) / len(achieved_rrs) if achieved_rrs else 0
        avg_pnl_pct = sum(pnl_pcts) / len(pnl_pcts) if pnl_pcts else 0
        winning = sum(1 for tr in trade_results if tr.was_winner)

        # 4. Store in ModelFeedback table
        async with async_session() as session:
            feedback = ModelFeedback(
                period="daily",
                total_trades=total,
                winning_trades=winning,
                direction_accuracy=round(direction_accuracy, 2),
                avg_confidence=round(avg_confidence, 2),
                avg_predicted_rr=round(avg_predicted_rr, 2),
                avg_achieved_rr=round(avg_achieved_rr, 2),
                avg_pnl_pct=round(avg_pnl_pct, 2),
                feedback_json={
                    "trades": per_trade_details,
                    "confidence_buckets": _confidence_calibration(per_trade_details),
                },
            )
            session.add(feedback)
            await session.commit()

        logger.info(
            f"Training feedback: {total} trades, {winning} wins, "
            f"direction_acc={direction_accuracy:.1f}%, "
            f"avg_pnl={avg_pnl_pct:.2f}%"
        )

    except Exception as e:
        logger.error(f"Training feedback error: {e}", exc_info=True)


def _confidence_calibration(trade_details):
    """Group trades by confidence bucket and compute win rate per bucket."""
    buckets = {"50-60": [], "60-70": [], "70-80": [], "80-90": [], "90-100": []}

    for t in trade_details:
        conf = t.get("pred_confidence")
        if conf is None:
            continue
        if conf < 60:
            buckets["50-60"].append(t)
        elif conf < 70:
            buckets["60-70"].append(t)
        elif conf < 80:
            buckets["70-80"].append(t)
        elif conf < 90:
            buckets["80-90"].append(t)
        else:
            buckets["90-100"].append(t)

    result = {}
    for bucket, trades in buckets.items():
        if trades:
            wins = sum(1 for t in trades if t["was_winner"])
            result[bucket] = {
                "total": len(trades),
                "wins": wins,
                "win_rate": round(wins / len(trades) * 100, 1),
            }
    return result


async def get_feedback_stats(days: int = 30) -> dict:
    """Get aggregated feedback stats for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)

    async with async_session() as session:
        result = await session.execute(
            select(ModelFeedback)
            .where(ModelFeedback.timestamp >= since)
            .order_by(desc(ModelFeedback.timestamp))
        )
        feedbacks = result.scalars().all()

    if not feedbacks:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "direction_accuracy": 0,
            "avg_confidence": 0,
            "avg_predicted_rr": 0,
            "avg_achieved_rr": 0,
            "avg_pnl_pct": 0,
            "days": days,
            "data_points": 0,
            "daily": [],
            "confidence_calibration": {},
        }

    # Aggregate across all daily entries
    total_trades = sum(f.total_trades for f in feedbacks)
    winning_trades = sum(f.winning_trades for f in feedbacks)

    # Weighted averages
    direction_accuracy = (
        sum(f.direction_accuracy * f.total_trades for f in feedbacks) / total_trades
        if total_trades > 0 else 0
    )
    avg_confidence = (
        sum(f.avg_confidence * f.total_trades for f in feedbacks) / total_trades
        if total_trades > 0 else 0
    )
    avg_pnl_pct = (
        sum(f.avg_pnl_pct * f.total_trades for f in feedbacks) / total_trades
        if total_trades > 0 else 0
    )
    avg_predicted_rr = (
        sum(f.avg_predicted_rr * f.total_trades for f in feedbacks) / total_trades
        if total_trades > 0 else 0
    )
    avg_achieved_rr = (
        sum(f.avg_achieved_rr * f.total_trades for f in feedbacks) / total_trades
        if total_trades > 0 else 0
    )

    # Merge confidence calibration across days
    merged_cal = {}
    for f in feedbacks:
        if f.feedback_json and "confidence_buckets" in f.feedback_json:
            for bucket, data in f.feedback_json["confidence_buckets"].items():
                if bucket not in merged_cal:
                    merged_cal[bucket] = {"total": 0, "wins": 0}
                merged_cal[bucket]["total"] += data["total"]
                merged_cal[bucket]["wins"] += data["wins"]

    for bucket in merged_cal:
        t = merged_cal[bucket]["total"]
        w = merged_cal[bucket]["wins"]
        merged_cal[bucket]["win_rate"] = round(w / t * 100, 1) if t > 0 else 0

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "direction_accuracy": round(direction_accuracy, 1),
        "avg_confidence": round(avg_confidence, 1),
        "avg_predicted_rr": round(avg_predicted_rr, 2),
        "avg_achieved_rr": round(avg_achieved_rr, 2),
        "avg_pnl_pct": round(avg_pnl_pct, 2),
        "days": days,
        "data_points": len(feedbacks),
        "daily": [
            {
                "date": f.timestamp.strftime("%Y-%m-%d"),
                "trades": f.total_trades,
                "wins": f.winning_trades,
                "direction_accuracy": f.direction_accuracy,
                "avg_pnl_pct": f.avg_pnl_pct,
            }
            for f in feedbacks[:30]
        ],
        "confidence_calibration": merged_cal,
    }


async def run_adaptive_weight_learning():
    """Adjust ensemble weights based on per-model accuracy over recent predictions.

    Reads ModelPerformanceLog entries from the last 7 days, computes accuracy
    per model, and stores updated weights that the EnsemblePredictor will pick up.

    Runs daily after run_training_feedback.
    """
    try:
        since = datetime.utcnow() - timedelta(days=7)

        async with async_session() as session:
            result = await session.execute(
                select(ModelPerformanceLog)
                .where(
                    ModelPerformanceLog.timestamp >= since,
                    ModelPerformanceLog.was_correct.isnot(None),
                    ModelPerformanceLog.timeframe == "1h",
                )
            )
            logs = result.scalars().all()

        if len(logs) < 20:
            logger.info(f"Adaptive learning: only {len(logs)} data points, need 20+. Skipping.")
            return

        # Compute per-model accuracy
        model_stats = {}
        for log in logs:
            name = log.model_name
            if name == "ensemble":
                continue
            if name not in model_stats:
                model_stats[name] = {"correct": 0, "total": 0}
            model_stats[name]["total"] += 1
            if log.was_correct:
                model_stats[name]["correct"] += 1

        if not model_stats:
            logger.info("Adaptive learning: no per-model data found.")
            return

        # Calculate accuracy and new weights
        model_accuracy = {}
        for name, stats in model_stats.items():
            if stats["total"] >= 5:
                model_accuracy[name] = stats["correct"] / stats["total"]
            else:
                model_accuracy[name] = 0.5  # Assume baseline if insufficient data

        # Minimum weights to prevent any model from being zeroed out
        MIN_WEIGHT = 0.05
        DEFAULT_KEYS = {"tft": 0.40, "lstm": 0.20, "xgb": 0.25, "timesfm": 0.15}

        new_weights = {}
        for key, default_w in DEFAULT_KEYS.items():
            acc = model_accuracy.get(key, 0.5)
            # Scale weight by accuracy: better accuracy = higher weight
            # Use a blend: 60% data-driven + 40% default prior
            data_weight = max(MIN_WEIGHT, acc * default_w * 2)
            new_weights[key] = 0.6 * data_weight + 0.4 * default_w

        # Normalize to sum to 1
        total = sum(new_weights.values())
        new_weights = {k: round(v / total, 4) for k, v in new_weights.items()}

        # Store in ModelFeedback as a special "weights" entry
        async with async_session() as session:
            feedback = ModelFeedback(
                period="adaptive_weights",
                total_trades=len(logs),
                winning_trades=sum(1 for l in logs if l.was_correct),
                direction_accuracy=round(
                    sum(1 for l in logs if l.was_correct) / len(logs) * 100, 2
                ),
                avg_confidence=0,
                avg_predicted_rr=0,
                avg_achieved_rr=0,
                avg_pnl_pct=0,
                feedback_json={
                    "type": "adaptive_weights",
                    "new_weights": new_weights,
                    "model_accuracy": {k: round(v, 4) for k, v in model_accuracy.items()},
                    "sample_size": {k: v["total"] for k, v in model_stats.items()},
                },
            )
            session.add(feedback)
            await session.commit()

        logger.info(
            f"Adaptive learning: updated weights {new_weights} "
            f"(accuracy: {model_accuracy}, n={len(logs)})"
        )

        # Try to update live ensemble if available
        try:
            from app.models.ensemble import EnsemblePredictor
            # The weights will be picked up on next prediction cycle
            # by reading from DB in the scheduler
        except Exception:
            pass

        return new_weights

    except Exception as e:
        logger.error(f"Adaptive weight learning error: {e}", exc_info=True)
        return None
