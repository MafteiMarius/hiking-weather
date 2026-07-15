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

i18n note: this module owns the *logic* (which factor wins, how big the
penalty). The reason *wording* lives in app.i18n.messages, keyed by the codes
built here. `score_day` renders the winning reason in `lang` (default "en", so
callers and tests that don't care about language get English unchanged). The
score label stays an English enum ("Excellent"…"Dangerous") because the
frontend keys styling off it — the UI translates the label for display.
"""

from dataclasses import dataclass

from app.i18n import t

# WMO code → penalty. Unlisted codes (clear range 0-3) carry no penalty.
# Reason wording is in app.i18n.messages under "reason.wmo.{code}".
_WMO_PENALTIES: dict[int, int] = {
    45: 30,
    48: 35,
    51: 8,
    53: 12,
    55: 18,
    61: 20,
    63: 28,
    65: 40,
    71: 10,
    73: 25,
    75: 40,
    77: 10,
    80: 20,
    81: 30,
    82: 45,
    85: 25,
    86: 40,
    95: 55,
    96: 60,
    99: 65,
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
    label: str        # "Excellent" … "Dangerous" (English enum; UI translates)
    reason: str       # localized human-readable primary concern


# Each penalty fn returns (penalty, message_key, params). An empty key means
# "no penalty" — score_day filters those out. Keeping key+params separate from
# the rendered string is what lets the same logic produce EN or RO reasons.
def _wmo_penalty(code: int) -> tuple[int, str, dict]:
    penalty = _WMO_PENALTIES.get(code)
    if penalty is None:
        return 0, "", {}
    return penalty, f"reason.wmo.{code}", {}


def _wind_penalty(gusts_kmh: float) -> tuple[int, str, dict]:
    if gusts_kmh > 90:
        return 60, "reason.wind.dangerous", {"gusts": gusts_kmh}
    if gusts_kmh > 60:
        return 40, "reason.wind.very_strong", {"gusts": gusts_kmh}
    if gusts_kmh > 45:
        return 25, "reason.wind.strong", {"gusts": gusts_kmh}
    if gusts_kmh > 30:
        return 10, "reason.wind.moderate", {"gusts": gusts_kmh}
    return 0, "", {}


def _precip_penalty(mm: float) -> tuple[int, str, dict]:
    if mm > 20:
        return 25, "reason.precip.heavy", {"mm": mm}
    if mm > 10:
        return 15, "reason.precip.significant", {"mm": mm}
    if mm > 5:
        return 8, "reason.precip.moderate", {"mm": mm}
    if mm > 1:
        return 3, "reason.precip.light", {"mm": mm}
    return 0, "", {}


def _temp_penalty(temp_min: float, temp_max: float) -> tuple[int, str, dict]:
    if temp_min < -15:
        return 30, "reason.temp.extreme_cold", {"temp": temp_min}
    if temp_min < -5:
        return 15, "reason.temp.very_cold", {"temp": temp_min}
    if temp_min < 0:
        return 5, "reason.temp.below_freezing", {"temp": temp_min}
    if temp_max > 38:
        return 25, "reason.temp.extreme_heat", {"temp": temp_max}
    if temp_max > 32:
        return 10, "reason.temp.very_hot", {"temp": temp_max}
    return 0, "", {}


def score_day(
    weather_code: int,
    temp_max: float,
    temp_min: float,
    precip_mm: float,
    wind_gusts_kmh: float,
    lang: str = "en",
) -> ScoreResult:
    """Score one forecast day. Pure function — no I/O.

    `lang` only affects the rendered `reason` string; the score and label are
    language-independent.
    """
    penalties: list[tuple[int, str, dict]] = []

    for penalty, key, params in [
        _wmo_penalty(weather_code),
        _wind_penalty(wind_gusts_kmh),
        _precip_penalty(precip_mm),
        _temp_penalty(temp_min, temp_max),
    ]:
        if penalty:
            penalties.append((penalty, key, params))

    # Sort descending so the worst factor is first
    penalties.sort(key=lambda x: x[0], reverse=True)

    total_penalty = sum(p for p, _, _ in penalties)
    score = max(0, min(100, 100 - total_penalty))

    label = next(lbl for threshold, lbl in _SCORE_LABEL_THRESHOLDS if score >= threshold)
    if penalties:
        _, key, params = penalties[0]
        reason = t(key, lang, **params)
    else:
        reason = t("reason.good", lang)

    return ScoreResult(score=score, label=label, reason=reason)
