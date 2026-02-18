"""Price Alerts API — create, list, update, delete user price alerts."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func, desc

from app.database import async_session, PriceAlert, BotUser
from app.api.admin import _verify_telegram_init_data
from app.bot.subscription import is_premium

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    coin_id: str = "bitcoin"
    target_price: float
    direction: str  # above, below
    is_repeating: bool = False
    note: str | None = None


class AlertUpdate(BaseModel):
    target_price: float | None = None
    is_repeating: bool | None = None
    is_active: bool | None = None
    note: str | None = None


def _get_user_data(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(400, "Invalid user data")
    return telegram_id


@router.get("/")
async def list_alerts(request: Request):
    """List all alerts for the current user."""
    telegram_id = _get_user_data(request)

    async with async_session() as session:
        result = await session.execute(
            select(PriceAlert)
            .where(PriceAlert.telegram_id == telegram_id)
            .order_by(desc(PriceAlert.created_at))
            .limit(50)
        )
        alerts = result.scalars().all()

    active_count = sum(1 for a in alerts if a.is_active)
    return {
        "alerts": [
            {
                "id": a.id,
                "coin_id": a.coin_id,
                "target_price": a.target_price,
                "direction": a.direction,
                "is_active": a.is_active,
                "is_repeating": a.is_repeating,
                "note": a.note,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
                "triggered_price": a.triggered_price,
            }
            for a in alerts
        ],
        "active_count": active_count,
    }


@router.post("/")
async def create_alert(body: AlertCreate, request: Request):
    """Create a new price alert."""
    telegram_id = _get_user_data(request)

    if body.direction not in ("above", "below"):
        raise HTTPException(400, "direction must be 'above' or 'below'")

    async with async_session() as session:
        # Check user + limits
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        premium = is_premium(user) if user else False
        max_alerts = 10 if premium else 3

        result = await session.execute(
            select(func.count(PriceAlert.id))
            .where(PriceAlert.telegram_id == telegram_id)
            .where(PriceAlert.is_active == True)
        )
        active_count = result.scalar() or 0

        if active_count >= max_alerts:
            raise HTTPException(
                429,
                f"Alert limit reached ({max_alerts}). "
                + ("Delete an alert first." if premium else "Upgrade to Premium for 10 alerts."),
            )

        alert = PriceAlert(
            telegram_id=telegram_id,
            coin_id=body.coin_id,
            target_price=body.target_price,
            direction=body.direction,
            is_repeating=body.is_repeating,
            note=body.note,
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)

    return {
        "id": alert.id,
        "coin_id": alert.coin_id,
        "target_price": alert.target_price,
        "direction": alert.direction,
        "is_active": alert.is_active,
        "is_repeating": alert.is_repeating,
        "note": alert.note,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, request: Request):
    """Delete a price alert."""
    telegram_id = _get_user_data(request)

    async with async_session() as session:
        result = await session.execute(
            select(PriceAlert).where(
                PriceAlert.id == alert_id,
                PriceAlert.telegram_id == telegram_id,
            )
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(404, "Alert not found")

        await session.delete(alert)
        await session.commit()

    return {"deleted": True}


@router.patch("/{alert_id}")
async def update_alert(alert_id: int, body: AlertUpdate, request: Request):
    """Update a price alert."""
    telegram_id = _get_user_data(request)

    async with async_session() as session:
        result = await session.execute(
            select(PriceAlert).where(
                PriceAlert.id == alert_id,
                PriceAlert.telegram_id == telegram_id,
            )
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(404, "Alert not found")

        if body.target_price is not None:
            alert.target_price = body.target_price
        if body.is_repeating is not None:
            alert.is_repeating = body.is_repeating
        if body.is_active is not None:
            alert.is_active = body.is_active
            if body.is_active:
                alert.triggered_at = None
                alert.triggered_price = None
        if body.note is not None:
            alert.note = body.note

        await session.commit()

    return {"updated": True}
