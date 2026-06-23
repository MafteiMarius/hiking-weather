"""Shared test fixtures.

Test DB strategy:
- One PostgreSQL DB (hikecast_test, controlled by TEST_DATABASE_URL).
- Engine created inside a session-scoped fixture so it shares the pytest-asyncio
  session event loop — avoids the "another operation is in progress" asyncpg
  error that happens when a module-level engine is used across loop boundaries.
- Tables created once per test session; dropped at teardown.
- Before each test, all data tables are TRUNCATED (fast; schema stays intact).
"""
import os
from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://hikecast:hikecast@localhost:5432/hikecast_test",
)

# Truncate in FK-safe order (children before parent `users`).
_TRUNCATE_SQL = sa.text(
    "TRUNCATE access_tokens, user_profiles, saved_locations, "
    "trails, forecast_cache, climatology, users RESTART IDENTITY CASCADE"
)


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Session-scoped engine — same event loop as all async fixtures."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Create PostGIS extensions and all tables once; drop at teardown."""
    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def _clean_db(engine: AsyncEngine) -> None:
    """Truncate all data before each test so tests don't bleed into each other."""
    async with engine.begin() as conn:
        await conn.execute(_TRUNCATE_SQL)


@pytest_asyncio.fixture()
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture()
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with get_db overridden to use the per-test session.

    A real httpx.AsyncClient is attached to app.state.http so that
    the forecast endpoints can use it; respx intercepts its outbound
    requests in tests that need to mock the Open-Meteo API.
    """

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = _override
    async with httpx.AsyncClient() as http:
        app.state.http = http
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    app.dependency_overrides.pop(get_db, None)
