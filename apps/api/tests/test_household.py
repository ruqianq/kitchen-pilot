"""Tests for household CRUD endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.db.models import Allergy, Household, Person, Severity
from kitchen_pilot.main import app

NOW = datetime.now(tz=timezone.utc)
HOUSEHOLD_ID = uuid.uuid4()
PERSON_ID = uuid.uuid4()


def _make_household(**overrides) -> MagicMock:
    h = MagicMock(spec=Household)
    h.id = overrides.get("id", HOUSEHOLD_ID)
    h.name = overrides.get("name", "Test Family")
    h.timezone = overrides.get("timezone", "UTC")
    h.created_at = overrides.get("created_at", NOW)
    h.updated_at = overrides.get("updated_at", NOW)
    return h


def _make_person(**overrides) -> MagicMock:
    p = MagicMock(spec=Person)
    p.id = overrides.get("id", PERSON_ID)
    p.household_id = overrides.get("household_id", HOUSEHOLD_ID)
    p.name = overrides.get("name", "Alice")
    p.role = overrides.get("role", "adult")
    p.age_band = overrides.get("age_band", None)
    p.created_at = overrides.get("created_at", NOW)
    p.updated_at = overrides.get("updated_at", NOW)
    return p


def _make_allergy(**overrides) -> MagicMock:
    a = MagicMock(spec=Allergy)
    a.id = overrides.get("id", uuid.uuid4())
    a.person_id = overrides.get("person_id", PERSON_ID)
    a.allergen = overrides.get("allergen", "peanuts")
    a.severity = overrides.get("severity", Severity.SEVERE)
    a.notes = overrides.get("notes", None)
    a.created_at = overrides.get("created_at", NOW)
    return a


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock()

    async def fake_get_session():
        yield session

    app.dependency_overrides[get_session] = fake_get_session
    return session


class TestGetHousehold:
    @pytest.mark.asyncio
    async def test_returns_household(self, client, mock_session):
        household = _make_household()
        result = MagicMock()
        result.scalar_one_or_none.return_value = household
        mock_session.execute.return_value = result

        response = await client.get("/household")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Family"
        assert data["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_auto_creates_when_none(self, client, mock_session):
        """When no household exists, GET /household auto-creates one."""
        created = _make_household(name="My Household")

        with patch(
            "kitchen_pilot.dependencies.get_or_create_household",
            new=AsyncMock(return_value=created),
        ):
            response = await client.get("/household")
            assert response.status_code == 200
            assert response.json()["name"] == "My Household"


class TestUpdateHousehold:
    @pytest.mark.asyncio
    async def test_updates_name(self, client, mock_session):
        household = _make_household()
        result = MagicMock()
        result.scalar_one_or_none.return_value = household
        mock_session.execute.return_value = result

        response = await client.put(
            f"/household/{HOUSEHOLD_ID}",
            json={"name": "Updated Family"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_404_for_unknown(self, client, mock_session):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result

        response = await client.put(
            f"/household/{uuid.uuid4()}",
            json={"name": "Nope"},
        )
        assert response.status_code == 404


class TestPeopleCRUD:
    @pytest.mark.asyncio
    async def test_list_people(self, client, mock_session):
        household = _make_household()
        person = _make_person()

        results = [MagicMock(), MagicMock()]
        results[0].scalar_one_or_none.return_value = household
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [person]
        results[1].scalars.return_value = scalars_mock
        mock_session.execute.side_effect = results

        response = await client.get("/household/people")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_create_person(self, client, mock_session):
        """POST /household/people creates a person and returns 201."""
        created = _make_person(name="Bob", role="child", age_band="teen")

        with patch(
            "kitchen_pilot.routers.household.svc.create_person",
            new=AsyncMock(return_value=created),
        ):
            household = _make_household()
            result = MagicMock()
            result.scalar_one_or_none.return_value = household
            mock_session.execute.return_value = result

            response = await client.post(
                "/household/people",
                json={"name": "Bob", "role": "child", "age_band": "teen"},
            )
            assert response.status_code == 201
            assert response.json()["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_delete_person(self, client, mock_session):
        person = _make_person()
        result = MagicMock()
        result.scalar_one_or_none.return_value = person
        mock_session.execute.return_value = result

        response = await client.delete(f"/household/people/{PERSON_ID}")
        assert response.status_code == 204
        mock_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, client, mock_session):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result

        response = await client.delete(f"/household/people/{uuid.uuid4()}")
        assert response.status_code == 404


class TestAllergiesCRUD:
    @pytest.mark.asyncio
    async def test_create_allergy(self, client, mock_session):
        """POST /household/allergies creates an allergy and returns 201."""
        created = _make_allergy(allergen="shellfish", severity=Severity.MODERATE)

        with patch(
            "kitchen_pilot.routers.household.svc.create_allergy",
            new=AsyncMock(return_value=created),
        ):
            response = await client.post(
                "/household/allergies",
                json={
                    "person_id": str(PERSON_ID),
                    "allergen": "shellfish",
                    "severity": "moderate",
                },
            )
            assert response.status_code == 201
            assert response.json()["allergen"] == "shellfish"

    @pytest.mark.asyncio
    async def test_create_allergy_invalid_person(self, client, mock_session):
        mock_session.get.return_value = None

        response = await client.post(
            "/household/allergies",
            json={
                "person_id": str(uuid.uuid4()),
                "allergen": "dairy",
                "severity": "mild",
            },
        )
        assert response.status_code == 404


class TestContextEndpoint:
    @pytest.mark.asyncio
    async def test_returns_context(self, client, mock_session):
        """Context endpoint returns assembled HouseholdContext."""
        mock_ctx = AsyncMock(
            return_value={
                "household_name": "Test Family",
                "timezone": "UTC",
                "people": [{"name": "Alice", "role": "adult", "age_band": None}],
                "allergies": [],
                "dietary_rules": [],
                "preferences": [],
                "nutrition_goals": [],
            }
        )
        with patch(
            "kitchen_pilot.routers.household.svc.get_household_context",
            mock_ctx,
        ):
            response = await client.get("/household/context")
            assert response.status_code == 200
            data = response.json()
            assert data["household_name"] == "Test Family"
            assert len(data["people"]) == 1
