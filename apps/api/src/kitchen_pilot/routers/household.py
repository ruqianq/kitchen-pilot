"""Household CRUD router.

Thin wrapper over household service functions. All endpoints
implicitly operate on the single default household.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.db.models import Household
from kitchen_pilot.dependencies import get_current_household, get_household_id
from kitchen_pilot.schemas.household import (
    AllergyCreate,
    AllergyResponse,
    AllergyUpdate,
    DietaryRuleCreate,
    DietaryRuleResponse,
    DietaryRuleUpdate,
    FoodPreferenceCreate,
    FoodPreferenceResponse,
    FoodPreferenceUpdate,
    HouseholdContext,
    HouseholdCreate,
    HouseholdResponse,
    HouseholdUpdate,
    NutritionGoalCreate,
    NutritionGoalResponse,
    NutritionGoalUpdate,
    PersonCreate,
    PersonResponse,
    PersonUpdate,
)
from kitchen_pilot.services import household as svc

router = APIRouter(prefix="/household", tags=["household"])


# ── Household ──────────────────────────────────────────────


@router.get("", response_model=HouseholdResponse)
async def get_household(
    household: Household = Depends(get_current_household),  # noqa: B008
) -> Household:
    return household


@router.post("", response_model=HouseholdResponse, status_code=201)
async def create_household(
    data: HouseholdCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Household:
    """Create household. If one already exists, update it with provided data."""
    household = await svc.get_or_create_household(session)
    updated = await svc.update_household(
        session, household.id, HouseholdUpdate(name=data.name, timezone=data.timezone)
    )
    return updated


@router.put("/{household_id}", response_model=HouseholdResponse)
async def update_household(
    household_id: uuid.UUID,
    data: HouseholdUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Household:
    return await svc.update_household(session, household_id, data)


# ── People ─────────────────────────────────────────────────


@router.get("/people", response_model=list[PersonResponse])
async def list_people(
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.list_people(session, household_id)


@router.post("/people", response_model=PersonResponse, status_code=201)
async def create_person(
    data: PersonCreate,
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.create_person(session, household_id, data)


@router.put("/people/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: uuid.UUID,
    data: PersonUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.update_person(session, person_id, data)


@router.delete("/people/{person_id}", status_code=204)
async def delete_person(
    person_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    await svc.delete_person(session, person_id)


# ── Allergies ──────────────────────────────────────────────


@router.get("/allergies", response_model=list[AllergyResponse])
async def list_allergies(
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.list_allergies(session, household_id)


@router.post("/allergies", response_model=AllergyResponse, status_code=201)
async def create_allergy(
    data: AllergyCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.create_allergy(session, data)


@router.put("/allergies/{allergy_id}", response_model=AllergyResponse)
async def update_allergy(
    allergy_id: uuid.UUID,
    data: AllergyUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.update_allergy(session, allergy_id, data)


@router.delete("/allergies/{allergy_id}", status_code=204)
async def delete_allergy(
    allergy_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    await svc.delete_allergy(session, allergy_id)


# ── Dietary Rules ──────────────────────────────────────────


@router.get("/dietary-rules", response_model=list[DietaryRuleResponse])
async def list_dietary_rules(
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.list_dietary_rules(session, household_id)


@router.post("/dietary-rules", response_model=DietaryRuleResponse, status_code=201)
async def create_dietary_rule(
    data: DietaryRuleCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.create_dietary_rule(session, data)


@router.put("/dietary-rules/{rule_id}", response_model=DietaryRuleResponse)
async def update_dietary_rule(
    rule_id: uuid.UUID,
    data: DietaryRuleUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.update_dietary_rule(session, rule_id, data)


@router.delete("/dietary-rules/{rule_id}", status_code=204)
async def delete_dietary_rule(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    await svc.delete_dietary_rule(session, rule_id)


# ── Food Preferences ──────────────────────────────────────


@router.get("/preferences", response_model=list[FoodPreferenceResponse])
async def list_preferences(
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.list_food_preferences(session, household_id)


@router.post("/preferences", response_model=FoodPreferenceResponse, status_code=201)
async def create_preference(
    data: FoodPreferenceCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.create_food_preference(session, data)


@router.put("/preferences/{pref_id}", response_model=FoodPreferenceResponse)
async def update_preference(
    pref_id: uuid.UUID,
    data: FoodPreferenceUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.update_food_preference(session, pref_id, data)


@router.delete("/preferences/{pref_id}", status_code=204)
async def delete_preference(
    pref_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    await svc.delete_food_preference(session, pref_id)


# ── Nutrition Goals ────────────────────────────────────────


@router.get("/goals", response_model=list[NutritionGoalResponse])
async def list_goals(
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.list_nutrition_goals(session, household_id)


@router.post("/goals", response_model=NutritionGoalResponse, status_code=201)
async def create_goal(
    data: NutritionGoalCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.create_nutrition_goal(session, data)


@router.put("/goals/{goal_id}", response_model=NutritionGoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    data: NutritionGoalUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    return await svc.update_nutrition_goal(session, goal_id, data)


@router.delete("/goals/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    await svc.delete_nutrition_goal(session, goal_id)


# ── Context Agent ──────────────────────────────────────────


@router.get("/context", response_model=HouseholdContext)
async def get_context(
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Return the full HouseholdContext for agent consumption."""
    return await svc.get_household_context(session)
