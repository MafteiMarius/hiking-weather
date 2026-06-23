from typing import Optional
from pydantic import BaseModel, Field


class ProfileRead(BaseModel):
    display_name: Optional[str] = None
    home_lat: Optional[float] = None
    home_lng: Optional[float] = None
    experience_level: int = 3
    max_distance_km: int = 150
    max_difficulty: int = 4
    units_metric: bool = True
    locale: str = "ro-RO"

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=80)
    home_lat: Optional[float] = None
    home_lng: Optional[float] = None
    experience_level: Optional[int] = Field(None, ge=1, le=5)
    max_distance_km: Optional[int] = Field(None, ge=1, le=5000)
    max_difficulty: Optional[int] = Field(None, ge=1, le=5)
    units_metric: Optional[bool] = None
    locale: Optional[str] = Field(None, max_length=8)
