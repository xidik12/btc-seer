from collections import defaultdict
from datetime import datetime, timedelta
import time

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Prediction, PredictionAnalysis, LearnedPattern, ModelPerformanceLog

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

_request_counts: dict[str, list[float]] = defaultdict(list)


def _rate_check(ip: str, limit: int = 60, window: float = 60.0):
    """Simple per-IP rate limiter. Raises 429 if exceeded."""
    now = time.time()
    bucket = _request_counts[ip]
    _request_counts[ip] = [t for t in bucket if t > now - window]
    if len(_request_counts[ip]) >= limit:
        raise HTTPException(429, "Rate limit exceeded. Please slow down.")
    _request_counts[ip].append(now)


@router.get("/current")
async def get_current_predictions(request: Request, session: AsyncSession = Depends(get_session)):
    """Get the latest predictions for all timeframes."""
    _rate_check(request.client.host)
    result = await session.execute(
        select(Prediction)
        .order_by(desc(Prediction.timestamp))
        .limit(5)
    )
    predictions = result.scalars().all()

    if not predictions:
        return {"predictions": {}, "message": "No predictions available yet"}

    pred_dict = {}
    for p in predictions:
        pred_dict[p.timeframe] = {
            "id": p.id,
            "direction": p.direction,
            "confidence": p.confidence,
            "predicted_price": p.predicted_price,
            "predicted_change_pct": p.predicted_change_pct,
            "current_price": p.current_price,
            "timestamp": p.timestamp.isoformat(),
            "model_outputs": p.model_outputs,
        }

    return {"predictions": pred_dict}


@router.get("/history")
async def get_prediction_history(
    request: Request,
    timeframe: str = Query("1h", pattern="^(1h|4h|24h|1w|1mo)$"),
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Get prediction history for accuracy tracking."""
    _rate_check(request.client.host)
    since = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(Prediction)
        .where(Prediction.timeframe == timeframe)
        .where(Prediction.timestamp >= since)
        .order_by(desc(Prediction.timestamp))
    )
    predictions = result.scalars().all()

    history = []
    correct = 0
    total_with_result = 0

    for p in predictions:
        entry = {
            "id": p.id,
            "timestamp": p.timestamp.isoformat(),
            "direction": p.direction,
            "confidence": p.confidence,
            "current_price": p.current_price,
            "predicted_price": p.predicted_price,
            "actual_price": p.actual_price,
            "was_correct": p.was_correct,
        }
        history.append(entry)

        if p.was_correct is not None:
            total_with_result += 1
            if p.was_correct:
                correct += 1

    accuracy = (correct / total_with_result * 100) if total_with_result > 0 else None

    return {
        "timeframe": timeframe,
        "days": days,
        "total_predictions": len(history),
        "evaluated": total_with_result,
        "correct": correct,
        "accuracy_pct": round(accuracy, 1) if accuracy else None,
        "history": history,
    }


@router.get("/analysis")
async def get_prediction_analysis(
    request: Request,
    timeframe: str = Query("1h", pattern="^(1h|4h|24h|1w|1mo)$"),
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Get detailed error analysis and per-model accuracy for predictions."""
    _rate_check(request.client.host)
    since = datetime.utcnow() - timedelta(days=days)

    # Get analyses
    result = await session.execute(
        select(PredictionAnalysis)
        .where(PredictionAnalysis.timeframe == timeframe)
        .where(PredictionAnalysis.timestamp >= since)
        .order_by(desc(PredictionAnalysis.timestamp))
    )
    analyses = result.scalars().all()

    if not analyses:
        return {"timeframe": timeframe, "days": days, "analyses": [], "summary": None}

    # Aggregate per-model accuracy
    model_stats = {}
    error_values = []
    abs_error_values = []
    regime_stats = {}
    trend_stats = {}

    for a in analyses:
        if a.error_pct is not None:
            error_values.append(a.error_pct)
        if a.abs_error_pct is not None:
            abs_error_values.append(a.abs_error_pct)

        # Regime stats
        if a.volatility_regime:
            if a.volatility_regime not in regime_stats:
                regime_stats[a.volatility_regime] = {"correct": 0, "total": 0}
            regime_stats[a.volatility_regime]["total"] += 1
            if a.direction_correct:
                regime_stats[a.volatility_regime]["correct"] += 1

        # Trend stats
        if a.trend_state:
            if a.trend_state not in trend_stats:
                trend_stats[a.trend_state] = {"correct": 0, "total": 0}
            trend_stats[a.trend_state]["total"] += 1
            if a.direction_correct:
                trend_stats[a.trend_state]["correct"] += 1

        # Per-model
        if a.per_model_results:
            for model_name, model_data in a.per_model_results.items():
                if model_name not in model_stats:
                    model_stats[model_name] = {"correct": 0, "total": 0}
                model_stats[model_name]["total"] += 1
                if model_data.get("correct"):
                    model_stats[model_name]["correct"] += 1

    # Compute summaries
    per_model_accuracy = {
        name: {
            "accuracy_pct": round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else None,
            "correct": s["correct"],
            "total": s["total"],
        }
        for name, s in model_stats.items()
    }

    regime_accuracy = {
        regime: {
            "accuracy_pct": round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else None,
            "total": s["total"],
        }
        for regime, s in regime_stats.items()
    }

    trend_accuracy = {
        trend: {
            "accuracy_pct": round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else None,
            "total": s["total"],
        }
        for trend, s in trend_stats.items()
    }

    summary = {
        "total_analyzed": len(analyses),
        "mean_error_pct": round(sum(error_values) / len(error_values), 3) if error_values else None,
        "mean_abs_error_pct": round(sum(abs_error_values) / len(abs_error_values), 3) if abs_error_values else None,
        "per_model_accuracy": per_model_accuracy,
        "regime_accuracy": regime_accuracy,
        "trend_accuracy": trend_accuracy,
    }

    return {
        "timeframe": timeframe,
        "days": days,
        "summary": summary,
        "analyses": [
            {
                "prediction_id": a.prediction_id,
                "timestamp": a.timestamp.isoformat(),
                "error_pct": a.error_pct,
                "abs_error_pct": a.abs_error_pct,
                "direction_correct": a.direction_correct,
                "volatility_regime": a.volatility_regime,
                "trend_state": a.trend_state,
                "model_agreement_score": a.model_agreement_score,
            }
            for a in analyses[:100]  # Limit to 100 most recent
        ],
    }


@router.get("/patterns")
async def get_learned_patterns(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Get active learned patterns that modify prediction confidence."""
    _rate_check(request.client.host)

    result = await session.execute(
        select(LearnedPattern)
        .where(LearnedPattern.is_active == True)
        .order_by(desc(LearnedPattern.sample_size))
    )
    patterns = result.scalars().all()

    return {
        "patterns": [
            {
                "id": p.id,
                "pattern_type": p.pattern_type,
                "timeframe": p.timeframe,
                "description": p.description,
                "conditions": p.conditions,
                "sample_size": p.sample_size,
                "accuracy_when_pattern": p.accuracy_when_pattern,
                "accuracy_when_not_pattern": p.accuracy_when_not_pattern,
                "confidence_modifier": p.confidence_modifier,
                "direction_bias": p.direction_bias,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in patterns
        ],
        "total": len(patterns),
    }


@router.get("/learning-progress")
async def get_learning_progress(
    request: Request,
    days: int = Query(30, ge=7, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Get accuracy trend over time to show learning improvement."""
    _rate_check(request.client.host)
    since = datetime.utcnow() - timedelta(days=days)

    # Get predictions with results
    result = await session.execute(
        select(Prediction)
        .where(Prediction.was_correct.isnot(None))
        .where(Prediction.timestamp >= since)
        .order_by(Prediction.timestamp)
    )
    predictions = result.scalars().all()

    if not predictions:
        return {"days": days, "daily_accuracy": [], "rolling_7d": []}

    # Group by day
    daily = {}
    for p in predictions:
        day = p.timestamp.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"correct": 0, "total": 0, "timeframes": {}}
        daily[day]["total"] += 1
        if p.was_correct:
            daily[day]["correct"] += 1

        tf = p.timeframe
        if tf not in daily[day]["timeframes"]:
            daily[day]["timeframes"][tf] = {"correct": 0, "total": 0}
        daily[day]["timeframes"][tf]["total"] += 1
        if p.was_correct:
            daily[day]["timeframes"][tf]["correct"] += 1

    daily_accuracy = []
    for date in sorted(daily.keys()):
        d = daily[date]
        entry = {
            "date": date,
            "accuracy_pct": round(d["correct"] / d["total"] * 100, 1) if d["total"] > 0 else None,
            "total": d["total"],
            "correct": d["correct"],
            "by_timeframe": {
                tf: round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else None
                for tf, s in d["timeframes"].items()
            },
        }
        daily_accuracy.append(entry)

    # Compute rolling 7-day accuracy
    rolling_7d = []
    for i, entry in enumerate(daily_accuracy):
        window = daily_accuracy[max(0, i - 6):i + 1]
        total = sum(w["total"] for w in window)
        correct = sum(w["correct"] for w in window)
        rolling_7d.append({
            "date": entry["date"],
            "accuracy_pct": round(correct / total * 100, 1) if total > 0 else None,
            "total": total,
        })

    # Count active patterns
    pattern_result = await session.execute(
        select(func.count(LearnedPattern.id))
        .where(LearnedPattern.is_active == True)
    )
    active_patterns = pattern_result.scalar() or 0

    # Count ModelPerformanceLog entries (shows learning loop activation)
    perf_result = await session.execute(
        select(func.count(ModelPerformanceLog.id))
        .where(ModelPerformanceLog.timestamp >= since)
    )
    perf_log_count = perf_result.scalar() or 0

    return {
        "days": days,
        "daily_accuracy": daily_accuracy,
        "rolling_7d": rolling_7d,
        "active_patterns": active_patterns,
        "performance_log_entries": perf_log_count,
    }
