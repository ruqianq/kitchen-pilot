from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from kitchen_pilot.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client):
    """Health endpoint should always return 200, even when services are down."""
    with (
        patch("kitchen_pilot.routers.health.get_session") as mock_session,
        patch("kitchen_pilot.routers.health.httpx.AsyncClient") as mock_http_cls,
    ):
        # Mock DB session that succeeds
        session = AsyncMock()
        session.execute = AsyncMock()

        async def fake_get_session():
            yield session

        mock_session.side_effect = fake_get_session
        app.dependency_overrides[
            __import__(
                "kitchen_pilot.db.engine", fromlist=["get_session"]
            ).get_session
        ] = fake_get_session

        # Mock httpx client that succeeds
        mock_http = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http_cls.return_value = mock_http

        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data

    app.dependency_overrides.clear()
