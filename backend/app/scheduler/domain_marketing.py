"""Marketing & operations jobs: metrics snapshots, prediction game, cleanup, database backup."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc, func, and_, or_

from app.database import (
    async_session, Price, News, Feature, Prediction, Signal,
    MacroData, OnChainData, InfluencerTweet, QuantPrediction,
    FundingRate, BtcDominance, IndicatorSnapshot, AlertLog,
    WhaleTransaction, MarketingMetrics, SupportTicket,
    PaymentHistory, ApiUsageLog, Referral, BotUser,
    UserPrediction, GameProfile, DailyBriefing,
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

                # Calculate points (multiplier only applies to wins, losses are flat -5)
                if was_correct:
                    points = int(CORRECT_POINTS * pred.multiplier)
                else:
                    points = WRONG_POINTS
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

                profile.total_predictions = (profile.total_predictions or 0) + 1
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


# -- Onboarding Drip Sequence --

DRIP_MESSAGES = {
    1: (
        "\U0001f44b Welcome to BTC Seer Premium!\n\n"
        "Your 7-day trial is active. Here\u2019s what you can do:\n\n"
        "\U0001f9e0 /predict \u2014 AI predictions with confidence scores\n"
        "\U0001f4e1 /signal \u2014 Live trading signals with entry/target/stop\n"
        "\U0001f3af /advisor \u2014 Personalized AI trading plans\n"
        "\U0001f3ae /game \u2014 Daily BTC prediction challenge\n\n"
        "Try /predict now to see your first AI prediction!"
    ),
    3: (
        "\U0001f4ca Day 3 of your trial!\n\n"
        "Did you know? BTC Seer\u2019s AI has been tracking accuracy:\n"
        "\u2022 Use /accuracy to see our track record\n"
        "\u2022 Our ensemble uses 4 AI models (TFT, LSTM, XGBoost, TimeSFM)\n\n"
        "Try /advisor for a personalized trade recommendation!"
    ),
    5: (
        "\u23f0 2 days left on your trial!\n\n"
        "You\u2019ve had access to premium features. Here\u2019s what you\u2019ll lose:\n"
        "\u2022 AI predictions across 5 timeframes\n"
        "\u2022 Live trading signals\n"
        "\u2022 Whale & smart money tracking\n"
        "\u2022 Daily AI briefings\n\n"
        "Subscribe now to keep access \u2192 /subscribe"
    ),
    7: (
        "\U0001f514 Your trial ends today!\n\n"
        "Subscribe to keep your premium access:\n"
        "\U0001f4ab 500 Stars/month (~$9.99)\n"
        "\U0001f4ab 1250 Stars/quarter (Save 17%)\n"
        "\U0001f4ab 4500 Stars/year (Save 25%)\n\n"
        "\u2192 /subscribe"
    ),
}


async def send_onboarding_drip():
    """Send personalized onboarding drip messages to trial users.

    Runs daily at 09:00 UTC. Each day's message is sent only once per user,
    tracked via a Redis/local cache key: drip:{telegram_id}:day{N}.
    """
    from app.config import settings
    from app.cache import cache_get, cache_set

    if not settings.subscription_enabled:
        return

    if not settings.telegram_bot_token:
        logger.debug("No bot token, skipping onboarding drip")
        return

    try:
        now = datetime.utcnow()

        async with async_session() as session:
            # Query all trial users with an active trial
            result = await session.execute(
                select(BotUser).where(
                    BotUser.subscription_tier == "trial",
                    BotUser.trial_end.isnot(None),
                )
            )
            trial_users = result.scalars().all()

        if not trial_users:
            return

        from aiogram import Bot
        bot = Bot(token=settings.telegram_bot_token)
        sent = 0

        try:
            for user in trial_users:
                try:
                    # Calculate days since start (use joined_at as trial start)
                    start_date = user.joined_at
                    if not start_date:
                        continue

                    days_since_start = (now - start_date).days + 1  # Day 1 = signup day

                    # Check if there's a drip message for this day
                    message = DRIP_MESSAGES.get(days_since_start)
                    if not message:
                        continue

                    # Check if already sent today via cache
                    cache_key = f"drip:{user.telegram_id}:day{days_since_start}"
                    already_sent = await cache_get(cache_key)
                    if already_sent:
                        continue

                    # Send the message
                    await bot.send_message(
                        user.telegram_id,
                        message,
                        parse_mode="HTML",
                    )

                    # Mark as sent (TTL = 25 hours to cover daily runs with some buffer)
                    await cache_set(cache_key, {"sent": True}, ttl=90000)
                    sent += 1

                except Exception as e:
                    # User may have blocked the bot — log and continue
                    logger.debug(f"Drip send failed for {user.telegram_id}: {e}")

        finally:
            await bot.session.close()

        if sent:
            logger.info(f"Onboarding drip: sent {sent} messages")

    except Exception as e:
        logger.error(f"send_onboarding_drip error: {e}", exc_info=True)


async def send_daily_briefing_push():
    """Send a concise daily briefing push notification to all active subscribers/trialists.

    Runs daily at 08:00 UTC. Includes:
    - Current BTC price + 24h change
    - Yesterday's 24h prediction result (correct/incorrect)
    - Today's outlook summary from the latest DailyBriefing
    """
    from app.config import settings

    if not settings.telegram_bot_token:
        logger.debug("No bot token, skipping daily briefing push")
        return

    try:
        now = datetime.utcnow()
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        async with async_session() as session:
            # 1. Get latest daily briefing
            result = await session.execute(
                select(DailyBriefing).order_by(desc(DailyBriefing.date)).limit(1)
            )
            briefing = result.scalar_one_or_none()

            # 2. Get current BTC price
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            price_row = result.scalar_one_or_none()
            btc_price = price_row.close if price_row else None

            # 3. Get yesterday's 24h prediction result
            result = await session.execute(
                select(Prediction)
                .where(Prediction.timeframe == "24h")
                .order_by(desc(Prediction.timestamp))
                .limit(5)
            )
            recent_preds = result.scalars().all()

            # Find a resolved 24h prediction (was_correct is not None)
            yesterday_pred = None
            for p in recent_preds:
                if p.was_correct is not None:
                    yesterday_pred = p
                    break

            # 4. Get all users with active subscription OR active trial
            if settings.subscription_enabled:
                query = select(BotUser).where(
                    or_(
                        and_(
                            BotUser.subscription_tier == "premium",
                            BotUser.subscription_end.isnot(None),
                            BotUser.subscription_end > now,
                        ),
                        and_(
                            BotUser.trial_end.isnot(None),
                            BotUser.trial_end > now,
                        ),
                    )
                )
            else:
                # If subscriptions not enabled, send to all subscribed users
                query = select(BotUser).where(BotUser.subscribed == True)

            result = await session.execute(query)
            users = result.scalars().all()

        if not users:
            logger.info("No eligible users for daily briefing push")
            return

        # -- Build the message --
        lines = ["\U0001f305 <b>Good morning! Your BTC Seer Daily Brief:</b>\n"]

        # Price line
        if btc_price:
            price_str = f"${btc_price:,.0f}"
            if briefing and briefing.btc_24h_change is not None:
                change = briefing.btc_24h_change
                sign = "+" if change >= 0 else ""
                lines.append(f"\U0001f4ca BTC: <b>{price_str}</b> ({sign}{change:.1f}%)")
            else:
                lines.append(f"\U0001f4ca BTC: <b>{price_str}</b>")

        # Yesterday's prediction result
        if yesterday_pred:
            was_correct = yesterday_pred.was_correct
            direction = yesterday_pred.direction or "unknown"
            result_emoji = "\u2705 CORRECT" if was_correct else "\u274c WRONG"
            lines.append(
                f"\U0001f9e0 Yesterday's 24h call: {result_emoji} "
                f"(predicted {direction.upper()})"
            )

        # Today's outlook from briefing
        if briefing and briefing.summary_text:
            # Extract first 1-2 sentences for a compact outlook
            full_text = briefing.summary_text.strip()
            # Strip HTML tags for plain text extraction
            import re
            clean = re.sub(r"<[^>]+>", "", full_text)
            sentences = re.split(r"(?<=[.!?])\s+", clean)
            outlook = " ".join(sentences[:2]).strip()
            if len(outlook) > 280:
                outlook = outlook[:277] + "..."
            lines.append(f"\n\U0001f4c8 Today's outlook: {outlook}")

        lines.append("\n<i>Open BTC Seer for full analysis \u2192</i>")

        message = "\n".join(lines)

        # -- Send to all eligible users --
        from aiogram import Bot
        bot = Bot(token=settings.telegram_bot_token)

        sent = 0
        failed = 0
        try:
            for user in users:
                try:
                    await bot.send_message(
                        user.telegram_id,
                        message,
                        parse_mode="HTML",
                    )
                    sent += 1
                except Exception as e:
                    failed += 1
                    logger.debug(f"Briefing push failed for {user.telegram_id}: {e}")
        finally:
            await bot.session.close()

        logger.info(f"Daily briefing push: sent {sent}, failed {failed} (total eligible: {len(users)})")

    except Exception as e:
        logger.error(f"send_daily_briefing_push error: {e}", exc_info=True)
