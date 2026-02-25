"""Partner dashboard API — partners access their own stats via Telegram auth."""

import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select, desc

from app.config import settings
from app.database import async_session, Partner, PartnerReferral
from app.api.admin import _verify_telegram_init_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/partner", tags=["partner-dashboard"])


def _get_partner_telegram_id(request: Request) -> int:
    """Extract and verify the partner's telegram_id from initData."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Authentication required. Open BTC Seer from Telegram.")
    user_data = _verify_telegram_init_data(init_data, max_age=0)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(401, "Invalid Telegram authentication")
    return telegram_id


@router.get("/{code}/stats")
async def partner_self_stats(code: str, request: Request):
    """Get a partner's own referral stats. Requires Telegram auth matching partner's telegram_id."""
    caller_id = _get_partner_telegram_id(request)

    async with async_session() as session:
        result = await session.execute(
            select(Partner).where(Partner.code == code, Partner.is_active == True)
        )
        partner = result.scalar_one_or_none()
        if not partner:
            raise HTTPException(404, "Partner not found")

        # Allow access if caller is the partner OR the admin
        if partner.telegram_id != caller_id and caller_id != settings.admin_telegram_id:
            raise HTTPException(403, "Access denied. This dashboard belongs to another partner.")

        ref_result = await session.execute(
            select(PartnerReferral).where(PartnerReferral.partner_id == partner.id)
        )
        referrals = ref_result.scalars().all()

        total = len(referrals)
        converted = sum(1 for r in referrals if r.subscribed)
        total_stars = sum(r.stars_paid or 0 for r in referrals)
        total_commission = sum(r.commission_amount or 0 for r in referrals)
        pending_commission = sum(
            r.commission_amount or 0 for r in referrals if r.commission_amount and not r.commission_paid
        )

        return {
            "partner_name": partner.name,
            "code": partner.code,
            "commission_pct": partner.commission_pct,
            "stats": {
                "total_referrals": total,
                "conversions": converted,
                "conversion_rate": round(converted / total * 100, 1) if total > 0 else 0,
                "total_stars_earned": total_stars,
                "total_commission": round(total_commission, 1),
                "pending_commission": round(pending_commission, 1),
            },
            "referral_link": f"https://t.me/{settings.bot_username}?start=partner_{partner.code}",
        }


@router.get("/{code}/referrals")
async def partner_self_referrals(code: str, request: Request):
    """Get a partner's referred users (anonymized). Requires Telegram auth."""
    caller_id = _get_partner_telegram_id(request)

    async with async_session() as session:
        result = await session.execute(
            select(Partner).where(Partner.code == code, Partner.is_active == True)
        )
        partner = result.scalar_one_or_none()
        if not partner:
            raise HTTPException(404, "Partner not found")

        if partner.telegram_id != caller_id and caller_id != settings.admin_telegram_id:
            raise HTTPException(403, "Access denied. This dashboard belongs to another partner.")

        ref_result = await session.execute(
            select(PartnerReferral).where(PartnerReferral.partner_id == partner.id)
            .order_by(desc(PartnerReferral.signed_up_at))
        )
        referrals = ref_result.scalars().all()

        referral_list = []
        for i, r in enumerate(referrals, 1):
            referral_list.append({
                "user_label": f"User #{i}",
                "signed_up_at": r.signed_up_at.isoformat() if r.signed_up_at else None,
                "subscribed": r.subscribed,
                "subscription_tier": r.subscription_tier,
                "commission_earned": r.commission_amount,
            })

    return {"referrals": referral_list, "total": len(referral_list)}
