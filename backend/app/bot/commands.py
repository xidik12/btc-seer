import logging

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy import select, desc

from app.database import async_session, BotUser, Prediction, Signal, News
from app.bot.keyboards import main_keyboard, settings_keyboard, back_keyboard
from app.signals.generator import DISCLAIMER

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command — subscribe and show main menu."""
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = BotUser(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                subscribed=True,
            )
            session.add(user)
            await session.commit()

    await message.answer(
        "🔮 <b>BTC Oracle</b> — Bitcoin Price Prediction System\n\n"
        "I use ML models analyzing 60+ features from news, market data, "
        "on-chain metrics, and sentiment to predict Bitcoin's price direction.\n\n"
        "📊 Hourly predictions with confidence scores\n"
        "📈 Full trading signals (entry, target, stop-loss)\n"
        "📰 Real-time news sentiment analysis\n"
        "🎯 Transparent accuracy tracking\n\n"
        f"<i>{DISCLAIMER}</i>",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@router.message(Command("predict"))
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
