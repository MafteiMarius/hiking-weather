from functools import lru_cache

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str

    # Auth
    jwt_secret: str
    jwt_lifetime_seconds: int = 900
    refresh_lifetime_seconds: int = 2_592_000
    cookie_secure: bool = True

    # CORS — accepts a comma-separated string or a JSON list in the env var
    cors_origins: list[AnyHttpUrl] = ["http://localhost:5173"]  # type: ignore[assignment]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

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
