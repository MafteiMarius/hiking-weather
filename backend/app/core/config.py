from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Walk up from this file (backend/app/core/) to find the nearest .env —
# works whether uvicorn is run from backend/ or the repo root.
_HERE = Path(__file__).resolve().parent
_ENV_CANDIDATES = [
    _HERE.parent.parent.parent / ".env",  # repo root  (docker-compose / CI)
    _HERE.parent.parent / ".env",         # backend/   (local pip install)
]
_ENV_FILE = next((str(p) for p in _ENV_CANDIDATES if p.exists()), ".env")


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
