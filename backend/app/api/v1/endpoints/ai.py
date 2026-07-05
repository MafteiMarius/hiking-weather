"""AI endpoints — auth-required, optional (503 when no API key configured).

Auth-gating matters here: each call costs real money on the Anthropic API,
so anonymous visitors can't trigger it.
"""
from typing import Annotated

import anthropic
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.climatology import instability_reasons
from app.api.v1.endpoints.forecast import get_http_client
from app.core.auth import current_active_user
from app.db.models import User
from app.db.session import get_db
from app.services import ai
from app.services.climatology import get_climatology
from app.services.openmeteo import get_forecast
from app.services.scoring import WMO_DESCRIPTIONS, score_day

router = APIRouter(prefix="/ai", tags=["ai"])


class EquipmentRequest(BaseModel):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lng: Annotated[float, Field(ge=-180, le=180)]
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]


class EquipmentResponse(ai.EquipmentPlan):
    date: str


@router.post("/equipment", response_model=EquipmentResponse)
async def equipment_endpoint(
    body: EquipmentRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> EquipmentResponse:
    if not ai.is_configured():
        raise HTTPException(status_code=503, detail="AI features are not configured")

    # Forecast context (usually a cache hit — the user is looking at this spot)
    try:
        payload, _ = await get_forecast(body.lat, body.lng, 7, http, session)
    except (httpx.HTTPStatusError, httpx.NetworkError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=502, detail="Weather API error") from exc

    daily = payload["daily"]
    if body.date not in daily["time"]:
        raise HTTPException(status_code=404, detail="Date not in the forecast window")
    i = daily["time"].index(body.date)

    code = int(daily["weather_code"][i])
    temp_max = float(daily["temperature_2m_max"][i] or 0)
    temp_min = float(daily["temperature_2m_min"][i] or 0)
    precip = float(daily["precipitation_sum"][i] or 0)
    gusts = float(daily["wind_gusts_10m_max"][i] or 0)
    result = score_day(code, temp_max, temp_min, precip, gusts)
    day = {
        "weather_code": code,
        "weather_description": WMO_DESCRIPTIONS.get(code, f"Code {code}"),
        "temp_max_c": temp_max,
        "temp_min_c": temp_min,
        "precipitation_sum_mm": precip,
        "precipitation_probability_max": int(daily["precipitation_probability_max"][i] or 0),
        "wind_gusts_max_kmh": gusts,
        "score": result.score,
        "score_label": result.label,
        "score_reason": result.reason,
    }

    hourly = payload.get("hourly") or {}
    hours = [
        {
            "time": t,
            "temp_c": float(hourly["temperature_2m"][j] or 0),
            "precipitation_mm": float(hourly["precipitation"][j] or 0),
            "wind_gusts_kmh": float(hourly["wind_gusts_10m"][j] or 0),
        }
        for j, t in enumerate(hourly.get("time", []))
        if t.startswith(body.date)
    ]

    # Climatology is context, not a requirement — ignore archive failures
    reasons: list[str] = []
    try:
        row, _ = await get_climatology(body.lat, body.lng, http, session)
        if row is not None:
            reasons = instability_reasons(row)
    except Exception:  # noqa: BLE001 — never block the AI call on missing context
        reasons = []

    try:
        plan = await ai.recommend_equipment(
            date=body.date,
            elevation_m=float(payload.get("elevation") or 0),
            day=day,
            hours=hours,
            climatology_reasons=reasons,
        )
    except anthropic.APIStatusError as exc:
        raise HTTPException(status_code=502, detail="AI service error") from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(status_code=504, detail="AI service unreachable") from exc

    return EquipmentResponse(date=body.date, **plan.model_dump())
