"""Admin API endpoints — protected by Telegram initData HMAC-SHA256 verification."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qs, unquote

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, desc, func

from app.config import settings
from app.database import (
    async_session,
    BotUser,
    Prediction,
    TradeAdvice,
    TradeResult,
    Price,
    PortfolioState,
    ModelVersion,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ─── Auth ────────────────────────────────────────────────────────────────────


def _verify_telegram_init_data(init_data: str, **kwargs) -> dict:
    """Verify Telegram WebApp initData using HMAC-SHA256.

    Returns parsed user data if valid, raises HTTPException if not.
    Pass max_age=seconds to control auth_date expiry (default: 300s for admin).
    """
    if not settings.telegram_bot_token:
        raise HTTPException(403, "Bot token not configured")
    if not init_data:
        raise HTTPException(401, "Missing initData")

    # Parse the init data
    parsed = parse_qs(init_data)
    data_check_string_parts = []

    for key in sorted(parsed.keys()):
        if key == "hash":
            continue
        data_check_string_parts.append(f"{key}={parsed[key][0]}")

    data_check_string = "\n".join(data_check_string_parts)

    # Get the hash from the init data
    hash_value = parsed.get("hash", [None])[0]
    if not hash_value:
        raise HTTPException(401, "Missing hash in initData")

    # Create the secret key
    secret_key = hmac.new(
        b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256
    ).digest()

    # Calculate the hash
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, hash_value):
        logger.warning("Admin auth: HMAC signature mismatch")
        raise HTTPException(401, "Invalid initData signature")

    # Check auth_date freshness
    auth_date = parsed.get("auth_date", [None])[0]
    if auth_date:
        auth_time = datetime.utcfromtimestamp(int(auth_date))
        age_seconds = (datetime.utcnow() - auth_time).total_seconds()
        max_age = kwargs.get("max_age", 300)  # default 5 min for admin
        if age_seconds > max_age:
            logger.warning(f"Auth: initData expired (age={age_seconds:.0f}s, max={max_age})")
            raise HTTPException(401, "Session expired — please reopen the app from Telegram")

    # Parse user data
    user_raw = parsed.get("user", [None])[0]
    if not user_raw:
        raise HTTPException(401, "No user in initData")

    try:
        user_data = json.loads(unquote(user_raw))
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(400, "Malformed authentication data")
    logger.info(f"Admin auth: verified user id={user_data.get('id')}")
    return user_data


def _require_admin(request: Request) -> dict:
    """Verify request comes from admin user."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")

    if not init_data:
        logger.warning("Admin auth: no initData header")
        raise HTTPException(401, "Admin access requires Telegram authentication")

    user = _verify_telegram_init_data(init_data)
    telegram_id = user.get("id", 0)

    if not settings.admin_telegram_id:
        logger.warning("Admin auth: ADMIN_TELEGRAM_ID not set in env")
        raise HTTPException(403, "Admin not configured on server")
    if telegram_id != settings.admin_telegram_id:
        logger.warning(f"Admin auth: user {telegram_id} is not admin (expected {settings.admin_telegram_id})")
        raise HTTPException(403, f"Not authorized (your ID: {telegram_id})")

    return user


# ─── Models ──────────────────────────────────────────────────────────────────


class BanRequest(BaseModel):
    reason: str = "Banned by admin"


class GrantPremiumRequest(BaseModel):
    days: int = 30


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/stats")
async def admin_stats(request: Request):
    """Overview stats: total users, active subs, predictions, trades."""
    _require_admin(request)

    async with async_session() as session:
        # User counts
        total_users = (await session.execute(select(func.count(BotUser.id)))).scalar() or 0
        premium_users = (
            await session.execute(
                select(func.count(BotUser.id)).where(
                    BotUser.subscription_tier == "premium",
                    BotUser.subscription_end > datetime.utcnow(),
                )
            )
        ).scalar() or 0
        banned_users = (
            await session.execute(
                select(func.count(BotUser.id)).where(BotUser.is_banned == True)
            )
        ).scalar() or 0

        # Prediction stats
        total_predictions = (
            await session.execute(select(func.count(Prediction.id)))
        ).scalar() or 0
        evaluated_predictions = (
            await session.execute(
                select(func.count(Prediction.id)).where(Prediction.was_correct.isnot(None))
            )
        ).scalar() or 0
        correct_predictions = (
            await session.execute(
                select(func.count(Prediction.id)).where(Prediction.was_correct == True)
            )
        ).scalar() or 0

        # Trade stats
        total_trades = (
            await session.execute(select(func.count(TradeAdvice.id)))
        ).scalar() or 0
        total_results = (
            await session.execute(select(func.count(TradeResult.id)))
        ).scalar() or 0
        winning_results = (
            await session.execute(
                select(func.count(TradeResult.id)).where(TradeResult.was_winner == True)
            )
        ).scalar() or 0

        # Users joined last 24h / 7d
        day_ago = datetime.utcnow() - timedelta(hours=24)
        week_ago = datetime.utcnow() - timedelta(days=7)
        users_24h = (
            await session.execute(
                select(func.count(BotUser.id)).where(BotUser.joined_at >= day_ago)
            )
        ).scalar() or 0
        users_7d = (
            await session.execute(
                select(func.count(BotUser.id)).where(BotUser.joined_at >= week_ago)
            )
        ).scalar() or 0

        # Active users (based on last_active timestamp)
        active_24h = (
            await session.execute(
                select(func.count(BotUser.id)).where(
                    BotUser.last_active.isnot(None),
                    BotUser.last_active >= day_ago,
                )
            )
        ).scalar() or 0
        active_7d = (
            await session.execute(
                select(func.count(BotUser.id)).where(
                    BotUser.last_active.isnot(None),
                    BotUser.last_active >= week_ago,
                )
            )
        ).scalar() or 0

    accuracy = (correct_predictions / evaluated_predictions * 100) if evaluated_predictions > 0 else 0
    trade_win_rate = (winning_results / total_results * 100) if total_results > 0 else 0

    return {
        "users": {
            "total": total_users,
            "premium": premium_users,
            "banned": banned_users,
            "joined_24h": users_24h,
            "joined_7d": users_7d,
            "active_24h": active_24h,
            "active_7d": active_7d,
        },
        "predictions": {
            "total": total_predictions,
            "evaluated": evaluated_predictions,
            "correct": correct_predictions,
            "accuracy_pct": round(accuracy, 1),
        },
        "trades": {
            "total": total_trades,
            "results": total_results,
            "wins": winning_results,
            "win_rate_pct": round(trade_win_rate, 1),
        },
    }


@router.get("/users")
async def admin_users(request: Request, page: int = Query(1, ge=1, le=10000), search: str = ""):
    """List all users with pagination and search."""
    _require_admin(request)

    if len(search) > 100:
        raise HTTPException(400, "Search query too long")

    per_page = 50
    offset = (page - 1) * per_page

    async with async_session() as session:
        query = select(BotUser)
        count_query = select(func.count(BotUser.id))

        if search:
            filter_cond = BotUser.username.ilike(f"%{search}%")
            # Also try searching by telegram_id
            try:
                search_id = int(search)
                from sqlalchemy import or_
                filter_cond = or_(filter_cond, BotUser.telegram_id == search_id)
            except ValueError:
                pass
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)

        total = (await session.execute(count_query)).scalar() or 0
        result = await session.execute(
            query.order_by(desc(BotUser.joined_at)).offset(offset).limit(per_page)
        )
        users = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "username": u.username,
                "subscribed": u.subscribed,
                "subscription_tier": u.subscription_tier,
                "subscription_end": u.subscription_end.isoformat() if u.subscription_end else None,
                "trial_end": u.trial_end.isoformat() if u.trial_end else None,
                "joined_at": u.joined_at.isoformat() if u.joined_at else None,
                "is_banned": u.is_banned,
                "ban_reason": u.ban_reason,
                "alert_interval": u.alert_interval,
            }
            for u in users
        ],
    }


@router.post("/users/{telegram_id}/ban")
async def admin_ban_user(request: Request, telegram_id: int, body: BanRequest):
    """Ban a user."""
    _require_admin(request)

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        user.is_banned = True
        user.ban_reason = body.reason
        await session.commit()

    logger.info(f"Admin banned user {telegram_id}: {body.reason}")
    return {"status": "banned", "telegram_id": telegram_id}


@router.post("/users/{telegram_id}/unban")
async def admin_unban_user(request: Request, telegram_id: int):
    """Unban a user."""
    _require_admin(request)

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        user.is_banned = False
        user.ban_reason = None
        await session.commit()

    logger.info(f"Admin unbanned user {telegram_id}")
    return {"status": "unbanned", "telegram_id": telegram_id}


@router.post("/users/{telegram_id}/grant-premium")
async def admin_grant_premium(request: Request, telegram_id: int, body: GrantPremiumRequest):
    """Grant premium days to a user."""
    _require_admin(request)

    if body.days < 1 or body.days > 3650:
        raise HTTPException(400, "Days must be 1-3650")

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        now = datetime.utcnow()
        if user.subscription_end and user.subscription_end > now:
            user.subscription_end = user.subscription_end + timedelta(days=body.days)
        else:
            user.subscription_end = now + timedelta(days=body.days)
        user.subscription_tier = "premium"
        await session.commit()

    logger.info(f"Admin granted {body.days}d premium to user {telegram_id}")
    return {"status": "granted", "telegram_id": telegram_id, "days": body.days}


@router.get("/predictions")
async def admin_predictions(request: Request, limit: int = Query(50, ge=1, le=500)):
    """Get recent predictions with accuracy info."""
    _require_admin(request)

    async with async_session() as session:
        result = await session.execute(
            select(Prediction)
            .order_by(desc(Prediction.timestamp))
            .limit(limit)
        )
        predictions = result.scalars().all()

    return {
        "predictions": [
            {
                "id": p.id,
                "timestamp": p.timestamp.isoformat(),
                "timeframe": p.timeframe,
                "direction": p.direction,
                "confidence": p.confidence,
                "current_price": p.current_price,
                "predicted_price": p.predicted_price,
                "predicted_change_pct": p.predicted_change_pct,
                "actual_price": p.actual_price,
                "was_correct": p.was_correct,
                "model_outputs": p.model_outputs,
            }
            for p in predictions
        ]
    }


@router.get("/system")
async def admin_system(request: Request):
    """System health info: DB size, active models, scheduler status."""
    _require_admin(request)

    async with async_session() as session:
        # Active model versions
        result = await session.execute(
            select(ModelVersion).where(ModelVersion.is_active == True)
        )
        active_models = result.scalars().all()

        # Latest price
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        latest_price = result.scalar_one_or_none()

        # Table row counts
        counts = {}
        for table_name, model in [
            ("prices", Price),
            ("predictions", Prediction),
            ("trade_advices", TradeAdvice),
            ("trade_results", TradeResult),
            ("bot_users", BotUser),
        ]:
            c = (await session.execute(select(func.count(model.id)))).scalar() or 0
            counts[table_name] = c

    return {
        "active_models": [
            {
                "id": m.id,
                "model_type": m.model_type,
                "version": m.version,
                "weights_path": m.weights_path,
                "live_accuracy_1h": m.live_accuracy_1h,
                "live_accuracy_24h": m.live_accuracy_24h,
            }
            for m in active_models
        ],
        "latest_price": {
            "price": latest_price.close if latest_price else None,
            "timestamp": latest_price.timestamp.isoformat() if latest_price else None,
        },
        "table_counts": counts,
        "config": {
            "subscription_enabled": settings.subscription_enabled,
            "advisor_enabled": settings.advisor_enabled,
            "prediction_interval_minutes": settings.prediction_interval_minutes,
            "admin_configured": bool(settings.admin_telegram_id),
        },
    }


@router.get("/bot-status")
async def admin_bot_status(request: Request):
    """Check if the Telegram bot is running and can reach the API."""
    _require_admin(request)

    bot_ok = False
    bot_info = None
    bot_error = None

    if settings.telegram_bot_token:
        try:
            from aiogram import Bot
            bot = Bot(token=settings.telegram_bot_token)
            me = await bot.get_me()
            bot_info = {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "can_read_all": me.can_read_all_group_messages,
            }
            bot_ok = True
            await bot.session.close()
        except Exception as e:
            bot_error = str(e)
    else:
        bot_error = "TELEGRAM_BOT_TOKEN not set"

    # Check DB connectivity for bot_users
    user_count = 0
    async with async_session() as session:
        user_count = (await session.execute(select(func.count(BotUser.id)))).scalar() or 0

    return {
        "bot_ok": bot_ok,
        "bot_info": bot_info,
        "bot_error": bot_error,
        "bot_users_count": user_count,
        "token_set": bool(settings.telegram_bot_token),
        "database_type": "postgresql" if settings.is_postgres else "sqlite",
    }
