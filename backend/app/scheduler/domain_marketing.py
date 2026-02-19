"""Marketing & operations jobs: metrics snapshots, prediction game, cleanup, database backup."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc, func, and_

from app.database import (
    async_session, Price, News, Feature, Prediction, Signal,
    MacroData, OnChainData, InfluencerTweet, QuantPrediction,
    FundingRate, BtcDominance, IndicatorSnapshot, AlertLog,
    WhaleTransaction, MarketingMetrics, SupportTicket,
    PaymentHistory, ApiUsageLog, Referral, BotUser,
    UserPrediction, GameProfile,
)

logger = logging.getLogger(__name__)


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


# -- Prediction Game Jobs --

CORRECT_POINTS = 10
WRONG_POINTS = -5
STREAK_MULTIPLIERS = {3: 2.0, 5: 3.0, 10: 5.0}


def _get_multiplier(streak: int) -> float:
    mult = 1.0
    for threshold, m in sorted(STREAK_MULTIPLIERS.items()):
        if streak >= threshold:
            mult = m
    return mult


async def evaluate_game_predictions():
    """Resolve pending game predictions. Runs every hour at :05."""
    try:
        now = datetime.utcnow()
        yesterday = (now - timedelta(hours=24)).strftime("%Y-%m-%d")

        async with async_session() as session:
            # Get current BTC price
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            price_row = result.scalar_one_or_none()
            if not price_row:
                return
            current_price = price_row.close

            # Get pending 24h predictions from yesterday (they've had 24h to resolve)
            result = await session.execute(
                select(UserPrediction).where(
                    UserPrediction.status == "pending",
                    UserPrediction.round_date <= yesterday,
                )
            )
            pending = result.scalars().all()

            if not pending:
                return

            resolved = 0
            for pred in pending:
                pred.resolve_price = current_price
                pred.status = "resolved"
                was_correct = (
                    (pred.direction == "up" and current_price > pred.lock_price) or
                    (pred.direction == "down" and current_price < pred.lock_price)
                )
                pred.was_correct = was_correct

                # Calculate points
                base_points = CORRECT_POINTS if was_correct else WRONG_POINTS
                points = int(base_points * pred.multiplier)
                pred.points_earned = points

                # Update game profile
                result = await session.execute(
                    select(GameProfile).where(GameProfile.telegram_id == pred.telegram_id)
                )
                profile = result.scalar_one_or_none()
                if not profile:
                    profile = GameProfile(telegram_id=pred.telegram_id)
                    session.add(profile)
                    await session.flush()

                profile.total_points = max(0, (profile.total_points or 0) + points)
                profile.weekly_points = max(0, (profile.weekly_points or 0) + points)
                profile.monthly_points = max(0, (profile.monthly_points or 0) + points)

                if was_correct:
                    profile.correct_predictions = (profile.correct_predictions or 0) + 1
                    profile.current_streak = (profile.current_streak or 0) + 1
                    if profile.current_streak > (profile.best_streak or 0):
                        profile.best_streak = profile.current_streak
                else:
                    profile.current_streak = 0

                # Recalculate accuracy
                if profile.total_predictions and profile.total_predictions > 0:
                    profile.accuracy_pct = (profile.correct_predictions or 0) / profile.total_predictions * 100

                resolved += 1

            await session.commit()
            if resolved:
                logger.info(f"Game predictions resolved: {resolved}")

    except Exception as e:
        logger.error(f"evaluate_game_predictions error: {e}", exc_info=True)


async def reset_game_periods():
    """Reset weekly/monthly leaderboard points. Runs daily at 00:00 UTC."""
    try:
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        weekday = now.weekday()  # 0 = Monday
        day_of_month = now.day

        async with async_session() as session:
            result = await session.execute(select(GameProfile))
            profiles = result.scalars().all()

            updated = 0
            for profile in profiles:
                # Reset weekly on Monday
                if weekday == 0 and profile.weekly_reset_date != today:
                    profile.weekly_points = 0
                    profile.weekly_reset_date = today
                    updated += 1

                # Reset monthly on 1st
                if day_of_month == 1 and profile.monthly_reset_date != today:
                    profile.monthly_points = 0
                    profile.monthly_reset_date = today
                    updated += 1

            if updated:
                await session.commit()
                logger.info(f"Game period reset: {updated} profile updates")

    except Exception as e:
        logger.error(f"reset_game_periods error: {e}", exc_info=True)
