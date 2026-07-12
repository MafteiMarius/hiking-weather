"""Trail recommendations: pure ranking math + endpoint orchestration.

The ranker tests use hand-computed values (points 1° of latitude apart are
111.19 km on the R=6371 sphere, so distance penalties are checkable by hand).
The endpoint tests mock Open-Meteo's bulk response with one payload per
requested coordinate, mirroring the real multi-location API shape.
"""
import pytest
import respx
from httpx import AsyncClient, Response

from app.seeds.trails import TRAILS, seed_trails
from app.services.recommend import TrailDay, haversine_km, rank_trails
from tests.test_forecast import _OM_CLEAR_DAY

pytestmark = pytest.mark.asyncio(loop_scope="session")

RECOMMEND_URL = "/api/v1/recommendations"
PROFILE_URL = "/api/v1/profile"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/jwt/login"


def _candidate(slug: str, difficulty: int, score: int, lat: float = 45.0) -> TrailDay:
    return TrailDay(slug=slug, difficulty=difficulty, start_lat=lat, start_lng=25.0,
                    weather_score=score)


# ── Pure ranking ─────────────────────────────────────────────────────────────

def test_haversine_one_degree_latitude() -> None:
    # 1° of latitude on the R=6371 km sphere: 6371 * pi/180 = 111.19 km
    assert haversine_km(45.0, 25.0, 46.0, 25.0) == pytest.approx(111.19, abs=0.01)


def test_difficulty_above_max_is_excluded() -> None:
    ranked = rank_trails(
        [_candidate("scramble", 5, 100)],
        experience_level=3, max_difficulty=4,
    )
    assert ranked == []


def test_difficulty_stretch_penalty_is_8_per_level() -> None:
    ranked = rank_trails(
        [_candidate("hard", 4, 90)],
        experience_level=2, max_difficulty=4,
    )
    # two levels above experience: 90 - 2*8 = 74
    assert ranked[0].rank_score == 74
    assert ranked[0].difficulty_penalty == 16


def test_distance_penalty_and_filter() -> None:
    home = (45.0, 25.0)
    near = _candidate("near", 2, 80, lat=45.0)     # 0 km
    far = _candidate("far", 2, 80, lat=46.0)       # 111.19 km
    too_far = _candidate("out", 2, 100, lat=47.0)  # 222.39 km > 150

    ranked = rank_trails(
        [far, near, too_far],
        experience_level=3, max_difficulty=4,
        home=home, max_distance_km=150,
    )
    assert [r.slug for r in ranked] == ["near", "far"]  # "out" filtered
    assert ranked[0].distance_penalty == 0
    # round(10 * 111.19 / 150) = round(7.41) = 7 → 80 - 7 = 73
    assert ranked[1].distance_penalty == 7
    assert ranked[1].rank_score == 73


def test_weather_dominates_distance() -> None:
    # A stormy day nearby must not outrank a clear day far away:
    # the max distance penalty (10) is smaller than any label step.
    home = (45.0, 25.0)
    stormy_near = _candidate("stormy", 2, 30, lat=45.0)
    clear_far = _candidate("clear", 2, 95, lat=46.0)
    ranked = rank_trails(
        [stormy_near, clear_far],
        experience_level=3, max_difficulty=4,
        home=home, max_distance_km=150,
    )
    assert ranked[0].slug == "clear"


def test_rank_score_clamped_at_zero() -> None:
    ranked = rank_trails(
        [_candidate("grim", 5, 5)],
        experience_level=1, max_difficulty=5,
    )
    # 5 - 4*8 = -27 → clamped to 0
    assert ranked[0].rank_score == 0


# ── Endpoint ─────────────────────────────────────────────────────────────────

def _bulk_side_effect(request) -> Response:
    """One clear-day payload per requested coordinate, like the real API."""
    lats = str(request.url.params["latitude"]).split(",")
    lngs = str(request.url.params["longitude"]).split(",")
    payloads = [
        {**_OM_CLEAR_DAY, "latitude": float(lat), "longitude": float(lng)}
        for lat, lng in zip(lats, lngs)
    ]
    return Response(200, json=payloads if len(payloads) > 1 else payloads[0])


async def _login(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json={"email": "rec@example.com", "password": "RecTest1234!"})
    resp = await client.post(LOGIN_URL, data={"username": "rec@example.com", "password": "RecTest1234!"})
    assert resp.status_code == 200


async def test_recommendations_require_auth(client: AsyncClient) -> None:
    assert (await client.get(RECOMMEND_URL)).status_code == 401


async def test_recommendations_default_profile(client: AsyncClient, session) -> None:
    await seed_trails(session)
    await _login(client)

    with respx.mock:
        route = respx.get("https://api.open-meteo.com/v1/forecast").mock(
            side_effect=_bulk_side_effect
        )
        resp = await client.get(RECOMMEND_URL, params={"date": "2026-06-23", "limit": 25})
        assert resp.status_code == 200
        assert route.call_count == 1  # ONE bulk call for all 25 trails

        body = resp.json()
        # default max_difficulty=4 excludes the difficulty-5 routes
        expected_excluded = sum(1 for t in TRAILS if t["difficulty"] > 4)
        assert body["excluded"] == expected_excluded
        assert len(body["items"]) == len(TRAILS) - expected_excluded

        top = body["items"][0]
        # clear day → weather 100; difficulty ≤ experience(3) → no penalty
        assert top["rank_score"] == 100
        assert top["trail"]["difficulty"] <= 3
        # ranked best-first
        scores = [i["rank_score"] for i in body["items"]]
        assert scores == sorted(scores, reverse=True)

        # difficulty-4 trails carry the stretch penalty over experience 3
        d4 = next(i for i in body["items"] if i["trail"]["difficulty"] == 4)
        assert d4["difficulty_penalty"] == 8
        assert d4["rank_score"] == 92

        # second request: everything cached, no new upstream calls;
        # also exercises the default limit of 10
        resp2 = await client.get(RECOMMEND_URL, params={"date": "2026-06-23"})
        assert resp2.status_code == 200
        assert route.call_count == 1
        assert len(resp2.json()["items"]) == 10


async def test_recommendations_use_profile_home_and_limits(
    client: AsyncClient, session
) -> None:
    await seed_trails(session)
    await _login(client)

    # Home in Bușteni, tight radius: only Bucegi-ish trails stay
    resp = await client.patch(PROFILE_URL, json={
        "home_lat": 45.41, "home_lng": 25.53,
        "max_distance_km": 30, "max_difficulty": 5, "experience_level": 5,
    })
    assert resp.status_code == 200

    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            side_effect=_bulk_side_effect
        )
        resp = await client.get(RECOMMEND_URL, params={"date": "2026-06-23", "limit": 25})

    assert resp.status_code == 200
    body = resp.json()
    assert 0 < len(body["items"]) < len(TRAILS)  # radius filtered most massifs
    for item in body["items"]:
        assert item["distance_from_home_km"] <= 30
        # Bucegi + Piatra Craiului are within 30 km of Bușteni
        assert item["trail"]["region"] in ("Bucegi", "Piatra Craiului")


async def test_recommendations_unknown_date_404(client: AsyncClient, session) -> None:
    await seed_trails(session)
    await _login(client)
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            side_effect=_bulk_side_effect
        )
        resp = await client.get(RECOMMEND_URL, params={"date": "2030-01-01"})
    assert resp.status_code == 404
