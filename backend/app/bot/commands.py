import logging
from datetime import datetime

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.filters.command import CommandObject
from aiogram.types import Message
from sqlalchemy import select, desc

from app.config import settings
from app.database import (
    async_session, BotUser, Prediction, Signal, News,
    PortfolioState, TradeAdvice, TradeResult, Price, ApiKey, ApiUsageLog,
)
from app.bot.keyboards import main_keyboard, settings_keyboard, back_keyboard, advisor_keyboard, trade_close_keyboard, subscribe_keyboard
from app.bot.subscription import require_premium, is_premium, get_status_text, grant_trial
from app.bot.referral import parse_referral_code, process_referral
from app.signals.generator import DISCLAIMER

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """Handle /start command — subscribe, process referrals, show main menu."""
    is_new = False
    referral_info = None
    referral_code = parse_referral_code(command.args)

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = BotUser(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                subscribed=False,
            )
            session.add(user)
            await session.flush()
            is_new = True

            # Grant free trial for new users
            if settings.subscription_enabled:
                await grant_trial(user, session)
            else:
                await session.commit()

            # Process referral for new users only
            if referral_code:
                referral_info = await process_referral(user, referral_code, session)
        else:
            # Grant trial to existing users who missed it during beta
            if settings.subscription_enabled:
                await grant_trial(user, session)
            await session.commit()

    # Check if user is banned
    if user.is_banned:
        ban_msg = "Your account has been suspended."
        if user.ban_reason:
            ban_msg += f"\nReason: {user.ban_reason}"
        await message.answer(ban_msg)
        return

    # Build status line
    status_line = ""
    if settings.subscription_enabled:
        status = get_status_text(user)
        if is_new and user.trial_end:
            status_line = f"\n\nYou have {settings.trial_days} days of free Premium access!"
        else:
            status_line = f"\n\nStatus: <b>{status}</b>"

    # Referral bonus message
    referral_line = ""
    if referral_info:
        ref_user = referral_info.get("referrer_username") or "a friend"
        bonus = referral_info["bonus_days"]
        referral_line = f"\n\n🎁 Referred by @{ref_user} — you both got +{bonus} days Premium!"

    name = message.from_user.first_name or "there"

    await message.answer(
        f"Hey {name}, welcome to <b>BTC Seer</b>!\n\n"
        "I'm your AI-powered Bitcoin analyst. I crunch 60+ data points "
        "every hour — news, on-chain flows, market structure, whale moves "
        "— and turn them into clear, actionable predictions.\n\n"
        "<b>Here's how to get started:</b>\n"
        "/predict — see the latest price predictions\n"
        "/signal — get a trading signal with entry, target & stop-loss\n"
        "/advisor — open the AI trading advisor\n"
        "/news — browse real-time crypto news with sentiment\n"
        "/accuracy — check my prediction track record\n"
        "/settings — choose your alert frequency\n\n"
        "Or just tap the buttons below to explore."
        f"{status_line}"
        f"{referral_line}\n\n"
        f"<i>{DISCLAIMER}</i>",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@router.message(Command("predict"))
@require_premium
async def cmd_predict(message: Message):
    """Handle /predict command — show current prediction."""
    async with async_session() as session:
        result = await session.execute(
            select(Prediction)
            .order_by(desc(Prediction.timestamp))
            .limit(3)
        )
        predictions = result.scalars().all()

    if not predictions:
        await message.answer("⏳ No predictions available yet. Data is being collected...")
        return

    lines = ["🔮 <b>Current Predictions</b>\n"]

    direction_emoji = {"bullish": "🟢 ▲", "bearish": "🔴 ▼", "neutral": "🟡 ◄►"}

    for p in predictions:
        emoji = direction_emoji.get(p.direction, "⚪")
        lines.append(
            f"<b>{p.timeframe.upper()}</b>: {emoji} {p.direction.title()} "
            f"({p.confidence:.0f}% conf)\n"
            f"   Price: ${p.current_price:,.0f}"
        )
        if p.predicted_change_pct:
            lines.append(f"   Expected: {p.predicted_change_pct:+.2f}%")
        lines.append("")

    lines.append(f"<i>{DISCLAIMER}</i>")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_keyboard())


@router.message(Command("signal"))
@require_premium
async def cmd_signal(message: Message):
    """Handle /signal command — show current trading signal."""
    async with async_session() as session:
        result = await session.execute(
            select(Signal)
            .order_by(desc(Signal.timestamp))
            .limit(1)
        )
        signal = result.scalar_one_or_none()

    if not signal:
        await message.answer("⏳ No signals available yet.")
        return

    action_emoji = {
        "strong_buy": "🟢🟢",
        "buy": "🟢",
        "hold": "🟡",
        "sell": "🔴",
        "strong_sell": "🔴🔴",
    }

    emoji = action_emoji.get(signal.action, "⚪")
    risk_bar = "█" * signal.risk_rating + "░" * (10 - signal.risk_rating)

    text = (
        f"📈 <b>Trading Signal ({signal.timeframe.upper()})</b>\n\n"
        f"{emoji} <b>{signal.action.replace('_', ' ').upper()}</b>\n\n"
        f"💰 Entry: <code>${signal.entry_price:,.0f}</code>\n"
        f"🎯 Target: <code>${signal.target_price:,.0f}</code>\n"
        f"🛑 Stop-Loss: <code>${signal.stop_loss:,.0f}</code>\n\n"
        f"📊 Confidence: {signal.confidence:.0f}%\n"
        f"⚠️ Risk: {risk_bar} ({signal.risk_rating}/10)\n\n"
        f"💡 {signal.reasoning}\n\n"
        f"<i>{DISCLAIMER}</i>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())


@router.message(Command("news"))
@require_premium
async def cmd_news(message: Message):
    """Handle /news command — show latest news summary."""
    async with async_session() as session:
        result = await session.execute(
            select(News)
            .order_by(desc(News.timestamp))
            .limit(5)
        )
        news = result.scalars().all()

    if not news:
        await message.answer("📰 No news collected yet.")
        return

    lines = ["📰 <b>Latest Crypto News</b>\n"]

    for n in news:
        sentiment = ""
        if n.sentiment_score is not None:
            if n.sentiment_score > 0.1:
                sentiment = "🟢"
            elif n.sentiment_score < -0.1:
                sentiment = "🔴"
            else:
                sentiment = "🟡"

        title = n.title[:80] + "..." if len(n.title) > 80 else n.title
        lines.append(f"{sentiment} {title}")
        lines.append(f"   <i>{n.source}</i>")
        lines.append("")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=back_keyboard())


@router.message(Command("accuracy"))
@require_premium
async def cmd_accuracy(message: Message):
    """Handle /accuracy command — show prediction track record."""
    async with async_session() as session:
        result = await session.execute(
            select(Prediction).where(Prediction.was_correct.isnot(None))
        )
        predictions = result.scalars().all()

    if not predictions:
        await message.answer("🎯 No evaluated predictions yet. Check back in 24+ hours.")
        return

    total = len(predictions)
    correct = sum(1 for p in predictions if p.was_correct)
    accuracy = correct / total * 100

    # By timeframe
    tf_stats = {}
    for tf in ["1h", "4h", "24h"]:
        tf_preds = [p for p in predictions if p.timeframe == tf]
        tf_correct = sum(1 for p in tf_preds if p.was_correct)
        tf_total = len(tf_preds)
        if tf_total > 0:
            tf_stats[tf] = f"{tf_correct}/{tf_total} ({tf_correct / tf_total * 100:.0f}%)"

    text = (
        f"🎯 <b>Prediction Accuracy</b>\n\n"
        f"Overall: <b>{correct}/{total} ({accuracy:.1f}%)</b>\n\n"
    )

    for tf, stat in tf_stats.items():
        text += f"  {tf.upper()}: {stat}\n"

    text += f"\n<i>Based on {total} evaluated predictions</i>"

    await message.answer(text, parse_mode="HTML", reply_markup=back_keyboard())


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command — alert preferences."""
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    interval = user.alert_interval if user else "1h"

    await message.answer(
        "⚙️ <b>Alert Settings</b>\n\n"
        "Choose how often you want to receive prediction alerts:",
        parse_mode="HTML",
        reply_markup=settings_keyboard(interval),
    )


# ────────────────────────────────────────────────────────────────
#  ADVISOR COMMANDS
# ────────────────────────────────────────────────────────────────

@router.message(Command("advisor"))
@require_premium
async def cmd_advisor(message: Message):
    """Show advisor status, balance, open trades, and $10K progress."""
    from app.advisor.portfolio import get_or_create_portfolio, get_stats

    telegram_id = message.from_user.id
    portfolio = await get_or_create_portfolio(telegram_id)
    stats = await get_stats(telegram_id)

    # Open trades count
    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.telegram_id == telegram_id,
                TradeAdvice.status.in_(["opened", "partial_tp"]),
            )
        )
        open_trades = result.scalars().all()

    # Progress bar
    progress = stats.get("progress_to_10k", 0)
    bar_filled = int(progress / 5)  # 20 chars total
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    cooldown = ""
    if stats.get("cooldown_until"):
        cooldown = f"\nCooldown active until {stats['cooldown_until']}"

    text = (
        f"<b>Trading Advisor</b>\n\n"
        f"<b>Balance:</b> ${stats['balance']:.2f}\n"
        f"<b>Total PnL:</b> ${stats['total_pnl']:+.2f} ({stats['total_pnl_pct']:+.1f}%)\n\n"
        f"<b>Trades:</b> {stats['total_trades']} total | "
        f"{stats['winning_trades']}W / {stats['losing_trades']}L\n"
        f"<b>Win Rate:</b> {stats['win_rate']:.1f}%\n"
        f"<b>Profit Factor:</b> {stats['profit_factor']:.2f}\n\n"
        f"<b>Open Trades:</b> {len(open_trades)}\n"
        f"<b>Streak:</b> {stats['consecutive_wins']}W / {stats['consecutive_losses']}L\n\n"
        f"<b>$10K Progress:</b> {progress:.1f}%\n"
        f"[{bar}]\n"
        f"${stats['balance']:.2f} / $10,000.00"
        f"{cooldown}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=advisor_keyboard())


@router.message(Command("balance"))
@require_premium
async def cmd_balance(message: Message):
    """Show balance and PnL summary."""
    from app.advisor.portfolio import get_or_create_portfolio, get_stats

    telegram_id = message.from_user.id
    stats = await get_stats(telegram_id)

    if stats.get("error"):
        await get_or_create_portfolio(telegram_id)
        stats = await get_stats(telegram_id)

    text = (
        f"<b>Portfolio Balance</b>\n\n"
        f"Balance: <code>${stats['balance']:.4f}</code>\n"
        f"Initial: <code>${stats['initial_balance']:.2f}</code>\n\n"
        f"Total PnL: <code>${stats['total_pnl']:+.4f}</code>\n"
        f"Total PnL %: <code>{stats['total_pnl_pct']:+.2f}%</code>\n\n"
        f"Best Trade: <code>${stats.get('best_trade', 0):+.4f}</code>\n"
        f"Worst Trade: <code>${stats.get('worst_trade', 0):+.4f}</code>\n"
        f"Avg Win: <code>${stats.get('avg_win', 0):+.4f}</code>\n"
        f"Avg Loss: <code>${stats.get('avg_loss', 0):+.4f}</code>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=back_keyboard())


@router.message(Command("setbalance"))
@require_premium
async def cmd_setbalance(message: Message):
    """Set balance manually: /setbalance <amount>"""
    from app.advisor.portfolio import update_balance

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /setbalance <amount>\nExample: /setbalance 25.50")
        return

    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("Invalid amount. Use a number like: /setbalance 25.50")
        return

    if amount < 0:
        await message.answer("Amount must be positive.")
        return

    portfolio = await update_balance(message.from_user.id, amount)

    await message.answer(
        f"Balance updated to <code>${portfolio.balance_usdt:.4f}</code>",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@router.message(Command("trades"))
@require_premium
async def cmd_trades(message: Message):
    """Show open trade advices with current status."""
    telegram_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.telegram_id == telegram_id,
                TradeAdvice.status.in_(["pending", "opened", "partial_tp"]),
            ).order_by(desc(TradeAdvice.timestamp))
        )
        trades = result.scalars().all()

        # Get current price
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price_row = result.scalar_one_or_none()

    if not trades:
        await message.answer("No open trades.", reply_markup=advisor_keyboard())
        return

    current_price = price_row.close if price_row else 0

    lines = ["<b>Open Trades</b>\n"]
    for t in trades:
        if t.direction == "LONG":
            pnl_pct = ((current_price - t.entry_price) / t.entry_price * 100) * t.leverage
        else:
            pnl_pct = ((t.entry_price - current_price) / t.entry_price * 100) * t.leverage

        emoji = "🟢" if pnl_pct >= 0 else "🔴"
        lines.append(
            f"#{t.id} {t.direction} {t.leverage}x | {t.status}\n"
            f"   Entry: ${t.entry_price:,.0f} | Now: ${current_price:,.0f}\n"
            f"   {emoji} PnL: {pnl_pct:+.2f}%\n"
            f"   SL: ${t.stop_loss:,.0f} | TP1: ${t.take_profit_1:,.0f}\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=advisor_keyboard())


@router.message(Command("history"))
@require_premium
async def cmd_history(message: Message):
    """Show trade result history with W/L stats."""
    telegram_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(TradeResult)
            .where(TradeResult.telegram_id == telegram_id)
            .order_by(desc(TradeResult.timestamp))
            .limit(10)
        )
        results = result.scalars().all()

    if not results:
        await message.answer("No trade history yet.", reply_markup=advisor_keyboard())
        return

    lines = ["<b>Trade History (last 10)</b>\n"]
    for r in results:
        emoji = "✅" if r.was_winner else "❌"
        lines.append(
            f"{emoji} #{r.trade_advice_id} {r.direction} {r.leverage}x\n"
            f"   ${r.entry_price:,.0f} -> ${r.exit_price:,.0f}\n"
            f"   PnL: ${r.pnl_usdt:+.4f} ({r.pnl_pct_leveraged:+.2f}%)\n"
            f"   {r.close_reason} | {r.duration_minutes}min\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=advisor_keyboard())


# ────────────────────────────────────────────────────────────────
#  API KEY COMMANDS
# ────────────────────────────────────────────────────────────────

@router.message(Command("apikey"))
async def cmd_apikey(message: Message):
    """Generate a free-tier API key for the user."""
    import secrets
    from app.middleware.auth import hash_api_key
    from sqlalchemy import func

    telegram_id = message.from_user.id

    async with async_session() as session:
        # Check if user already has an active key
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.telegram_id == telegram_id,
                ApiKey.is_active == True,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            await message.answer(
                f"<b>Your API Key</b>\n\n"
                f"Prefix: <code>{existing.key_prefix}...</code>\n"
                f"Tier: <b>{existing.tier}</b>\n"
                f"Rate limit: {existing.rate_limit} req/hr\n\n"
                "<i>You already have an active key. Use /revokekey to revoke and generate a new one.</i>",
                parse_mode="HTML",
            )
            return

        # Generate new key
        raw_key = f"bto_{secrets.token_urlsafe(32)}"
        key_hash = hash_api_key(raw_key)
        key_prefix = raw_key[:12]

        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            owner=message.from_user.username or str(telegram_id),
            telegram_id=telegram_id,
            tier="free",
            rate_limit=60,
            is_active=True,
        )
        session.add(api_key)
        await session.commit()

    await message.answer(
        f"<b>Your API Key (FREE tier)</b>\n\n"
        f"<code>{raw_key}</code>\n\n"
        f"Rate limit: 60 requests/hour\n"
        f"Endpoints: Price, Power Law\n\n"
        f"Use with:\n"
        f"<code>curl -H 'X-API-Key: {raw_key}' https://your-domain/api/v1/price</code>\n\n"
        f"<b>Save this key now!</b> It won't be shown again.",
        parse_mode="HTML",
    )


@router.message(Command("revokekey"))
async def cmd_revokekey(message: Message):
    """Revoke the user's active API key."""
    telegram_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.telegram_id == telegram_id,
                ApiKey.is_active == True,
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            await message.answer("You don't have an active API key. Use /apikey to generate one.")
            return

        key.is_active = False
        await session.commit()

    await message.answer(
        "API key revoked. Use /apikey to generate a new one.",
        parse_mode="HTML",
    )


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    """Show subscription tier options."""
    if not settings.subscription_enabled:
        await message.answer(
            "All features are currently <b>free</b> during beta!",
            parse_mode="HTML",
        )
        return

    # Check current status
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    status = get_status_text(user) if user else "Free"

    from app.bot.keyboards import subscription_tiers_keyboard

    await message.answer(
        "<b>BTC Seer Premium</b>\n\n"
        "Unlock AI predictions, trading signals, advisor & alerts.\n\n"
        f"Current status: <b>{status}</b>\n\n"
        "Choose your plan:",
        parse_mode="HTML",
        reply_markup=subscription_tiers_keyboard(),
    )


@router.message(Command("usage"))
async def cmd_usage(message: Message):
    """Show API usage stats for the user's key."""
    from sqlalchemy import func
    from datetime import timedelta

    telegram_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.telegram_id == telegram_id,
                ApiKey.is_active == True,
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            await message.answer("No active API key. Use /apikey to generate one.")
            return

        # Count usage
        from datetime import datetime
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        day_ago = datetime.utcnow() - timedelta(hours=24)

        result_1h = await session.execute(
            select(func.count(ApiUsageLog.id))
            .where(ApiUsageLog.api_key_id == key.id)
            .where(ApiUsageLog.timestamp >= hour_ago)
        )
        result_24h = await session.execute(
            select(func.count(ApiUsageLog.id))
            .where(ApiUsageLog.api_key_id == key.id)
            .where(ApiUsageLog.timestamp >= day_ago)
        )
        result_total = await session.execute(
            select(func.count(ApiUsageLog.id))
            .where(ApiUsageLog.api_key_id == key.id)
        )

    requests_1h = result_1h.scalar() or 0
    requests_24h = result_24h.scalar() or 0
    requests_total = result_total.scalar() or 0

    await message.answer(
        f"<b>API Usage Stats</b>\n\n"
        f"Tier: <b>{key.tier}</b>\n"
        f"Rate limit: {key.rate_limit} req/hr\n\n"
        f"Last hour: {requests_1h}/{key.rate_limit}\n"
        f"Last 24h: {requests_24h}\n"
        f"All time: {requests_total}\n\n"
        f"Key prefix: <code>{key.key_prefix}...</code>",
        parse_mode="HTML",
    )


@router.message(Command("close"))
@require_premium
async def cmd_close(message: Message):
    """Record trade close: /close <trade_id> <exit_price>"""
    from app.advisor.portfolio import record_trade_result

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /close <trade_id> <exit_price>\nExample: /close 5 98500")
        return

    try:
        trade_id = int(parts[1])
        exit_price = float(parts[2])
    except ValueError:
        await message.answer("Invalid arguments. Example: /close 5 98500")
        return

    result = await record_trade_result(
        telegram_id=message.from_user.id,
        trade_id=trade_id,
        exit_price=exit_price,
        reason="manual_close",
    )

    if not result:
        await message.answer("Trade not found or already closed.")
        return

    emoji = "✅" if result.was_winner else "❌"
    text = (
        f"{emoji} <b>Trade #{trade_id} Closed</b>\n\n"
        f"PnL: <code>${result.pnl_usdt:+.4f}</code> ({result.pnl_pct_leveraged:+.2f}%)\n"
        f"Balance: ${result.balance_before:.4f} -> ${result.balance_after:.4f}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=advisor_keyboard())
