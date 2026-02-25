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

    # Admin is always premium
    if settings.admin_telegram_id and user.telegram_id == settings.admin_telegram_id:
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

    # Admin
    if settings.admin_telegram_id and user.telegram_id == settings.admin_telegram_id:
        return "Admin (unlimited)"

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


async def activate_premium(user: BotUser, payment_id: str, session, days: int = 30):
    """Activate or extend premium subscription by N days."""
    now = datetime.utcnow()

    # If already has active subscription, extend from current end
    if user.subscription_end and user.subscription_end > now:
        user.subscription_end = user.subscription_end + timedelta(days=days)
    else:
        user.subscription_end = now + timedelta(days=days)

    user.subscription_tier = "premium"
    user.stars_payment_id = payment_id
    await session.commit()
    logger.info(f"Premium activated for user {user.telegram_id} for {days}d until {user.subscription_end}")


async def check_premium(event) -> bool:
    """Check if the user behind event has premium access.

    Returns True if premium/admin, False otherwise.
    Handles ban check and sends upgrade prompt if not premium.
    Works for both Message and CallbackQuery events.
    """
    if isinstance(event, CallbackQuery):
        telegram_id = event.from_user.id
    elif isinstance(event, Message):
        telegram_id = event.from_user.id
    else:
        return True

    # Master switch off = everyone is premium
    if not settings.subscription_enabled:
        return True

    # Look up user
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

    # Check ban
    if user and user.is_banned:
        ban_text = "Your account has been suspended."
        if user.ban_reason:
            ban_text += f"\nReason: {user.ban_reason}"
        if isinstance(event, CallbackQuery):
            await event.answer(ban_text, show_alert=True)
        else:
            await event.answer(ban_text)
        return False

    if user and is_premium(user):
        return True

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

    return False


def require_premium(handler):
    """Decorator that gates a handler behind premium subscription.

    Works for both Message handlers and CallbackQuery handlers.
    Passes through **kwargs (e.g. _from_user_id) to the handler.
    """
    @functools.wraps(handler)
    async def wrapper(event, *args, **kwargs):
        if await check_premium(event):
            return await handler(event, **kwargs)
        return None

    return wrapper
