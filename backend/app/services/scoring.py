"""Hiking safety score: 0-100 per forecast day.

WHY these numbers:
  - Thunderstorm: -55 base because lightning on exposed Carpathian ridges is
    the top cause of mountaineering fatalities; no other factor comes close.
  - Wind gusts > 90 km/h: -60 because at that speed a person can be knocked
    off a narrow ridge. We deliberately make this larger than the thunderstorm
    penalty so the total score collapses to Dangerous.
  - Fog: -30 because navigation failure is a real emergency above treeline.
  - Heavy rain / snow: -40 because hypothermia + slippery rocks combine.
  - Temperature thresholds are alpine, not lowland — 0°C at summit elevation
    is very different from 0°C at sea level.
"""

from dataclasses import dataclass

# WMO Weather Code descriptions (used in API responses and score reasons)
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

# WMO code → (penalty, reason). Unlisted codes (0-3) carry no penalty.
_WMO_PENALTIES: dict[int, tuple[int, str]] = {
    45: (30, "Fog — navigation risk on ridges"),
    48: (35, "Icy fog — visibility and ice hazard"),
    51: (8, "Light drizzle"),
    53: (12, "Drizzle"),
    55: (18, "Dense drizzle"),
    61: (20, "Rain expected"),
    63: (28, "Moderate rain"),
    65: (40, "Heavy rain — hypothermia risk"),
    71: (10, "Light snow"),
    73: (25, "Snow — slippery terrain"),
    75: (40, "Heavy snow — trail may be impassable"),
    77: (10, "Snow grains"),
    80: (20, "Rain showers"),
    81: (30, "Heavy rain showers"),
    82: (45, "Violent rain showers"),
    85: (25, "Snow showers"),
    86: (40, "Heavy snow showers"),
    95: (55, "Thunderstorm — stay off exposed ridges"),
    96: (60, "Thunderstorm with hail"),
    99: (65, "Thunderstorm with heavy hail"),
}

_SCORE_LABEL_THRESHOLDS = [
    (85, "Excellent"),
    (70, "Good"),
    (50, "Fair"),
    (30, "Poor"),
    (0, "Dangerous"),
]


@dataclass(frozen=True)
class ScoreResult:
    score: int        # 0-100
    label: str        # "Excellent" … "Dangerous"
    reason: str       # human-readable primary concern


def _wmo_penalty(code: int) -> tuple[int, str]:
    return _WMO_PENALTIES.get(code, (0, ""))


def _wind_penalty(gusts_kmh: float) -> tuple[int, str]:
    if gusts_kmh > 90:
        return 60, f"Dangerous gusts ({gusts_kmh:.0f} km/h) — do not summit"
    if gusts_kmh > 60:
        return 40, f"Very strong gusts ({gusts_kmh:.0f} km/h)"
    if gusts_kmh > 45:
        return 25, f"Strong gusts ({gusts_kmh:.0f} km/h)"
    if gusts_kmh > 30:
        return 10, f"Moderate gusts ({gusts_kmh:.0f} km/h)"
    return 0, ""


def _precip_penalty(mm: float) -> tuple[int, str]:
    if mm > 20:
        return 25, f"Heavy rainfall ({mm:.1f} mm)"
    if mm > 10:
        return 15, f"Significant rainfall ({mm:.1f} mm)"
    if mm > 5:
        return 8, f"Moderate rainfall ({mm:.1f} mm)"
    if mm > 1:
        return 3, f"Light rainfall ({mm:.1f} mm)"
    return 0, ""


def _temp_penalty(temp_min: float, temp_max: float) -> tuple[int, str]:
    if temp_min < -15:
        return 30, f"Extreme cold ({temp_min:.0f}°C) — frostbite risk"
    if temp_min < -5:
        return 15, f"Very cold ({temp_min:.0f}°C)"
    if temp_min < 0:
        return 5, f"Below freezing ({temp_min:.0f}°C)"
    if temp_max > 38:
        return 25, f"Extreme heat ({temp_max:.0f}°C) — heat stroke risk"
    if temp_max > 32:
        return 10, f"Very hot ({temp_max:.0f}°C) — carry extra water"
    return 0, ""


def score_day(
    weather_code: int,
    temp_max: float,
    temp_min: float,
    precip_mm: float,
    wind_gusts_kmh: float,
) -> ScoreResult:
    """Score one forecast day. Pure function — no I/O."""
    penalties: list[tuple[int, str]] = []

    for fn_result in [
        _wmo_penalty(weather_code),
        _wind_penalty(wind_gusts_kmh),
        _precip_penalty(precip_mm),
        _temp_penalty(temp_min, temp_max),
    ]:
        p, r = fn_result
        if p:
            penalties.append((p, r))

    # Sort descending so the worst factor is first
    penalties.sort(key=lambda x: x[0], reverse=True)

    total_penalty = sum(p for p, _ in penalties)
    score = max(0, min(100, 100 - total_penalty))

    label = next(lbl for threshold, lbl in _SCORE_LABEL_THRESHOLDS if score >= threshold)
    reason = penalties[0][1] if penalties else "Conditions look good for hiking"

    return ScoreResult(score=score, label=label, reason=reason)
