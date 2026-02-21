"""Household service layer.

All DB queries for household-related entities. Routers and agents
call these functions; no direct ORM usage outside this module.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kitchen_pilot.db.models import (
    Allergy,
    Biometric,
    DietaryRule,
    FoodPreference,
    HealthCondition,
    Household,
    NutritionGoal,
    Person,
)
from kitchen_pilot.schemas.household import (
    AllergyCreate,
    AllergySchema,
    AllergyUpdate,
    BiometricCreate,
    BiometricUpdate,
    DietaryRuleCreate,
    DietaryRuleSchema,
    DietaryRuleUpdate,
    FoodPreferenceCreate,
    FoodPreferenceSchema,
    FoodPreferenceUpdate,
    HealthConditionCreate,
    HouseholdContext,
    HouseholdUpdate,
    NutritionGoalCreate,
    NutritionGoalSchema,
    NutritionGoalUpdate,
    PersonCreate,
    PersonSchema,
    PersonUpdate,
)

DEFAULT_HOUSEHOLD_NAME = "My Household"


# ── Household ──────────────────────────────────────────────


async def get_or_create_household(session: AsyncSession) -> Household:
    """Get the single default household, creating it on first call."""
    result = await session.execute(select(Household).limit(1))
    household = result.scalar_one_or_none()
    if household is None:
        household = Household(name=DEFAULT_HOUSEHOLD_NAME, timezone="UTC")
        session.add(household)
        await session.commit()
        await session.refresh(household)
    return household


async def get_household(session: AsyncSession) -> Household:
    """Get the default household. Raises 404 if none exists."""
    result = await session.execute(select(Household).limit(1))
    household = result.scalar_one_or_none()
    if household is None:
        raise HTTPException(status_code=404, detail="No household found")
    return household


async def update_household(
    session: AsyncSession, household_id: uuid.UUID, data: HouseholdUpdate
) -> Household:
    result = await session.execute(
        select(Household).where(Household.id == household_id)
    )
    household = result.scalar_one_or_none()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(household, key, value)
    await session.commit()
    await session.refresh(household)
    return household


# ── People ─────────────────────────────────────────────────


async def list_people(session: AsyncSession, household_id: uuid.UUID) -> list[Person]:
    result = await session.execute(
        select(Person)
        .where(Person.household_id == household_id)
        .order_by(Person.created_at)
    )
    return list(result.scalars().all())


async def create_person(
    session: AsyncSession, household_id: uuid.UUID, data: PersonCreate
) -> Person:
    person = Person(household_id=household_id, **data.model_dump())
    session.add(person)
    await session.commit()
    await session.refresh(person)
    return person


async def update_person(
    session: AsyncSession, person_id: uuid.UUID, data: PersonUpdate
) -> Person:
    result = await session.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(person, key, value)
    await session.commit()
    await session.refresh(person)
    return person


async def delete_person(session: AsyncSession, person_id: uuid.UUID) -> None:
    result = await session.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    await session.delete(person)
    await session.commit()


# ── Allergies ──────────────────────────────────────────────


async def list_allergies(
    session: AsyncSession, household_id: uuid.UUID
) -> list[Allergy]:
    result = await session.execute(
        select(Allergy)
        .join(Person)
        .where(Person.household_id == household_id)
        .options(selectinload(Allergy.person))
        .order_by(Allergy.created_at)
    )
    return list(result.scalars().all())


async def create_allergy(session: AsyncSession, data: AllergyCreate) -> Allergy:
    person = await session.get(Person, data.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    allergy = Allergy(**data.model_dump())
    session.add(allergy)
    await session.commit()
    await session.refresh(allergy)
    return allergy


async def update_allergy(
    session: AsyncSession, allergy_id: uuid.UUID, data: AllergyUpdate
) -> Allergy:
    result = await session.execute(select(Allergy).where(Allergy.id == allergy_id))
    allergy = result.scalar_one_or_none()
    if allergy is None:
        raise HTTPException(status_code=404, detail="Allergy not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(allergy, key, value)
    await session.commit()
    await session.refresh(allergy)
    return allergy


async def delete_allergy(session: AsyncSession, allergy_id: uuid.UUID) -> None:
    result = await session.execute(select(Allergy).where(Allergy.id == allergy_id))
    allergy = result.scalar_one_or_none()
    if allergy is None:
        raise HTTPException(status_code=404, detail="Allergy not found")
    await session.delete(allergy)
    await session.commit()


# ── Dietary Rules ──────────────────────────────────────────


def _scoped_query(model: type, household_id: uuid.UUID):
    """Build a query for scoped entities (household OR person in household)."""
    people_ids = select(Person.id).where(Person.household_id == household_id).scalar_subquery()
    return (
        select(model)
        .where((model.household_id == household_id) | (model.person_id.in_(people_ids)))
        .order_by(model.created_at)
    )


async def list_dietary_rules(
    session: AsyncSession, household_id: uuid.UUID
) -> list[DietaryRule]:
    result = await session.execute(_scoped_query(DietaryRule, household_id))
    return list(result.scalars().all())


async def create_dietary_rule(
    session: AsyncSession, data: DietaryRuleCreate
) -> DietaryRule:
    rule = DietaryRule(**data.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def update_dietary_rule(
    session: AsyncSession, rule_id: uuid.UUID, data: DietaryRuleUpdate
) -> DietaryRule:
    result = await session.execute(
        select(DietaryRule).where(DietaryRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Dietary rule not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    await session.commit()
    await session.refresh(rule)
    return rule


async def delete_dietary_rule(session: AsyncSession, rule_id: uuid.UUID) -> None:
    result = await session.execute(
        select(DietaryRule).where(DietaryRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Dietary rule not found")
    await session.delete(rule)
    await session.commit()


# ── Food Preferences ──────────────────────────────────────


async def list_food_preferences(
    session: AsyncSession, household_id: uuid.UUID
) -> list[FoodPreference]:
    result = await session.execute(_scoped_query(FoodPreference, household_id))
    return list(result.scalars().all())


async def create_food_preference(
    session: AsyncSession, data: FoodPreferenceCreate
) -> FoodPreference:
    pref = FoodPreference(**data.model_dump())
    session.add(pref)
    await session.commit()
    await session.refresh(pref)
    return pref


async def update_food_preference(
    session: AsyncSession, pref_id: uuid.UUID, data: FoodPreferenceUpdate
) -> FoodPreference:
    result = await session.execute(
        select(FoodPreference).where(FoodPreference.id == pref_id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        raise HTTPException(status_code=404, detail="Food preference not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pref, key, value)
    await session.commit()
    await session.refresh(pref)
    return pref


async def delete_food_preference(session: AsyncSession, pref_id: uuid.UUID) -> None:
    result = await session.execute(
        select(FoodPreference).where(FoodPreference.id == pref_id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        raise HTTPException(status_code=404, detail="Food preference not found")
    await session.delete(pref)
    await session.commit()


# ── Nutrition Goals ────────────────────────────────────────


async def list_nutrition_goals(
    session: AsyncSession, household_id: uuid.UUID
) -> list[NutritionGoal]:
    result = await session.execute(_scoped_query(NutritionGoal, household_id))
    return list(result.scalars().all())


async def create_nutrition_goal(
    session: AsyncSession, data: NutritionGoalCreate
) -> NutritionGoal:
    goal = NutritionGoal(**data.model_dump())
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


async def update_nutrition_goal(
    session: AsyncSession, goal_id: uuid.UUID, data: NutritionGoalUpdate
) -> NutritionGoal:
    result = await session.execute(
        select(NutritionGoal).where(NutritionGoal.id == goal_id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=404, detail="Nutrition goal not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    await session.commit()
    await session.refresh(goal)
    return goal


async def delete_nutrition_goal(session: AsyncSession, goal_id: uuid.UUID) -> None:
    result = await session.execute(
        select(NutritionGoal).where(NutritionGoal.id == goal_id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=404, detail="Nutrition goal not found")
    await session.delete(goal)
    await session.commit()


# ── Context Agent ──────────────────────────────────────────


async def get_household_context(session: AsyncSession) -> HouseholdContext:
    """Build the normalized HouseholdContext for agent consumption.

    Loads all household data and transforms DB models into the
    agent-friendly schema format with scope strings.
    """
    household = await get_household(session)

    people_result = await session.execute(
        select(Person)
        .where(Person.household_id == household.id)
        .options(
            selectinload(Person.allergies),
            selectinload(Person.biometrics),
            selectinload(Person.health_conditions),
        )
    )
    people = list(people_result.scalars().all())
    people_by_id: dict[uuid.UUID, Person] = {p.id: p for p in people}

    allergies = await list_allergies(session, household.id)
    dietary_rules = await list_dietary_rules(session, household.id)
    food_preferences = await list_food_preferences(session, household.id)
    nutrition_goals = await list_nutrition_goals(session, household.id)

    def _scope(hid: uuid.UUID | None, pid: uuid.UUID | None) -> str:
        if pid and pid in people_by_id:
            return people_by_id[pid].name
        return "household"

    def _person_schema(p: Person) -> PersonSchema:
        # Get latest biometric if available
        bio = p.biometrics[-1] if p.biometrics else None
        conditions = [hc.condition for hc in p.health_conditions]
        return PersonSchema(
            name=p.name,
            role=p.role,
            age_band=p.age_band,
            gender=p.gender,
            date_of_birth=p.date_of_birth,
            ethnicity=p.ethnicity,
            activity_level=p.activity_level,
            height_cm=bio.height_cm if bio else None,
            weight_kg=bio.weight_kg if bio else None,
            health_conditions=conditions,
        )

    return HouseholdContext(
        household_name=household.name,
        timezone=household.timezone,
        people=[_person_schema(p) for p in people],
        allergies=[
            AllergySchema(
                person_name=people_by_id[a.person_id].name,
                allergen=a.allergen,
                severity=a.severity.value,
                notes=a.notes,
            )
            for a in allergies
            if a.person_id in people_by_id
        ],
        dietary_rules=[
            DietaryRuleSchema(
                scope=_scope(r.household_id, r.person_id),
                rule=r.rule,
                notes=r.notes,
            )
            for r in dietary_rules
        ],
        preferences=[
            FoodPreferenceSchema(
                scope=_scope(fp.household_id, fp.person_id),
                item=fp.item,
                preference=fp.preference.value,
                notes=fp.notes,
            )
            for fp in food_preferences
        ],
        nutrition_goals=[
            NutritionGoalSchema(
                scope=_scope(g.household_id, g.person_id),
                calories_min=g.calories_min,
                calories_max=g.calories_max,
                protein_g=g.protein_g,
                carbs_g=g.carbs_g,
                fat_g=g.fat_g,
                fiber_g=g.fiber_g,
                sodium_mg=g.sodium_mg,
                cholesterol_mg=g.cholesterol_mg,
                sugar_g=g.sugar_g,
                saturated_fat_g=g.saturated_fat_g,
                potassium_mg=g.potassium_mg,
            )
            for g in nutrition_goals
        ],
    )


# ── Biometrics ────────────────────────────────────────────


async def get_biometric(
    session: AsyncSession, person_id: uuid.UUID
) -> Biometric | None:
    result = await session.execute(
        select(Biometric)
        .where(Biometric.person_id == person_id)
        .order_by(Biometric.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def upsert_biometric(
    session: AsyncSession, data: BiometricCreate
) -> Biometric:
    """Create or update the biometric record for a person."""
    person = await session.get(Person, data.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    result = await session.execute(
        select(Biometric)
        .where(Biometric.person_id == data.person_id)
        .order_by(Biometric.created_at.desc())
        .limit(1)
    )
    bio = result.scalar_one_or_none()

    values = data.model_dump(exclude={"person_id"}, exclude_unset=True)
    # Compute BMI if height and weight available
    h = values.get("height_cm") or (bio.height_cm if bio else None)
    w = values.get("weight_kg") or (bio.weight_kg if bio else None)
    if h and w and h > 0:
        values["bmi"] = round(w / ((h / 100) ** 2), 1)

    if bio:
        for key, value in values.items():
            setattr(bio, key, value)
        await session.commit()
        await session.refresh(bio)
        return bio
    else:
        bio = Biometric(person_id=data.person_id, **values)
        session.add(bio)
        await session.commit()
        await session.refresh(bio)
        return bio


# ── Health Conditions ─────────────────────────────────────


async def list_health_conditions(
    session: AsyncSession, household_id: uuid.UUID
) -> list[HealthCondition]:
    result = await session.execute(
        select(HealthCondition)
        .join(Person)
        .where(Person.household_id == household_id)
        .order_by(HealthCondition.created_at)
    )
    return list(result.scalars().all())


async def create_health_condition(
    session: AsyncSession, data: HealthConditionCreate
) -> HealthCondition:
    person = await session.get(Person, data.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    condition = HealthCondition(**data.model_dump())
    session.add(condition)
    await session.commit()
    await session.refresh(condition)
    return condition


async def delete_health_condition(
    session: AsyncSession, condition_id: uuid.UUID
) -> None:
    result = await session.execute(
        select(HealthCondition).where(HealthCondition.id == condition_id)
    )
    condition = result.scalar_one_or_none()
    if condition is None:
        raise HTTPException(status_code=404, detail="Health condition not found")
    await session.delete(condition)
    await session.commit()
