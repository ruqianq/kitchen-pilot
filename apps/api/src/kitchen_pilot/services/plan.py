"""Plan generation service.

Orchestrates the per-day decomposition pipeline:
  1. Load household context
  2. Generate DayPlan x 7 via LLM
  3. Validate allergy compliance
  4. Compute daily totals
  5. Aggregate shopping list
  6. Persist to DB
"""

import logging
import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kitchen_pilot.db.models import (
    Meal as MealModel,
)
from kitchen_pilot.db.models import (
    PlanStatus,
)
from kitchen_pilot.db.models import (
    ShoppingList as ShoppingListModel,
)
from kitchen_pilot.db.models import (
    WeeklyPlan as WeeklyPlanModel,
)
from kitchen_pilot.schemas.household import HouseholdContext
from kitchen_pilot.schemas.plan import (
    ConstraintOverride,
    DailyTotal,
    DayPlan,
    ShoppingItem,
    ShoppingList,
    WeeklyPlan,
)
from kitchen_pilot.services.household import get_household_context
from kitchen_pilot.services.llm import generate_structured
from kitchen_pilot.services.nutrition import refine_day_nutrition

logger = logging.getLogger(__name__)


# ── Prompt Construction ───────────────────────────────────


def _build_system_prompt(ctx: HouseholdContext) -> str:
    """Build the system prompt from household context."""
    lines = [
        "You are Kitchen Pilot, a meal planning assistant.",
        "Generate a meal plan for ONE DAY for the following household.",
        "",
        f"Household: {ctx.household_name} (timezone: {ctx.timezone})",
        f"Members: {len(ctx.people)}",
    ]

    for p in ctx.people:
        lines.append(f"  - {p.name} ({p.role}, age band: {p.age_band or 'adult'})")

    if ctx.allergies:
        lines.append("")
        lines.append("CRITICAL ALLERGIES (MUST AVOID these ingredients):")
        for a in ctx.allergies:
            lines.append(
                f"  - {a.person_name}: {a.allergen} (severity: {a.severity})"
            )

    if ctx.dietary_rules:
        lines.append("")
        lines.append("Dietary rules:")
        for r in ctx.dietary_rules:
            lines.append(f"  - [{r.scope}] {r.rule}")

    if ctx.preferences:
        lines.append("")
        lines.append("Food preferences:")
        for p in ctx.preferences:
            lines.append(f"  - [{p.scope}] {p.item}: {p.preference}")

    if ctx.nutrition_goals:
        lines.append("")
        lines.append("Nutrition goals (try to meet these):")
        for g in ctx.nutrition_goals:
            parts = []
            if g.calories_min is not None:
                parts.append(f"min {g.calories_min} cal")
            if g.calories_max is not None:
                parts.append(f"max {g.calories_max} cal")
            if g.protein_g is not None:
                parts.append(f"{g.protein_g}g protein")
            if g.carbs_g is not None:
                parts.append(f"{g.carbs_g}g carbs")
            if g.fat_g is not None:
                parts.append(f"{g.fat_g}g fat")
            if g.fiber_g is not None:
                parts.append(f"{g.fiber_g}g fiber")
            if parts:
                lines.append(f"  - [{g.scope}] {', '.join(parts)}")

    lines.extend(
        [
            "",
            "Requirements:",
            "- Generate breakfast, lunch, and dinner for the given date.",
            "- Include realistic ingredient quantities and nutrition estimates.",
            "- NEVER include any allergen from the allergies list above.",
            "- Respect dietary rules strictly.",
            "- Try to incorporate food preferences (likes/favorites).",
            "- Each meal must have at least one ingredient.",
            "- Nutrition values should be reasonable estimates.",
        ]
    )

    return "\n".join(lines)


def _build_day_prompt(
    target_date: str,
    day_index: int,
    previous_meals: list[str],
    max_cook_time: int | None,
    notes: str | None,
) -> str:
    """Build the user message for a specific day."""
    lines = [f"Plan meals for {target_date} (day {day_index + 1} of 7)."]

    if previous_meals:
        lines.append("")
        lines.append("Previous days' dinners (avoid repetition):")
        for m in previous_meals[-3:]:
            lines.append(f"  - {m}")

    if max_cook_time:
        lines.append(f"\nMaximum cook time per meal: {max_cook_time} minutes.")

    if notes:
        lines.append(f"\nAdditional instructions: {notes}")

    lines.append(f"\nGenerate the meal plan for {target_date}.")
    return "\n".join(lines)


# ── Validation ────────────────────────────────────────────


def _validate_allergy_compliance(
    day_plan: DayPlan,
    allergens: list[str],
) -> tuple[list[str], list[str]]:
    """Check if any meal contains a known allergen.

    Returns (violations, warnings). Violations are hard-blocks (allergen found
    in ingredient name). Warnings are informational (LLM-flagged notes).
    """
    violations = []
    warnings = []
    allergen_set = {a.lower() for a in allergens}

    for meal in day_plan.meals:
        for ingredient in meal.ingredients:
            ing_lower = ingredient.name.lower()
            for allergen in allergen_set:
                if allergen in ing_lower:
                    violations.append(
                        f"{meal.title}: ingredient '{ingredient.name}' "
                        f"may contain allergen '{allergen}'"
                    )
        for warning in meal.flags.allergen_warnings:
            warnings.append(
                f"{meal.title}: LLM allergen note: {warning}"
            )

    return violations, warnings


# ── Post-processing ───────────────────────────────────────


def _compute_daily_totals(day_plans: list[DayPlan]) -> list[DailyTotal]:
    """Sum nutrition across all meals for each day."""
    totals = []
    for day in day_plans:
        cal = sum(m.nutrition.calories for m in day.meals)
        pro = sum(m.nutrition.protein_g for m in day.meals)
        carb = sum(m.nutrition.carbs_g for m in day.meals)
        fat = sum(m.nutrition.fat_g for m in day.meals)
        fib = sum(m.nutrition.fiber_g for m in day.meals)
        totals.append(
            DailyTotal(
                date=day.date,
                calories=cal,
                protein_g=pro,
                carbs_g=carb,
                fat_g=fat,
                fiber_g=fib,
            )
        )
    return totals


CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "produce": [
        "lettuce", "tomato", "onion", "garlic", "pepper", "broccoli",
        "carrot", "spinach", "potato", "avocado", "lemon", "lime",
        "banana", "apple", "berry", "mushroom", "celery", "cucumber",
        "zucchini", "kale", "cabbage", "corn", "pea", "bean sprout",
    ],
    "meat": [
        "chicken", "beef", "pork", "turkey", "lamb", "fish", "salmon",
        "shrimp", "tuna", "bacon", "sausage", "ground meat", "steak",
    ],
    "dairy": [
        "milk", "cheese", "yogurt", "butter", "cream", "egg", "sour cream",
    ],
    "spices": [
        "salt", "pepper", "cumin", "paprika", "oregano", "basil",
        "thyme", "cinnamon", "chili", "ginger", "turmeric", "nutmeg",
    ],
    "pantry": [
        "rice", "pasta", "flour", "sugar", "oil", "vinegar", "soy sauce",
        "bread", "tortilla", "bean", "lentil", "oat", "honey", "stock",
        "broth", "can", "sauce",
    ],
}


def _categorize(name: str) -> str:
    name_lower = name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return category.capitalize()
    return "Other"


def _aggregate_shopping_list(day_plans: list[DayPlan]) -> ShoppingList:
    """Aggregate all ingredients across 7 days into a shopping list."""
    aggregated: dict[tuple[str, str], float] = defaultdict(float)

    for day in day_plans:
        for meal in day.meals:
            for ing in meal.ingredients:
                key = (ing.name.lower().strip(), ing.unit.lower().strip())
                aggregated[key] += ing.quantity

    items = []
    for (name, unit), quantity in sorted(aggregated.items()):
        items.append(
            ShoppingItem(
                name=name.title(),
                quantity=round(quantity, 2),
                unit=unit,
                category=_categorize(name),
            )
        )

    return ShoppingList(items=items)


# ── Generation Pipeline ───────────────────────────────────


async def generate_plan(
    session: AsyncSession,
    household_id: uuid.UUID,
    week_start_date: str,
    overrides: list[ConstraintOverride] | None = None,
    max_cook_time_min: int | None = None,
    notes: str | None = None,
) -> tuple[WeeklyPlanModel, list[str], list[str]]:
    """Generate a weekly meal plan.

    Returns (db_plan, warnings, errors).

    Pipeline:
      1. Load household context
      2. Build system prompt
      3. For each of 7 days, call generate_structured(DayPlan)
      4. Validate allergy compliance
      5. Compute daily totals + aggregate shopping list
      6. Persist to DB
    """
    warnings: list[str] = []
    errors: list[str] = []

    # 1. Load context
    ctx = await get_household_context(session)
    allergens = [a.allergen for a in ctx.allergies]
    override_types = {o.constraint_type for o in (overrides or [])}

    # 2. Build system prompt
    system_prompt = _build_system_prompt(ctx)

    # 3. Generate 7 DayPlans
    start = date.fromisoformat(week_start_date)
    day_plans: list[DayPlan] = []
    previous_dinners: list[str] = []

    for i in range(7):
        target = start + timedelta(days=i)
        target_str = target.isoformat()

        user_prompt = _build_day_prompt(
            target_date=target_str,
            day_index=i,
            previous_meals=previous_dinners,
            max_cook_time=max_cook_time_min,
            notes=notes,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            day_plan = await generate_structured(
                response_model=DayPlan,
                messages=messages,
                max_retries=3,
                temperature=0,
            )
            # Force correct date (LLM might get it wrong)
            day_plan.date = target_str
        except Exception as e:
            logger.error("Failed to generate day plan for %s: %s", target_str, e)
            raise RuntimeError(
                f"Plan generation failed for {target_str}: {e}"
            ) from e

        # 4. Allergy validation
        violations, allergy_notes = _validate_allergy_compliance(day_plan, allergens)
        if violations and "allergy" not in override_types:
            raise ValueError(
                f"Allergy compliance check failed for {target_str}. "
                f"Violations: {violations}. "
                f"Provide an 'allergy' override to proceed."
            )
        elif violations:
            for v in violations:
                warnings.append(f"Allergy warning (overridden): {v}")
        for note in allergy_notes:
            warnings.append(note)

        # 4b. Nutrition refinement (USDA lookup)
        try:
            day_plan = await refine_day_nutrition(session, day_plan)
        except Exception as e:
            logger.warning("Nutrition refinement failed for %s: %s", target_str, e)

        day_plans.append(day_plan)

        # Track dinners for variety
        for meal in day_plan.meals:
            if meal.meal_type.value == "dinner":
                previous_dinners.append(meal.title)

    # 5. Post-processing
    daily_totals = _compute_daily_totals(day_plans)
    shopping_list = _aggregate_shopping_list(day_plans)

    weekly_plan_schema = WeeklyPlan(
        week_start_date=week_start_date,
        days=day_plans,
        daily_totals=daily_totals,
        shopping_list=shopping_list,
        overrides=overrides or [],
    )

    # Generate summary markdown
    summary_lines = [f"# Meal Plan: Week of {week_start_date}", ""]
    for day in day_plans:
        summary_lines.append(f"## {day.date}")
        for meal in day.meals:
            summary_lines.append(
                f"- **{meal.meal_type.value.title()}**: {meal.title}"
            )
        summary_lines.append("")
    summary_md = "\n".join(summary_lines)

    # 6. Persist
    db_plan = WeeklyPlanModel(
        household_id=household_id,
        week_start_date=week_start_date,
        status=PlanStatus.DRAFT,
        plan_json=weekly_plan_schema.model_dump(),
        summary_md=summary_md,
        model_info_json={},
    )
    session.add(db_plan)
    await session.flush()

    for day in day_plans:
        for meal in day.meals:
            db_meal = MealModel(
                weekly_plan_id=db_plan.id,
                date=day.date,
                meal_type=meal.meal_type.value,
                title=meal.title,
                recipe_source_url=meal.recipe.url if meal.recipe else None,
                cook_time_min=meal.cook_time_min,
                servings=meal.servings,
                ingredients_json=[ing.model_dump() for ing in meal.ingredients],
                nutrition_json=meal.nutrition.model_dump(),
                flags_json=meal.flags.model_dump(),
            )
            session.add(db_meal)

    db_shopping = ShoppingListModel(
        weekly_plan_id=db_plan.id,
        items_json=[item.model_dump() for item in shopping_list.items],
        exports_json=None,
    )
    session.add(db_shopping)

    await session.commit()
    await session.refresh(db_plan)

    return db_plan, warnings, errors


# ── CRUD ──────────────────────────────────────────────────


async def list_plans(
    session: AsyncSession,
    household_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[WeeklyPlanModel]:
    result = await session.execute(
        select(WeeklyPlanModel)
        .where(WeeklyPlanModel.household_id == household_id)
        .order_by(WeeklyPlanModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_plan(
    session: AsyncSession,
    plan_id: uuid.UUID,
) -> WeeklyPlanModel | None:
    result = await session.execute(
        select(WeeklyPlanModel)
        .where(WeeklyPlanModel.id == plan_id)
        .options(
            selectinload(WeeklyPlanModel.meals),
            selectinload(WeeklyPlanModel.shopping_list),
        )
    )
    return result.scalar_one_or_none()


async def get_plan_shopping_list(
    session: AsyncSession,
    plan_id: uuid.UUID,
) -> ShoppingListModel | None:
    result = await session.execute(
        select(ShoppingListModel).where(
            ShoppingListModel.weekly_plan_id == plan_id
        )
    )
    return result.scalar_one_or_none()


async def delete_plan(session: AsyncSession, plan_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(WeeklyPlanModel).where(WeeklyPlanModel.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        return False
    await session.delete(plan)
    await session.commit()
    return True


async def update_plan_status(
    session: AsyncSession,
    plan_id: uuid.UUID,
    status: PlanStatus,
) -> WeeklyPlanModel | None:
    result = await session.execute(
        select(WeeklyPlanModel).where(WeeklyPlanModel.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        return None
    plan.status = status
    await session.commit()
    await session.refresh(plan)
    return plan
