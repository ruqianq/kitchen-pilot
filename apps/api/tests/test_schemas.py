import pytest
from pydantic import ValidationError

from kitchen_pilot.schemas.plan import (
    DayPlan,
    DailyTotal,
    Ingredient,
    Meal,
    MealFlags,
    MealType,
    NutritionConfidence,
    NutritionInfo,
    RecipeRef,
    ShoppingList,
    WeeklyPlan,
)


def _make_meal(**overrides) -> dict:
    base = {
        "meal_type": "dinner",
        "title": "Chicken Stir Fry",
        "cook_time_min": 25,
        "servings": 4,
        "recipe": {"source": "manual"},
        "ingredients": [
            {"name": "chicken breast", "quantity": 500, "unit": "g"},
            {"name": "broccoli", "quantity": 2, "unit": "cups"},
            {"name": "soy sauce", "quantity": 2, "unit": "tbsp"},
        ],
        "nutrition": {
            "calories": 350,
            "protein_g": 35,
            "carbs_g": 15,
            "fat_g": 12,
            "fiber_g": 4,
            "confidence": "estimated",
            "source": "llm",
        },
        "flags": {},
    }
    base.update(overrides)
    return base


def _make_day_plan(date: str = "2026-02-16") -> dict:
    return {"date": date, "meals": [_make_meal()]}


class TestMealSchema:
    def test_valid_meal(self):
        meal = Meal(**_make_meal())
        assert meal.title == "Chicken Stir Fry"
        assert meal.meal_type == MealType.DINNER
        assert len(meal.ingredients) == 3

    def test_nutrition_constraints(self):
        with pytest.raises(ValidationError):
            Meal(**_make_meal(nutrition={
                "calories": -1, "protein_g": 0, "carbs_g": 0,
                "fat_g": 0, "fiber_g": 0, "confidence": "estimated", "source": "llm",
            }))

    def test_calories_upper_bound(self):
        with pytest.raises(ValidationError):
            Meal(**_make_meal(nutrition={
                "calories": 6000, "protein_g": 0, "carbs_g": 0,
                "fat_g": 0, "fiber_g": 0, "confidence": "estimated", "source": "llm",
            }))

    def test_cook_time_bounds(self):
        with pytest.raises(ValidationError):
            Meal(**_make_meal(cook_time_min=500))

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            Meal(**_make_meal(title=""))

    def test_empty_ingredients_rejected(self):
        with pytest.raises(ValidationError):
            Meal(**_make_meal(ingredients=[]))


class TestDayPlanSchema:
    def test_valid_day_plan(self):
        plan = DayPlan(**_make_day_plan())
        assert plan.date == "2026-02-16"
        assert len(plan.meals) == 1

    def test_empty_meals_rejected(self):
        with pytest.raises(ValidationError):
            DayPlan(date="2026-02-16", meals=[])


class TestWeeklyPlanSchema:
    def test_valid_weekly_plan(self):
        days = [_make_day_plan(f"2026-02-{16 + i}") for i in range(7)]
        plan = WeeklyPlan(week_start_date="2026-02-16", days=days)
        assert len(plan.days) == 7
        assert plan.shopping_list.items == []

    def test_wrong_day_count_rejected(self):
        days = [_make_day_plan(f"2026-02-{16 + i}") for i in range(5)]
        with pytest.raises(ValidationError):
            WeeklyPlan(week_start_date="2026-02-16", days=days)

    def test_roundtrip_json(self):
        days = [_make_day_plan(f"2026-02-{16 + i}") for i in range(7)]
        plan = WeeklyPlan(week_start_date="2026-02-16", days=days)
        json_str = plan.model_dump_json()
        restored = WeeklyPlan.model_validate_json(json_str)
        assert restored.week_start_date == plan.week_start_date
        assert len(restored.days) == 7


class TestNutritionInfo:
    def test_confidence_enum(self):
        info = NutritionInfo(
            calories=200, protein_g=20, carbs_g=30, fat_g=10, fiber_g=5,
            confidence=NutritionConfidence.EXACT, source="usda",
        )
        assert info.confidence == NutritionConfidence.EXACT

    def test_default_confidence(self):
        info = NutritionInfo(
            calories=200, protein_g=20, carbs_g=30, fat_g=10, fiber_g=5,
        )
        assert info.confidence == NutritionConfidence.ESTIMATED
        assert info.source == "llm"
