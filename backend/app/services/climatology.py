"""Historical instability detector.

WHY this exists:
  A forecast can look fine while the location has a long track record of
  afternoon thunderstorms in this exact week of the year (classic Carpathian
  summer pattern). We pull ~10 years of ERA5 reanalysis daily data from
  Open-Meteo's archive API, keep only the days that fall in the same ISO week
  as the query date, and aggregate them into six stability metrics.

WHY ISO week instead of calendar month:
  Mountain weather patterns shift on a scale of days, not months — early June
  and late June differ a lot. A week is the finest bucket that still gives
  ~70 samples from 10 years (7 days x 10 years).

WHY cache for 30 days:
  Climatology moves on a scale of years. The only reason to recompute at all
  is the rolling 10-year window; monthly is more than enough. One archive
  request covers ~3650 days of data, so we really don't want it per page view.
"""

import hashlib
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

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
from app.db.models import Climatology

_ARCHIVE_DAILY_VARS = ",".join([
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_gusts_10m_max",
])

_THUNDER_CODES = {95, 96, 99}

# A "wet day" needs enough rain to matter on a trail, not a trace.
WET_DAY_THRESHOLD_MM = 1.0

# ERA5 lags real time by a few days; stay a week behind to be safe.
_ARCHIVE_LAG_DAYS = 7


def _cache_key(lat: float, lng: float) -> str:
    """Same ~1 km grid rounding as the forecast cache (no days component —
    climatology is keyed by (grid cell, iso_week) instead)."""
    raw = f"{round(lat, 2)}:{round(lng, 2)}"
    return hashlib.sha1(raw.encode()).hexdigest()


@dataclass(frozen=True)
class WeekStats:
    years_analyzed: int
    precip_day_frequency_pct: int
    thunderstorm_pct: int
    temp_avg_max_c: float
    temp_avg_min_c: float
    wind_gust_p90_kmh: int
    volatility_index: int


@retry(
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _fetch_archive(
    client: httpx.AsyncClient, lat: float, lng: float, start: date, end: date
) -> dict[str, Any]:
    settings = get_settings()
    r = await client.get(
        f"{settings.open_meteo_archive_url}/archive",
        params={
            "latitude": lat,
            "longitude": lng,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": _ARCHIVE_DAILY_VARS,
            "timezone": "auto",
        },
        timeout=30.0,  # ~3650 rows; slower than a forecast call
    )
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


def aggregate_week(payload: dict[str, Any], iso_week: int) -> Optional[WeekStats]:
    """Reduce a multi-year daily archive to stats for one ISO week.

    Pure function — all the interesting math lives here so it can be unit
    tested without HTTP or a database.
    """
    daily = payload.get("daily") or {}
    times: list[str] = daily.get("time", [])

    # Collect (date, code, tmax, tmin, precip, gust) rows for the target week.
    rows: list[tuple[date, int, float, float, float, float]] = []
    for i, iso in enumerate(times):
        d = date.fromisoformat(iso)
        if d.isocalendar().week != iso_week:
            continue
        code = daily["weather_code"][i]
        tmax = daily["temperature_2m_max"][i]
        tmin = daily["temperature_2m_min"][i]
        precip = daily["precipitation_sum"][i]
        gust = daily["wind_gusts_10m_max"][i]
        if None in (code, tmax, tmin, precip, gust):
            continue  # ERA5 has occasional gaps; skip incomplete days
        rows.append((d, int(code), float(tmax), float(tmin), float(precip), float(gust)))

    if not rows:
        return None

    rows.sort(key=lambda r: r[0])
    n = len(rows)
    wet_days = sum(r[4] >= WET_DAY_THRESHOLD_MM for r in rows)

    # Volatility: how often the weather flips wet<->dry between consecutive
    # calendar days. A week that alternates rain/sun every day is harder to
    # plan around than one that is uniformly wet.
    pairs = flips = 0
    for a, b in zip(rows, rows[1:]):
        if (b[0] - a[0]).days == 1:
            pairs += 1
            if (a[4] >= WET_DAY_THRESHOLD_MM) != (b[4] >= WET_DAY_THRESHOLD_MM):
                flips += 1

    gusts = sorted(r[5] for r in rows)
    p90 = gusts[min(n - 1, round(0.9 * (n - 1)))]

    return WeekStats(
        years_analyzed=len({r[0].isocalendar().year for r in rows}),
        precip_day_frequency_pct=round(100 * wet_days / n),
        thunderstorm_pct=round(100 * sum(r[1] in _THUNDER_CODES for r in rows) / n),
        temp_avg_max_c=round(statistics.fmean(r[2] for r in rows), 1),
        temp_avg_min_c=round(statistics.fmean(r[3] for r in rows), 1),
        wind_gust_p90_kmh=round(p90),
        volatility_index=round(100 * flips / pairs) if pairs else 0,
    )


async def get_climatology(
    lat: float,
    lng: float,
    client: httpx.AsyncClient,
    session: AsyncSession,
    for_date: Optional[date] = None,
) -> tuple[Optional[Climatology], bool]:
    """Return (climatology row for the ISO week of for_date, was_cached).

    None when the archive has no usable data for the location/week.
    `for_date` is injectable for tests; defaults to today.
    """
    settings = get_settings()
    today = for_date or datetime.now(timezone.utc).date()
    iso_week = today.isocalendar().week
    key = _cache_key(lat, lng)
    now = datetime.now(timezone.utc)

    # --- Cache lookup (30-day freshness) ---
    result = await session.execute(
        select(Climatology).where(
            Climatology.cache_key == key,
            Climatology.iso_week == iso_week,
            Climatology.computed_at > now - timedelta(days=settings.climatology_cache_days),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row, True

    # --- Compute from the archive ---
    end = today - timedelta(days=_ARCHIVE_LAG_DAYS)
    start = end - timedelta(days=settings.climatology_years * 366)
    payload = await _fetch_archive(client, lat, lng, start, end)
    stats = aggregate_week(payload, iso_week)
    if stats is None:
        return None, False

    values = {
        "cache_key": key,
        "iso_week": iso_week,
        "years_analyzed": stats.years_analyzed,
        "precip_day_frequency_pct": stats.precip_day_frequency_pct,
        "thunderstorm_pct": stats.thunderstorm_pct,
        "temp_avg_max_c": stats.temp_avg_max_c,
        "temp_avg_min_c": stats.temp_avg_min_c,
        "wind_gust_p90_kmh": stats.wind_gust_p90_kmh,
        "volatility_index": stats.volatility_index,
        "computed_at": now,
    }
    stmt = (
        pg_insert(Climatology)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["cache_key", "iso_week"],
            set_={k: v for k, v in values.items() if k not in ("cache_key", "iso_week")},
        )
    )
    await session.execute(stmt)
    await session.commit()

    refreshed = await session.execute(
        select(Climatology).where(
            Climatology.cache_key == key, Climatology.iso_week == iso_week
        )
    )
    return refreshed.scalar_one(), False
