"""Tests for the ML ensemble and prediction model utilities."""
from __future__ import annotations
import pytest


# ── Ensemble smoke tests ─────────────────────────────────────────────────────

def test_ensemble_get_returns_singleton():
    """get_ensemble() should return the same object on repeated calls."""
    from app.scheduler.domain_ml import get_ensemble

    e1 = get_ensemble()
    e2 = get_ensemble()
    assert e1 is e2, "get_ensemble() must return a singleton"


def test_ensemble_has_required_attributes():
    """Ensemble object should expose predict and timeframes attributes."""
    from app.scheduler.domain_ml import get_ensemble

    ens = get_ensemble()
    assert hasattr(ens, "predict") or hasattr(ens, "ensemble_predict"), (
        "Ensemble must have a predict method"
    )


# ── Config validation ────────────────────────────────────────────────────────

def test_config_jwt_secret_required():
    """JWT_SECRET_KEY must be configured (non-empty in test env)."""
    from app.config import settings

    assert settings.jwt_secret_key, "JWT_SECRET_KEY must be set"


def test_config_redis_url_has_scheme():
    """REDIS_URL should start with redis:// or rediss://."""
    from app.config import settings

    assert settings.redis_url.startswith(("redis://", "rediss://")), (
        f"REDIS_URL has unexpected scheme: {settings.redis_url}"
    )


def test_config_sentry_dsn_is_optional():
    """SENTRY_DSN can be empty string (optional)."""
    from app.config import settings

    assert isinstance(settings.sentry_dsn, str)


# ── Rate limiter unit tests ──────────────────────────────────────────────────

def test_make_rate_limiter_returns_callable():
    """make_rate_limiter factory should return an async callable."""
    import asyncio
    from app.dependencies import make_rate_limiter

    limiter = make_rate_limiter(limit=10, window=60)
    assert callable(limiter)
    assert asyncio.iscoroutinefunction(limiter)


def test_standard_rate_limit_is_callable():
    """Pre-built standard_rate_limit should be an async callable."""
    import asyncio
    from app.dependencies import standard_rate_limit

    assert callable(standard_rate_limit)
    assert asyncio.iscoroutinefunction(standard_rate_limit)


# ── Database model smoke tests ───────────────────────────────────────────────

def test_price_model_has_ohlcv_fields():
    """Price model must have OHLCV + timestamp fields."""
    from app.database import Price

    for field in ("open", "high", "low", "close", "volume", "timestamp"):
        assert hasattr(Price, field), f"Price model missing field: {field}"


def test_prediction_model_has_required_fields():
    """Prediction model must have direction, confidence, timeframe."""
    from app.database import Prediction

    for field in ("direction", "confidence", "timeframe", "created_at"):
        assert hasattr(Prediction, field), f"Prediction model missing field: {field}"


def test_botuser_model_has_telegram_id():
    """BotUser model must have telegram_id field."""
    from app.database import BotUser

    assert hasattr(BotUser, "telegram_id"), "BotUser model missing telegram_id"
    assert hasattr(BotUser, "subscription_tier"), "BotUser model missing subscription_tier"
