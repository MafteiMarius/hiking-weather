"""Historical instability endpoint.

Threshold rationale (all tuned for "would this change my plan?"):
  - thunderstorms on >= 20% of days: 1-in-5 odds of the single deadliest
    mountain hazard is worth a warning even under a clear forecast.
  - wet days >= 50%: rain more often than not — pack accordingly.
  - p90 gust >= 70 km/h: the top decile of days is already in scoring's
    "very strong" band.
  - volatility >= 40%: weather flips wet/dry nearly every other day, so a
    one-day-old forecast ages badly here.
"""
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.forecast import get_http_client
from app.db.models import Climatology
from app.db.session import get_db
from app.schemas.climatology import ClimatologyResponse
from app.services.climatology import get_climatology

router = APIRouter(tags=["climatology"])

THUNDER_WARN_PCT = 20
WET_WARN_PCT = 50
GUST_WARN_KMH = 70
VOLATILITY_WARN_PCT = 40


def instability_reasons(row: Climatology) -> list[str]:
    reasons: list[str] = []
    years = row.years_analyzed
    if row.thunderstorm_pct is not None and row.thunderstorm_pct >= THUNDER_WARN_PCT:
        reasons.append(
            f"Thunderstorms on {row.thunderstorm_pct}% of these days "
            f"over the last {years} years"
        )
    if (
        row.precip_day_frequency_pct is not None
        and row.precip_day_frequency_pct >= WET_WARN_PCT
    ):
        reasons.append(
            f"Rain on {row.precip_day_frequency_pct}% of these days historically"
        )
    if row.wind_gust_p90_kmh is not None and row.wind_gust_p90_kmh >= GUST_WARN_KMH:
        reasons.append(
            f"Top-decile gusts reach {row.wind_gust_p90_kmh} km/h this week of the year"
        )
    if row.volatility_index is not None and row.volatility_index >= VOLATILITY_WARN_PCT:
        reasons.append(
            "Conditions flip between wet and dry "
            f"{row.volatility_index}% of day-to-day transitions — forecasts age fast here"
        )
    return reasons


@router.get("/climatology", response_model=ClimatologyResponse)
async def climatology_endpoint(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    session: AsyncSession = Depends(get_db),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> ClimatologyResponse:
    try:
        row, cached = await get_climatology(lat, lng, http, session)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Archive API error") from exc
    except (httpx.NetworkError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=504, detail="Archive API unreachable") from exc

    if row is None:
        raise HTTPException(
            status_code=404, detail="No archive data for this location"
        )

    reasons = instability_reasons(row)
    return ClimatologyResponse(
        lat=lat,
        lng=lng,
        iso_week=row.iso_week,
        years_analyzed=row.years_analyzed,
        precip_day_frequency_pct=row.precip_day_frequency_pct,
        thunderstorm_pct=row.thunderstorm_pct,
        temp_avg_max_c=float(row.temp_avg_max_c) if row.temp_avg_max_c is not None else None,
        temp_avg_min_c=float(row.temp_avg_min_c) if row.temp_avg_min_c is not None else None,
        wind_gust_p90_kmh=row.wind_gust_p90_kmh,
        volatility_index=row.volatility_index,
        unstable=bool(reasons),
        reasons=reasons,
        cached=cached,
    )
