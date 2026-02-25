"""User auth/registration API — registers Mini App users via Telegram initData."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.database import async_session, BotUser, Partner
from app.api.admin import _verify_telegram_init_data
from app.bot.subscription import grant_trial, is_premium, get_status_text
from app.jwt_utils import create_access_token
from app.dependencies import strict_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(strict_rate_limit)])


def _user_response(user: BotUser, is_new: bool = False, partner_code: str | None = None) -> dict:
    return {
        "status": "new" if is_new else "existing",
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "subscription_status": get_status_text(user),
            "is_premium": is_premium(user),
            "is_banned": user.is_banned,
            "is_admin": user.telegram_id == getattr(settings, 'admin_telegram_id', None),
            "trial_end": user.trial_end.isoformat() if user.trial_end else None,
            "subscription_end": user.subscription_end.isoformat() if user.subscription_end else None,
            "partner_code": partner_code,
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

    user_data = _verify_telegram_init_data(init_data, max_age=86400)  # 24h for user registration
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
            # Grant trial to existing users who missed it during beta
            if settings.subscription_enabled:
                await grant_trial(user, session)
            await session.commit()

        # Check if this user is a partner (has a Partner record linked to their telegram_id)
        partner_result = await session.execute(
            select(Partner.code).where(Partner.telegram_id == telegram_id, Partner.is_active == True)
        )
        partner_code = partner_result.scalar_one_or_none()

    token = create_access_token(
        telegram_id=user.telegram_id,
        username=user.username,
        subscription_tier=user.subscription_tier or "free",
        is_premium=is_premium(user),
        is_banned=user.is_banned,
    )
    return {**_user_response(user, is_new, partner_code=partner_code), "access_token": token}


@router.get("/me")
async def get_current_user(request: Request):
    """Get current user profile and subscription status."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    user_data = _verify_telegram_init_data(init_data, max_age=3600)
    telegram_id = user_data.get("id")

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not registered")

        partner_result = await session.execute(
            select(Partner.code).where(Partner.telegram_id == telegram_id, Partner.is_active == True)
        )
        partner_code = partner_result.scalar_one_or_none()

    return _user_response(user, partner_code=partner_code)


class AlertPreferencesRequest(BaseModel):
    subscribed: bool
    alert_interval: str  # 1h, 4h, 24h


@router.get("/alerts/preferences")
async def get_alert_preferences(request: Request):
    """Get current user's alert preferences."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    user_data = _verify_telegram_init_data(init_data, max_age=86400)
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

    user_data = _verify_telegram_init_data(init_data, max_age=86400)
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
