import uuid
from typing import Optional

from pydantic import BaseModel


class TrailRead(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    region: str
    difficulty: int              # 1 walk … 5 exposed/very hard
    duration_minutes: int
    distance_m: int
    elevation_gain_m: int
    start_lat: float
    start_lng: float
    summit_lat: Optional[float]
    summit_lng: Optional[float]
    summit_elev_m: Optional[int]
    description: Optional[str]
