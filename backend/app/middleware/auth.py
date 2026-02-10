"""API Key authentication middleware for public API monetization.

Extracts API key from X-API-Key header or ?api_key= query param.
Skips auth for internal webapp requests (non-/api/v1/ paths).
Validates key, checks tier permissions, enforces rate limits, logs usage.

Controlled by API_KEY_ENABLED config (default: False = all free).
"""
import hashlib
import logging
import time
from collections import defaultdict
from datetime import datetime

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.database import async_session, ApiKey, ApiUsageLog

logger = logging.getLogger(__name__)

# In-memory rate limit tracking: {key_hash: [timestamps]}
_rate_limit_buckets: dict[str, list[float]] = defaultdict(list)

# Tier -> allowed endpoint prefixes
TIER_PERMISSIONS = {
    "free": {"/api/v1/price", "/api/v1/powerlaw"},
    "basic": {"/api/v1/price", "/api/v1/powerlaw", "/api/v1/predictions", "/api/v1/market"},
    "pro": None,  # None = all endpoints
    "enterprise": None,
}

TIER_RATE_LIMITS = {
    "free": settings.api_free_rate_limit,
    "basic": settings.api_basic_rate_limit,
    "pro": settings.api_pro_rate_limit,
    "enterprise": settings.api_enterprise_rate_limit,
}


def hash_api_key(key: str) -> str:
    """Hash an API key for storage/lookup."""
    return hashlib.sha256(key.encode()).hexdigest()


def _clean_bucket(bucket: list[float], window: float = 3600.0) -> list[float]:
    """Remove timestamps older than window (1 hour)."""
    cutoff = time.time() - window
    return [t for t in bucket if t > cutoff]


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Authenticate and rate-limit public API requests via API key."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for non-public-API paths (internal webapp, health, etc.)
        if not path.startswith("/api/v1/"):
            return await call_next(request)

        # If API key auth is disabled, allow everything (free mode)
        if not settings.api_key_enabled:
            return await call_next(request)

        # Extract API key from header or query param
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "API key required. Pass via X-API-Key header or ?api_key= param."},
            )

        # Validate key
        key_hash = hash_api_key(api_key)

        try:
            async with async_session() as session:
                result = await session.execute(
                    select(ApiKey).where(
                        ApiKey.key_hash == key_hash,
                        ApiKey.is_active == True,
                    )
                )
                key_record = result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"API key lookup error: {e}")
            return JSONResponse(
                status_code=503,
                content={"error": "Service temporarily unavailable. Please retry."},
            )

        if not key_record:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or inactive API key."},
            )

        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            return JSONResponse(
                status_code=401,
                content={"error": "API key has expired."},
            )

        # Check tier permissions
        tier = key_record.tier
        allowed = TIER_PERMISSIONS.get(tier)
        if allowed is not None:
            if not any(path.startswith(prefix) for prefix in allowed):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": f"Endpoint not available on '{tier}' tier.",
                        "upgrade": "Contact us to upgrade your plan.",
                    },
                )

        # Rate limiting
        rate_limit = TIER_RATE_LIMITS.get(tier, settings.api_free_rate_limit)
        bucket = _rate_limit_buckets[key_hash]
        bucket = _clean_bucket(bucket)
        _rate_limit_buckets[key_hash] = bucket

        if len(bucket) >= rate_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded.",
                    "limit": rate_limit,
                    "period": "1 hour",
                    "retry_after_seconds": int(3600 - (time.time() - bucket[0])),
                },
            )

        bucket.append(time.time())

        # Store key info on request state for downstream use
        request.state.api_key_id = key_record.id
        request.state.api_tier = tier

        # Process request
        start = time.time()
        response = await call_next(request)
        elapsed_ms = (time.time() - start) * 1000

        # Log usage (fire and forget)
        try:
            async with async_session() as session:
                log = ApiUsageLog(
                    api_key_id=key_record.id,
                    endpoint=path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=round(elapsed_ms, 2),
                    ip_address=request.client.host if request.client else None,
                    tier=tier,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.debug(f"API usage log error: {e}")

        return response
