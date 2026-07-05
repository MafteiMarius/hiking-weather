from typing import Optional

from pydantic import BaseModel


class ClimatologyResponse(BaseModel):
    lat: float
    lng: float
    iso_week: int
    years_analyzed: int
    precip_day_frequency_pct: Optional[int]  # % of days with >= 1 mm rain
    thunderstorm_pct: Optional[int]          # % of days with WMO 95/96/99
    temp_avg_max_c: Optional[float]
    temp_avg_min_c: Optional[float]
    wind_gust_p90_kmh: Optional[int]         # 90th percentile daily max gust
    volatility_index: Optional[int]          # % of day-to-day wet/dry flips
    unstable: bool                           # any warning threshold crossed
    reasons: list[str]                       # human-readable, empty when stable
    cached: bool
