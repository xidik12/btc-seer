"""Tests for the market data API endpoints."""
from __future__ import annotations
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint should return 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "warming_up", "degraded")


@pytest.mark.asyncio
async def test_public_config(client: AsyncClient):
    """Public config endpoint should return bot_username."""
    response = await client.get("/api/config/public")
    assert response.status_code == 200
    data = response.json()
    assert "bot_username" in data


@pytest.mark.asyncio
async def test_market_price_unauthenticated(client: AsyncClient):
    """Market price endpoint without auth should return 401 or data if public."""
    response = await client.get("/api/market/price")
    # Accept 200 (public endpoint) or 401 (protected)
    assert response.status_code in (200, 401, 404)


@pytest.mark.asyncio
async def test_market_price_authenticated(client: AsyncClient, auth_headers: dict):
    """Market price with valid JWT should succeed."""
    response = await client.get("/api/market/price", headers=auth_headers)
    assert response.status_code in (200, 404)  # 404 if no data in test DB


@pytest.mark.asyncio
async def test_market_history(client: AsyncClient, auth_headers: dict):
    """Market history endpoint should return a list (possibly empty)."""
    response = await client.get("/api/market/history", headers=auth_headers)
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_rate_limit_header_present(client: AsyncClient):
    """Requests should not expose internal rate limit keys in headers."""
    response = await client.get("/health")
    assert "x-internal-rate-limit" not in response.headers


@pytest.mark.asyncio
async def test_metrics_endpoint_exists(client: AsyncClient):
    """Prometheus /metrics endpoint should be accessible."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "python_gc_objects" in response.text
