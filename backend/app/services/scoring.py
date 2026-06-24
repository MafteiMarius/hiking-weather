"""Hiking safety score: 0-100 per forecast day.

Penalties per FEATURE_SPEC:
  precip_penalty       max 35
  wind_penalty         max 25
  thunderstorm_penalty max 25  (CAPE-based, 11:00-18:00 window)
  cold_penalty         max 15  (apparent temperature)
  visibility_penalty   max 10
  uv_penalty           max  5
"""

from dataclasses import dataclass

WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Heavy rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


@dataclass(frozen=True)
class Reason:
    en: str
    ro: str


@dataclass
class ScoreResult:
    score: int             # 0-100
    verdict: str           # "go" | "caution" | "no_go"
    reasons: list[Reason]  # up to 3, largest-penalty first


def _precip_penalty(precip_sum_mm: float, precip_prob_max: int) -> tuple[int, Reason | None]:
    if precip_sum_mm > 20:
        return 35, Reason(
            en=f"Heavy precipitation ({precip_sum_mm:.0f} mm expected)",
            ro=f"Precipitații abundente ({precip_sum_mm:.0f} mm preconizate)",
        )
    if precip_sum_mm > 10:
        return 20, Reason(
            en=f"Significant precipitation ({precip_sum_mm:.0f} mm expected)",
            ro=f"Precipitații semnificative ({precip_sum_mm:.0f} mm preconizate)",
        )
    if precip_sum_mm > 2:
        p = 10 if precip_prob_max > 70 else 5
        return p, Reason(
            en=f"Light precipitation likely ({precip_prob_max}% chance, {precip_sum_mm:.1f} mm)",
            ro=f"Precipitații ușoare posibile ({precip_prob_max}% probabilitate, {precip_sum_mm:.1f} mm)",
        )
    return 0, None


def _wind_penalty(wind_gusts_kmh: float) -> tuple[int, Reason | None]:
    if wind_gusts_kmh > 70:
        return 25, Reason(
            en=f"Wind gusts up to {wind_gusts_kmh:.0f} km/h on ridge",
            ro=f"Rafale de vânt până la {wind_gusts_kmh:.0f} km/h pe creastă",
        )
    if wind_gusts_kmh > 50:
        return 15, Reason(
            en=f"Strong wind gusts ({wind_gusts_kmh:.0f} km/h)",
            ro=f"Rafale puternice de vânt ({wind_gusts_kmh:.0f} km/h)",
        )
    if wind_gusts_kmh > 35:
        return 5, Reason(
            en=f"Moderate wind gusts ({wind_gusts_kmh:.0f} km/h)",
            ro=f"Rafale moderate de vânt ({wind_gusts_kmh:.0f} km/h)",
        )
    return 0, None


def _thunderstorm_penalty(cape_afternoon: list[float]) -> tuple[int, Reason | None]:
    """Penalty from max CAPE between 11:00 and 18:00 local time."""
    if not cape_afternoon:
        return 0, None
    max_cape = max(cape_afternoon)
    if max_cape > 1000:
        return 25, Reason(
            en=f"Afternoon thunderstorm risk (CAPE {max_cape:.0f} J/kg)",
            ro=f"Risc de furtună după-amiază (CAPE {max_cape:.0f} J/kg)",
        )
    if max_cape > 500:
        return 10, Reason(
            en=f"Possible afternoon convection (CAPE {max_cape:.0f} J/kg)",
            ro=f"Posibilă convecție după-amiază (CAPE {max_cape:.0f} J/kg)",
        )
    return 0, None


def _cold_penalty(apparent_temp_min: float, elevation_m: float) -> tuple[int, Reason | None]:
    if apparent_temp_min < -5:
        return 15, Reason(
            en=f"Very cold — feels like {apparent_temp_min:.0f}°C (frostbite risk)",
            ro=f"Foarte frig — se simte ca {apparent_temp_min:.0f}°C (risc de degerături)",
        )
    if apparent_temp_min < 0 and elevation_m > 1800:
        return 8, Reason(
            en=f"Freezing level below summit ({apparent_temp_min:.0f}°C apparent at {elevation_m:.0f} m)",
            ro=f"Nivelul de îngheț sub vârf ({apparent_temp_min:.0f}°C aparent la {elevation_m:.0f} m)",
        )
    return 0, None


def _visibility_penalty(visibility_daylight: list[float]) -> tuple[int, Reason | None]:
    """Penalty from minimum visibility between sunrise and sunset."""
    if not visibility_daylight:
        return 0, None
    min_vis = min(visibility_daylight)
    if min_vis < 1000:
        return 10, Reason(
            en=f"Very poor visibility ({min_vis:.0f} m) — navigation hazard",
            ro=f"Vizibilitate foarte redusă ({min_vis:.0f} m) — risc de navigare",
        )
    if min_vis < 5000:
        return 5, Reason(
            en=f"Reduced visibility ({min_vis / 1000:.1f} km) during daylight hours",
            ro=f"Vizibilitate redusă ({min_vis / 1000:.1f} km) în timpul zilei",
        )
    return 0, None


def _uv_penalty(uv_index_max: float) -> tuple[int, Reason | None]:
    if uv_index_max >= 9:
        return 5, Reason(
            en=f"Extreme UV index ({uv_index_max:.0f}) — sunscreen essential above treeline",
            ro=f"Indice UV extrem ({uv_index_max:.0f}) — protecție solară obligatorie",
        )
    return 0, None


def _verdict(score: int) -> str:
    if score >= 70:
        return "go"
    if score >= 40:
        return "caution"
    return "no_go"


def score_day(
    precipitation_sum_mm: float,
    precipitation_probability_max: int,
    wind_gusts_kmh: float,
    apparent_temp_min: float,
    elevation_m: float,
    uv_index_max: float,
    cape_afternoon: list[float],
    visibility_daylight: list[float],
) -> ScoreResult:
    """Score one forecast day. Pure function — no I/O.

    cape_afternoon: CAPE values (J/kg) for hours 11:00-18:00 local time.
    visibility_daylight: visibility values (m) between sunrise and sunset.
    """
    penalties: list[tuple[int, Reason]] = []

    for penalty, reason in [
        _precip_penalty(precipitation_sum_mm, precipitation_probability_max),
        _wind_penalty(wind_gusts_kmh),
        _thunderstorm_penalty(cape_afternoon),
        _cold_penalty(apparent_temp_min, elevation_m),
        _visibility_penalty(visibility_daylight),
        _uv_penalty(uv_index_max),
    ]:
        if penalty > 0 and reason is not None:
            penalties.append((penalty, reason))

    penalties.sort(key=lambda x: x[0], reverse=True)

    total_penalty = sum(p for p, _ in penalties)
    score = max(0, min(100, 100 - total_penalty))

    return ScoreResult(
        score=score,
        verdict=_verdict(score),
        reasons=[r for _, r in penalties[:3]],
    )
