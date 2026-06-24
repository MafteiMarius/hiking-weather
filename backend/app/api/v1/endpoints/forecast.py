from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.db.session import get_db
from app.schemas.forecast import (
    DayForecast,
    ElevationResponse,
    ForecastResponse,
    GeocodeResponse,
    GeocodeResult,
)
from app.services.openmeteo import geocode, get_elevation, get_forecast
from app.services.scoring import WMO_DESCRIPTIONS, score_day

router = APIRouter(tags=["forecast"])


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Inject the shared AsyncClient from app.state (created in lifespan)."""
    return request.app.state.http  # type: ignore[no-any-return]


@router.get("/forecast", response_model=ForecastResponse)
async def forecast_endpoint(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    days: Annotated[int, Query(ge=1, le=7)] = 7,
    session: AsyncSession = Depends(get_db),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> ForecastResponse:
    try:
        payload, cached = await get_forecast(lat, lng, days, http, session)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Weather API error") from exc
    except (httpx.NetworkError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=504, detail="Weather API unreachable") from exc

    daily = payload["daily"]
    hourly = payload.get("hourly", {})
    hourly_cape: list[float] = [float(v or 0) for v in hourly.get("cape", [])]
    hourly_visibility: list[float] = [float(v or 0) for v in hourly.get("visibility", [])]
    elevation_m = float(payload.get("elevation") or 0)

    scored_days: list[DayForecast] = []

    for i, date in enumerate(daily["time"]):
        # CAPE window: hours 11:00-17:00 inclusive (7 entries per day starting at offset 11)
        cape_afternoon = hourly_cape[i * 24 + 11 : i * 24 + 18]

        # Visibility window: between sunrise and sunset
        sunrise_str = str(daily["sunrise"][i])  # "2026-06-24T05:32"
        sunset_str = str(daily["sunset"][i])
        sunrise_hour = int(sunrise_str[11:13]) if len(sunrise_str) >= 13 else 6
        sunset_hour = int(sunset_str[11:13]) if len(sunset_str) >= 13 else 21
        visibility_daylight = hourly_visibility[
            i * 24 + sunrise_hour : i * 24 + sunset_hour + 1
        ]

        code = int(daily["weather_code"][i])
        result = score_day(
            precipitation_sum_mm=float(daily["precipitation_sum"][i] or 0),
            precipitation_probability_max=int(daily["precipitation_probability_max"][i] or 0),
            wind_gusts_kmh=float(daily["wind_gusts_10m_max"][i] or 0),
            apparent_temp_min=float(daily["apparent_temperature_min"][i] or 0),
            elevation_m=elevation_m,
            uv_index_max=float(daily["uv_index_max"][i] or 0),
            cape_afternoon=cape_afternoon,
            visibility_daylight=visibility_daylight,
        )

        scored_days.append(
            DayForecast(
                date=date,
                weather_code=code,
                weather_description=WMO_DESCRIPTIONS.get(code, f"Code {code}"),
                temp_max_c=float(daily["temperature_2m_max"][i] or 0),
                temp_min_c=float(daily["temperature_2m_min"][i] or 0),
                apparent_temp_min_c=float(daily["apparent_temperature_min"][i] or 0),
                precipitation_sum_mm=float(daily["precipitation_sum"][i] or 0),
                precipitation_probability_max=int(daily["precipitation_probability_max"][i] or 0),
                wind_speed_max_kmh=float(daily["wind_speed_10m_max"][i] or 0),
                wind_gusts_max_kmh=float(daily["wind_gusts_10m_max"][i] or 0),
                uv_index_max=float(daily["uv_index_max"][i] or 0),
                sunrise=sunrise_str,
                sunset=sunset_str,
                score=result.score,
                verdict=result.verdict,
                reasons_en=[r.en for r in result.reasons],
                reasons_ro=[r.ro for r in result.reasons],
            )
        )

    return ForecastResponse(
        lat=float(payload["latitude"]),
        lng=float(payload["longitude"]),
        elevation_m=elevation_m,
        timezone=str(payload.get("timezone", "UTC")),
        days=scored_days,
        cached=cached,
    )


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode_endpoint(
    q: Annotated[str, Query(min_length=2, max_length=200)],
    http: httpx.AsyncClient = Depends(get_http_client),
) -> GeocodeResponse:
    try:
        data = await geocode(q, http)
    except (httpx.HTTPStatusError, httpx.NetworkError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=502, detail="Geocode API error") from exc

    results = [
        GeocodeResult(
            id=item["id"],
            name=item["name"],
            country=item.get("country", ""),
            country_code=item.get("country_code", ""),
            lat=float(item["latitude"]),
            lng=float(item["longitude"]),
            elevation_m=item.get("elevation"),
        )
        for item in data.get("results", [])
    ]
    return GeocodeResponse(results=results)


@router.get("/elevation", response_model=ElevationResponse)
async def elevation_endpoint(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    http: httpx.AsyncClient = Depends(get_http_client),
) -> ElevationResponse:
    try:
        elev = await get_elevation(lat, lng, http)
    except (httpx.HTTPStatusError, httpx.NetworkError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=502, detail="Elevation API error") from exc

    return ElevationResponse(lat=lat, lng=lng, elevation_m=elev)
