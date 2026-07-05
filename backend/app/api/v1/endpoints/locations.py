"""Saved locations CRUD — auth-required.

PostGIS notes:
  - The column is Geography(POINT, 4326). geoalchemy2 accepts an EWKT string
    ("SRID=4326;POINT(lng lat)") on insert — no shapely dependency needed.
  - ST_X/ST_Y only operate on geometry, so reads cast the geography column.
    In WKT axis order, X is longitude and Y is latitude.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2 import Geometry
from sqlalchemy import cast, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.db.models import SavedLocation, User
from app.db.session import get_db
from app.schemas.location import LocationCreate, LocationRead

router = APIRouter(prefix="/locations", tags=["locations"])

# Enough for a personal list of favourite spots; keeps a hostile client from
# filling the table.
MAX_LOCATIONS_PER_USER = 100


@router.get("", response_model=list[LocationRead])
async def list_locations(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[LocationRead]:
    geom = cast(SavedLocation.location, Geometry)
    result = await session.execute(
        select(
            SavedLocation,
            func.ST_Y(geom).label("lat"),
            func.ST_X(geom).label("lng"),
        )
        .where(SavedLocation.user_id == user.id)
        .order_by(SavedLocation.created_at.desc())
    )
    return [
        LocationRead(
            id=row.SavedLocation.id,
            name=row.SavedLocation.name,
            lat=row.lat,
            lng=row.lng,
            elevation_m=row.SavedLocation.elevation_m,
            notes=row.SavedLocation.notes,
            created_at=row.SavedLocation.created_at,
        )
        for row in result.all()
    ]


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> LocationRead:
    count = await session.scalar(
        select(func.count())
        .select_from(SavedLocation)
        .where(SavedLocation.user_id == user.id)
    )
    if count is not None and count >= MAX_LOCATIONS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Limit of {MAX_LOCATIONS_PER_USER} saved locations reached",
        )

    loc = SavedLocation(
        user_id=user.id,
        name=body.name,
        location=f"SRID=4326;POINT({body.lng} {body.lat})",
        elevation_m=body.elevation_m,
        notes=body.notes,
    )
    session.add(loc)
    await session.commit()
    await session.refresh(loc)

    return LocationRead(
        id=loc.id,
        name=loc.name,
        lat=body.lat,
        lng=body.lng,
        elevation_m=loc.elevation_m,
        notes=loc.notes,
        created_at=loc.created_at,
    )


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    # Filtering by user_id makes deleting someone else's location a plain 404 —
    # no information leak about whether the id exists.
    result = await session.execute(
        delete(SavedLocation).where(
            SavedLocation.id == location_id,
            SavedLocation.user_id == user.id,
        )
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Location not found"
        )
