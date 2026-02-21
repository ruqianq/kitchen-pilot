"""Tests for the nutrition service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kitchen_pilot.schemas.plan import (
    Ingredient,
    Meal,
    MealType,
    NutritionConfidence,
    NutritionInfo,
)
from kitchen_pilot.services import nutrition


# ── normalize_food ────────────────────────────────────────


def test_normalize_food_basic():
    assert nutrition.normalize_food("Chicken Breast") == "chicken breast"


def test_normalize_food_strips_quantity():
    assert nutrition.normalize_food("2 cups brown rice") == "brown rice"


def test_normalize_food_strips_quantity_and_unit():
    assert nutrition.normalize_food("1.5 tbsp olive oil") == "olive oil"


def test_normalize_food_extra_whitespace():
    assert nutrition.normalize_food("  garlic   cloves  ") == "garlic cloves"


def test_normalize_food_no_quantity():
    assert nutrition.normalize_food("spinach") == "spinach"


# ── _extract_per100g ──────────────────────────────────────


SAMPLE_USDA_NUTRIENTS = [
    {"nutrientId": 1008, "value": 165.0},  # calories
    {"nutrientId": 1003, "value": 31.0},  # protein
    {"nutrientId": 1004, "value": 3.6},  # fat
    {"nutrientId": 1005, "value": 0.0},  # carbs
    {"nutrientId": 1079, "value": 0.0},  # fiber
    {"nutrientId": 9999, "value": 99.0},  # should be ignored
]


def test_extract_per100g():
    result = nutrition._extract_per100g(SAMPLE_USDA_NUTRIENTS)
    assert result.calories == 165
    assert result.protein_g == 31.0
    assert result.fat_g == 3.6
    assert result.carbs_g == 0.0
    assert result.fiber_g == 0.0
    assert result.confidence == NutritionConfidence.EXACT
    assert result.source == "usda"


def test_extract_per100g_missing_nutrients():
    """Missing nutrient IDs should default to 0."""
    result = nutrition._extract_per100g([{"nutrientId": 1008, "value": 200}])
    assert result.calories == 200
    assert result.protein_g == 0.0
    assert result.fat_g == 0.0


# ── _scale_nutrition ──────────────────────────────────────


def _make_per100g(**kwargs) -> NutritionInfo:
    defaults = {
        "calories": 100,
        "protein_g": 10.0,
        "carbs_g": 20.0,
        "fat_g": 5.0,
        "fiber_g": 3.0,
        "confidence": NutritionConfidence.EXACT,
        "source": "usda",
    }
    defaults.update(kwargs)
    return NutritionInfo(**defaults)


def test_scale_nutrition_grams():
    per100g = _make_per100g()
    scaled = nutrition._scale_nutrition(per100g, 200, "g")
    assert scaled.calories == 200
    assert scaled.protein_g == 20.0
    assert scaled.fat_g == 10.0


def test_scale_nutrition_cup():
    per100g = _make_per100g()
    # 1 cup = 240g → factor = 2.4
    scaled = nutrition._scale_nutrition(per100g, 1, "cup")
    assert scaled.calories == 240
    assert scaled.protein_g == 24.0


def test_scale_nutrition_tbsp():
    per100g = _make_per100g()
    # 1 tbsp = 15g → factor = 0.15
    scaled = nutrition._scale_nutrition(per100g, 1, "tbsp")
    assert scaled.calories == 15
    assert scaled.protein_g == 1.5


def test_scale_nutrition_unknown_unit():
    """Unknown units default to 100g per unit."""
    per100g = _make_per100g()
    scaled = nutrition._scale_nutrition(per100g, 2, "handful")
    # 2 * 100g = 200g → factor = 2.0
    assert scaled.calories == 200
    assert scaled.protein_g == 20.0


# ── lookup_food ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_lookup_food_cache_hit():
    session = AsyncMock()
    cached = _make_per100g()

    with (
        patch.object(nutrition, "_check_cache", new_callable=AsyncMock) as mock_cache,
        patch.object(nutrition, "_usda_search", new_callable=AsyncMock) as mock_usda,
    ):
        mock_cache.return_value = cached
        result = await nutrition.lookup_food(session, "chicken breast", 200, "g")

    assert result.source == "usda"
    assert result.nutrition.calories == 200
    mock_usda.assert_not_called()


@pytest.mark.asyncio
async def test_lookup_food_usda_hit():
    session = AsyncMock()

    with (
        patch.object(nutrition, "_check_cache", new_callable=AsyncMock) as mock_cache,
        patch.object(nutrition, "_usda_search", new_callable=AsyncMock) as mock_usda,
        patch.object(
            nutrition, "_write_cache", new_callable=AsyncMock
        ) as mock_write,
    ):
        mock_cache.return_value = None
        mock_usda.return_value = SAMPLE_USDA_NUTRIENTS
        result = await nutrition.lookup_food(session, "chicken breast", 100, "g")

    assert result.source == "usda"
    assert result.nutrition.calories == 165
    mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_lookup_food_fallback():
    session = AsyncMock()

    with (
        patch.object(nutrition, "_check_cache", new_callable=AsyncMock) as mock_cache,
        patch.object(nutrition, "_usda_search", new_callable=AsyncMock) as mock_usda,
    ):
        mock_cache.return_value = None
        mock_usda.return_value = None
        result = await nutrition.lookup_food(session, "mystery food", 1, "serving")

    assert result.confidence == NutritionConfidence.ESTIMATED
    assert result.source == "estimated"
    assert result.nutrition.calories == 0


# ── estimate_recipe ───────────────────────────────────────


@pytest.mark.asyncio
async def test_estimate_recipe():
    session = AsyncMock()
    cached = _make_per100g(calories=200, protein_g=20.0, carbs_g=10.0, fat_g=5.0, fiber_g=2.0)

    with patch.object(nutrition, "_check_cache", new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = cached

        from kitchen_pilot.schemas.nutrition import NutritionLookupRequest

        ingredients = [
            NutritionLookupRequest(food="chicken", quantity=100, unit="g"),
            NutritionLookupRequest(food="rice", quantity=100, unit="g"),
        ]
        result = await nutrition.estimate_recipe(session, ingredients, servings=2)

    assert result.total.calories == 400
    assert result.per_serving.calories == 200
    assert len(result.ingredient_details) == 2


# ── refine_meal_nutrition ─────────────────────────────────


def _make_meal() -> Meal:
    return Meal(
        meal_type=MealType.LUNCH,
        title="Grilled Chicken Salad",
        cook_time_min=20,
        servings=2,
        ingredients=[
            Ingredient(name="chicken breast", quantity=200, unit="g"),
            Ingredient(name="mixed greens", quantity=100, unit="g"),
        ],
        nutrition=NutritionInfo(
            calories=350,
            protein_g=30.0,
            carbs_g=10.0,
            fat_g=15.0,
            fiber_g=3.0,
            confidence=NutritionConfidence.ESTIMATED,
            source="llm",
        ),
    )


@pytest.mark.asyncio
async def test_refine_meal_replaces_llm():
    session = AsyncMock()
    meal = _make_meal()
    cached = _make_per100g()

    with patch.object(nutrition, "_check_cache", new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = cached
        refined = await nutrition.refine_meal_nutrition(session, meal)

    assert refined.nutrition.source == "usda"
    assert refined.nutrition.confidence == NutritionConfidence.EXACT
    # 200g chicken (factor 2) + 100g greens (factor 1) = 300 cal
    assert refined.nutrition.calories == 300


@pytest.mark.asyncio
async def test_refine_meal_keeps_llm_on_failure():
    session = AsyncMock()
    meal = _make_meal()

    with (
        patch.object(nutrition, "_check_cache", new_callable=AsyncMock) as mock_cache,
        patch.object(nutrition, "_usda_search", new_callable=AsyncMock) as mock_usda,
    ):
        mock_cache.return_value = None
        mock_usda.return_value = None
        refined = await nutrition.refine_meal_nutrition(session, meal)

    # No USDA data found → keeps original LLM estimate
    assert refined.nutrition.source == "llm"
    assert refined.nutrition.calories == 350
