from typing import Optional

from pydantic import BaseModel


class DayForecast(BaseModel):
    date: str                           # "2026-06-24"
    weather_code: int
    weather_description: str
    temp_max_c: float
    temp_min_c: float
    apparent_temp_min_c: float
    precipitation_sum_mm: float
    precipitation_probability_max: int  # 0-100 %
    wind_speed_max_kmh: float
    wind_gusts_max_kmh: float
    uv_index_max: float
    sunrise: str                        # "2026-06-24T05:32"
    sunset: str                         # "2026-06-24T21:15"
    score: int                          # 0-100
    verdict: str                        # "go" | "caution" | "no_go"
    reasons_en: list[str]               # up to 3, largest-penalty first
    reasons_ro: list[str]               # up to 3, same order as reasons_en


class ForecastResponse(BaseModel):
    lat: float
    lng: float
    elevation_m: float
    timezone: str
    days: list[DayForecast]
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
