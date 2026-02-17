"""Marketing API endpoints for n8n workflow consumption.

Aggregates prediction, price, accuracy, sentiment, and signal data
into marketing-ready summaries for AI content generation.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    get_session, Price, Prediction, QuantPrediction,
    Signal, MacroData, OnChainData, News, InfluencerTweet,
    WhaleTransaction, BotUser, PaymentHistory, Referral,
    TradeResult, SupportTicket, PortfolioState,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketing", tags=["marketing"])


@router.get("/daily-summary")
async def daily_summary(session: AsyncSession = Depends(get_session)):
    """Aggregated snapshot for AI content generation.

    Returns current price, predictions, accuracy, sentiment, signals,
    and market context in a single call.
    """
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    # Current price
    price_result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price_row = price_result.scalar_one_or_none()

    # Price 24h ago for change calculation
    price_24h_result = await session.execute(
        select(Price)
        .where(Price.timestamp <= day_ago)
        .order_by(desc(Price.timestamp))
        .limit(1)
    )
    price_24h_row = price_24h_result.scalar_one_or_none()

    current_price = price_row.close if price_row else None
    price_24h_ago = price_24h_row.close if price_24h_row else None
    change_24h_pct = (
        round((current_price - price_24h_ago) / price_24h_ago * 100, 2)
        if current_price and price_24h_ago else None
    )

    # Latest predictions (one per timeframe)
    predictions_data = {}
    for tf in ["1h", "4h", "24h"]:
        pred_result = await session.execute(
            select(Prediction)
            .where(Prediction.timeframe == tf)
            .order_by(desc(Prediction.timestamp))
            .limit(1)
        )
        pred = pred_result.scalar_one_or_none()
        if pred:
            predictions_data[tf] = {
                "direction": pred.direction,
                "confidence": pred.confidence,
                "predicted_price": pred.predicted_price,
                "predicted_change_pct": pred.predicted_change_pct,
                "timestamp": pred.timestamp.isoformat(),
            }

    # Quant prediction
    quant_result = await session.execute(
        select(QuantPrediction).order_by(desc(QuantPrediction.timestamp)).limit(1)
    )
    quant = quant_result.scalar_one_or_none()
    quant_data = None
    if quant:
        quant_data = {
            "direction": quant.direction,
            "action": quant.action,
            "composite_score": quant.composite_score,
            "confidence": quant.confidence,
            "bullish_signals": quant.bullish_signals,
            "bearish_signals": quant.bearish_signals,
            "active_signals": quant.active_signals,
        }

    # Latest signal
    signal_result = await session.execute(
        select(Signal).order_by(desc(Signal.timestamp)).limit(1)
    )
    signal = signal_result.scalar_one_or_none()
    signal_data = None
    if signal:
        signal_data = {
            "action": signal.action,
            "entry_price": signal.entry_price,
            "target_price": signal.target_price,
            "stop_loss": signal.stop_loss,
            "risk_rating": signal.risk_rating,
            "timeframe": signal.timeframe,
            "reasoning": signal.reasoning,
        }

    # 7-day accuracy
    accuracy_result = await session.execute(
        select(Prediction)
        .where(Prediction.timestamp >= week_ago)
        .where(Prediction.was_correct.isnot(None))
    )
    evaluated = accuracy_result.scalars().all()
    total_evaluated = len(evaluated)
    total_correct = sum(1 for p in evaluated if p.was_correct)
    accuracy_7d = round(total_correct / total_evaluated * 100, 1) if total_evaluated > 0 else None

    # News sentiment (last 24h)
    news_result = await session.execute(
        select(News)
        .where(News.timestamp >= day_ago)
        .where(News.sentiment_score.isnot(None))
    )
    news_items = news_result.scalars().all()
    avg_sentiment = (
        round(sum(n.sentiment_score for n in news_items) / len(news_items), 3)
        if news_items else None
    )
    sentiment_label = "neutral"
    if avg_sentiment is not None:
        if avg_sentiment > 0.2:
            sentiment_label = "bullish"
        elif avg_sentiment < -0.2:
            sentiment_label = "bearish"

    # Macro data
    macro_result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    macro = macro_result.scalar_one_or_none()
    macro_data = None
    if macro:
        macro_data = {
            "fear_greed_index": macro.fear_greed_index,
            "fear_greed_label": macro.fear_greed_label,
            "dxy": macro.dxy,
            "gold": macro.gold,
            "sp500": macro.sp500,
        }

    return {
        "timestamp": now.isoformat(),
        "price": {
            "current": current_price,
            "change_24h_pct": change_24h_pct,
            "high_24h": price_row.high if price_row else None,
            "low_24h": price_row.low if price_row else None,
        },
        "predictions": predictions_data,
        "quant": quant_data,
        "signal": signal_data,
        "accuracy_7d": {
            "overall_pct": accuracy_7d,
            "total_predictions": total_evaluated,
            "correct": total_correct,
        },
        "sentiment": {
            "avg_score": avg_sentiment,
            "label": sentiment_label,
            "news_count_24h": len(news_items),
        },
        "macro": macro_data,
    }


@router.get("/performance-card")
async def performance_card(
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Weekly/monthly performance stats for content cards and threads.

    Returns accuracy by timeframe, best/worst calls, and trend data.
    """
    since = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(Prediction)
        .where(Prediction.timestamp >= since)
        .where(Prediction.was_correct.isnot(None))
        .order_by(Prediction.timestamp)
    )
    predictions = result.scalars().all()

    if not predictions:
        return {
            "days": days,
            "total": 0,
            "by_timeframe": {},
            "best_call": None,
            "worst_call": None,
            "streak": 0,
        }

    # By timeframe
    by_timeframe = {}
    for tf in ["1h", "4h", "24h"]:
        tf_preds = [p for p in predictions if p.timeframe == tf]
        tf_correct = sum(1 for p in tf_preds if p.was_correct)
        tf_total = len(tf_preds)
        by_timeframe[tf] = {
            "total": tf_total,
            "correct": tf_correct,
            "accuracy_pct": round(tf_correct / tf_total * 100, 1) if tf_total > 0 else None,
        }

    # Best call (highest confidence that was correct)
    correct_preds = [p for p in predictions if p.was_correct]
    best_call = None
    if correct_preds:
        best = max(correct_preds, key=lambda p: p.confidence)
        best_call = {
            "timeframe": best.timeframe,
            "direction": best.direction,
            "confidence": best.confidence,
            "predicted_change_pct": best.predicted_change_pct,
            "timestamp": best.timestamp.isoformat(),
        }

    # Worst call (highest confidence that was wrong)
    wrong_preds = [p for p in predictions if not p.was_correct]
    worst_call = None
    if wrong_preds:
        worst = max(wrong_preds, key=lambda p: p.confidence)
        worst_call = {
            "timeframe": worst.timeframe,
            "direction": worst.direction,
            "confidence": worst.confidence,
            "predicted_change_pct": worst.predicted_change_pct,
            "timestamp": worst.timestamp.isoformat(),
        }

    # Current streak (consecutive correct from most recent)
    streak = 0
    for p in reversed(predictions):
        if p.was_correct:
            streak += 1
        else:
            break

    # Overall
    total = len(predictions)
    correct = sum(1 for p in predictions if p.was_correct)

    return {
        "days": days,
        "total": total,
        "correct": correct,
        "accuracy_pct": round(correct / total * 100, 1) if total > 0 else None,
        "by_timeframe": by_timeframe,
        "best_call": best_call,
        "worst_call": worst_call,
        "streak": streak,
    }


@router.get("/trending-analysis")
async def trending_analysis(session: AsyncSession = Depends(get_session)):
    """Detect post-worthy market events.

    Checks for large price moves, sentiment spikes, whale activity,
    and other notable events worth posting about.
    """
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    four_hours_ago = now - timedelta(hours=4)
    day_ago = now - timedelta(hours=24)

    events = []

    # 1. Check for significant price moves (>3% in 4h)
    price_now_result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price_now = price_now_result.scalar_one_or_none()

    price_4h_result = await session.execute(
        select(Price)
        .where(Price.timestamp <= four_hours_ago)
        .order_by(desc(Price.timestamp))
        .limit(1)
    )
    price_4h = price_4h_result.scalar_one_or_none()

    if price_now and price_4h and price_4h.close > 0:
        move_pct = (price_now.close - price_4h.close) / price_4h.close * 100
        if abs(move_pct) >= 3:
            events.append({
                "type": "large_price_move",
                "severity": "high" if abs(move_pct) >= 5 else "medium",
                "data": {
                    "move_pct": round(move_pct, 2),
                    "direction": "up" if move_pct > 0 else "down",
                    "price_from": price_4h.close,
                    "price_to": price_now.close,
                    "period": "4h",
                },
            })

    # 2. Check for extreme fear/greed
    macro_result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    macro = macro_result.scalar_one_or_none()
    if macro and macro.fear_greed_index is not None:
        if macro.fear_greed_index <= 15:
            events.append({
                "type": "extreme_fear",
                "severity": "high",
                "data": {
                    "index": macro.fear_greed_index,
                    "label": macro.fear_greed_label,
                },
            })
        elif macro.fear_greed_index >= 85:
            events.append({
                "type": "extreme_greed",
                "severity": "high",
                "data": {
                    "index": macro.fear_greed_index,
                    "label": macro.fear_greed_label,
                },
            })

    # 3. Check for whale activity (last hour)
    whale_result = await session.execute(
        select(WhaleTransaction)
        .where(WhaleTransaction.timestamp >= hour_ago)
        .where(WhaleTransaction.amount_btc >= 500)
        .order_by(desc(WhaleTransaction.amount_btc))
        .limit(5)
    )
    whales = whale_result.scalars().all()
    if whales:
        total_btc = sum(w.amount_btc for w in whales)
        events.append({
            "type": "whale_activity",
            "severity": "high" if total_btc >= 2000 else "medium",
            "data": {
                "transaction_count": len(whales),
                "total_btc": round(total_btc, 2),
                "largest_btc": round(whales[0].amount_btc, 2),
                "largest_from": whales[0].from_entity,
                "largest_to": whales[0].to_entity,
            },
        })

    # 4. Check for high-confidence prediction flip
    latest_preds = {}
    for tf in ["1h", "4h", "24h"]:
        pred_result = await session.execute(
            select(Prediction)
            .where(Prediction.timeframe == tf)
            .order_by(desc(Prediction.timestamp))
            .limit(2)
        )
        preds = pred_result.scalars().all()
        if len(preds) >= 2:
            current_pred, prev_pred = preds[0], preds[1]
            if (current_pred.direction != prev_pred.direction
                    and current_pred.confidence >= 65):
                events.append({
                    "type": "prediction_flip",
                    "severity": "medium",
                    "data": {
                        "timeframe": tf,
                        "from_direction": prev_pred.direction,
                        "to_direction": current_pred.direction,
                        "confidence": current_pred.confidence,
                    },
                })

    # 5. News sentiment spike
    recent_news = await session.execute(
        select(News)
        .where(News.timestamp >= hour_ago)
        .where(News.sentiment_score.isnot(None))
    )
    recent = recent_news.scalars().all()
    if len(recent) >= 3:
        avg_s = sum(n.sentiment_score for n in recent) / len(recent)
        if abs(avg_s) >= 0.5:
            events.append({
                "type": "sentiment_spike",
                "severity": "medium",
                "data": {
                    "avg_sentiment": round(avg_s, 3),
                    "direction": "bullish" if avg_s > 0 else "bearish",
                    "news_count": len(recent),
                    "top_headline": recent[0].title if recent else None,
                },
            })

    return {
        "timestamp": now.isoformat(),
        "has_events": len(events) > 0,
        "event_count": len(events),
        "events": events,
        "current_price": price_now.close if price_now else None,
    }


# ────────────────────────────────────────────────────────────────
#  EXTENDED MARKETING API — Sales, Reports, Growth
# ────────────────────────────────────────────────────────────────


@router.get("/user-metrics")
async def user_metrics(session: AsyncSession = Depends(get_session)):
    """Total users, premium, trial, new today, active 24h."""
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total = (await session.execute(select(func.count(BotUser.id)))).scalar() or 0
    premium = (await session.execute(
        select(func.count(BotUser.id)).where(
            BotUser.subscription_end.isnot(None),
            BotUser.subscription_end > now,
        )
    )).scalar() or 0
    trial = (await session.execute(
        select(func.count(BotUser.id)).where(
            BotUser.trial_end.isnot(None),
            BotUser.trial_end > now,
            BotUser.subscription_tier == "free",
        )
    )).scalar() or 0
    new_today = (await session.execute(
        select(func.count(BotUser.id)).where(BotUser.joined_at >= today_start)
    )).scalar() or 0

    return {
        "timestamp": now.isoformat(),
        "total_users": total,
        "premium_users": premium,
        "trial_users": trial,
        "free_users": total - premium - trial,
        "new_today": new_today,
    }


@router.get("/revenue-metrics")
async def revenue_metrics(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    """Stars revenue, conversions, churn rate."""
    now = datetime.utcnow()
    since = now - timedelta(days=days)

    # Total stars revenue
    result = await session.execute(
        select(func.sum(PaymentHistory.stars_amount))
        .where(PaymentHistory.created_at >= since)
    )
    total_stars = result.scalar() or 0

    # Payment count
    payment_count = (await session.execute(
        select(func.count(PaymentHistory.id))
        .where(PaymentHistory.created_at >= since)
    )).scalar() or 0

    # Unique payers
    unique_payers = (await session.execute(
        select(func.count(func.distinct(PaymentHistory.telegram_id)))
        .where(PaymentHistory.created_at >= since)
    )).scalar() or 0

    # Trial conversions (users who had trial and then paid)
    trial_conversions = (await session.execute(
        select(func.count(func.distinct(PaymentHistory.telegram_id)))
        .where(PaymentHistory.created_at >= since)
    )).scalar() or 0

    # Churned (had premium, now expired)
    churned = (await session.execute(
        select(func.count(BotUser.id)).where(
            BotUser.subscription_end.isnot(None),
            BotUser.subscription_end < now,
            BotUser.subscription_end >= since,
        )
    )).scalar() or 0

    return {
        "days": days,
        "total_stars": total_stars,
        "estimated_usd": round(total_stars * 0.02, 2),  # ~$0.02 per star
        "payment_count": payment_count,
        "unique_payers": unique_payers,
        "trial_conversions": trial_conversions,
        "churned_users": churned,
    }


@router.get("/trial-expiring-users")
async def trial_expiring_users(
    days_remaining: int = Query(2, ge=0, le=7),
    session: AsyncSession = Depends(get_session),
):
    """Users whose trial ends within N days."""
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days_remaining)

    result = await session.execute(
        select(BotUser).where(
            BotUser.trial_end.isnot(None),
            BotUser.trial_end > now,
            BotUser.trial_end <= cutoff,
            BotUser.subscription_tier == "free",
        )
    )
    users = result.scalars().all()

    return {
        "days_remaining": days_remaining,
        "count": len(users),
        "users": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "trial_end": u.trial_end.isoformat() if u.trial_end else None,
                "joined_at": u.joined_at.isoformat() if u.joined_at else None,
            }
            for u in users
        ],
    }


@router.get("/churned-users")
async def churned_users(
    days_since: int = Query(3, ge=1, le=30),
    session: AsyncSession = Depends(get_session),
):
    """Premium users who lapsed N days ago."""
    now = datetime.utcnow()
    target_date = now - timedelta(days=days_since)
    window_start = target_date - timedelta(hours=12)
    window_end = target_date + timedelta(hours=12)

    result = await session.execute(
        select(BotUser).where(
            BotUser.subscription_end.isnot(None),
            BotUser.subscription_end >= window_start,
            BotUser.subscription_end <= window_end,
        )
    )
    users = result.scalars().all()

    return {
        "days_since": days_since,
        "count": len(users),
        "users": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "subscription_end": u.subscription_end.isoformat() if u.subscription_end else None,
            }
            for u in users
        ],
    }


@router.get("/new-users")
async def new_users(
    hours: int = Query(6, ge=1, le=48),
    session: AsyncSession = Depends(get_session),
):
    """Users who joined in last N hours."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(BotUser)
        .where(BotUser.joined_at >= since)
        .order_by(desc(BotUser.joined_at))
    )
    users = result.scalars().all()

    return {
        "hours": hours,
        "count": len(users),
        "users": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "joined_at": u.joined_at.isoformat() if u.joined_at else None,
                "referral_code": u.referral_code,
            }
            for u in users
        ],
    }


@router.get("/upsell-candidates")
async def upsell_candidates(session: AsyncSession = Depends(get_session)):
    """Monthly subscribers with 60+ days tenure (upsell to yearly)."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=60)

    result = await session.execute(
        select(BotUser).where(
            BotUser.subscription_end.isnot(None),
            BotUser.subscription_end > now,
            BotUser.joined_at <= cutoff,
        )
    )
    users = result.scalars().all()

    return {
        "count": len(users),
        "users": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "joined_at": u.joined_at.isoformat() if u.joined_at else None,
                "subscription_end": u.subscription_end.isoformat() if u.subscription_end else None,
                "tenure_days": (now - u.joined_at).days if u.joined_at else 0,
            }
            for u in users
        ],
    }


@router.get("/user-milestones")
async def user_milestones(session: AsyncSession = Depends(get_session)):
    """Users who hit 10/50/100 trades today."""
    milestones = [10, 50, 100, 250, 500]
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    result = await session.execute(
        select(PortfolioState).where(PortfolioState.total_trades > 0)
    )
    portfolios = result.scalars().all()

    milestone_users = []
    for p in portfolios:
        for m in milestones:
            if p.total_trades == m:
                milestone_users.append({
                    "telegram_id": p.telegram_id,
                    "milestone": m,
                    "total_trades": p.total_trades,
                    "winning_trades": p.winning_trades,
                    "win_rate": round(p.winning_trades / p.total_trades * 100, 1) if p.total_trades > 0 else 0,
                })

    return {
        "count": len(milestone_users),
        "users": milestone_users,
    }


@router.get("/referral-leaderboard")
async def referral_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """Top referrers by count."""
    result = await session.execute(
        select(BotUser)
        .where(BotUser.referral_count > 0)
        .order_by(desc(BotUser.referral_count))
        .limit(limit)
    )
    users = result.scalars().all()

    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "username": u.username,
                "referral_count": u.referral_count,
                "referral_code": u.referral_code,
            }
            for i, u in enumerate(users)
        ],
    }
