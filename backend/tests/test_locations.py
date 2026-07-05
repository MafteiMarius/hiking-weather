"""Saved locations CRUD: auth gating, create/list round-trip, ownership on delete."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/jwt/login"
LOCATIONS_URL = "/api/v1/locations"

USER_A = ("alice@example.com", "AlicePass123!")
USER_B = ("bob@example.com", "BobPass123!")

OMU = {
    "name": "Varful Omu",
    "lat": 45.4453,
    "lng": 25.4567,
    "elevation_m": 2505,
    "notes": "Highest hut in Bucegi",
}


async def _login(client: AsyncClient, email: str, password: str) -> None:
    await client.post(REGISTER_URL, json={"email": email, "password": password})
    resp = await client.post(LOGIN_URL, data={"username": email, "password": password})
    assert resp.status_code == 200


async def test_locations_require_auth(client: AsyncClient) -> None:
    assert (await client.get(LOCATIONS_URL)).status_code == 401
    assert (await client.post(LOCATIONS_URL, json=OMU)).status_code == 401


async def test_create_and_list_round_trip(client: AsyncClient) -> None:
    await _login(client, *USER_A)

    created = await client.post(LOCATIONS_URL, json=OMU)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == OMU["name"]
    assert body["elevation_m"] == 2505
    assert "id" in body

    listed = await client.get(LOCATIONS_URL)
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    # lat/lng must survive the PostGIS geography round-trip
    assert items[0]["lat"] == pytest.approx(OMU["lat"], abs=1e-6)
    assert items[0]["lng"] == pytest.approx(OMU["lng"], abs=1e-6)
    assert items[0]["notes"] == OMU["notes"]


async def test_list_is_newest_first(client: AsyncClient) -> None:
    await _login(client, *USER_A)
    await client.post(LOCATIONS_URL, json={**OMU, "name": "First"})
    await client.post(LOCATIONS_URL, json={**OMU, "name": "Second"})

    items = (await client.get(LOCATIONS_URL)).json()
    assert [i["name"] for i in items] == ["Second", "First"]


async def test_create_invalid_coords_returns_422(client: AsyncClient) -> None:
    await _login(client, *USER_A)
    resp = await client.post(LOCATIONS_URL, json={**OMU, "lat": 91.0})
    assert resp.status_code == 422


async def test_delete_own_location(client: AsyncClient) -> None:
    await _login(client, *USER_A)
    loc_id = (await client.post(LOCATIONS_URL, json=OMU)).json()["id"]

    resp = await client.delete(f"{LOCATIONS_URL}/{loc_id}")
    assert resp.status_code == 204
    assert (await client.get(LOCATIONS_URL)).json() == []


async def test_cannot_delete_other_users_location(client: AsyncClient) -> None:
    await _login(client, *USER_A)
    loc_id = (await client.post(LOCATIONS_URL, json=OMU)).json()["id"]

    # Fresh cookie jar for user B — same DB session, different identity
    client.cookies.clear()
    await _login(client, *USER_B)

    resp = await client.delete(f"{LOCATIONS_URL}/{loc_id}")
    assert resp.status_code == 404

    # A's location must still exist
    client.cookies.clear()
    resp = await client.post(LOGIN_URL, data={"username": USER_A[0], "password": USER_A[1]})
    assert resp.status_code == 200
    assert len((await client.get(LOCATIONS_URL)).json()) == 1
