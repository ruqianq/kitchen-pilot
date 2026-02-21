"""Nutrition lookup service.

Provides USDA FoodData Central lookups with local caching,
unit-aware scaling, and graceful fallback to zeroed estimates.
"""

import logging
import re
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.config import settings
from kitchen_pilot.db.models import NutritionCache
from kitchen_pilot.schemas.nutrition import (
    NutritionLookupRequest,
    NutritionLookupResponse,
    RecipeNutritionResponse,
)
from kitchen_pilot.schemas.plan import (
    DayPlan,
    Meal,
    NutritionConfidence,
    NutritionInfo,
)

logger = logging.getLogger(__name__)

# USDA nutrient IDs → our field names
NUTRIENT_MAP: dict[int, str] = {
    1008: "calories",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carbs_g",
    1079: "fiber_g",
}

# Common unit → grams conversion
UNIT_GRAMS: dict[str, float] = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "oz": 28.35,
    "ounce": 28.35,
    "ounces": 28.35,
    "lb": 453.6,
    "lbs": 453.6,
    "pound": 453.6,
    "pounds": 453.6,
    "cup": 240.0,
    "cups": 240.0,
    "tbsp": 15.0,
    "tablespoon": 15.0,
    "tablespoons": 15.0,
    "tsp": 5.0,
    "teaspoon": 5.0,
    "teaspoons": 5.0,
    "ml": 1.0,
    "milliliter": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "serving": 100.0,
    "servings": 100.0,
    "piece": 100.0,
    "pieces": 100.0,
    "slice": 30.0,
    "slices": 30.0,
    "clove": 3.0,
    "cloves": 3.0,
}

CACHE_TTL = timedelta(days=30)

# Pattern to strip leading quantities like "2 cups", "1.5", etc.
_QUANTITY_RE = re.compile(r"^\s*[\d./]+\s*")
# Pattern to strip common units from the beginning
_UNIT_RE = re.compile(
    r"^(cups?|tbsp|tsp|tablespoons?|teaspoons?|oz|ounces?|lbs?|pounds?"
    r"|grams?|kg|ml|liters?|servings?|pieces?|slices?|cloves?|cans?|large|medium|small)\b\s*",
    re.IGNORECASE,
)


# ── Normalization ─────────────────────────────────────────


def normalize_food(name: str) -> str:
    """Normalize a food name for cache lookups.

    Strips quantities, units, and extra whitespace. Lowercases.
    """
    result = name.strip().lower()
    # Remove leading numbers (e.g. "2 cups brown rice" → "cups brown rice")
    result = _QUANTITY_RE.sub("", result)
    # Remove leading unit words (e.g. "cups brown rice" → "brown rice")
    result = _UNIT_RE.sub("", result)
    # Collapse whitespace
    result = " ".join(result.split())
    return result


# ── USDA API ──────────────────────────────────────────────


async def _usda_search(food: str) -> list[dict] | None:
    """Search USDA FoodData Central for a food item.

    Returns the first result's foodNutrients list, or None on failure.
    """
    if not settings.usda_api_key:
        return None

    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={settings.usda_api_key}"
    body = {
        "query": food,
        "pageSize": 1,
        "dataType": ["Survey (FNDDS)", "SR Legacy"],
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

        foods = data.get("foods", [])
        if not foods:
            return None
        return foods[0].get("foodNutrients")
    except Exception:
        logger.warning("USDA API search failed for %r", food, exc_info=True)
        return None


def _extract_per100g(nutrients: list[dict]) -> NutritionInfo:
    """Extract per-100g nutrition from USDA foodNutrients list."""
    values: dict[str, float] = {
        "calories": 0,
        "protein_g": 0,
        "fat_g": 0,
        "carbs_g": 0,
        "fiber_g": 0,
    }

    for n in nutrients:
        nutrient_id = n.get("nutrientId")
        if nutrient_id in NUTRIENT_MAP:
            field = NUTRIENT_MAP[nutrient_id]
            values[field] = n.get("value", 0) or 0

    return NutritionInfo(
        calories=int(round(values["calories"])),
        protein_g=round(values["protein_g"], 1),
        carbs_g=round(values["carbs_g"], 1),
        fat_g=round(values["fat_g"], 1),
        fiber_g=round(values["fiber_g"], 1),
        confidence=NutritionConfidence.EXACT,
        source="usda",
    )


def _scale_nutrition(
    per100g: NutritionInfo, quantity: float, unit: str
) -> NutritionInfo:
    """Scale per-100g nutrition values to the requested quantity/unit."""
    unit_lower = unit.strip().lower()
    grams_per_unit = UNIT_GRAMS.get(unit_lower, 100.0)  # default: 100g per serving
    total_grams = quantity * grams_per_unit
    factor = total_grams / 100.0

    return NutritionInfo(
        calories=int(round(per100g.calories * factor)),
        protein_g=round(per100g.protein_g * factor, 1),
        carbs_g=round(per100g.carbs_g * factor, 1),
        fat_g=round(per100g.fat_g * factor, 1),
        fiber_g=round(per100g.fiber_g * factor, 1),
        confidence=per100g.confidence,
        source=per100g.source,
    )


# ── Cache ─────────────────────────────────────────────────


async def _check_cache(
    session: AsyncSession, normalized: str
) -> NutritionInfo | None:
    """Check NutritionCache for a previously fetched result."""
    result = await session.execute(
        select(NutritionCache).where(NutritionCache.normalized_food == normalized)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None

    # Check TTL
    if row.fetched_at < datetime.now(UTC) - CACHE_TTL:
        return None

    data = row.nutrition_json
    if data is None:
        return None

    return NutritionInfo(
        calories=data.get("calories", 0),
        protein_g=data.get("protein_g", 0),
        carbs_g=data.get("carbs_g", 0),
        fat_g=data.get("fat_g", 0),
        fiber_g=data.get("fiber_g", 0),
        confidence=NutritionConfidence(data.get("confidence", "exact")),
        source=data.get("source", "usda"),
    )


async def _write_cache(
    session: AsyncSession,
    query: str,
    normalized: str,
    info: NutritionInfo,
) -> None:
    """Upsert a nutrition cache entry (stores per-100g values)."""
    result = await session.execute(
        select(NutritionCache).where(NutritionCache.normalized_food == normalized)
    )
    existing = result.scalar_one_or_none()

    data = info.model_dump()

    if existing:
        existing.query = query
        existing.nutrition_json = data
        existing.source = info.source
        existing.confidence = info.confidence.value
        existing.fetched_at = datetime.now(UTC)
    else:
        session.add(
            NutritionCache(
                query=query,
                normalized_food=normalized,
                nutrition_json=data,
                source=info.source,
                confidence=info.confidence.value,
                fetched_at=datetime.now(UTC),
            )
        )

    await session.flush()


# ── Public API ────────────────────────────────────────────


def _zeroed_nutrition() -> NutritionInfo:
    """Return a zeroed NutritionInfo with estimated confidence."""
    return NutritionInfo(
        calories=0,
        protein_g=0,
        carbs_g=0,
        fat_g=0,
        fiber_g=0,
        confidence=NutritionConfidence.ESTIMATED,
        source="estimated",
    )


async def lookup_food(
    session: AsyncSession,
    food: str,
    quantity: float = 1.0,
    unit: str = "serving",
) -> NutritionLookupResponse:
    """Look up nutrition for a food item.

    Pipeline: cache → USDA API → zeroed fallback.
    """
    normalized = normalize_food(food)

    # 1. Check cache
    cached = await _check_cache(session, normalized)
    if cached is not None:
        scaled = _scale_nutrition(cached, quantity, unit)
        return NutritionLookupResponse(
            food=food,
            normalized_food=normalized,
            nutrition=scaled,
            confidence=scaled.confidence,
            source=scaled.source,
        )

    # 2. USDA API
    nutrients = await _usda_search(normalized)
    if nutrients is not None:
        per100g = _extract_per100g(nutrients)
        await _write_cache(session, food, normalized, per100g)
        scaled = _scale_nutrition(per100g, quantity, unit)
        return NutritionLookupResponse(
            food=food,
            normalized_food=normalized,
            nutrition=scaled,
            confidence=scaled.confidence,
            source=scaled.source,
        )

    # 3. Fallback
    fallback = _zeroed_nutrition()
    return NutritionLookupResponse(
        food=food,
        normalized_food=normalized,
        nutrition=fallback,
        confidence=fallback.confidence,
        source=fallback.source,
    )


async def estimate_recipe(
    session: AsyncSession,
    ingredients: list[NutritionLookupRequest],
    servings: int = 1,
) -> RecipeNutritionResponse:
    """Estimate nutrition for a recipe from its ingredients."""
    details = []
    total_cal = 0
    total_pro = 0.0
    total_carb = 0.0
    total_fat = 0.0
    total_fib = 0.0

    for ing in ingredients:
        result = await lookup_food(session, ing.food, ing.quantity, ing.unit)
        details.append(result)
        total_cal += result.nutrition.calories
        total_pro += result.nutrition.protein_g
        total_carb += result.nutrition.carbs_g
        total_fat += result.nutrition.fat_g
        total_fib += result.nutrition.fiber_g

    total = NutritionInfo(
        calories=total_cal,
        protein_g=round(total_pro, 1),
        carbs_g=round(total_carb, 1),
        fat_g=round(total_fat, 1),
        fiber_g=round(total_fib, 1),
        confidence=NutritionConfidence.EXACT
        if any(d.confidence == NutritionConfidence.EXACT for d in details)
        else NutritionConfidence.ESTIMATED,
        source="usda" if any(d.source == "usda" for d in details) else "estimated",
    )

    per_serving = NutritionInfo(
        calories=int(round(total_cal / servings)),
        protein_g=round(total_pro / servings, 1),
        carbs_g=round(total_carb / servings, 1),
        fat_g=round(total_fat / servings, 1),
        fiber_g=round(total_fib / servings, 1),
        confidence=total.confidence,
        source=total.source,
    )

    return RecipeNutritionResponse(
        per_serving=per_serving,
        total=total,
        ingredient_details=details,
    )


# ── Plan Refinement ───────────────────────────────────────


async def refine_meal_nutrition(session: AsyncSession, meal: Meal) -> Meal:
    """Refine a meal's nutrition using USDA data for its ingredients.

    If at least one ingredient has USDA data, replaces the LLM estimate.
    Otherwise keeps the original nutrition unchanged.
    """
    total_cal = 0
    total_pro = 0.0
    total_carb = 0.0
    total_fat = 0.0
    total_fib = 0.0
    has_usda = False

    for ing in meal.ingredients:
        result = await lookup_food(session, ing.name, ing.quantity, ing.unit)
        if result.source == "usda":
            has_usda = True
        total_cal += result.nutrition.calories
        total_pro += result.nutrition.protein_g
        total_carb += result.nutrition.carbs_g
        total_fat += result.nutrition.fat_g
        total_fib += result.nutrition.fiber_g

    if not has_usda:
        return meal

    meal.nutrition = NutritionInfo(
        calories=total_cal,
        protein_g=round(total_pro, 1),
        carbs_g=round(total_carb, 1),
        fat_g=round(total_fat, 1),
        fiber_g=round(total_fib, 1),
        confidence=NutritionConfidence.EXACT,
        source="usda",
    )
    return meal


async def refine_day_nutrition(session: AsyncSession, day_plan: DayPlan) -> DayPlan:
    """Refine nutrition for all meals in a day plan using USDA data."""
    for i, meal in enumerate(day_plan.meals):
        try:
            day_plan.meals[i] = await refine_meal_nutrition(session, meal)
        except Exception:
            logger.warning(
                "Nutrition refinement failed for meal %r", meal.title, exc_info=True
            )
    return day_plan
