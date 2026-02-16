"""Tests for household CRUD Pydantic schemas."""

import uuid

import pytest
from pydantic import ValidationError

from kitchen_pilot.schemas.household import (
    AllergenSeverity,
    AllergyCreate,
    DietaryRuleCreate,
    FoodPreferenceCreate,
    HouseholdCreate,
    HouseholdResponse,
    HouseholdUpdate,
    NutritionGoalCreate,
    PersonCreate,
    PersonUpdate,
    PreferenceLevel,
)


class TestHouseholdSchemas:
    def test_valid_create(self):
        h = HouseholdCreate(name="Smith Family", timezone="America/New_York")
        assert h.name == "Smith Family"
        assert h.timezone == "America/New_York"

    def test_default_timezone(self):
        h = HouseholdCreate(name="Test")
        assert h.timezone == "UTC"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            HouseholdCreate(name="")

    def test_update_partial(self):
        u = HouseholdUpdate(name="New Name")
        dumped = u.model_dump(exclude_unset=True)
        assert "name" in dumped
        assert "timezone" not in dumped

    def test_response_from_attributes(self):
        assert HouseholdResponse.model_config["from_attributes"] is True


class TestPersonSchemas:
    def test_valid_person(self):
        p = PersonCreate(name="Alice", role="adult")
        assert p.age_band is None

    def test_with_age_band(self):
        p = PersonCreate(name="Bob", role="child", age_band="teen")
        assert p.age_band == "teen"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            PersonCreate(name="", role="adult")

    def test_empty_role_rejected(self):
        with pytest.raises(ValidationError):
            PersonCreate(name="Alice", role="")

    def test_update_partial(self):
        u = PersonUpdate(name="Updated")
        dumped = u.model_dump(exclude_unset=True)
        assert dumped == {"name": "Updated"}


class TestAllergySchemas:
    def test_valid_allergy(self):
        a = AllergyCreate(
            person_id=uuid.uuid4(), allergen="peanuts", severity=AllergenSeverity.SEVERE
        )
        assert a.allergen == "peanuts"
        assert a.notes is None

    def test_empty_allergen_rejected(self):
        with pytest.raises(ValidationError):
            AllergyCreate(
                person_id=uuid.uuid4(), allergen="", severity=AllergenSeverity.MILD
            )


class TestScopeValidation:
    def test_dietary_rule_requires_scope(self):
        with pytest.raises(ValidationError, match="household_id or person_id"):
            DietaryRuleCreate(rule="vegetarian")

    def test_dietary_rule_with_household_id(self):
        r = DietaryRuleCreate(household_id=uuid.uuid4(), rule="vegetarian")
        assert r.person_id is None

    def test_dietary_rule_with_person_id(self):
        r = DietaryRuleCreate(person_id=uuid.uuid4(), rule="keto")
        assert r.household_id is None

    def test_dietary_rule_with_both_ids(self):
        r = DietaryRuleCreate(
            household_id=uuid.uuid4(), person_id=uuid.uuid4(), rule="halal"
        )
        assert r.household_id is not None
        assert r.person_id is not None

    def test_food_preference_requires_scope(self):
        with pytest.raises(ValidationError, match="household_id or person_id"):
            FoodPreferenceCreate(item="broccoli", preference=PreferenceLevel.LIKE)

    def test_food_preference_valid(self):
        fp = FoodPreferenceCreate(
            household_id=uuid.uuid4(),
            item="sushi",
            preference=PreferenceLevel.FAVORITE,
        )
        assert fp.preference == PreferenceLevel.FAVORITE

    def test_nutrition_goal_requires_scope(self):
        with pytest.raises(ValidationError, match="household_id or person_id"):
            NutritionGoalCreate(calories_min=2000)

    def test_nutrition_goal_valid(self):
        g = NutritionGoalCreate(
            household_id=uuid.uuid4(),
            calories_min=1800,
            calories_max=2200,
            protein_g=50.0,
        )
        assert g.calories_min == 1800

    def test_nutrition_goal_negative_rejected(self):
        with pytest.raises(ValidationError):
            NutritionGoalCreate(household_id=uuid.uuid4(), calories_min=-100)
