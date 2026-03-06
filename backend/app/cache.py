"""Shared async cache — Redis-backed with in-process fallback.

Usage:
    from app.cache import cache_get, cache_set, cache_delete

All values are JSON-serialized. TTL is in seconds.
Falls back to a simple dict if Redis is unavailable (e.g. local dev).
"""
from __future__ import annotations

import json
import logging
import time

logger = logging.getLogger(__name__)

# ── In-process fallback ──────────────────────────────────────────
_local: dict[str, tuple[bytes, float]] = {}


def _local_get(key: str) -> dict | list | None:
    if key in _local:
        raw, expires = _local[key]
        if time.monotonic() < expires:
            return json.loads(raw)
        del _local[key]
    return None


def _local_set(key: str, data, ttl: int) -> None:
    _local[key] = (json.dumps(data, default=str), time.monotonic() + ttl)


def _local_delete(key: str) -> None:
    _local.pop(key, None)


# ── Public API ───────────────────────────────────────────────────

async def cache_get(key: str) -> dict | list | None:
    """Get cached value by key. Returns None on miss."""
    try:
        from app.redis_client import get_redis
        r = await get_redis()
        raw = await r.get(f"c:{key}")
        if raw is not None:
            return json.loads(raw)
        return None
    except Exception:
        return _local_get(key)


async def cache_set(key: str, data, ttl: int = 30) -> None:
    """Set cache value with TTL in seconds."""
    try:
        from app.redis_client import get_redis
        r = await get_redis()
        await r.set(f"c:{key}", json.dumps(data, default=str), ex=ttl)
    except Exception:
        _local_set(key, data, ttl)


async def cache_delete(key: str) -> None:
    """Delete a cache key (used for invalidation after data writes)."""
    try:
        from app.redis_client import get_redis
        r = await get_redis()
        await r.delete(f"c:{key}")
    except Exception:
        _local_delete(key)
    # Always clear local fallback too
    _local.pop(key, None)
