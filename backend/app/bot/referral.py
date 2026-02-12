"""Referral system — code generation, deep-link parsing, bonus granting."""

import logging
import string
import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import BotUser, Referral

logger = logging.getLogger(__name__)


def generate_referral_code(length: int = 8) -> str:
    """Generate a random uppercase alphanumeric referral code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


async def get_or_create_referral_code(user: BotUser, session: AsyncSession) -> str:
    """Return the user's referral code, generating one if needed."""
    if user.referral_code:
        return user.referral_code

    # Generate unique code with retry
    for _ in range(5):
        code = generate_referral_code()
        existing = await session.execute(
            select(BotUser).where(BotUser.referral_code == code)
        )
        if not existing.scalar_one_or_none():
            user.referral_code = code
            await session.commit()
            return code

    # Fallback: use telegram_id suffix for uniqueness
    code = generate_referral_code(5) + str(user.telegram_id)[-3:]
    user.referral_code = code
    await session.commit()
    return code


def parse_referral_code(start_param: str | None) -> str | None:
    """Extract referral code from /start deep link parameter.

    Expected format: ref_ABCD1234
    """
    if not start_param:
        return None
    start_param = start_param.strip()
    if start_param.startswith("ref_"):
        return start_param[4:]
    return None


async def process_referral(
    new_user: BotUser,
    referral_code: str | None,
    session: AsyncSession,
) -> dict | None:
    """Process a referral for a newly registered user.

    Returns dict with referral info on success, None on failure/skip.
    """
    if not referral_code or not settings.referral_enabled:
        return None

    # Find the referrer by code
    result = await session.execute(
        select(BotUser).where(BotUser.referral_code == referral_code)
    )
    referrer = result.scalar_one_or_none()
    if not referrer:
        logger.debug(f"Referral code '{referral_code}' not found")
        return None

    # Prevent self-referral
    if referrer.telegram_id == new_user.telegram_id:
        logger.debug(f"Self-referral blocked for {new_user.telegram_id}")
        return None

    # Prevent double-referral (user already referred)
    existing = await session.execute(
        select(Referral).where(Referral.referee_telegram_id == new_user.telegram_id)
    )
    if existing.scalar_one_or_none():
        logger.debug(f"User {new_user.telegram_id} already referred")
        return None

    bonus_days = settings.referral_bonus_days

    # Grant bonus to both parties
    _extend_premium(new_user, bonus_days)
    _extend_premium(referrer, bonus_days)

    # Update referrer stats
    referrer.referral_count = (referrer.referral_count or 0) + 1

    # Record who referred the new user
    new_user.referred_by = referrer.telegram_id

    # Create referral record
    ref = Referral(
        referrer_telegram_id=referrer.telegram_id,
        referee_telegram_id=new_user.telegram_id,
        referrer_bonus_days=bonus_days,
        referee_bonus_days=bonus_days,
    )
    session.add(ref)
    await session.commit()

    logger.info(
        f"Referral success: {referrer.telegram_id} -> {new_user.telegram_id}, "
        f"+{bonus_days}d each"
    )

    return {
        "referrer_username": referrer.username,
        "referrer_telegram_id": referrer.telegram_id,
        "bonus_days": bonus_days,
    }


def _extend_premium(user: BotUser, days: int) -> None:
    """Extend a user's premium access by N days.

    Logic:
    - If active subscription_end -> extend from subscription_end
    - Elif active trial_end -> extend from trial_end
    - Else -> grant new trial_end from now
    """
    now = datetime.utcnow()
    delta = timedelta(days=days)

    if user.subscription_end and user.subscription_end > now:
        user.subscription_end = user.subscription_end + delta
    elif user.trial_end and user.trial_end > now:
        user.trial_end = user.trial_end + delta
    else:
        user.trial_end = now + delta
