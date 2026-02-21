"""Nutrition lookup router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.schemas.nutrition import (
    NutritionLookupRequest,
    NutritionLookupResponse,
    RecipeNutritionRequest,
    RecipeNutritionResponse,
)
from kitchen_pilot.services import nutrition as nutrition_svc

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.post("/lookup", response_model=NutritionLookupResponse)
async def lookup_food(
    body: NutritionLookupRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> NutritionLookupResponse:
    """Look up nutrition data for a single food item."""
    return await nutrition_svc.lookup_food(
        session, body.food, body.quantity, body.unit
    )


@router.post("/recipe/estimate", response_model=RecipeNutritionResponse)
async def estimate_recipe(
    body: RecipeNutritionRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RecipeNutritionResponse:
    """Estimate nutrition for a recipe from its ingredients."""
    return await nutrition_svc.estimate_recipe(
        session, body.ingredients, body.servings
    )
