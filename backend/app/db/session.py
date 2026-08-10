from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.sqlalchemy_url,
    echo=False,
    future=True,
    connect_args=_settings.sqlalchemy_connect_args,
    # Managed Postgres (Neon) and cloud proxies drop idle connections; without
    # a liveness check the pool hands out a dead one after an idle spell and
    # the first request after that fails. Recycling below the typical 5-minute
    # idle timeout keeps connections fresh.
    pool_pre_ping=True,
    pool_recycle=280,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
