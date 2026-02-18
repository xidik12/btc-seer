"""Partner dashboard API — partners access their own stats via their code."""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc

from app.config import settings
from app.database import async_session, Partner, PartnerReferral

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/partner", tags=["partner-dashboard"])


@router.get("/{code}/stats")
async def partner_self_stats(code: str):
    """Get a partner's own referral stats."""
    async with async_session() as session:
        result = await session.execute(
            select(Partner).where(Partner.code == code, Partner.is_active == True)
        )
        partner = result.scalar_one_or_none()
        if not partner:
            raise HTTPException(404, "Partner not found")

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
async def partner_self_referrals(code: str):
    """Get a partner's referred users (anonymized)."""
    async with async_session() as session:
        result = await session.execute(
            select(Partner).where(Partner.code == code, Partner.is_active == True)
        )
        partner = result.scalar_one_or_none()
        if not partner:
            raise HTTPException(404, "Partner not found")

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
