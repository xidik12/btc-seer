"""JWT token utilities for BTC Oracle auth."""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, Request

from app.config import settings

logger = logging.getLogger(__name__)

_ALGORITHM = settings.jwt_algorithm


def create_access_token(
    telegram_id: int,
    username: str | None,
    subscription_tier: str,
    is_premium: bool,
    is_banned: bool,
) -> str:
    """Issue a signed JWT valid for jwt_expire_hours hours."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": str(telegram_id),
        "username": username,
        "tier": subscription_tier,
        "premium": is_premium,
        "banned": is_banned,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def get_current_user_from_jwt(request: Request) -> Optional[dict]:
    """
    Extract user from Bearer JWT token in Authorization header.
    Returns None if no token present (for optional auth endpoints).
    Raises HTTPException if token is present but invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return decode_access_token(token)


async def require_jwt_user(request: Request) -> dict:
    """FastAPI dependency: require valid JWT, return payload dict."""
    user = get_current_user_from_jwt(request)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a Bearer token.",
        )
    if user.get("banned"):
        raise HTTPException(status_code=403, detail="Account is banned.")
    return user
