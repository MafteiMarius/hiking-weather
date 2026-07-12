"""Personalised trail recommendations — auth-required.

Flow: load the user's profile (defaults when none saved yet) → load the
trail catalogue → ONE bulk Open-Meteo call for every trail's forecast
point (summit when present, else trailhead) → score each trail's day with
the same score_day() the map uses → pure rank_trails() applies the
personal filters/penalties.

Auth-gating is a product choice, not a cost one (unlike /ai): the ranking
is only meaningful relative to a profile, and it nudges demo users to
sign in and set one.
"""
from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.forecast import get_http_client
from app.api.v1.endpoints.trails import _base_query, _row_to_read
from app.core.auth import current_active_user
from app.db.models import User, UserProfile
from app.db.session import get_db
from app.schemas.recommend import RecommendationItem, RecommendationResponse
from app.services.openmeteo import get_forecasts_bulk
from app.services.recommend import TrailDay, rank_trails
from app.services.scoring import WMO_DESCRIPTIONS, score_day

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Fallbacks for users who never opened the profile page — mirror the
# UserProfile column defaults.
_DEFAULT_EXPERIENCE = 3
_DEFAULT_MAX_DIFFICULTY = 4
_DEFAULT_MAX_DISTANCE_KM = 150


@router.get("", response_model=RecommendationResponse)
async def recommendations_endpoint(
    date: Annotated[Optional[str], Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> RecommendationResponse:
    profile = (
        await session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    experience = profile.experience_level if profile else _DEFAULT_EXPERIENCE
    max_difficulty = profile.max_difficulty if profile else _DEFAULT_MAX_DIFFICULTY
    max_distance = profile.max_distance_km if profile else _DEFAULT_MAX_DISTANCE_KM
    home = (
        (profile.home_lat, profile.home_lng)
        if profile and profile.home_lat is not None and profile.home_lng is not None
        else None
    )

    rows = (await session.execute(_base_query())).all()
    if not rows:
        return RecommendationResponse(date=date or "", items=[], excluded=0)
    trails = [_row_to_read(row) for row in rows]

    # Conditions at the summit decide the day; trailhead as fallback.
    points = [
        (t.summit_lat, t.summit_lng) if t.summit_lat is not None else (t.start_lat, t.start_lng)
        for t in trails
    ]
    try:
        payloads = await get_forecasts_bulk(points, 7, http, session)
    except (httpx.HTTPStatusError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Weather API error") from exc
    except (httpx.NetworkError, httpx.TimeoutException) as exc:
        raise HTTPException(status_code=504, detail="Weather API unreachable") from exc

    if date is None:
        date = payloads[0]["daily"]["time"][0]

    candidates: list[TrailDay] = []
    day_facts: dict[str, dict] = {}
    for trail, payload in zip(trails, payloads):
        daily = payload["daily"]
        if date not in daily["time"]:
            raise HTTPException(status_code=404, detail="Date not in the forecast window")
        i = daily["time"].index(date)

        code = int(daily["weather_code"][i])
        temp_max = float(daily["temperature_2m_max"][i] or 0)
        temp_min = float(daily["temperature_2m_min"][i] or 0)
        precip = float(daily["precipitation_sum"][i] or 0)
        gusts = float(daily["wind_gusts_10m_max"][i] or 0)
        result = score_day(code, temp_max, temp_min, precip, gusts)

        candidates.append(TrailDay(
            slug=trail.slug,
            difficulty=trail.difficulty,
            start_lat=trail.start_lat,
            start_lng=trail.start_lng,
            weather_score=result.score,
        ))
        day_facts[trail.slug] = {
            "label": result.label,
            "reason": result.reason,
            "description": WMO_DESCRIPTIONS.get(code, f"Code {code}"),
            "temp_max_c": temp_max,
            "temp_min_c": temp_min,
            "precipitation_sum_mm": precip,
            "wind_gusts_max_kmh": gusts,
        }

    ranked = rank_trails(
        candidates,
        experience_level=experience,
        max_difficulty=max_difficulty,
        home=home,
        max_distance_km=max_distance,
    )

    by_slug = {t.slug: t for t in trails}
    items = [
        RecommendationItem(
            trail=by_slug[r.slug],
            rank_score=r.rank_score,
            weather_score=r.weather_score,
            weather_label=day_facts[r.slug]["label"],
            weather_description=day_facts[r.slug]["description"],
            weather_reason=day_facts[r.slug]["reason"],
            temp_max_c=day_facts[r.slug]["temp_max_c"],
            temp_min_c=day_facts[r.slug]["temp_min_c"],
            precipitation_sum_mm=day_facts[r.slug]["precipitation_sum_mm"],
            wind_gusts_max_kmh=day_facts[r.slug]["wind_gusts_max_kmh"],
            difficulty_penalty=r.difficulty_penalty,
            distance_penalty=r.distance_penalty,
            distance_from_home_km=r.distance_from_home_km,
        )
        for r in ranked[:limit]
    ]
    return RecommendationResponse(date=date, items=items, excluded=len(trails) - len(ranked))
