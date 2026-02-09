import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, LabeledPrice
from sqlalchemy import select

from app.config import settings
from app.database import async_session, BotUser, TradeAdvice, Price
from app.bot.commands import router as commands_router
from app.bot.keyboards import main_keyboard, settings_keyboard, advisor_keyboard, trade_close_keyboard
from app.bot.subscription import require_premium, activate_premium, get_status_text

logger = logging.getLogger(__name__)

# Callback query router
callback_router = Router()


@callback_router.callback_query(lambda c: c.data == "predict")
@require_premium
async def cb_predict(callback: CallbackQuery):
    from app.bot.commands import cmd_predict
    await callback.answer()
    await cmd_predict(callback.message)


@callback_router.callback_query(lambda c: c.data == "signal")
@require_premium
async def cb_signal(callback: CallbackQuery):
    from app.bot.commands import cmd_signal
    await callback.answer()
    await cmd_signal(callback.message)


@callback_router.callback_query(lambda c: c.data == "news")
@require_premium
async def cb_news(callback: CallbackQuery):
    from app.bot.commands import cmd_news
    await callback.answer()
    await cmd_news(callback.message)


@callback_router.callback_query(lambda c: c.data == "accuracy")
@require_premium
async def cb_accuracy(callback: CallbackQuery):
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
@require_premium
async def cb_advisor_portfolio(callback: CallbackQuery):
    from app.bot.commands import cmd_advisor
    await callback.answer()
    await cmd_advisor(callback.message)


@callback_router.callback_query(lambda c: c.data == "advisor_trades")
@require_premium
async def cb_advisor_trades(callback: CallbackQuery):
    from app.bot.commands import cmd_trades
    await callback.answer()
    await cmd_trades(callback.message)


@callback_router.callback_query(lambda c: c.data == "advisor_history")
@require_premium
async def cb_advisor_history(callback: CallbackQuery):
    from app.bot.commands import cmd_history
    await callback.answer()
    await cmd_history(callback.message)


@callback_router.callback_query(lambda c: c.data == "advisor_risk")
@require_premium
async def cb_advisor_risk(callback: CallbackQuery):
    """Show risk settings for the advisor."""
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
    """Approve Telegram Stars pre-checkout."""
    await query.answer(ok=True)


@payment_router.message(F.successful_payment)
async def on_payment_success(message: Message):
    """Handle successful Telegram Stars payment."""
    payment = message.successful_payment
    telegram_id = message.from_user.id

    # Parse days from payload: "premium_30d", "premium_90d", "premium_365d"
    payload = payment.invoice_payload
    days = 30
    if payload and "premium_" in payload:
        try:
            days = int(payload.replace("premium_", "").replace("d", ""))
        except ValueError:
            days = 30

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = BotUser(
                telegram_id=telegram_id,
                username=message.from_user.username,
                subscribed=True,
            )
            session.add(user)
            await session.flush()

        await activate_premium(user, payment.telegram_payment_charge_id, session, days=days)
        status = get_status_text(user)

    await message.answer(
        f"<b>Payment successful!</b>\n\n"
        f"You now have <b>BTC Seer Premium</b> access for {days} days.\n"
        f"Status: {status}\n\n"
        f"All predictions, signals, advisor & alerts are unlocked.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


def create_bot() -> tuple[Bot, Dispatcher]:
    """Create and configure the Telegram bot."""
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    dp.include_router(payment_router)  # Payment handlers first (pre_checkout must be fast)
    dp.include_router(commands_router)
    dp.include_router(callback_router)

    return bot, dp
