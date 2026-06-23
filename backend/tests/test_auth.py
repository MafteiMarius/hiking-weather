"""Auth flow: register → login → access → refresh → logout → verify revocation."""
import pytest
from httpx import AsyncClient

# All tests share the session-scoped event loop so they can use the
# session-scoped engine (and its asyncpg connections) without loop mismatches.
pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/jwt/login"
REFRESH_URL = "/api/v1/auth/jwt/refresh"
LOGOUT_URL = "/api/v1/auth/jwt/logout"
ME_URL = "/api/v1/users/me"
PROFILE_URL = "/api/v1/profile"

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "TestPass123!"


async def test_register_creates_user_and_profile(client: AsyncClient) -> None:
    resp = await client.post(
        REGISTER_URL, json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == TEST_EMAIL
    assert "id" in body
    # hashed_password must never appear in the response
    assert "hashed_password" not in body
    assert "password" not in body


async def test_login_sets_both_cookies(client: AsyncClient) -> None:
    # Register first
    await client.post(
        REGISTER_URL, json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    resp = await client.post(
        LOGIN_URL, data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert resp.status_code == 200
    assert "hikecast_access" in resp.cookies
    assert "hikecast_refresh" in resp.cookies


async def test_me_requires_access_cookie(client: AsyncClient) -> None:
    resp = await client.get(ME_URL)
    assert resp.status_code == 401


async def test_full_auth_flow(client: AsyncClient) -> None:
    """register → login → /users/me → /profile → refresh → logout → verify revocation."""
    # 1. Register
    reg = await client.post(
        REGISTER_URL, json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert reg.status_code == 201

    # 2. Login
    login = await client.post(
        LOGIN_URL, data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert login.status_code == 200
    access_cookie = login.cookies.get("hikecast_access")
    refresh_cookie = login.cookies.get("hikecast_refresh")
    assert access_cookie is not None
    assert refresh_cookie is not None

    # 3. Access protected route with valid access token
    client.cookies.set("hikecast_access", access_cookie)
    me = await client.get(ME_URL)
    assert me.status_code == 200
    assert me.json()["email"] == TEST_EMAIL

    # 4. Profile is auto-created on register; GET should return defaults
    profile = await client.get(PROFILE_URL)
    assert profile.status_code == 200
    assert profile.json()["experience_level"] == 3
    assert profile.json()["locale"] == "ro-RO"

    # 5. PATCH profile
    patch = await client.patch(PROFILE_URL, json={"experience_level": 4, "locale": "en"})
    assert patch.status_code == 200
    assert patch.json()["experience_level"] == 4

    # 6. Refresh — simulate access token expiry by clearing the access cookie
    client.cookies.delete("hikecast_access")
    client.cookies.set("hikecast_refresh", refresh_cookie)
    refresh_resp = await client.post(REFRESH_URL)
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.cookies.get("hikecast_access")
    assert new_access is not None  # a fresh access cookie was set

    # 7. New access token works
    client.cookies.set("hikecast_access", new_access)
    me2 = await client.get(ME_URL)
    assert me2.status_code == 200

    # 8. Logout — revokes refresh token in DB
    logout = await client.post(LOGOUT_URL)
    assert logout.status_code == 204

    # 9. Access cookie cleared → /users/me returns 401
    client.cookies.clear()
    me3 = await client.get(ME_URL)
    assert me3.status_code == 401

    # 10. Refresh with revoked token → 401
    client.cookies.set("hikecast_refresh", refresh_cookie)
    refresh2 = await client.post(REFRESH_URL)
    assert refresh2.status_code == 401


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        REGISTER_URL, json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    resp = await client.post(
        LOGIN_URL, data={"username": TEST_EMAIL, "password": "wrong"}
    )
    assert resp.status_code == 400


async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    resp = await client.post(REFRESH_URL)
    assert resp.status_code == 401


async def test_profile_update_validates_bounds(client: AsyncClient) -> None:
    await client.post(
        REGISTER_URL, json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    login = await client.post(
        LOGIN_URL, data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    client.cookies.set("hikecast_access", login.cookies["hikecast_access"])

    # experience_level must be 1-5
    bad = await client.patch(PROFILE_URL, json={"experience_level": 6})
    assert bad.status_code == 422
