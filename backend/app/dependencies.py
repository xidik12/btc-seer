"""Shared FastAPI dependencies."""
from __future__ import annotations
import time
import logging
from fastapi import Request, HTTPException

from app.redis_client import get_redis

logger = logging.getLogger(__name__)


async def rate_limit(
    request: Request,
    limit: int = 60,
    window: int = 60,
):
    """
    Redis-backed sliding window rate limiter.
    Falls back to fail-open mode if Redis is unavailable.
    """
    ip = request.client.host if request.client else "unknown"
    key = f"rl:{ip}"
    try:
        redis = await get_redis()
        now = time.time()
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        count = results[2]
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(window)},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis unavailable — fail open (allow request, log warning)
        logger.warning(f"Rate limiter Redis error (fail-open): {exc}")


def make_rate_limiter(limit: int = 60, window: int = 60):
    """Factory to create a rate limiter dependency with custom limits."""
    async def _limiter(request: Request):
        await rate_limit(request, limit=limit, window=window)
    return _limiter


# Pre-built limiters for common use cases
standard_rate_limit = make_rate_limiter(limit=60, window=60)
strict_rate_limit = make_rate_limiter(limit=20, window=60)
relaxed_rate_limit = make_rate_limiter(limit=120, window=60)
