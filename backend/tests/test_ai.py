"""AI equipment endpoint: auth gating, unconfigured 503, mocked success path.

The Claude call itself is monkeypatched — these tests cover the endpoint's
orchestration (auth, config gate, forecast context assembly), not the model.
"""
import pytest
import respx
from httpx import AsyncClient, Response

from app.services.ai import EquipmentItem, EquipmentPlan
from tests.test_forecast import _OM_CLEAR_DAY

pytestmark = pytest.mark.asyncio(loop_scope="session")

EQUIPMENT_URL = "/api/v1/ai/equipment"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/jwt/login"

BODY = {"lat": 45.5, "lng": 25.3, "date": "2026-06-23"}

FAKE_PLAN = EquipmentPlan(
    summary="Clear and mild — a straightforward day.",
    items=[
        EquipmentItem(name="Hiking boots", reason="Rocky terrain", essential=True),
        EquipmentItem(name="Sun hat", reason="Clear sky all day", essential=False),
    ],
    warnings=[],
)


async def _login(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json={"email": "ai@example.com", "password": "AiTest1234!"})
    resp = await client.post(LOGIN_URL, data={"username": "ai@example.com", "password": "AiTest1234!"})
    assert resp.status_code == 200


async def test_equipment_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(EQUIPMENT_URL, json=BODY)
    assert resp.status_code == 401


async def test_equipment_503_when_not_configured(client: AsyncClient) -> None:
    await _login(client)
    resp = await client.post(EQUIPMENT_URL, json=BODY)
    assert resp.status_code == 503


async def test_equipment_success_with_mocked_model(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}

    async def fake_recommend(**kwargs) -> EquipmentPlan:
        captured.update(kwargs)
        return FAKE_PLAN

    monkeypatch.setattr("app.services.ai.is_configured", lambda: True)
    monkeypatch.setattr("app.services.ai.recommend_equipment", fake_recommend)

    await _login(client)
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=_OM_CLEAR_DAY)
        )
        # Archive not mocked on purpose: climatology failure must not block
        resp = await client.post(EQUIPMENT_URL, json=BODY)

    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == "2026-06-23"
    assert body["summary"].startswith("Clear and mild")
    assert body["items"][0]["essential"] is True

    # The endpoint assembled real forecast context for the model
    assert captured["day"]["score"] == 100
    assert len(captured["hours"]) == 2
    assert captured["elevation_m"] == 1234.0
    assert captured["climatology_reasons"] == []


async def test_equipment_404_for_date_outside_window(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.ai.is_configured", lambda: True)
    await _login(client)
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=_OM_CLEAR_DAY)
        )
        resp = await client.post(EQUIPMENT_URL, json={**BODY, "date": "2030-01-01"})
    assert resp.status_code == 404


async def test_equipment_422_for_bad_date_format(client: AsyncClient) -> None:
    await _login(client)
    resp = await client.post(EQUIPMENT_URL, json={**BODY, "date": "23-06-2026"})
    assert resp.status_code == 422
