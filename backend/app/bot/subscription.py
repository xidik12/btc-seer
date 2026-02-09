import functools
import logging
from datetime import datetime, timedelta

from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from app.config import settings
from app.database import async_session, BotUser

logger = logging.getLogger(__name__)


def is_premium(user: BotUser) -> bool:
    """Check if a user has active premium access."""
    # Master switch off = everyone is premium
    if not settings.subscription_enabled:
        return True

    now = datetime.utcnow()

    # Active paid subscription
    if (
        user.subscription_tier == "premium"
        and user.subscription_end
        and user.subscription_end > now
    ):
        return True

    # Active trial
    if user.trial_end and user.trial_end > now:
        return True

    return False


def get_status_text(user: BotUser) -> str:
    """Return human-readable subscription status."""
    if not settings.subscription_enabled:
        return "All features unlocked (beta)"

    now = datetime.utcnow()

    # Active paid subscription
    if (
        user.subscription_tier == "premium"
        and user.subscription_end
        and user.subscription_end > now
    ):
        days_left = (user.subscription_end - now).days
        return f"Premium (expires in {days_left}d)"

    # Active trial
    if user.trial_end and user.trial_end > now:
        days_left = (user.trial_end - now).days
        hours_left = int((user.trial_end - now).total_seconds() // 3600)
        if days_left > 0:
            return f"Trial ({days_left}d left)"
        return f"Trial ({hours_left}h left)"

    return "Free"


async def grant_trial(user: BotUser, session):
    """Grant a 7-day free trial if user never had one."""
    if user.trial_end is not None:
        return  # Already had a trial
    user.trial_end = datetime.utcnow() + timedelta(days=settings.trial_days)
    await session.commit()
    logger.info(f"Trial granted to user {user.telegram_id}")


async def activate_premium(user: BotUser, payment_id: str, session):
    """Activate or extend premium subscription by 30 days."""
    now = datetime.utcnow()

    # If already has active subscription, extend from current end
    if user.subscription_end and user.subscription_end > now:
        user.subscription_end = user.subscription_end + timedelta(days=30)
    else:
        user.subscription_end = now + timedelta(days=30)

    user.subscription_tier = "premium"
    user.stars_payment_id = payment_id
    await session.commit()
    logger.info(f"Premium activated for user {user.telegram_id} until {user.subscription_end}")


def require_premium(handler):
    """Decorator that gates a handler behind premium subscription.

    Works for both Message handlers and CallbackQuery handlers.
    """
    @functools.wraps(handler)
    async def wrapper(event, *args, **kwargs):
        # Extract telegram_id based on event type
        if isinstance(event, CallbackQuery):
            telegram_id = event.from_user.id
        elif isinstance(event, Message):
            telegram_id = event.from_user.id
        else:
            return await handler(event, *args, **kwargs)

        # Master switch off = skip gate
        if not settings.subscription_enabled:
            return await handler(event, *args, **kwargs)

        # Look up user
        async with async_session() as session:
            result = await session.execute(
                select(BotUser).where(BotUser.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

        if user and is_premium(user):
            return await handler(event, *args, **kwargs)

        # User is not premium — send upgrade prompt
        from app.bot.keyboards import subscribe_keyboard
        text = (
            "This feature requires <b>BTC Seer Premium</b>.\n\n"
            "Get AI predictions, trading signals, advisor & alerts "
            f"for just {settings.premium_price_stars} Stars (~$9.99/mo).\n\n"
            "Use /subscribe to unlock."
        )

        if isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.answer(text, parse_mode="HTML", reply_markup=subscribe_keyboard())
        else:
            await event.answer(text, parse_mode="HTML", reply_markup=subscribe_keyboard())

    return wrapper
