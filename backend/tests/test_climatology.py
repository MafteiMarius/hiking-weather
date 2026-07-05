"""Climatology: pure aggregation math + endpoint behaviour (mocked archive).

The aggregation fixture uses date.fromisocalendar so the synthetic days are
guaranteed to land in the intended ISO week regardless of what year it is.
"""
from datetime import date, datetime, timezone

import pytest
import respx
from httpx import AsyncClient, Response

from app.services.climatology import aggregate_week

# Applied per-test (not module-wide) because the aggregation tests are sync.
session_loop = pytest.mark.asyncio(loop_scope="session")

CLIMATOLOGY_URL = "/api/v1/climatology"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

_WEEK = 28


def _week_dates(year: int, week: int) -> list[str]:
    return [date.fromisocalendar(year, week, d).isoformat() for d in range(1, 8)]


# Two full ISO-28 weeks (2024 + 2025) with hand-computable stats, plus an
# out-of-week day and a gap day that must both be ignored.
_ARCHIVE_PAYLOAD = {
    "latitude": 45.5,
    "longitude": 25.3,
    "daily": {
        "time": (
            ["2024-06-01"]                      # wrong week — must be filtered out
            + _week_dates(2024, _WEEK)
            + _week_dates(2025, _WEEK)
            + [date.fromisocalendar(2023, _WEEK, 1).isoformat()]  # gap day (None temp)
        ),
        "weather_code":        [99] + [95, 0, 96, 1, 99, 2, 3] + [0] * 7 + [0],
        "temperature_2m_max":  [99.0] + [20.0] * 7 + [24.0] * 7 + [None],
        "temperature_2m_min":  [-99.0] + [10.0] * 7 + [14.0] * 7 + [5.0],
        "precipitation_sum":   [99.0] + [5.0, 0.0, 10.0, 0.0, 2.0, 0.0, 0.0] + [0.0] * 7 + [0.0],
        "wind_gusts_10m_max":  [999.0] + [10, 20, 30, 40, 50, 60, 70] + [15, 25, 35, 45, 55, 65, 100] + [20.0],
    },
}


# ── Pure aggregation ──────────────────────────────────────────────────────────

def test_aggregate_week_computes_all_metrics() -> None:
    stats = aggregate_week(_ARCHIVE_PAYLOAD, _WEEK)
    assert stats is not None

    # 14 usable days: gap day skipped (None temp), out-of-week day filtered
    assert stats.years_analyzed == 2               # 2023 row was skipped
    assert stats.thunderstorm_pct == 21            # 3/14 (codes 95, 96, 99)
    assert stats.precip_day_frequency_pct == 21    # 3/14 days >= 1 mm
    assert stats.temp_avg_max_c == 22.0            # mean(7x20, 7x24)
    assert stats.temp_avg_min_c == 12.0
    assert stats.wind_gust_p90_kmh == 70           # sorted gusts, index round(0.9*13)
    # 12 consecutive-day pairs (6 per year), 5 wet/dry flips, all in 2024
    assert stats.volatility_index == 42


def test_aggregate_week_no_matching_days_returns_none() -> None:
    assert aggregate_week(_ARCHIVE_PAYLOAD, iso_week=2) is None


def test_aggregate_week_empty_payload_returns_none() -> None:
    assert aggregate_week({}, iso_week=_WEEK) is None


# ── Endpoint (archive mocked, current ISO week generated dynamically) ─────────

def _stormy_current_week_payload() -> dict:
    """Every day this ISO week (last 2 years) is a wet thunderstorm day —
    guaranteed to cross the warning thresholds."""
    week = datetime.now(timezone.utc).date().isocalendar().week
    year = datetime.now(timezone.utc).date().year
    times = _week_dates(year - 2, week) + _week_dates(year - 1, week)
    n = len(times)
    return {
        "latitude": 45.5,
        "longitude": 25.3,
        "daily": {
            "time": times,
            "weather_code": [95] * n,
            "temperature_2m_max": [18.0] * n,
            "temperature_2m_min": [9.0] * n,
            "precipitation_sum": [12.0] * n,
            "wind_gusts_10m_max": [80.0] * n,
        },
    }


@session_loop
async def test_climatology_unstable_location(client: AsyncClient) -> None:
    with respx.mock:
        respx.get(ARCHIVE_URL).mock(
            return_value=Response(200, json=_stormy_current_week_payload())
        )
        resp = await client.get(CLIMATOLOGY_URL, params={"lat": 45.5, "lng": 25.3})

    assert resp.status_code == 200
    body = resp.json()
    assert body["thunderstorm_pct"] == 100
    assert body["precip_day_frequency_pct"] == 100
    assert body["wind_gust_p90_kmh"] == 80
    assert body["years_analyzed"] == 2
    assert body["unstable"] is True
    assert len(body["reasons"]) >= 3
    assert body["cached"] is False


@session_loop
async def test_climatology_second_call_hits_cache(client: AsyncClient) -> None:
    with respx.mock:
        route = respx.get(ARCHIVE_URL).mock(
            return_value=Response(200, json=_stormy_current_week_payload())
        )
        await client.get(CLIMATOLOGY_URL, params={"lat": 45.5, "lng": 25.3})
        resp2 = await client.get(CLIMATOLOGY_URL, params={"lat": 45.5, "lng": 25.3})

    assert resp2.status_code == 200
    assert resp2.json()["cached"] is True
    assert route.call_count == 1


@session_loop
async def test_climatology_no_data_returns_404(client: AsyncClient) -> None:
    empty = {"latitude": 0.0, "longitude": 0.0, "daily": {"time": []}}
    with respx.mock:
        respx.get(ARCHIVE_URL).mock(return_value=Response(200, json=empty))
        resp = await client.get(CLIMATOLOGY_URL, params={"lat": 0.0, "lng": 0.0})
    assert resp.status_code == 404


@session_loop
async def test_climatology_archive_error_returns_502(client: AsyncClient) -> None:
    with respx.mock:
        respx.get(ARCHIVE_URL).mock(return_value=Response(500, text="boom"))
        resp = await client.get(CLIMATOLOGY_URL, params={"lat": 45.5, "lng": 25.3})
    assert resp.status_code == 502


@session_loop
async def test_climatology_invalid_lat_returns_422(client: AsyncClient) -> None:
    resp = await client.get(CLIMATOLOGY_URL, params={"lat": 200, "lng": 25.3})
    assert resp.status_code == 422
