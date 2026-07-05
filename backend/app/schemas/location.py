import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    elevation_m: Optional[int] = Field(default=None, ge=-500, le=9000)
    notes: Optional[str] = Field(default=None, max_length=2000)


class LocationRead(BaseModel):
    id: uuid.UUID
    name: str
    lat: float
    lng: float
    elevation_m: Optional[int]
    notes: Optional[str]
    created_at: datetime
