"""Subscription API — creates Telegram Stars invoice links for the WebApp."""

import logging

from fastapi import APIRouter, Query, HTTPException
from aiogram import Bot
from aiogram.types import LabeledPrice

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/subscription", tags=["subscription"])

TIER_CONFIG = {
    "monthly":   {"days": 30,  "stars": settings.premium_price_stars_monthly,   "label": "Premium (30 days)"},
    "quarterly": {"days": 90,  "stars": settings.premium_price_stars_quarterly,  "label": "Premium (90 days)"},
    "yearly":    {"days": 365, "stars": settings.premium_price_stars_yearly,     "label": "Premium (365 days)"},
}


@router.get("/create-invoice")
async def create_invoice(tier: str = Query(..., pattern="^(monthly|quarterly|yearly)$")):
    """Create a Telegram Stars invoice link for the WebApp to open via tg.openInvoice()."""
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
