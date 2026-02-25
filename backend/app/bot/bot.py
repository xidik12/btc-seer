import logging
import time
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router, BaseMiddleware
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, LabeledPrice
from sqlalchemy import select, desc, update

from app.config import settings
from app.database import async_session, BotUser, TradeAdvice, Price, PaymentHistory, Prediction, GameProfile, UserPrediction, PriceAlert
from app.bot.commands import router as commands_router
from app.bot.keyboards import main_keyboard, settings_keyboard, advisor_keyboard, trade_close_keyboard, feedback_keyboard
from app.bot.subscription import check_premium, activate_premium, get_status_text

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseMiddleware):
    _timestamps: dict[int, float] = {}
    RATE_LIMIT = 1.0  # seconds between commands

    async def __call__(self, handler, event, data):
        user_id = getattr(getattr(event, 'from_user', None), 'id', None)
        if user_id:
            now = time.time()
            last = self._timestamps.get(user_id, 0)
            if now - last < self.RATE_LIMIT:
                return  # silently drop
            self._timestamps[user_id] = now

            # Update last_active timestamp for the user
            try:
                async with async_session() as session:
                    await session.execute(
                        update(BotUser)
                        .where(BotUser.telegram_id == user_id)
                        .values(last_active=datetime.utcnow())
                    )
                    await session.commit()
            except Exception:
                pass  # Don't break bot flow if activity tracking fails

        return await handler(event, data)


# Callback query router
callback_router = Router()


@callback_router.callback_query(lambda c: c.data == "predict")
async def cb_predict(callback: CallbackQuery):
    if not await check_premium(callback):
        return
    from app.bot.commands import cmd_predict
    await callback.answer()
    await cmd_predict(callback.message, _from_user_id=callback.from_user.id)


@callback_router.callback_query(lambda c: c.data == "signal")
async def cb_signal(callback: CallbackQuery):
    if not await check_premium(callback):
        return
    from app.bot.commands import cmd_signal
    await callback.answer()
    await cmd_signal(callback.message, _from_user_id=callback.from_user.id)


@callback_router.callback_query(lambda c: c.data == "news")
async def cb_news(callback: CallbackQuery):
    if not await check_premium(callback):
        return
    from app.bot.commands import cmd_news
    await callback.answer()
    await cmd_news(callback.message)


@callback_router.callback_query(lambda c: c.data == "accuracy")
async def cb_accuracy(callback: CallbackQuery):
    if not await check_premium(callback):
        return
    from app.bot.commands import cmd_accuracy
    await callback.answer()
    await cmd_accuracy(callback.message)


@callback_router.callback_query(lambda c: c.data == "settings")
async def cb_settings(callback: CallbackQuery):
    from app.bot.commands import cmd_settings
    await callback.answer()
    await cmd_settings(callback.message)


@callback_router.callback_query(lambda c: c.data == "back_to_main")
async def cb_back(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🔮 <b>BTC Seer</b> — What would you like to see?",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@callback_router.callback_query(lambda c: c.data and c.data.startswith("set_interval:"))
async def cb_set_interval(callback: CallbackQuery):
    interval = callback.data.split(":")[1]
    if interval not in ("1h", "4h", "24h"):
        await callback.answer("Invalid interval.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.alert_interval = interval
            await session.commit()

    await callback.answer(f"Alert interval set to {interval}")
    await callback.message.edit_text(
        f"⚙️ <b>Alert Settings</b>\n\nAlert interval: <b>{interval}</b>",
        parse_mode="HTML",
        reply_markup=settings_keyboard(interval),
    )


@callback_router.callback_query(lambda c: c.data == "unsubscribe")
async def cb_unsubscribe(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.subscribed = False
            await session.commit()

    await callback.answer("Unsubscribed from alerts")
    await callback.message.edit_text(
        "🔕 You've been unsubscribed from alerts.\n\n"
        "Use /start to re-subscribe anytime.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# ────────────────────────────────────────────────────────────────
#  ADVISOR CALLBACKS
# ────────────────────────────────────────────────────────────────

@callback_router.callback_query(lambda c: c.data == "advisor_portfolio")
async def cb_advisor_portfolio(callback: CallbackQuery):
    if not await check_premium(callback):
        return
    from app.bot.commands import cmd_advisor
    await callback.answer()
    await cmd_advisor(callback.message, _from_user_id=callback.from_user.id)


@callback_router.callback_query(lambda c: c.data == "advisor_trades")
async def cb_advisor_trades(callback: CallbackQuery):
    if not await check_premium(callback):
        return
    from app.bot.commands import cmd_trades
    await callback.answer()
    await cmd_trades(callback.message, _from_user_id=callback.from_user.id)


@callback_router.callback_query(lambda c: c.data == "advisor_history")
async def cb_advisor_history(callback: CallbackQuery):
    if not await check_premium(callback):
        return
    from app.bot.commands import cmd_history
    await callback.answer()
    await cmd_history(callback.message, _from_user_id=callback.from_user.id)


@callback_router.callback_query(lambda c: c.data == "advisor_risk")
async def cb_advisor_risk(callback: CallbackQuery):
    """Show risk settings for the advisor."""
    if not await check_premium(callback):
        return
    await callback.answer()

    from app.advisor.portfolio import get_or_create_portfolio
    portfolio = await get_or_create_portfolio(callback.from_user.id)

    text = (
        "<b>Risk Settings</b>\n\n"
        f"Max risk per trade: {portfolio.max_risk_per_trade_pct:.1f}%\n"
        f"Max leverage: {portfolio.max_leverage}x\n"
        f"Max open trades: {portfolio.max_open_trades}\n"
        f"Daily max loss: {portfolio.daily_max_loss_pct:.1f}%\n\n"
        "<i>Risk settings auto-adjust based on performance.\n"
        "Use /setbalance to update your balance.</i>"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=advisor_keyboard())


@callback_router.callback_query(lambda c: c.data and c.data.startswith("trade_opened:"))
async def cb_trade_opened(callback: CallbackQuery):
    """User confirms they opened the trade."""
    trade_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.id == trade_id,
                TradeAdvice.telegram_id == callback.from_user.id,
            )
        )
        trade = result.scalar_one_or_none()

        if trade and trade.status == "pending":
            from datetime import datetime
            trade.status = "opened"
            trade.opened_at = datetime.utcnow()
            await session.commit()

    await callback.answer("Trade marked as opened!")
    await callback.message.edit_reply_markup(reply_markup=trade_close_keyboard(trade_id))


@callback_router.callback_query(lambda c: c.data and c.data.startswith("trade_cancel:"))
async def cb_trade_cancel(callback: CallbackQuery):
    """User skips the trade plan."""
    trade_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.id == trade_id,
                TradeAdvice.telegram_id == callback.from_user.id,
            )
        )
        trade = result.scalar_one_or_none()

        if trade and trade.status == "pending":
            trade.status = "cancelled"
            trade.close_reason = "skipped"
            await session.commit()

    await callback.answer("Trade skipped.")
    await callback.message.edit_reply_markup(reply_markup=None)


@callback_router.callback_query(lambda c: c.data and c.data.startswith("trade_close:"))
async def cb_trade_close(callback: CallbackQuery):
    """User wants to close an open trade at current price."""
    trade_id = int(callback.data.split(":")[1])

    # Get current price
    async with async_session() as session:
        result = await session.execute(
            select(Price).order_by(Price.timestamp.desc()).limit(1)
        )
        price_row = result.scalar_one_or_none()

    if not price_row:
        await callback.answer("No current price available.")
        return

    from app.advisor.portfolio import record_trade_result

    result = await record_trade_result(
        telegram_id=callback.from_user.id,
        trade_id=trade_id,
        exit_price=price_row.close,
        reason="manual_close",
    )

    if not result:
        await callback.answer("Trade not found or already closed.")
        return

    emoji = "✅" if result.was_winner else "❌"
    text = (
        f"{emoji} <b>Trade #{trade_id} Closed</b>\n\n"
        f"Exit: <code>${result.exit_price:,.0f}</code>\n"
        f"PnL: <code>${result.pnl_usdt:+.4f}</code> ({result.pnl_pct_leveraged:+.2f}%)\n"
        f"Balance: ${result.balance_before:.4f} -> ${result.balance_after:.4f}"
    )

    await callback.answer("Trade closed!")
    await callback.message.answer(text, parse_mode="HTML", reply_markup=advisor_keyboard())
    await callback.message.edit_reply_markup(reply_markup=None)


@callback_router.callback_query(lambda c: c.data == "subscribe")
async def cb_subscribe(callback: CallbackQuery):
    """Handle subscribe button — trigger /subscribe command."""
    from app.bot.commands import cmd_subscribe
    await callback.answer()
    await cmd_subscribe(callback.message)


# ────────────────────────────────────────────────────────────────
#  SUBSCRIPTION TIER CALLBACKS
# ────────────────────────────────────────────────────────────────

TIER_CONFIG = {
    "monthly":   {"days": 30,  "stars": settings.premium_price_stars_monthly, "label": "Premium (30 days)"},
    "quarterly": {"days": 90,  "stars": settings.premium_price_stars_quarterly, "label": "Premium (90 days)"},
    "yearly":    {"days": 365, "stars": settings.premium_price_stars_yearly, "label": "Premium (365 days)"},
}


@callback_router.callback_query(lambda c: c.data and c.data.startswith("sub_tier:"))
async def cb_sub_tier(callback: CallbackQuery):
    """Handle subscription tier selection — send Stars invoice."""
    tier = callback.data.split(":")[1]
    cfg = TIER_CONFIG.get(tier)
    if not cfg:
        await callback.answer("Invalid tier")
        return
    await callback.answer()
    await callback.message.answer_invoice(
        title="BTC Seer Premium",
        description=f"{cfg['label']} — AI predictions, signals, advisor & alerts.",
        payload=f"premium_{cfg['days']}d",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=cfg["label"], amount=cfg["stars"])],
    )


# ────────────────────────────────────────────────────────────────
#  PAYMENT HANDLERS
# ────────────────────────────────────────────────────────────────

payment_router = Router()


@payment_router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery):
    """Validate and approve Telegram Stars pre-checkout."""
    payload = query.invoice_payload
    valid_payloads = {"premium_30d", "premium_90d", "premium_365d"}
    if payload not in valid_payloads or query.currency != "XTR":
        await query.answer(ok=False, error_message="Invalid payment request.")
        return
    await query.answer(ok=True)


@payment_router.message(F.successful_payment)
async def on_payment_success(message: Message):
    """Handle successful Telegram Stars payment."""
    payment = message.successful_payment
    telegram_id = message.from_user.id

    # Parse days from payload: "premium_30d", "premium_90d", "premium_365d"
    payload = payment.invoice_payload
    VALID_PAYLOADS = {"premium_30d": 30, "premium_90d": 90, "premium_365d": 365}
    days = VALID_PAYLOADS.get(payload, 30)

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = BotUser(
                telegram_id=telegram_id,
                username=message.from_user.username,
                subscribed=False,
            )
            session.add(user)
            await session.flush()

        await activate_premium(user, payment.telegram_payment_charge_id, session, days=days)

        # Record payment history
        tier_map = {30: "monthly", 90: "quarterly", 365: "yearly"}
        tier_label = tier_map.get(days, "monthly")
        session.add(PaymentHistory(
            telegram_id=telegram_id,
            tier=tier_label,
            days=days,
            stars_amount=payment.total_amount,
            payment_id=payment.telegram_payment_charge_id,
        ))
        await session.commit()

        # Record partner conversion if user was referred by a partner
        if user.partner_code:
            try:
                from app.bot.partner_referral import record_partner_conversion
                await record_partner_conversion(telegram_id, tier_label, payment.total_amount)
            except Exception as e:
                logger.error(f"Partner conversion recording failed: {e}")

        status = get_status_text(user)

    await message.answer(
        f"<b>Payment successful!</b>\n\n"
        f"You now have <b>BTC Seer Premium</b> access for {days} days.\n"
        f"Status: {status}\n\n"
        f"All predictions, signals, advisor & alerts are unlocked.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# ────────────────────────────────────────────────────────────────
#  FAQ CALLBACKS
# ────────────────────────────────────────────────────────────────

@callback_router.callback_query(lambda c: c.data and c.data.startswith("faq:"))
async def cb_faq_answer(callback: CallbackQuery):
    """Show FAQ answer for selected topic."""
    from app.bot.commands import FAQ_ANSWERS
    from app.bot.keyboards import faq_keyboard
    topic = callback.data.split(":")[1]
    answer = FAQ_ANSWERS.get(topic, "Topic not found. Please try again.")
    await callback.answer()
    await callback.message.edit_text(
        answer,
        parse_mode="HTML",
        reply_markup=faq_keyboard(),
    )


# ────────────────────────────────────────────────────────────────
#  FEEDBACK CALLBACKS
# ────────────────────────────────────────────────────────────────

@callback_router.callback_query(lambda c: c.data and c.data.startswith("feedback:"))
async def cb_feedback(callback: CallbackQuery):
    """Handle thumbs up/down feedback."""
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.answer("Invalid feedback")
        return

    direction = parts[1]  # up or down
    feedback_type = parts[2]  # trade, prediction, signal
    reference_id = int(parts[3])
    is_positive = direction == "up"

    from app.database import UserFeedback
    async with async_session() as session:
        fb = UserFeedback(
            telegram_id=callback.from_user.id,
            feedback_type=feedback_type,
            reference_id=reference_id,
            is_positive=is_positive,
        )
        session.add(fb)
        await session.commit()

    emoji = "\ud83d\udc4d" if is_positive else "\ud83d\udc4e"
    await callback.answer(f"{emoji} Thanks for your feedback!")
    await callback.message.edit_reply_markup(reply_markup=None)


# ────────────────────────────────────────────────────────────────
#  GAME PREDICTION CALLBACKS
# ────────────────────────────────────────────────────────────────

@callback_router.callback_query(lambda c: c.data and c.data.startswith("game_predict:"))
async def cb_game_predict(callback: CallbackQuery):
    direction = callback.data.split(":")[1]
    telegram_id = callback.from_user.id
    try:
        async with async_session() as session:
            from datetime import datetime, date
            today = date.today().isoformat()
            # Check existing prediction
            existing = await session.execute(
                select(UserPrediction).where(
                    UserPrediction.telegram_id == telegram_id,
                    UserPrediction.round_date == today,
                    UserPrediction.timeframe == "24h",
                    UserPrediction.status == "pending",
                )
            )
            if existing.scalar_one_or_none():
                await callback.answer("Already predicted for today!", show_alert=True)
                return
            # Get current price for lock_price
            price_row = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            current_price = price_row.scalar_one_or_none()
            lock_price = current_price.close if current_price else 0.0
            pred = UserPrediction(
                telegram_id=telegram_id,
                direction=direction,
                round_date=today,
                timeframe="24h",
                status="pending",
                lock_price=lock_price,
                created_at=datetime.utcnow(),
            )
            session.add(pred)
            await session.commit()
        emoji = "\U0001f7e2" if direction == "up" else "\U0001f534"
        await callback.answer(f"{emoji} Predicted {direction.upper()}!", show_alert=True)
        await callback.message.edit_text(
            f"\U0001f3ae Prediction Game\n\n{emoji} You predicted BTC will go {direction.upper()} in the next 24h!\n\nResults will be evaluated tomorrow.",
            reply_markup=None,
        )
    except Exception as e:
        logger.error(f"Game predict error: {e}")
        await callback.answer("Something went wrong. Try again.", show_alert=True)


@callback_router.callback_query(lambda c: c.data == "game_leaderboard")
async def cb_game_leaderboard(callback: CallbackQuery):
    try:
        async with async_session() as session:
            result = await session.execute(
                select(GameProfile).order_by(desc(GameProfile.total_points)).limit(10)
            )
            profiles = result.scalars().all()
        if not profiles:
            await callback.answer("No leaderboard data yet!", show_alert=True)
            return
        lines = ["\U0001f3c6 Top 10 Players\n"]
        for i, p in enumerate(profiles, 1):
            medal = ["\U0001f947", "\U0001f948", "\U0001f949"][i - 1] if i <= 3 else f"{i}."
            lines.append(f"{medal} {p.username or 'Anonymous'} \u2014 {p.total_points} pts ({p.accuracy_pct:.0f}%)")
        await callback.message.edit_text("\n".join(lines), reply_markup=None)
    except Exception as e:
        logger.error(f"Game leaderboard error: {e}")
        await callback.answer("Failed to load leaderboard.", show_alert=True)


# ────────────────────────────────────────────────────────────────
#  DELETE ALERT CALLBACK
# ────────────────────────────────────────────────────────────────

@callback_router.callback_query(lambda c: c.data and c.data.startswith("delete_alert:"))
async def cb_delete_alert(callback: CallbackQuery):
    try:
        alert_id = int(callback.data.split(":")[1])
        async with async_session() as session:
            result = await session.execute(
                select(PriceAlert).where(
                    PriceAlert.id == alert_id,
                    PriceAlert.telegram_id == callback.from_user.id,
                )
            )
            alert = result.scalar_one_or_none()
            if not alert:
                await callback.answer("Alert not found.", show_alert=True)
                return
            alert.is_active = False
            await session.commit()
        await callback.answer("Alert deleted!", show_alert=True)
        await callback.message.edit_text("\u2705 Alert deleted.", reply_markup=None)
    except Exception as e:
        logger.error(f"Delete alert error: {e}")
        await callback.answer("Failed to delete alert.", show_alert=True)


# ────────────────────────────────────────────────────────────────
#  TIMEFRAME CALLBACK
# ────────────────────────────────────────────────────────────────

@callback_router.callback_query(lambda c: c.data and c.data.startswith("tf:"))
async def cb_timeframe(callback: CallbackQuery):
    tf = callback.data.split(":")[1]
    if tf not in ("1h", "4h", "24h"):
        await callback.answer("Invalid timeframe.", show_alert=True)
        return
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Prediction)
                .where(Prediction.timeframe == tf)
                .order_by(desc(Prediction.timestamp))
                .limit(1)
            )
            pred = result.scalar_one_or_none()
        if not pred:
            await callback.answer(f"No {tf} prediction available yet.", show_alert=True)
            return
        direction_emoji = "\U0001f7e2" if pred.direction == "bullish" else "\U0001f534" if pred.direction == "bearish" else "\U0001f7e1"
        text = (
            f"\U0001f4ca {tf.upper()} Prediction\n\n"
            f"{direction_emoji} {pred.direction.upper()}\n"
            f"Confidence: {pred.confidence:.0f}%\n"
        )
        if pred.predicted_price:
            text += f"Target: ${pred.predicted_price:,.0f}\n"
        await callback.message.edit_text(text, reply_markup=None)
    except Exception as e:
        logger.error(f"Timeframe callback error: {e}")
        await callback.answer("Failed to load prediction.", show_alert=True)


def create_bot() -> tuple[Bot, Dispatcher]:
    """Create and configure the Telegram bot."""
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    # Register throttle middleware on command and callback routers
    commands_router.message.middleware(ThrottleMiddleware())
    callback_router.callback_query.middleware(ThrottleMiddleware())

    dp.include_router(payment_router)  # Payment handlers first (pre_checkout must be fast)
    dp.include_router(commands_router)
    dp.include_router(callback_router)

    return bot, dp
