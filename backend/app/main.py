import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import get_settings

# Uvicorn configures its own loggers but leaves the root logger alone, so
# application logs would otherwise fall through to logging's unformatted
# "last resort" handler (and anything below WARNING would vanish entirely).
# Configuring root here means `logger.error(...)` in a service shows up in the
# host's log stream with a timestamp — the only debugging surface available on
# a free tier with no shell access.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


# Identify ourselves to upstream APIs. httpx's default User-Agent
# ("python-httpx/x.y") coming from a datacenter IP is indistinguishable from
# scraper traffic, and these providers have tightened blocking because of it —
# Overpass already 406s without a custom agent (see docs/CHANGELOG.md gotchas).
# A contactable identifier is both the polite thing to send and the difference
# between being served and being filtered.
_USER_AGENT = "HikeCast/1.0 (+https://hiking-weather.vercel.app)"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    import httpx
    app.state.http = httpx.AsyncClient(headers={"User-Agent": _USER_AGENT})
    yield
    await app.state.http.aclose()
    from app.db.session import engine
    await engine.dispose()

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="HikeCast API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/api/v1")

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
