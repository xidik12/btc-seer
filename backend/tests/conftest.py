"""Shared pytest fixtures for BTC Seer test suite."""
from __future__ import annotations
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Set required env vars before importing app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_btc_seer.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")  # Use DB 1 for tests
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")

from app.main import app
from app.database import async_session, Base
from sqlalchemy.ext.asyncio import create_async_engine


TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    """HTTPX async client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session(engine):
    """Yield a database session, rolling back after each test."""
    async with async_session() as session:
        yield session
        await session.rollback()


# Sample JWT token for test auth
@pytest.fixture
def auth_headers():
    """Return Authorization headers with a test JWT."""
    from app.jwt_utils import create_access_token
    token = create_access_token(
        telegram_id=123456789,
        username="testuser",
        subscription_tier="free",
        is_premium=False,
        is_banned=False,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def premium_auth_headers():
    """Return Authorization headers with a premium test JWT."""
    from app.jwt_utils import create_access_token
    token = create_access_token(
        telegram_id=987654321,
        username="premiumuser",
        subscription_tier="premium",
        is_premium=True,
        is_banned=False,
    )
    return {"Authorization": f"Bearer {token}"}
