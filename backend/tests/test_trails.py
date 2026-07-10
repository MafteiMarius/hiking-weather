"""Trail catalogue: seed integrity, listing, filters, detail."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.seeds.trails import TRAILS, seed_trails

pytestmark = pytest.mark.asyncio(loop_scope="session")

TRAILS_URL = "/api/v1/trails"


async def test_seed_creates_25_and_is_idempotent(session: AsyncSession) -> None:
    assert await seed_trails(session) == 25
    assert await seed_trails(session) == 0  # second run: nothing new


async def test_seed_update_refreshes_existing_rows(
    client: AsyncClient, session: AsyncSession
) -> None:
    await seed_trails(session)

    # simulate stale data in the DB, as if seeded from an older TRAILS
    from sqlalchemy import update as sa_update

    from app.db.models import Trail

    await session.execute(
        sa_update(Trail)
        .where(Trail.slug == "iezerul-mare")
        .values(distance_m=99999, start_point="SRID=4326;POINT(24.9439 45.3467)")
    )
    await session.commit()

    # default mode must NOT touch the stale row
    assert await seed_trails(session) == 0
    stale = (await client.get(f"{TRAILS_URL}/iezerul-mare")).json()
    assert stale["distance_m"] == 99999

    # update mode refreshes it from TRAILS
    assert await seed_trails(session, update=True) == 0
    src = next(t for t in TRAILS if t["slug"] == "iezerul-mare")
    fresh = (await client.get(f"{TRAILS_URL}/iezerul-mare")).json()
    assert fresh["distance_m"] == src["distance_m"]
    assert fresh["start_lat"] == pytest.approx(src["start"][0], abs=1e-6)


async def test_list_returns_all_with_coords(client: AsyncClient, session: AsyncSession) -> None:
    await seed_trails(session)
    resp = await client.get(TRAILS_URL)
    assert resp.status_code == 200
    trails = resp.json()
    assert len(trails) == 25

    omu = next(t for t in trails if t["slug"] == "omu-valea-jepilor")
    src = next(t for t in TRAILS if t["slug"] == "omu-valea-jepilor")
    assert omu["region"] == "Bucegi"
    # coords must survive the PostGIS write/read round-trip unchanged
    assert omu["start_lat"] == pytest.approx(src["start"][0], abs=1e-6)
    assert omu["start_lng"] == pytest.approx(src["start"][1], abs=1e-6)
    assert omu["summit_elev_m"] == src["summit_elev_m"]

    # gorge walk has no summit point
    gorge = next(t for t in trails if t["slug"] == "prapastiile-zarnestiului")
    assert gorge["summit_lat"] is None


async def test_list_filters(client: AsyncClient, session: AsyncSession) -> None:
    await seed_trails(session)

    bucegi = (await client.get(TRAILS_URL, params={"region": "Bucegi"})).json()
    assert len(bucegi) == 5
    assert all(t["region"] == "Bucegi" for t in bucegi)

    easy = (await client.get(TRAILS_URL, params={"max_difficulty": 2})).json()
    assert easy and all(t["difficulty"] <= 2 for t in easy)

    expected_easy = sum(1 for t in TRAILS if t["difficulty"] <= 2)
    assert len(easy) == expected_easy


async def test_detail_and_404(client: AsyncClient, session: AsyncSession) -> None:
    await seed_trails(session)
    resp = await client.get(f"{TRAILS_URL}/peleaga-carnic")
    assert resp.status_code == 200
    assert resp.json()["name"].startswith("Vârful Peleaga")

    assert (await client.get(f"{TRAILS_URL}/no-such-trail")).status_code == 404
