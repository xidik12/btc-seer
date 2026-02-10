"""User auth/registration API — registers Mini App users via Telegram initData."""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.database import async_session, BotUser
from app.api.admin import _verify_telegram_init_data
from app.bot.subscription import grant_trial, is_premium, get_status_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_response(user: BotUser, is_new: bool = False) -> dict:
    return {
        "status": "new" if is_new else "existing",
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "subscription_status": get_status_text(user),
            "is_premium": is_premium(user),
            "is_banned": user.is_banned,
            "trial_end": user.trial_end.isoformat() if user.trial_end else None,
            "subscription_end": user.subscription_end.isoformat() if user.subscription_end else None,
        },
    }


@router.post("/register")
async def register_user(request: Request):
    """Register a new user or return existing user via Telegram initData.

    Called automatically when the Mini App loads.
    """
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    user_data = _verify_telegram_init_data(init_data)
    telegram_id = user_data.get("id")
    username = user_data.get("username")

    if not telegram_id:
        raise HTTPException(400, "Invalid user data")

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        is_new = False
        if not user:
            user = BotUser(
                telegram_id=telegram_id,
                username=username,
                subscribed=False,
            )
            session.add(user)
            await session.flush()
            is_new = True
            logger.info(f"New user registered via Mini App: {telegram_id} (@{username})")

            if settings.subscription_enabled:
                await grant_trial(user, session)
            else:
                await session.commit()
        else:
            # Update username if changed
            if username and user.username != username:
                user.username = username
            await session.commit()

    return _user_response(user, is_new)


@router.get("/me")
async def get_current_user(request: Request):
    """Get current user profile and subscription status."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    user_data = _verify_telegram_init_data(init_data)
    telegram_id = user_data.get("id")

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not registered")

    return _user_response(user)


class AlertPreferencesRequest(BaseModel):
    subscribed: bool
    alert_interval: str  # 1h, 4h, 24h


@router.get("/alerts/preferences")
async def get_alert_preferences(request: Request):
    """Get current user's alert preferences."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    user_data = _verify_telegram_init_data(init_data)
    telegram_id = user_data.get("id")

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not registered")

    return {
        "subscribed": user.subscribed,
        "alert_interval": user.alert_interval,
    }


@router.post("/alerts/preferences")
async def update_alert_preferences(request: Request, body: AlertPreferencesRequest):
    """Update current user's alert preferences."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    if body.alert_interval not in ("1h", "4h", "24h"):
        raise HTTPException(400, "Invalid interval. Must be 1h, 4h, or 24h")

    user_data = _verify_telegram_init_data(init_data)
    telegram_id = user_data.get("id")

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not registered")

        user.subscribed = body.subscribed
        user.alert_interval = body.alert_interval
        await session.commit()

    logger.info(f"User {telegram_id} updated alerts: subscribed={body.subscribed}, interval={body.alert_interval}")

    return {
        "subscribed": user.subscribed,
        "alert_interval": user.alert_interval,
    }
