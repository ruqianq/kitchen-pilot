"""Tests for health profile CRUD endpoints (biometrics, health conditions, person update)."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.db.models import Biometric, HealthCondition, Household, Person
from kitchen_pilot.main import app

NOW = datetime.now(tz=timezone.utc)
HOUSEHOLD_ID = uuid.uuid4()
PERSON_ID = uuid.uuid4()


def _make_household() -> MagicMock:
    h = MagicMock(spec=Household)
    h.id = HOUSEHOLD_ID
    h.name = "Test Family"
    h.timezone = "UTC"
    h.created_at = NOW
    h.updated_at = NOW
    return h


def _make_person(**overrides) -> MagicMock:
    p = MagicMock(spec=Person)
    p.id = overrides.get("id", PERSON_ID)
    p.household_id = HOUSEHOLD_ID
    p.name = overrides.get("name", "Alice")
    p.role = overrides.get("role", "adult")
    p.age_band = overrides.get("age_band", None)
    p.gender = overrides.get("gender", None)
    p.date_of_birth = overrides.get("date_of_birth", None)
    p.ethnicity = overrides.get("ethnicity", None)
    p.activity_level = overrides.get("activity_level", None)
    p.created_at = NOW
    p.updated_at = NOW
    return p


def _make_biometric(**overrides) -> MagicMock:
    b = MagicMock(spec=Biometric)
    b.id = overrides.get("id", uuid.uuid4())
    b.person_id = overrides.get("person_id", PERSON_ID)
    b.height_cm = overrides.get("height_cm", 170.0)
    b.weight_kg = overrides.get("weight_kg", 70.0)
    b.bmi = overrides.get("bmi", 24.2)
    b.waist_cm = overrides.get("waist_cm", None)
    b.created_at = NOW
    b.updated_at = NOW
    return b


def _make_health_condition(**overrides) -> MagicMock:
    hc = MagicMock(spec=HealthCondition)
    hc.id = overrides.get("id", uuid.uuid4())
    hc.person_id = overrides.get("person_id", PERSON_ID)
    hc.condition = overrides.get("condition", "hypertension")
    hc.severity = overrides.get("severity", None)
    hc.notes = overrides.get("notes", None)
    hc.created_at = NOW
    return hc


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


# ── Person Update with Health Fields ─────────────────────


class TestPersonHealthUpdate:
    @pytest.mark.asyncio
    async def test_update_person_with_health_fields(self, client, mock_session):
        """PUT /household/people/{id} should accept gender, DOB, etc."""
        updated = _make_person(
            gender="female",
            date_of_birth="1990-05-15",
            ethnicity="Asian",
            activity_level="active",
        )

        with patch(
            "kitchen_pilot.routers.household.svc.update_person",
            new=AsyncMock(return_value=updated),
        ):
            response = await client.put(
                f"/household/people/{PERSON_ID}",
                json={
                    "gender": "female",
                    "date_of_birth": "1990-05-15",
                    "ethnicity": "Asian",
                    "activity_level": "active",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["gender"] == "female"
        assert data["date_of_birth"] == "1990-05-15"
        assert data["activity_level"] == "active"

    @pytest.mark.asyncio
    async def test_create_person_with_health_fields(self, client, mock_session):
        """POST /household/people should accept new health fields."""
        created = _make_person(
            name="Bob", gender="male", activity_level="sedentary"
        )

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
                json={
                    "name": "Bob",
                    "role": "adult",
                    "gender": "male",
                    "activity_level": "sedentary",
                },
            )

        assert response.status_code == 201


# ── Biometrics ────────────────────────────────────────────


class TestBiometrics:
    @pytest.mark.asyncio
    async def test_get_biometric(self, client, mock_session):
        bio = _make_biometric()

        with patch(
            "kitchen_pilot.routers.household.svc.get_biometric",
            new=AsyncMock(return_value=bio),
        ):
            response = await client.get(f"/household/people/{PERSON_ID}/biometrics")

        assert response.status_code == 200
        data = response.json()
        assert data["height_cm"] == 170.0
        assert data["weight_kg"] == 70.0
        assert data["bmi"] == 24.2

    @pytest.mark.asyncio
    async def test_get_biometric_none(self, client, mock_session):
        with patch(
            "kitchen_pilot.routers.household.svc.get_biometric",
            new=AsyncMock(return_value=None),
        ):
            response = await client.get(f"/household/people/{PERSON_ID}/biometrics")

        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_upsert_biometric(self, client, mock_session):
        bio = _make_biometric(height_cm=175.0, weight_kg=80.0, bmi=26.1)

        with patch(
            "kitchen_pilot.routers.household.svc.upsert_biometric",
            new=AsyncMock(return_value=bio),
        ):
            response = await client.post(
                f"/household/people/{PERSON_ID}/biometrics",
                json={"height_cm": 175.0, "weight_kg": 80.0},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["height_cm"] == 175.0
        assert data["weight_kg"] == 80.0


# ── Health Conditions ─────────────────────────────────────


class TestHealthConditions:
    @pytest.mark.asyncio
    async def test_list_health_conditions(self, client, mock_session):
        conditions = [
            _make_health_condition(condition="hypertension"),
            _make_health_condition(condition="type_2_diabetes"),
        ]

        with patch(
            "kitchen_pilot.routers.household.svc.list_health_conditions",
            new=AsyncMock(return_value=conditions),
        ):
            household = _make_household()
            result = MagicMock()
            result.scalar_one_or_none.return_value = household
            mock_session.execute.return_value = result

            response = await client.get("/household/health-conditions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["condition"] == "hypertension"

    @pytest.mark.asyncio
    async def test_create_health_condition(self, client, mock_session):
        condition = _make_health_condition(condition="celiac")

        with patch(
            "kitchen_pilot.routers.household.svc.create_health_condition",
            new=AsyncMock(return_value=condition),
        ):
            response = await client.post(
                "/household/health-conditions",
                json={
                    "person_id": str(PERSON_ID),
                    "condition": "celiac",
                },
            )

        assert response.status_code == 201
        assert response.json()["condition"] == "celiac"

    @pytest.mark.asyncio
    async def test_delete_health_condition(self, client, mock_session):
        condition_id = uuid.uuid4()
        condition = _make_health_condition(id=condition_id)

        with patch(
            "kitchen_pilot.routers.household.svc.delete_health_condition",
            new=AsyncMock(return_value=None),
        ):
            response = await client.delete(
                f"/household/health-conditions/{condition_id}"
            )

        assert response.status_code == 204
