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


async def test_list_returns_all_with_coords(client: AsyncClient, session: AsyncSession) -> None:
    await seed_trails(session)
    resp = await client.get(TRAILS_URL)
    assert resp.status_code == 200
    trails = resp.json()
    assert len(trails) == 25

    omu = next(t for t in trails if t["slug"] == "omu-valea-jepilor")
    assert omu["region"] == "Bucegi"
    assert omu["start_lat"] == pytest.approx(45.4104, abs=1e-4)
    assert omu["start_lng"] == pytest.approx(25.5350, abs=1e-4)
    assert omu["summit_elev_m"] == 2505

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
