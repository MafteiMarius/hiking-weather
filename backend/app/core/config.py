from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict

# Walk up from this file (backend/app/core/) to find the nearest .env —
# works whether uvicorn is run from backend/ or the repo root.
_HERE = Path(__file__).resolve().parent
_ENV_CANDIDATES = [
    _HERE.parent.parent.parent / ".env",  # repo root  (docker-compose / CI)
    _HERE.parent.parent / ".env",         # backend/   (local pip install)
]
_ENV_FILE = next((str(p) for p in _ENV_CANDIDATES if p.exists()), ".env")


# ── Database URL normalization ────────────────────────────────────────────────
# Managed Postgres providers (Neon, Supabase, Railway, Heroku) hand out libpq
# connection strings — `postgresql://user:pass@host/db?sslmode=require`. Two
# things in that string break asyncpg:
#
#   1. The driver. SQLAlchemy needs `postgresql+asyncpg://` to pick the async
#      dialect; a bare `postgresql://` silently selects psycopg2, which isn't
#      installed. (`postgres://` is Heroku's legacy spelling of the same thing.)
#   2. `sslmode` is a *libpq* parameter. asyncpg doesn't accept it and raises
#      TypeError on connect. Its equivalent is an `ssl` connect argument.
#
# We translate both ourselves rather than relying on the dialect to do it, so
# the behaviour is identical across SQLAlchemy versions and is unit-testable
# without a live database. Local dev URLs (no query string) pass through
# untouched and get no ssl argument.

# libpq-only query parameters that asyncpg would choke on. `sslmode` is
# translated to an ssl argument; the rest are simply dropped because asyncpg
# has no equivalent and the provider defaults are fine.
_LIBPQ_ONLY_PARAMS = frozenset(
    {"sslmode", "channel_binding", "sslrootcert", "sslcert", "sslkey", "gssencmode"}
)


def normalize_database_url(url: str) -> tuple[str, dict[str, Any]]:
    """Return an asyncpg-safe (url, connect_args) pair for `create_async_engine`.

    Pure function — no I/O, no settings access — so it can be unit-tested with
    hand-written expectations. See the module comment above for the why.
    """
    scheme, netloc, path, query, fragment = urlsplit(url)

    # 1 — force the async driver, preserving any already-correct one.
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    # 2 — split libpq-only parameters out of the query string. parse_qsl keeps
    # ordering and repeated keys, so unrelated params (application_name, …)
    # survive in the order the provider sent them.
    kept: list[tuple[str, str]] = []
    sslmode: str | None = None
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key.lower() == "sslmode":
            sslmode = value
        elif key.lower() in _LIBPQ_ONLY_PARAMS:
            continue  # no asyncpg equivalent — drop it
        else:
            kept.append((key, value))

    connect_args: dict[str, Any] = {}
    if sslmode is not None:
        # asyncpg accepts the libpq mode names directly as an `ssl` string
        # ("require", "verify-full", …), so the value carries over as-is.
        # `disable` is asyncpg's way of saying "no TLS" and is passed through
        # too, which keeps a provider's explicit opt-out meaningful.
        connect_args["ssl"] = sslmode

    return urlunsplit((scheme, netloc, path, urlencode(kept), fragment)), connect_args


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore", #TEMPORARY fix
    )

    # Database
    database_url: str

    # Auth
    jwt_secret: str
    jwt_lifetime_seconds: int = 900
    refresh_lifetime_seconds: int = 2_592_000
    cookie_secure: bool = True

    # Comma-separated origins, e.g. "http://localhost:5173,https://hikecast.app"
    # Kept as str so pydantic-settings doesn't try to JSON-decode it.
    cors_origins: str = "http://localhost:5173"

    # Open-Meteo
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    open_meteo_archive_url: str = "https://archive-api.open-meteo.com/v1"
    open_meteo_geocode_url: str = "https://geocoding-api.open-meteo.com/v1"

    # Cache
    forecast_cache_ttl_minutes: int = 30
    climatology_years: int = 10
    climatology_cache_days: int = 30

    # AI (optional — endpoints return 503 when the key is not configured)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    # ── Derived database settings ─────────────────────────────────────────
    # Everything that opens a connection (app engine, Alembic) must go through
    # these two rather than reading `database_url` directly, or a managed
    # provider's URL will blow up at connect time. See normalize_database_url.

    @property
    def sqlalchemy_url(self) -> str:
        return normalize_database_url(self.database_url)[0]

    @property
    def sqlalchemy_connect_args(self) -> dict[str, Any]:
        return normalize_database_url(self.database_url)[1]


@lru_cache
def get_settings() -> Settings:
    return Settings()
