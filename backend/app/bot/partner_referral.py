"""Partner referral system — separate from user referrals.

Partners are created by admins and get commission on referred user subscriptions.
Flow: Partner shares link → user signs up → partner gets credit → user subscribes → commission calculated.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BotUser, Partner, PartnerReferral

logger = logging.getLogger(__name__)


def parse_partner_code(start_param: str | None) -> str | None:
    """Extract partner code from /start deep link parameter.

    Expected format: partner_CRYPTOEDU
    """
    if not start_param:
        return None
    start_param = start_param.strip()
    if start_param.startswith("partner_"):
        return start_param[8:]
    return None


async def process_partner_referral(
    user: BotUser,
    partner_code: str,
    session: AsyncSession,
) -> dict | None:
    """Link a new user to a partner via their referral code.

    Returns dict with partner info on success, None on failure/skip.
    """
    # Find the partner by code
    result = await session.execute(
        select(Partner).where(Partner.code == partner_code, Partner.is_active == True)
    )
    partner = result.scalar_one_or_none()
    if not partner:
        logger.debug(f"Partner code '{partner_code}' not found or inactive")
        return None

    # Check if user is already referred by a partner
    existing = await session.execute(
        select(PartnerReferral).where(PartnerReferral.telegram_id == user.telegram_id)
    )
    if existing.scalar_one_or_none():
        logger.debug(f"User {user.telegram_id} already has partner referral")
        return None

    # Store partner code on user
    user.partner_code = partner_code

    # Create partner referral record
    referral = PartnerReferral(
        partner_id=partner.id,
        telegram_id=user.telegram_id,
        signed_up_at=datetime.utcnow(),
    )
    session.add(referral)
    await session.commit()

    logger.info(f"Partner referral: {partner.name} ({partner_code}) -> user {user.telegram_id}")

    return {
        "partner_name": partner.name,
        "partner_code": partner_code,
    }


async def record_partner_conversion(
    telegram_id: int,
    tier: str,
    stars_paid: int,
) -> dict | None:
    """Record a subscription conversion for a partner-referred user.

    Called when a user with a partner_code buys a premium subscription.
    Calculates commission based on the partner's commission_pct.
    """
    from app.database import async_session

    async with async_session() as session:
        # Find the partner referral
        result = await session.execute(
            select(PartnerReferral).where(PartnerReferral.telegram_id == telegram_id)
        )
        referral = result.scalar_one_or_none()
        if not referral:
            return None

        # Get the partner to calculate commission
        partner_result = await session.execute(
            select(Partner).where(Partner.id == referral.partner_id)
        )
        partner = partner_result.scalar_one_or_none()
        if not partner:
            return None

        # Update referral with conversion info
        referral.subscribed = True
        referral.subscription_tier = tier
        referral.subscription_date = datetime.utcnow()
        referral.stars_paid = stars_paid
        referral.commission_amount = stars_paid * (partner.commission_pct / 100)

        await session.commit()

        logger.info(
            f"Partner conversion: {partner.name} -> user {telegram_id}, "
            f"{stars_paid} stars, commission {referral.commission_amount:.1f} stars"
        )

        return {
            "partner_name": partner.name,
            "commission_amount": referral.commission_amount,
            "stars_paid": stars_paid,
        }
