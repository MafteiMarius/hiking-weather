"""Trail catalogue — public, read-only.

Same PostGIS pattern as saved locations: geography columns are cast to
geometry for ST_X/ST_Y extraction (X = lng, Y = lat).
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Trail
from app.db.session import get_db
from app.schemas.trail import TrailRead

router = APIRouter(prefix="/trails", tags=["trails"])


def _row_to_read(row) -> TrailRead:
    t: Trail = row.Trail
    return TrailRead(
        id=t.id,
        slug=t.slug,
        name=t.name,
        region=t.region,
        difficulty=t.difficulty,
        duration_minutes=t.duration_minutes,
        distance_m=t.distance_m,
        elevation_gain_m=t.elevation_gain_m,
        start_lat=row.start_lat,
        start_lng=row.start_lng,
        summit_lat=row.summit_lat,
        summit_lng=row.summit_lng,
        summit_elev_m=t.summit_elev_m,
        description=t.description,
    )


def _base_query():
    start_geom = cast(Trail.start_point, Geometry)
    summit_geom = cast(Trail.summit_point, Geometry)
    return select(
        Trail,
        func.ST_Y(start_geom).label("start_lat"),
        func.ST_X(start_geom).label("start_lng"),
        func.ST_Y(summit_geom).label("summit_lat"),
        func.ST_X(summit_geom).label("summit_lng"),
    )


@router.get("", response_model=list[TrailRead])
async def list_trails(
    region: Annotated[Optional[str], Query(max_length=80)] = None,
    max_difficulty: Annotated[Optional[int], Query(ge=1, le=5)] = None,
    session: AsyncSession = Depends(get_db),
) -> list[TrailRead]:
    query = _base_query().order_by(Trail.region, Trail.difficulty, Trail.name)
    if region is not None:
        query = query.where(Trail.region == region)
    if max_difficulty is not None:
        query = query.where(Trail.difficulty <= max_difficulty)

    result = await session.execute(query)
    return [_row_to_read(row) for row in result.all()]


@router.get("/{slug}", response_model=TrailRead)
async def get_trail(
    slug: str,
    session: AsyncSession = Depends(get_db),
) -> TrailRead:
    result = await session.execute(_base_query().where(Trail.slug == slug))
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Trail not found")
    return _row_to_read(row)
