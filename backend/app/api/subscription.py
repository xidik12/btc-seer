"""Subscription API — invoice creation + subscription status for the WebApp."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from aiogram import Bot
from aiogram.types import LabeledPrice
from sqlalchemy import select

from app.config import settings
from app.database import async_session, BotUser, PaymentHistory
from app.telegram_auth import _verify_telegram_init_data
from app.bot.subscription import is_premium, get_status_text
from app.dependencies import strict_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/subscription", tags=["subscription"], dependencies=[Depends(strict_rate_limit)])

TIER_CONFIG = {
    "monthly":   {"days": 30,  "stars": settings.premium_price_stars_monthly,   "label": "Premium (30 days)"},
    "quarterly": {"days": 90,  "stars": settings.premium_price_stars_quarterly,  "label": "Premium (90 days)"},
    "yearly":    {"days": 365, "stars": settings.premium_price_stars_yearly,     "label": "Premium (365 days)"},
}


@router.get("/create-invoice")
async def create_invoice(request: Request, tier: str = Query(..., pattern="^(monthly|quarterly|yearly)$")):
    """Create a Telegram Stars invoice link for the WebApp to open via tg.openInvoice()."""
    # Require Telegram authentication
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")
    _verify_telegram_init_data(init_data, max_age=86400)

    if not settings.telegram_bot_token:
        raise HTTPException(500, "Bot token not configured")

    cfg = TIER_CONFIG.get(tier)
    if not cfg:
        raise HTTPException(400, "Invalid tier")

    try:
        bot = Bot(token=settings.telegram_bot_token)
        try:
            link = await bot.create_invoice_link(
                title="BTC Seer Premium",
                description=f"{cfg['label']} — AI predictions, signals, advisor & alerts.",
                payload=f"premium_{cfg['days']}d",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label=cfg["label"], amount=cfg["stars"])],
            )
        finally:
            await bot.session.close()

        return {"invoice_link": link}

    except Exception as e:
        logger.error(f"Invoice link creation failed: {e}")
        raise HTTPException(500, "Failed to create invoice link")


@router.get("/status")
async def subscription_status(request: Request):
    """Return the user's subscription tier, expiry, and payment history."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(400, "Invalid user data")

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        # Determine tier
        now = datetime.utcnow()
        premium = is_premium(user)
        if premium:
            tier = "premium"
        elif user.trial_end and user.trial_end > now:
            tier = "trial"
        else:
            tier = "free"

        # Days remaining & progress
        days_remaining = 0
        total_days = 0
        progress_pct = 0
        if tier == "premium" and user.subscription_end:
            days_remaining = max(0, (user.subscription_end - now).days)
            # Estimate total from closest tier
            if days_remaining > 180:
                total_days = 365
            elif days_remaining > 60:
                total_days = 90
            else:
                total_days = 30
            progress_pct = round((days_remaining / total_days) * 100) if total_days else 0
        elif tier == "trial" and user.trial_end:
            days_remaining = max(0, (user.trial_end - now).days)
            total_days = 3  # trial is typically 3 days
            progress_pct = round((days_remaining / total_days) * 100) if total_days else 0

        # Payment history
        pay_result = await session.execute(
            select(PaymentHistory)
            .where(PaymentHistory.telegram_id == telegram_id)
            .order_by(PaymentHistory.created_at.desc())
        )
        payments = [
            {
                "id": p.id,
                "tier": p.tier,
                "days": p.days,
                "stars_amount": p.stars_amount,
                "payment_id": p.payment_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in pay_result.scalars().all()
        ]

    return {
        "tier": tier,
        "is_premium": premium,
        "status_text": get_status_text(user),
        "subscription_end": user.subscription_end.isoformat() if user.subscription_end else None,
        "trial_end": user.trial_end.isoformat() if user.trial_end else None,
        "days_remaining": days_remaining,
        "total_days": total_days,
        "progress_pct": min(progress_pct, 100),
        "joined_at": user.joined_at.isoformat() if user.joined_at else None,
        "payments": payments,
    }
