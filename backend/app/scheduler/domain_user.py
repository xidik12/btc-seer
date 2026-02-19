"""User-facing jobs: advisor, trade management, subscriptions, alerts."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc

from app.config import settings
from app.database import (
    async_session, Price, Prediction, Signal, QuantPrediction,
    IndicatorSnapshot, EventImpact, PortfolioState, TradeAdvice,
    BotUser,
)

logger = logging.getLogger(__name__)


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


# -- Subscription expiry check --

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
