"""Personalised trail ranking: weather first, profile second.

WHY this shape:
  - The weather safety score (0-100, from scoring.py) is the backbone of the
    rank. Personal factors only *adjust* it — a thunderstorm day must never
    outrank a clear day because the stormy trail is closer to home.
  - Difficulty above the profile's max_difficulty is a HARD filter: the user
    said "never show me UIAA scrambles", so we don't, however sunny it is.
  - Difficulty above experience_level (but within max) is a SOFT penalty of
    8 points per level: a level-2 hiker sees a difficulty-4 route drop by 16
    — visible in the ranking, but a perfect-weather stretch objective can
    still beat a drizzly easy walk.
  - Distance from home costs up to 10 points, linear to max_distance_km, and
    trails beyond max_distance_km are filtered out. 10 was picked to break
    ties between comparable days, not to override real weather differences
    (one score label step is 15-20 points).

The ranking core is pure (no I/O) so it can be unit-tested with
hand-computed values, same as scoring.py.
"""
from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt
from typing import Optional

DIFFICULTY_STRETCH_PENALTY = 8   # per level above experience_level
DISTANCE_PENALTY_MAX = 10        # at exactly max_distance_km from home


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance. Good to ~0.5% — plenty for a distance filter."""
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 6371.0 * 2 * atan2(sqrt(a), sqrt(1 - a))


@dataclass(frozen=True)
class TrailDay:
    """One trail on one forecast day — the input to the pure ranker."""
    slug: str
    difficulty: int
    start_lat: float
    start_lng: float
    weather_score: int  # score_day() result at the trail's summit (or start)


@dataclass(frozen=True)
class RankedTrail:
    slug: str
    rank_score: int
    weather_score: int
    difficulty_penalty: int
    distance_penalty: int
    distance_from_home_km: Optional[float]


def rank_trails(
    candidates: list[TrailDay],
    *,
    experience_level: int,
    max_difficulty: int,
    home: Optional[tuple[float, float]] = None,
    max_distance_km: Optional[int] = None,
) -> list[RankedTrail]:
    """Filter and order candidates for one day. Pure — no I/O.

    Returns best-first; ties break by distance from home (closest wins),
    then slug for a stable order.
    """
    ranked: list[RankedTrail] = []
    for c in candidates:
        if c.difficulty > max_difficulty:
            continue

        distance_km: Optional[float] = None
        distance_penalty = 0
        if home is not None:
            distance_km = haversine_km(home[0], home[1], c.start_lat, c.start_lng)
            if max_distance_km is not None:
                if distance_km > max_distance_km:
                    continue
                distance_penalty = round(DISTANCE_PENALTY_MAX * distance_km / max_distance_km)

        difficulty_penalty = DIFFICULTY_STRETCH_PENALTY * max(0, c.difficulty - experience_level)
        rank_score = max(0, c.weather_score - difficulty_penalty - distance_penalty)

        ranked.append(RankedTrail(
            slug=c.slug,
            rank_score=rank_score,
            weather_score=c.weather_score,
            difficulty_penalty=difficulty_penalty,
            distance_penalty=distance_penalty,
            distance_from_home_km=round(distance_km, 1) if distance_km is not None else None,
        ))

    ranked.sort(key=lambda r: (-r.rank_score, r.distance_from_home_km or 0.0, r.slug))
    return ranked
