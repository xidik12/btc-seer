"""Telegram WebApp initData verification and auth utilities.

Extracted from app.api.admin to be shared across all API modules.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote

from fastapi import Request, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)


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
        max_age = kwargs.get("max_age", 300)  # default 5 min for admin; 0 = no expiry
        if max_age > 0 and age_seconds > max_age:
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


async def require_premium(request: Request):
    """FastAPI dependency that checks if the caller has an active premium subscription."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")
    parsed = _verify_telegram_init_data(init_data)
    telegram_id = parsed.get("telegram_id") or parsed.get("id")
    if not telegram_id:
        raise HTTPException(401, "Invalid initData")

    from app.database import async_session
    from sqlalchemy import select, text

    async with async_session() as session:
        # Check if user has active subscription (uses bot_users table)
        result = await session.execute(
            text("SELECT subscription_tier, subscription_end, trial_end FROM bot_users WHERE telegram_id = :tid"),
            {"tid": int(telegram_id)}
        )
        row = result.first()
        if not row:
            raise HTTPException(403, "Premium subscription required")

        tier, sub_end, trial_end = row
        now = datetime.now(timezone.utc)
        # Check active subscription or active trial
        has_active_sub = tier in ("premium", "pro") and (not sub_end or sub_end > now)
        has_active_trial = tier == "trial" and trial_end and trial_end > now
        if not (has_active_sub or has_active_trial):
            raise HTTPException(403, "Premium subscription required")

    return telegram_id
