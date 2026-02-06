import logging

from aiogram import Bot
from sqlalchemy import select

from app.database import async_session, BotUser, Prediction, Signal
from app.signals.generator import DISCLAIMER
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class AlertSender:
    """Sends prediction alerts to subscribed Telegram users."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_hourly_alerts(self):
        """Send prediction alerts to all subscribed users."""
        async with async_session() as session:
            # Get latest predictions
            result = await session.execute(
                select(Prediction).order_by(desc(Prediction.timestamp)).limit(3)
            )
            predictions = result.scalars().all()

            # Get latest signal
            result = await session.execute(
                select(Signal).order_by(desc(Signal.timestamp)).limit(1)
            )
            signal = result.scalar_one_or_none()

            if not predictions:
                logger.warning("No predictions available for alerts")
                return

            # Get subscribed users
            result = await session.execute(
                select(BotUser)
                .where(BotUser.subscribed == True)
                .where(BotUser.alert_interval == "1h")
            )
            users = result.scalars().all()

        message = self._format_alert(predictions, signal)

        sent = 0
        failed = 0
        for user in users:
            try:
                await self.bot.send_message(
                    user.telegram_id,
                    message,
                    parse_mode="HTML",
                )
                sent += 1
            except Exception as e:
                logger.error(f"Failed to send alert to {user.telegram_id}: {e}")
                failed += 1

        logger.info(f"Hourly alerts sent: {sent} success, {failed} failed")

    async def send_breaking_alert(self, title: str, sentiment: float, analysis: str):
        """Send breaking news alert to all subscribed users."""
        emoji = "🟢" if sentiment > 0.3 else "🔴" if sentiment < -0.3 else "🟡"

        message = (
            f"🚨 <b>Breaking News Alert</b>\n\n"
            f"{emoji} {title}\n\n"
            f"Sentiment: {sentiment:+.2f}\n"
            f"Analysis: {analysis}\n\n"
            f"<i>{DISCLAIMER}</i>"
        )

        async with async_session() as session:
            result = await session.execute(
                select(BotUser).where(BotUser.subscribed == True)
            )
            users = result.scalars().all()

        for user in users:
            try:
                await self.bot.send_message(user.telegram_id, message, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send breaking alert to {user.telegram_id}: {e}")

    def _format_alert(self, predictions: list, signal) -> str:
        """Format hourly prediction alert message."""
        direction_emoji = {"bullish": "🟢 ▲", "bearish": "🔴 ▼", "neutral": "🟡 ◄►"}

        lines = ["🔮 <b>BTC Oracle — Hourly Update</b>\n"]

        # Price
        if predictions:
            price = predictions[0].current_price
            lines.append(f"💰 BTC: <code>${price:,.0f}</code>\n")

        # Predictions
        for p in predictions:
            emoji = direction_emoji.get(p.direction, "⚪")
            lines.append(
                f"<b>{p.timeframe.upper()}</b>: {emoji} {p.direction.title()} ({p.confidence:.0f}%)"
            )

        # Signal
        if signal:
            action_emoji = {
                "strong_buy": "🟢🟢", "buy": "🟢", "hold": "🟡",
                "sell": "🔴", "strong_sell": "🔴🔴",
            }
            emoji = action_emoji.get(signal.action, "⚪")
            lines.append(f"\n📈 Signal: {emoji} <b>{signal.action.replace('_', ' ').upper()}</b>")
            lines.append(f"   Entry: ${signal.entry_price:,.0f} | Target: ${signal.target_price:,.0f}")
            lines.append(f"   Stop: ${signal.stop_loss:,.0f} | Risk: {signal.risk_rating}/10")

        lines.append(f"\n<i>{DISCLAIMER}</i>")

        return "\n".join(lines)
