from typing import Optional

from pydantic import BaseModel


class DayForecast(BaseModel):
    date: str                           # "2026-06-23"
    weather_code: int
    weather_description: str
    temp_max_c: float
    temp_min_c: float
    precipitation_sum_mm: float
    precipitation_probability_max: int  # 0-100 %
    wind_speed_max_kmh: float
    wind_gusts_max_kmh: float
    score: int                          # 0-100
    score_label: str                    # "Excellent" … "Dangerous"
    score_reason: str


class HourForecast(BaseModel):
    time: str                           # "2026-06-23T14:00" (location-local)
    temp_c: float
    precipitation_mm: float
    precipitation_probability: int      # 0-100 %
    wind_gusts_kmh: float
    weather_code: int


class ForecastResponse(BaseModel):
    lat: float
    lng: float
    elevation_m: float
    timezone: str
    days: list[DayForecast]
    # Empty when serving a cached payload fetched before hourly support existed
    # (those entries age out within the 30-minute TTL).
    hours: list[HourForecast] = []
    cached: bool                        # True when served from forecast_cache table


class GeocodeResult(BaseModel):
    id: int
    name: str
    country: str
    country_code: str
    lat: float
    lng: float
    elevation_m: Optional[float] = None


class GeocodeResponse(BaseModel):
    results: list[GeocodeResult]


class ElevationResponse(BaseModel):
    lat: float
    lng: float
    elevation_m: float
