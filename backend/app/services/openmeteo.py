"""Open-Meteo async client with PostgreSQL forecast cache.

WHY cache in Postgres instead of Redis:
  - No Redis in v1 (free tier budget). The forecast_cache table with a
    GiST-indexed expires_at column is fast enough for our read pattern.
  - TTL is 30 minutes (configurable). Mountain weather changes hourly,
    so serving a 29-minute-old cache is acceptable and saves ~300 API
    calls/day per popular trail.

WHY round to 2 decimal places for the cache key:
  - 0.01° ≈ 1.1 km at Romanian latitudes. Hikers within 1 km share a
    cache entry. This keeps the table small while covering typical
    "same trail, slightly different GPS reading" requests.

WHY tenacity for retries:
  - Open-Meteo is free — no SLA. Short transient failures are common.
    3 attempts with exponential backoff add < 2 seconds in the 99th
    percentile while hiding flaps from the frontend.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.db.models import ForecastCache

_DAILY_VARS = ",".join([
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "uv_index_max",
    "sunrise",
    "sunset",
])

# Hourly variables needed for CAPE (thunderstorm) and visibility scoring.
_HOURLY_VARS = ",".join(["cape", "visibility"])


def _cache_key(lat: float, lng: float) -> str:
    raw = f"{round(lat, 2)}:{round(lng, 2)}"
    return hashlib.sha1(raw.encode()).hexdigest()  # 40 hex chars


@retry(
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _fetch_forecast(
    client: httpx.AsyncClient, lat: float, lng: float, days: int
) -> dict[str, Any]:
    settings = get_settings()
    r = await client.get(
        f"{settings.open_meteo_base_url}/forecast",
        params={
            "latitude": lat,
            "longitude": lng,
            "daily": _DAILY_VARS,
            "hourly": _HOURLY_VARS,
            "timezone": "auto",
            "forecast_days": days,
        },
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


async def get_forecast(
    lat: float,
    lng: float,
    days: int,
    client: httpx.AsyncClient,
    session: AsyncSession,
) -> tuple[dict[str, Any], bool]:
    """Return (raw Open-Meteo payload, was_cached).

    The raw payload is stored in JSONB so scoring logic can be changed
    without re-fetching. Score is always computed fresh on read.
    """
    key = _cache_key(lat, lng)
    now = datetime.now(timezone.utc)

    # --- Cache lookup ---
    result = await session.execute(
        select(ForecastCache).where(
            ForecastCache.cache_key == key,
            ForecastCache.expires_at > now,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row.payload, True

    # --- Cache miss: fetch from API ---
    payload = await _fetch_forecast(client, lat, lng, days)
    settings = get_settings()

    stmt = (
        pg_insert(ForecastCache)
        .values(
            cache_key=key,
            lat=payload["latitude"],
            lng=payload["longitude"],
            elevation_m=int(payload.get("elevation") or 0) or None,
            payload=payload,
            fetched_at=now,
            expires_at=now + timedelta(minutes=settings.forecast_cache_ttl_minutes),
        )
        .on_conflict_do_update(
            index_elements=["cache_key"],
            set_={
                "payload": payload,
                "fetched_at": now,
                "expires_at": now + timedelta(minutes=settings.forecast_cache_ttl_minutes),
            },
        )
    )
    await session.execute(stmt)
    await session.commit()

    return payload, False


@retry(
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def geocode(q: str, client: httpx.AsyncClient) -> dict[str, Any]:
    settings = get_settings()
    r = await client.get(
        f"{settings.open_meteo_geocode_url}/search",
        params={"name": q, "count": 5, "language": "en", "format": "json"},
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


@retry(
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def get_elevation(lat: float, lng: float, client: httpx.AsyncClient) -> float:
    """Fetch elevation by requesting a 1-day forecast (Open-Meteo always returns it)."""
    settings = get_settings()
    r = await client.get(
        f"{settings.open_meteo_base_url}/forecast",
        params={
            "latitude": lat,
            "longitude": lng,
            "daily": "weather_code",
            "forecast_days": 1,
            "timezone": "auto",
        },
        timeout=10.0,
    )
    r.raise_for_status()
    return float(r.json().get("elevation", 0.0))
