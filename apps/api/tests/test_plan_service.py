"""Tests for the plan generation service.

Tests the deterministic parts of the pipeline (prompt construction,
validation, post-processing). LLM calls are not tested here.
"""

import pytest

from kitchen_pilot.schemas.plan import (
    DailyTotal,
    DayPlan,
    Ingredient,
    Meal,
    MealFlags,
    MealType,
    NutritionConfidence,
    NutritionInfo,
    RecipeRef,
    ShoppingItem,
)
from kitchen_pilot.schemas.household import (
    AllergySchema,
    DietaryRuleSchema,
    FoodPreferenceSchema,
    HouseholdContext,
    NutritionGoalSchema,
    PersonSchema,
)
from kitchen_pilot.services.plan import (
    _aggregate_shopping_list,
    _build_day_prompt,
    _build_system_prompt,
    _compute_daily_totals,
    _validate_allergy_compliance,
)


def _make_context(**overrides) -> HouseholdContext:
    defaults = {
        "household_name": "Test Family",
        "timezone": "America/Los_Angeles",
        "people": [PersonSchema(name="Alice", role="adult")],
        "allergies": [],
        "dietary_rules": [],
        "preferences": [],
        "nutrition_goals": [],
    }
    defaults.update(overrides)
    return HouseholdContext(**defaults)


def _make_meal(title="Test Meal", ingredients=None, **kwargs) -> Meal:
    return Meal(
        meal_type=kwargs.get("meal_type", MealType.DINNER),
        title=title,
        cook_time_min=25,
        servings=4,
        recipe=RecipeRef(),
        ingredients=ingredients
        or [Ingredient(name="chicken breast", quantity=500, unit="g")],
        nutrition=NutritionInfo(
            calories=350,
            protein_g=35,
            carbs_g=15,
            fat_g=12,
            fiber_g=4,
            confidence=NutritionConfidence.ESTIMATED,
            source="llm",
        ),
        flags=kwargs.get("flags", MealFlags()),
    )


def _make_day_plan(dt="2026-02-16", meals=None) -> DayPlan:
    return DayPlan(date=dt, meals=meals or [_make_meal()])


class TestPromptConstruction:
    def test_system_prompt_includes_household_name(self):
        ctx = _make_context()
        prompt = _build_system_prompt(ctx)
        assert "Test Family" in prompt

    def test_system_prompt_includes_people(self):
        ctx = _make_context(
            people=[
                PersonSchema(name="Alice", role="adult"),
                PersonSchema(name="Bob", role="child", age_band="teen"),
            ]
        )
        prompt = _build_system_prompt(ctx)
        assert "Alice" in prompt
        assert "Bob" in prompt
        assert "teen" in prompt

    def test_system_prompt_includes_allergies(self):
        ctx = _make_context(
            allergies=[
                AllergySchema(
                    person_name="Alice", allergen="peanuts", severity="severe"
                ),
            ]
        )
        prompt = _build_system_prompt(ctx)
        assert "peanuts" in prompt
        assert "CRITICAL" in prompt

    def test_system_prompt_includes_dietary_rules(self):
        ctx = _make_context(
            dietary_rules=[
                DietaryRuleSchema(scope="household", rule="No red meat"),
            ]
        )
        prompt = _build_system_prompt(ctx)
        assert "No red meat" in prompt

    def test_system_prompt_includes_preferences(self):
        ctx = _make_context(
            preferences=[
                FoodPreferenceSchema(
                    scope="Alice", item="pasta", preference="favorite"
                ),
            ]
        )
        prompt = _build_system_prompt(ctx)
        assert "pasta" in prompt
        assert "favorite" in prompt

    def test_system_prompt_includes_nutrition_goals(self):
        ctx = _make_context(
            nutrition_goals=[
                NutritionGoalSchema(
                    scope="household", calories_min=1800, protein_g=100
                ),
            ]
        )
        prompt = _build_system_prompt(ctx)
        assert "1800" in prompt
        assert "100" in prompt

    def test_day_prompt_includes_date(self):
        prompt = _build_day_prompt("2026-02-16", 0, [], None, None)
        assert "2026-02-16" in prompt

    def test_day_prompt_includes_previous_dinners(self):
        prompt = _build_day_prompt("2026-02-17", 1, ["Pasta Primavera"], None, None)
        assert "Pasta Primavera" in prompt

    def test_day_prompt_includes_cook_time_constraint(self):
        prompt = _build_day_prompt("2026-02-16", 0, [], 30, None)
        assert "30 minutes" in prompt

    def test_day_prompt_includes_notes(self):
        prompt = _build_day_prompt("2026-02-16", 0, [], None, "high protein")
        assert "high protein" in prompt


class TestAllergyValidation:
    def test_clean_plan_passes(self):
        plan = _make_day_plan()
        violations, warnings = _validate_allergy_compliance(plan, ["peanuts"])
        assert violations == []

    def test_detects_allergen_in_ingredient(self):
        plan = _make_day_plan(
            meals=[
                _make_meal(
                    ingredients=[
                        Ingredient(name="peanut butter", quantity=2, unit="tbsp"),
                    ]
                ),
            ]
        )
        violations, warnings = _validate_allergy_compliance(plan, ["peanut"])
        assert len(violations) > 0
        assert "peanut" in violations[0].lower()

    def test_case_insensitive(self):
        plan = _make_day_plan(
            meals=[
                _make_meal(
                    ingredients=[
                        Ingredient(name="PEANUT OIL", quantity=1, unit="tbsp"),
                    ]
                ),
            ]
        )
        violations, warnings = _validate_allergy_compliance(plan, ["peanut"])
        assert len(violations) > 0

    def test_no_false_positive(self):
        plan = _make_day_plan(
            meals=[
                _make_meal(
                    ingredients=[
                        Ingredient(name="olive oil", quantity=1, unit="tbsp"),
                    ]
                ),
            ]
        )
        violations, warnings = _validate_allergy_compliance(plan, ["peanut"])
        assert violations == []

    def test_llm_flagged_warnings_are_warnings_not_violations(self):
        plan = _make_day_plan(
            meals=[
                _make_meal(
                    flags=MealFlags(
                        allergen_warnings=["May contain traces of nuts"]
                    ),
                ),
            ]
        )
        violations, warnings = _validate_allergy_compliance(plan, ["nuts"])
        assert violations == []
        assert len(warnings) > 0


class TestDailyTotals:
    def test_single_meal_totals(self):
        plans = [_make_day_plan()]
        totals = _compute_daily_totals(plans)
        assert len(totals) == 1
        assert totals[0].calories == 350
        assert totals[0].protein_g == 35

    def test_multiple_meals_sum(self):
        meals = [_make_meal(title="First"), _make_meal(title="Second")]
        plans = [_make_day_plan(meals=meals)]
        totals = _compute_daily_totals(plans)
        assert totals[0].calories == 700
        assert totals[0].protein_g == 70

    def test_multiple_days(self):
        plans = [_make_day_plan("2026-02-16"), _make_day_plan("2026-02-17")]
        totals = _compute_daily_totals(plans)
        assert len(totals) == 2
        assert totals[0].date == "2026-02-16"
        assert totals[1].date == "2026-02-17"


class TestShoppingListAggregation:
    def test_aggregates_same_ingredient(self):
        plans = [
            _make_day_plan("2026-02-16"),
            _make_day_plan("2026-02-17"),
        ]
        shopping = _aggregate_shopping_list(plans)
        chicken = [i for i in shopping.items if "chicken" in i.name.lower()]
        assert len(chicken) == 1
        assert chicken[0].quantity == 1000

    def test_categorizes_meat(self):
        plan = _make_day_plan()
        shopping = _aggregate_shopping_list([plan])
        chicken = [i for i in shopping.items if "chicken" in i.name.lower()]
        assert chicken[0].category == "Meat"

    def test_categorizes_produce(self):
        plan = _make_day_plan(
            meals=[
                _make_meal(
                    ingredients=[
                        Ingredient(name="broccoli", quantity=2, unit="cups"),
                    ]
                ),
            ]
        )
        shopping = _aggregate_shopping_list([plan])
        assert shopping.items[0].category == "Produce"

    def test_different_units_not_merged(self):
        plan = _make_day_plan(
            meals=[
                _make_meal(
                    ingredients=[
                        Ingredient(name="chicken breast", quantity=500, unit="g"),
                        Ingredient(name="chicken breast", quantity=2, unit="pieces"),
                    ]
                ),
            ]
        )
        shopping = _aggregate_shopping_list([plan])
        chicken = [i for i in shopping.items if "chicken" in i.name.lower()]
        assert len(chicken) == 2
