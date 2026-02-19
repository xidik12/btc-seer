"""Tests for JWT auth utilities and auth API endpoints."""
from __future__ import annotations
import pytest
from httpx import AsyncClient


# ── JWT utility unit tests ──────────────────────────────────────────────────

def test_create_and_decode_token():
    """JWT round-trip: create → decode recovers original claims."""
    from app.jwt_utils import create_access_token, decode_access_token

    token = create_access_token(
        telegram_id=42,
        username="alice",
        subscription_tier="premium",
        is_premium=True,
        is_banned=False,
    )
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["username"] == "alice"
    assert payload["tier"] == "premium"
    assert payload["premium"] is True
    assert payload["banned"] is False


def test_decode_invalid_token_raises():
    """Decoding garbage should raise HTTPException 401."""
    from fastapi import HTTPException
    from app.jwt_utils import decode_access_token

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not.a.valid.token")
    assert exc_info.value.status_code == 401


def test_decode_expired_token_raises():
    """Expired token should raise HTTPException 401."""
    import jwt
    from datetime import datetime, timedelta, timezone
    from fastapi import HTTPException
    from app.config import settings
    from app.jwt_utils import decode_access_token, _ALGORITHM

    expired_payload = {
        "sub": "1",
        "username": "bob",
        "tier": "free",
        "premium": False,
        "banned": False,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=_ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_get_current_user_no_header():
    """No Authorization header → returns None."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI, Request
    from app.jwt_utils import get_current_user_from_jwt

    mini_app = FastAPI()

    @mini_app.get("/test")
    async def _handler(request: Request):
        user = get_current_user_from_jwt(request)
        return {"user": user}

    tc = TestClient(mini_app)
    resp = tc.get("/test")
    assert resp.status_code == 200
    assert resp.json()["user"] is None


# ── Auth API endpoint tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_missing_body(client: AsyncClient):
    """Register without body should return 422 validation error."""
    response = await client.post("/api/auth/register", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_init_data(client: AsyncClient):
    """Register with invalid Telegram initData should return 400/401."""
    response = await client.post(
        "/api/auth/register",
        json={"init_data": "invalid_data_string"},
    )
    assert response.status_code in (400, 401, 422)


@pytest.mark.asyncio
async def test_jwt_in_register_response_shape(client: AsyncClient):
    """When registration succeeds, response must include access_token field."""
    # We can only verify the shape; a real Telegram initData is needed for success.
    # This test documents the expected contract for the auth endpoint.
    # With invalid data we still verify the 400/401 path doesn't return a token.
    response = await client.post(
        "/api/auth/register",
        json={"init_data": "bad_data"},
    )
    if response.status_code == 200:
        # If somehow 200, access_token must be present
        assert "access_token" in response.json()
    else:
        assert response.status_code in (400, 401, 422)
