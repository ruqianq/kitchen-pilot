"""Tests for auth router endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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
async def test_google_start_returns_url(client):
    with patch(
        "kitchen_pilot.routers.auth.settings"
    ) as mock_settings:
        mock_settings.google_oauth_client_id = "test-client-id"
        mock_settings.google_oauth_redirect_url = "http://localhost:8000/auth/google/callback"

        response = await client.get("/auth/google/start")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "test-client-id" in data["authorization_url"]
        assert "accounts.google.com" in data["authorization_url"]


@pytest.mark.asyncio
async def test_google_start_requires_config(client):
    with patch(
        "kitchen_pilot.routers.auth.settings"
    ) as mock_settings:
        mock_settings.google_oauth_client_id = ""

        response = await client.get("/auth/google/start")
        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_google_status_disconnected(client):
    with patch(
        "kitchen_pilot.routers.auth.token_service.get_tokens",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = None
        response = await client.get("/auth/google/status")
        assert response.status_code == 200
        assert response.json()["connected"] is False


@pytest.mark.asyncio
async def test_google_status_connected(client):
    row = MagicMock()
    row.scopes = ["https://www.googleapis.com/auth/calendar"]
    row.token_expiry = MagicMock()
    row.token_expiry.isoformat.return_value = "2026-01-01T00:00:00+00:00"

    with patch(
        "kitchen_pilot.routers.auth.token_service.get_tokens",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = row
        response = await client.get("/auth/google/status")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["scopes"] == ["https://www.googleapis.com/auth/calendar"]


@pytest.mark.asyncio
async def test_google_disconnect(client):
    with (
        patch(
            "kitchen_pilot.routers.auth.token_service.get_tokens",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "kitchen_pilot.routers.auth.token_service.delete_tokens",
            new_callable=AsyncMock,
        ) as mock_delete,
    ):
        mock_get.return_value = None
        mock_delete.return_value = False

        response = await client.post("/auth/google/disconnect")
        assert response.status_code == 200
        assert response.json()["disconnected"] is False
