from typing import Optional

from pydantic import BaseModel

from app.schemas.trail import TrailRead


class RecommendationItem(BaseModel):
    trail: TrailRead
    rank_score: int                      # weather score minus personal penalties
    weather_score: int                   # 0-100 safety score at the trail
    weather_label: str                   # Excellent … Dangerous
    weather_description: str             # e.g. "Rain showers"
    weather_reason: str                  # dominant penalty from scoring.py
    temp_max_c: float
    temp_min_c: float
    precipitation_sum_mm: float
    wind_gusts_max_kmh: float
    difficulty_penalty: int              # 8/level above experience_level
    distance_penalty: int                # 0-10, linear to max_distance_km
    distance_from_home_km: Optional[float]  # None when no home location set


class RecommendationResponse(BaseModel):
    date: str
    items: list[RecommendationItem]
    excluded: int  # trails filtered out by max_difficulty / max_distance_km
