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
import logging
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

logger = logging.getLogger(__name__)


def _raise_for_status(r: httpx.Response, what: str) -> None:
    """`raise_for_status`, but log why first.

    Open-Meteo explains itself in the response body — "Daily API request limit
    exceeded", a bad parameter name, and so on — and `raise_for_status()`
    throws that body away, leaving only a bare 502 at the endpoint. On a host
    with no shell (Render's free tier) that body is the only way to tell
    "we are rate-limited" apart from "we sent a malformed request", so it goes
    to the log before the exception propagates.

    Truncated because these bodies are occasionally an HTML error page.
    """
    if r.is_error:
        logger.error(
            "%s failed: HTTP %s from %s - %s",
            what,
            r.status_code,
            r.request.url.host,
            r.text[:300].replace("\n", " "),
        )
    r.raise_for_status()

# Exactly the daily variables we need for scoring — nothing more.
_DAILY_VARS = ",".join([
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
])

# Hourly counterparts for the drill-down chart — same factors the score uses,
# so a hiker can see *when* in the day the risk concentrates.
_HOURLY_VARS = ",".join([
    "temperature_2m",
    "precipitation",
    "precipitation_probability",
    "wind_gusts_10m",
    "weather_code",
])


def _cache_key(lat: float, lng: float, days: int) -> str:
    # days is part of the key: a cached 1-day payload must never be served
    # for a 7-day request (they share the grid cell but not the horizon).
    raw = f"{round(lat, 2)}:{round(lng, 2)}:{days}"
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
    _raise_for_status(r, "forecast fetch")
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
    key = _cache_key(lat, lng, days)
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
async def _fetch_forecast_bulk(
    client: httpx.AsyncClient, points: list[tuple[float, float]], days: int
) -> list[dict[str, Any]]:
    """One request for many points — Open-Meteo accepts comma-separated
    coordinate lists and returns one payload per point (a bare object when
    only one point is asked for)."""
    settings = get_settings()
    r = await client.get(
        f"{settings.open_meteo_base_url}/forecast",
        params={
            "latitude": ",".join(str(lat) for lat, _ in points),
            "longitude": ",".join(str(lng) for _, lng in points),
            "daily": _DAILY_VARS,
            "hourly": _HOURLY_VARS,
            "timezone": "auto",
            "forecast_days": days,
        },
        timeout=20.0,
    )
    _raise_for_status(r, "bulk forecast fetch")
    data = r.json()
    return data if isinstance(data, list) else [data]


async def get_forecasts_bulk(
    points: list[tuple[float, float]],
    days: int,
    client: httpx.AsyncClient,
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Forecast payloads for many points, in input order.

    Cache-aware: cached grid cells are served from Postgres; ALL misses go
    upstream in a single bulk request (25 trails ≠ 25 round trips). Fetched
    payloads are upserted under the same per-cell keys `get_forecast` uses,
    so trail recommendations and map clicks share one cache.
    """
    now = datetime.now(timezone.utc)
    keys = [_cache_key(lat, lng, days) for lat, lng in points]

    result = await session.execute(
        select(ForecastCache).where(
            ForecastCache.cache_key.in_(set(keys)),
            ForecastCache.expires_at > now,
        )
    )
    payloads: dict[str, dict[str, Any]] = {
        row.cache_key: row.payload for row in result.scalars()
    }

    # Misses, deduped by cell (nearby summits can share a grid cell).
    misses: dict[str, tuple[float, float]] = {}
    for key, point in zip(keys, points):
        if key not in payloads and key not in misses:
            misses[key] = point

    if misses:
        fetched = await _fetch_forecast_bulk(client, list(misses.values()), days)
        if len(fetched) != len(misses):
            # zip() would silently pair wrong payloads with wrong cells
            raise ValueError(
                f"Open-Meteo returned {len(fetched)} payloads for {len(misses)} points"
            )
        settings = get_settings()
        expires_at = now + timedelta(minutes=settings.forecast_cache_ttl_minutes)
        for key, payload in zip(misses, fetched):
            await session.execute(
                pg_insert(ForecastCache)
                .values(
                    cache_key=key,
                    lat=payload["latitude"],
                    lng=payload["longitude"],
                    elevation_m=int(payload.get("elevation") or 0) or None,
                    payload=payload,
                    fetched_at=now,
                    expires_at=expires_at,
                )
                .on_conflict_do_update(
                    index_elements=["cache_key"],
                    set_={"payload": payload, "fetched_at": now, "expires_at": expires_at},
                )
            )
            payloads[key] = payload
        await session.commit()

    return [payloads[key] for key in keys]


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
    _raise_for_status(r, "geocode")
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
    _raise_for_status(r, "elevation fetch")
    return float(r.json().get("elevation", 0.0))
