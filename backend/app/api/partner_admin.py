"""Admin API for managing partners — CRUD + stats."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session, Partner, PartnerReferral, BotUser
from app.api.admin import _verify_telegram_init_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/partners", tags=["partner-admin"])


def _require_admin(request: Request) -> int:
    """Verify admin access from Telegram initData."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")
    user_data = _verify_telegram_init_data(init_data, max_age=604800)
    telegram_id = user_data.get("id")
    if not telegram_id or telegram_id != settings.admin_telegram_id:
        raise HTTPException(403, "Admin access required")
    return telegram_id


class PartnerCreate(BaseModel):
    name: str
    code: str
    telegram_id: int | None = None
    commission_pct: float = 20.0
    contact_email: str | None = None
    contact_telegram: str | None = None
    notes: str | None = None


class PartnerUpdate(BaseModel):
    name: str | None = None
    telegram_id: int | None = None
    commission_pct: float | None = None
    contact_email: str | None = None
    contact_telegram: str | None = None
    is_active: bool | None = None
    notes: str | None = None


@router.get("")
async def list_partners(request: Request):
    """List all partners with summary stats."""
    admin_id = _require_admin(request)

    async with async_session() as session:
        result = await session.execute(
            select(Partner).order_by(desc(Partner.created_at))
        )
        partners = result.scalars().all()

        partner_list = []
        for p in partners:
            # Get referral stats
            ref_result = await session.execute(
                select(
                    func.count(PartnerReferral.id).label("total_referrals"),
                    func.count(PartnerReferral.id).filter(PartnerReferral.subscribed == True).label("conversions"),
                    func.sum(PartnerReferral.stars_paid).label("total_stars"),
                    func.sum(PartnerReferral.commission_amount).label("total_commission"),
                ).where(PartnerReferral.partner_id == p.id)
            )
            stats = ref_result.one()

            total_referrals = stats.total_referrals or 0
            conversions = stats.conversions or 0
            total_stars = stats.total_stars or 0
            total_commission = stats.total_commission or 0

            partner_list.append({
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "telegram_id": p.telegram_id,
                "commission_pct": p.commission_pct,
                "contact_email": p.contact_email,
                "contact_telegram": p.contact_telegram,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "notes": p.notes,
                "total_referrals": total_referrals,
                "conversions": conversions,
                "conversion_rate": round(conversions / total_referrals * 100, 1) if total_referrals > 0 else 0,
                "total_stars": total_stars,
                "total_commission": round(total_commission, 1),
            })

    return {"partners": partner_list, "total": len(partner_list)}


@router.post("")
async def create_partner(request: Request, body: PartnerCreate):
    """Create a new partner."""
    admin_id = _require_admin(request)

    async with async_session() as session:
        # Check code uniqueness
        existing = await session.execute(
            select(Partner).where(Partner.code == body.code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(400, f"Partner code '{body.code}' already exists")

        partner = Partner(
            name=body.name,
            code=body.code,
            telegram_id=body.telegram_id,
            commission_pct=body.commission_pct,
            contact_email=body.contact_email,
            contact_telegram=body.contact_telegram,
            notes=body.notes,
            created_by=admin_id,
        )
        session.add(partner)
        await session.commit()

        return {
            "id": partner.id,
            "name": partner.name,
            "code": partner.code,
            "commission_pct": partner.commission_pct,
            "referral_link": f"https://t.me/{settings.bot_username}?start=partner_{partner.code}",
        }


@router.put("/{partner_id}")
async def update_partner(request: Request, partner_id: int, body: PartnerUpdate):
    """Update a partner's details."""
    _require_admin(request)

    async with async_session() as session:
        result = await session.execute(
            select(Partner).where(Partner.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        if not partner:
            raise HTTPException(404, "Partner not found")

        if body.name is not None:
            partner.name = body.name
        if body.telegram_id is not None:
            partner.telegram_id = body.telegram_id
        if body.commission_pct is not None:
            partner.commission_pct = body.commission_pct
        if body.contact_email is not None:
            partner.contact_email = body.contact_email
        if body.contact_telegram is not None:
            partner.contact_telegram = body.contact_telegram
        if body.is_active is not None:
            partner.is_active = body.is_active
        if body.notes is not None:
            partner.notes = body.notes

        await session.commit()
        return {"status": "ok", "id": partner.id}


@router.delete("/{partner_id}")
async def deactivate_partner(request: Request, partner_id: int):
    """Deactivate a partner (soft delete)."""
    _require_admin(request)

    async with async_session() as session:
        result = await session.execute(
            select(Partner).where(Partner.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        if not partner:
            raise HTTPException(404, "Partner not found")

        partner.is_active = False
        await session.commit()
        return {"status": "ok", "deactivated": partner.name}


@router.get("/{partner_id}/stats")
async def partner_stats(request: Request, partner_id: int):
    """Detailed stats for a specific partner."""
    _require_admin(request)

    async with async_session() as session:
        result = await session.execute(
            select(Partner).where(Partner.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        if not partner:
            raise HTTPException(404, "Partner not found")

        ref_result = await session.execute(
            select(PartnerReferral).where(PartnerReferral.partner_id == partner_id)
            .order_by(desc(PartnerReferral.signed_up_at))
        )
        referrals = ref_result.scalars().all()

        total = len(referrals)
        converted = sum(1 for r in referrals if r.subscribed)
        total_stars = sum(r.stars_paid or 0 for r in referrals)
        total_commission = sum(r.commission_amount or 0 for r in referrals)
        unpaid_commission = sum(r.commission_amount or 0 for r in referrals if not r.commission_paid)

        return {
            "partner": {
                "id": partner.id,
                "name": partner.name,
                "code": partner.code,
                "commission_pct": partner.commission_pct,
                "is_active": partner.is_active,
            },
            "stats": {
                "total_referrals": total,
                "conversions": converted,
                "conversion_rate": round(converted / total * 100, 1) if total > 0 else 0,
                "total_stars": total_stars,
                "total_commission": round(total_commission, 1),
                "unpaid_commission": round(unpaid_commission, 1),
            },
            "referral_link": f"https://t.me/{settings.bot_username}?start=partner_{partner.code}",
        }


@router.get("/{partner_id}/referrals")
async def partner_referrals(request: Request, partner_id: int):
    """List all users referred by a partner."""
    _require_admin(request)

    async with async_session() as session:
        result = await session.execute(
            select(PartnerReferral).where(PartnerReferral.partner_id == partner_id)
            .order_by(desc(PartnerReferral.signed_up_at))
        )
        referrals = result.scalars().all()

        referral_list = []
        for r in referrals:
            # Get user info
            user_result = await session.execute(
                select(BotUser).where(BotUser.telegram_id == r.telegram_id)
            )
            user = user_result.scalar_one_or_none()

            referral_list.append({
                "id": r.id,
                "telegram_id": r.telegram_id,
                "username": user.username if user else None,
                "signed_up_at": r.signed_up_at.isoformat() if r.signed_up_at else None,
                "subscribed": r.subscribed,
                "subscription_tier": r.subscription_tier,
                "stars_paid": r.stars_paid,
                "commission_amount": r.commission_amount,
                "commission_paid": r.commission_paid,
            })

    return {"referrals": referral_list, "total": len(referral_list)}
