"""AI recommendations via the Claude API.

Design notes:
  - The frontend never calls Anthropic directly — the backend assembles the
    weather context it already has (scored day, hourly numbers, climatology)
    and asks for a *structured* packing plan. `client.messages.parse()` with a
    Pydantic `output_format` guarantees the response validates against
    EquipmentPlan — no JSON-repair code needed.
  - The system prompt is static so Anthropic's prompt caching can kick in;
    all per-request facts go in the user message.
  - AI features are optional: if `anthropic_api_key` is unset the endpoint
    layer returns 503 and the UI hides the button.
"""
from functools import lru_cache

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from app.core.config import get_settings


class EquipmentItem(BaseModel):
    name: str = Field(description="Short item name, e.g. 'Hardshell jacket'")
    reason: str = Field(description="One sentence tying the item to the forecast")
    essential: bool = Field(description="True if leaving it behind would be unsafe")


class EquipmentPlan(BaseModel):
    summary: str = Field(description="2-3 sentences sizing up the day for a hiker")
    items: list[EquipmentItem]
    warnings: list[str] = Field(description="Safety caveats; empty when benign")


_SYSTEM_PROMPT = """You are the packing advisor inside HikeCast, a weather app for \
hiking in the Romanian Carpathians. Given one day's mountain forecast you produce a \
practical equipment list for a day hike.

Rules:
- Recommend 6-12 items, ordered most important first. Mark as essential only what \
safety depends on for THIS forecast (e.g. hardshell when heavy rain, microspikes when \
ice is plausible) — boots and water are always essential.
- Tie every reason to a concrete number or fact from the forecast. Do not invent \
conditions that are not in the data.
- Assume a reasonably fit hiker on marked trails, out roughly 09:00-17:00.
- Temperatures are at ~2 m over the queried point; on ridges above it, expect colder \
and windier. Mention this in the summary when the elevation suggests exposed terrain.
- Add warnings for: thunderstorm codes, gusts over 60 km/h, freezing temperatures, \
or a historically unstable pattern. Otherwise leave warnings empty.
- Write in plain English, no emoji."""


def is_configured() -> bool:
    return bool(get_settings().anthropic_api_key)


@lru_cache
def _client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key)


def _format_context(
    date: str,
    elevation_m: float,
    day: dict,
    hours: list[dict],
    climatology_reasons: list[str],
) -> str:
    lines = [
        f"Date: {date}",
        f"Location elevation: {elevation_m:.0f} m",
        "",
        "Daily forecast:",
        f"- Conditions: {day['weather_description']} (WMO {day['weather_code']})",
        f"- Temperature: {day['temp_min_c']:.0f} to {day['temp_max_c']:.0f} °C",
        f"- Precipitation: {day['precipitation_sum_mm']:.1f} mm "
        f"({day['precipitation_probability_max']}% max probability)",
        f"- Max wind gusts: {day['wind_gusts_max_kmh']:.0f} km/h",
        f"- HikeCast safety score: {day['score']}/100 ({day['score_label']}) — {day['score_reason']}",
    ]
    daytime = [h for h in hours if 8 <= int(h["time"][11:13]) <= 18]
    if daytime:
        lines += ["", "Hourly (08:00-18:00): time, °C, mm, gusts km/h"]
        lines += [
            f"- {h['time'][11:16]}: {h['temp_c']:.0f}°C, {h['precipitation_mm']:.1f}mm, "
            f"{h['wind_gusts_kmh']:.0f}km/h"
            for h in daytime
        ]
    if climatology_reasons:
        lines += ["", "Historical pattern for this week of the year (10-yr ERA5):"]
        lines += [f"- {r}" for r in climatology_reasons]
    return "\n".join(lines)


async def recommend_equipment(
    date: str,
    elevation_m: float,
    day: dict,
    hours: list[dict],
    climatology_reasons: list[str],
) -> EquipmentPlan:
    """One Claude call → validated EquipmentPlan. Raises anthropic.* on failure."""
    settings = get_settings()
    response = await _client().messages.parse(
        model=settings.anthropic_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": _format_context(date, elevation_m, day, hours, climatology_reasons),
        }],
        output_format=EquipmentPlan,
    )
    return response.parsed_output
