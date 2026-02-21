"""Tests for plan router endpoints.

Mocks the plan service to test HTTP layer behavior.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.dependencies import get_household_id
from kitchen_pilot.main import app

MOCK_HOUSEHOLD_ID = uuid.uuid4()


@pytest.fixture
async def client():
    async def fake_session():
        yield AsyncMock()

    async def fake_household_id():
        return MOCK_HOUSEHOLD_ID

    app.dependency_overrides[get_session] = fake_session
    app.dependency_overrides[get_household_id] = fake_household_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_plans_empty(client):
    with patch(
        "kitchen_pilot.routers.plans.plan_svc.list_plans",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = []
        response = await client.get("/plan")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_get_plan_not_found(client):
    with patch(
        "kitchen_pilot.routers.plans.plan_svc.get_plan",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = None
        response = await client.get(f"/plan/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_shopping_list_not_found(client):
    with patch(
        "kitchen_pilot.routers.plans.plan_svc.get_plan_shopping_list",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = None
        response = await client.get(f"/plan/{uuid.uuid4()}/shopping-list")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_plan_not_found(client):
    with patch(
        "kitchen_pilot.routers.plans.plan_svc.delete_plan",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = False
        response = await client.delete(f"/plan/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_publish_no_calendar(client):
    with patch(
        "kitchen_pilot.routers.plans.calendar_service.is_available",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = False
        response = await client.post(
            "/plan/publish",
            json={"plan_id": str(uuid.uuid4())},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_generate_validates_date_format(client):
    """Invalid date format is rejected by Pydantic."""
    response = await client.post(
        "/plan/generate",
        json={"week_start_date": "not-a-date"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_rejects_missing_date(client):
    """Missing week_start_date is rejected."""
    response = await client.post("/plan/generate", json={})
    assert response.status_code == 422
