"""Forecast, geocode, and elevation endpoint tests.

Uses respx to mock outbound HTTP calls so tests run offline and fast.
The `client` fixture (from conftest.py) already attaches a real
httpx.AsyncClient to app.state.http; respx intercepts at the transport
level so no special setup is needed beyond `with respx.mock:`.
"""

import pytest
import respx
from httpx import AsyncClient, Response

pytestmark = pytest.mark.asyncio(loop_scope="session")

FORECAST_URL = "/api/v1/forecast"
GEOCODE_URL = "/api/v1/geocode"
ELEVATION_URL = "/api/v1/elevation"

# Minimal but valid Open-Meteo /forecast response for 1 day
_OM_CLEAR_DAY = {
    "latitude": 45.5,
    "longitude": 25.3,
    "elevation": 1234.0,
    "timezone": "Europe/Bucharest",
    "daily_units": {},
    "daily": {
        "time": ["2026-06-23"],
        "weather_code": [0],
        "temperature_2m_max": [20.0],
        "temperature_2m_min": [10.0],
        "precipitation_sum": [0.0],
        "precipitation_probability_max": [0],
        "wind_speed_10m_max": [15.0],
        "wind_gusts_10m_max": [25.0],
    },
}

# Bad weather day: thunderstorm + strong gusts
_OM_STORM_DAY = {
    **_OM_CLEAR_DAY,
    "daily": {
        "time": ["2026-06-23"],
        "weather_code": [95],
        "temperature_2m_max": [18.0],
        "temperature_2m_min": [12.0],
        "precipitation_sum": [15.0],
        "precipitation_probability_max": [90],
        "wind_speed_10m_max": [55.0],
        "wind_gusts_10m_max": [75.0],
    },
}

_GEOCODE_RESPONSE = {
    "results": [
        {
            "id": 1234,
            "name": "Bucegi",
            "country": "Romania",
            "country_code": "RO",
            "latitude": 45.4,
            "longitude": 25.4,
            "elevation": 2505.0,
        }
    ]
}


# ── Forecast endpoint ─────────────────────────────────────────────────────────

async def test_forecast_clear_day_scores_100(client: AsyncClient) -> None:
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=_OM_CLEAR_DAY)
        )
        resp = await client.get(FORECAST_URL, params={"lat": 45.5, "lng": 25.3, "days": 1})

    assert resp.status_code == 200
    body = resp.json()
    assert body["elevation_m"] == 1234.0
    assert body["timezone"] == "Europe/Bucharest"
    assert len(body["days"]) == 1

    day = body["days"][0]
    assert day["date"] == "2026-06-23"
    assert day["weather_code"] == 0
    assert day["weather_description"] == "Clear sky"
    assert day["score"] == 100
    assert day["score_label"] == "Excellent"
    assert body["cached"] is False


async def test_forecast_storm_day_is_dangerous(client: AsyncClient) -> None:
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=_OM_STORM_DAY)
        )
        resp = await client.get(FORECAST_URL, params={"lat": 45.5, "lng": 25.3, "days": 1})

    assert resp.status_code == 200
    day = resp.json()["days"][0]
    assert day["score"] == 0
    assert day["score_label"] == "Dangerous"


async def test_forecast_cache_hit_skips_http(client: AsyncClient) -> None:
    """Second request for same lat/lng must hit cache — respx will error if
    a second real HTTP call is made without a registered route."""
    with respx.mock:
        route = respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=_OM_CLEAR_DAY)
        )
        # First call — cache miss, HTTP fetch
        await client.get(FORECAST_URL, params={"lat": 45.5, "lng": 25.3, "days": 1})
        # Second call — should hit cache, no HTTP
        resp2 = await client.get(FORECAST_URL, params={"lat": 45.5, "lng": 25.3, "days": 1})

    assert resp2.status_code == 200
    assert resp2.json()["cached"] is True
    assert route.call_count == 1  # only one real HTTP call


async def test_forecast_invalid_lat_returns_422(client: AsyncClient) -> None:
    resp = await client.get(FORECAST_URL, params={"lat": 200, "lng": 25.3})
    assert resp.status_code == 422


async def test_forecast_missing_params_returns_422(client: AsyncClient) -> None:
    resp = await client.get(FORECAST_URL, params={"lat": 45.5})
    assert resp.status_code == 422


async def test_forecast_api_error_returns_502(client: AsyncClient) -> None:
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(500, text="Internal Server Error")
        )
        resp = await client.get(FORECAST_URL, params={"lat": 45.5, "lng": 25.3})
    assert resp.status_code == 502


# ── Geocode endpoint ──────────────────────────────────────────────────────────

async def test_geocode_returns_results(client: AsyncClient) -> None:
    with respx.mock:
        respx.get("https://geocoding-api.open-meteo.com/v1/search").mock(
            return_value=Response(200, json=_GEOCODE_RESPONSE)
        )
        resp = await client.get(GEOCODE_URL, params={"q": "Bucegi"})

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["name"] == "Bucegi"
    assert results[0]["country_code"] == "RO"
    assert results[0]["elevation_m"] == 2505.0


async def test_geocode_empty_query_returns_422(client: AsyncClient) -> None:
    resp = await client.get(GEOCODE_URL, params={"q": "x"})  # min_length=2
    assert resp.status_code == 422


async def test_geocode_no_results(client: AsyncClient) -> None:
    with respx.mock:
        respx.get("https://geocoding-api.open-meteo.com/v1/search").mock(
            return_value=Response(200, json={"results": []})
        )
        resp = await client.get(GEOCODE_URL, params={"q": "xyznonexistent"})

    assert resp.status_code == 200
    assert resp.json()["results"] == []


# ── Elevation endpoint ────────────────────────────────────────────────────────

async def test_elevation_returns_value(client: AsyncClient) -> None:
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=_OM_CLEAR_DAY)
        )
        resp = await client.get(ELEVATION_URL, params={"lat": 45.5, "lng": 25.3})

    assert resp.status_code == 200
    body = resp.json()
    assert body["elevation_m"] == 1234.0
    assert body["lat"] == 45.5
    assert body["lng"] == 25.3


async def test_elevation_invalid_coords_returns_422(client: AsyncClient) -> None:
    resp = await client.get(ELEVATION_URL, params={"lat": 45.5, "lng": 200})
    assert resp.status_code == 422
