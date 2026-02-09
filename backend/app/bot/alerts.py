import logging
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select

from app.database import async_session, BotUser, Price, Prediction, Signal, AlertLog
from app.bot.subscription import is_premium
from app.signals.generator import DISCLAIMER
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class AlertSender:
    """Sends prediction alerts to subscribed Telegram users."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def _log_alert(self, telegram_id: int, alert_type: str, status: str, error: str = None):
        """Log an alert send attempt to the database."""
        try:
            async with async_session() as session:
                log = AlertLog(
                    timestamp=datetime.utcnow(),
                    telegram_id=telegram_id,
                    alert_type=alert_type,
                    status=status,
                    error=error,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.debug(f"Failed to log alert: {e}")

    async def send_hourly_alerts(self):
        """Send prediction alerts to all subscribed users."""
        async with async_session() as session:
            # Get FRESH current price (not from stale prediction)
            price_result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            current_price_row = price_result.scalar_one_or_none()

            # Get latest prediction for EACH timeframe (not just any 3)
            predictions_by_tf = {}
            for tf in ["1h", "4h", "24h"]:
                result = await session.execute(
                    select(Prediction)
                    .where(Prediction.timeframe == tf)
                    .order_by(desc(Prediction.timestamp))
                    .limit(1)
                )
                pred = result.scalar_one_or_none()
                if pred:
                    predictions_by_tf[tf] = pred

            # Get latest signal
            result = await session.execute(
                select(Signal).order_by(desc(Signal.timestamp)).limit(1)
            )
            signal = result.scalar_one_or_none()

            if not predictions_by_tf:
                logger.warning("No predictions available for alerts")
                return

            # Get subscribed users
            result = await session.execute(
                select(BotUser)
                .where(BotUser.subscribed == True)
                .where(BotUser.alert_interval == "1h")
            )
            users = result.scalars().all()

        # Use fresh price for the alert
        current_price = current_price_row.close if current_price_row else None
        predictions = list(predictions_by_tf.values())
        message = self._format_alert(predictions, signal, current_price)

        # Only send to users with active subscription or trial
        users = [u for u in users if is_premium(u)]

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
                await self._log_alert(user.telegram_id, "hourly", "sent")
            except Exception as e:
                logger.error(f"Failed to send alert to {user.telegram_id}: {e}")
                failed += 1
                await self._log_alert(user.telegram_id, "hourly", "failed", str(e))

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

        # Only send to users with active subscription or trial
        users = [u for u in users if is_premium(u)]

        for user in users:
            try:
                await self.bot.send_message(user.telegram_id, message, parse_mode="HTML")
                await self._log_alert(user.telegram_id, "breaking", "sent")
            except Exception as e:
                logger.error(f"Failed to send breaking alert to {user.telegram_id}: {e}")
                await self._log_alert(user.telegram_id, "breaking", "failed", str(e))

    def _format_alert(self, predictions: list, signal, current_price: float = None) -> str:
        """Format hourly prediction alert message."""
        direction_emoji = {"bullish": "🟢 ▲", "bearish": "🔴 ▼", "neutral": "🟡 ◄►"}

        lines = ["🔮 <b>BTC Seer — Hourly Update</b>\n"]

        # Price — use fresh price passed in, fallback to prediction price
        price = current_price or (predictions[0].current_price if predictions else None)
        if price:
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
