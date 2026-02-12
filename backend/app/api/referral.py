"""Referral API — user referral info + public leaderboard."""

import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select, func, desc

from app.config import settings
from app.database import async_session, BotUser, Referral
from app.api.admin import _verify_telegram_init_data
from app.bot.referral import get_or_create_referral_code

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/referral", tags=["referral"])


@router.get("/info")
async def get_referral_info(request: Request):
    """Get current user's referral code, stats, and history."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    user_data = _verify_telegram_init_data(init_data)
    telegram_id = user_data.get("id")

    if not telegram_id:
        raise HTTPException(400, "Invalid user data")

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not registered")

        # Lazy-generate referral code
        code = await get_or_create_referral_code(user, session)

        # Get referral history
        result = await session.execute(
            select(Referral)
            .where(Referral.referrer_telegram_id == telegram_id)
            .order_by(desc(Referral.created_at))
            .limit(50)
        )
        referrals = result.scalars().all()

        # Get total bonus days earned as referrer
        result = await session.execute(
            select(func.coalesce(func.sum(Referral.referrer_bonus_days), 0))
            .where(Referral.referrer_telegram_id == telegram_id)
        )
        total_bonus = result.scalar() or 0

        # Get referred_by username if exists
        referred_by_username = None
        if user.referred_by:
            result = await session.execute(
                select(BotUser.username).where(BotUser.telegram_id == user.referred_by)
            )
            referred_by_username = result.scalar_one_or_none()

    share_link = f"https://t.me/{settings.bot_username}?start=ref_{code}"

    # Build referral history list
    history = []
    for ref in referrals:
        history.append({
            "referee_telegram_id": ref.referee_telegram_id,
            "bonus_days": ref.referrer_bonus_days,
            "created_at": ref.created_at.isoformat() if ref.created_at else None,
        })

    return {
        "referral_code": code,
        "share_link": share_link,
        "referral_count": user.referral_count or 0,
        "total_bonus_days": total_bonus,
        "referred_by": referred_by_username,
        "history": history,
    }


@router.get("/leaderboard")
async def get_referral_leaderboard():
    """Public leaderboard — top 20 referrers."""
    async with async_session() as session:
        result = await session.execute(
            select(
                BotUser.username,
                BotUser.referral_count,
            )
            .where(BotUser.referral_count > 0)
            .order_by(desc(BotUser.referral_count))
            .limit(20)
        )
        rows = result.all()

    leaderboard = []
    for i, row in enumerate(rows, 1):
        leaderboard.append({
            "rank": i,
            "username": row.username or "Anonymous",
            "referral_count": row.referral_count,
        })

    return {"leaderboard": leaderboard}
