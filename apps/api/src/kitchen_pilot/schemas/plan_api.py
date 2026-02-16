"""HTTP request/response schemas for plan endpoints.

Distinct from schemas/plan.py which contains LLM-facing schemas (DayPlan, WeeklyPlan).
These wrap DB models with IDs, timestamps, and status for the REST API.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from kitchen_pilot.schemas.plan import ConstraintOverride

# ── Request schemas ───────────────────────────────────────


class PlanGenerateRequest(BaseModel):
    week_start_date: str = Field(
        description="Monday of the week in ISO format, e.g. 2026-02-16",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    overrides: list[ConstraintOverride] = Field(default_factory=list)
    max_cook_time_min: int | None = Field(
        default=None,
        ge=10,
        le=480,
        description="Optional max cook time per meal in minutes",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Free-text instructions, e.g. 'high protein dinners'",
    )


class PlanPublishRequest(BaseModel):
    plan_id: uuid.UUID
    calendar_id: str = Field(
        default="primary",
        description="Google Calendar ID to publish to",
    )


# ── Response schemas ──────────────────────────────────────


class MealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: str
    meal_type: str
    title: str
    recipe_source_url: str | None = None
    cook_time_min: int | None = None
    servings: int | None = None
    ingredients_json: list | dict | None = None
    nutrition_json: dict | None = None
    flags_json: dict | None = None


class ShoppingListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    items_json: list | dict | None = None
    exports_json: list | dict | None = None


class WeeklyPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    week_start_date: str
    status: str
    plan_json: dict | None = None
    summary_md: str | None = None
    model_info_json: dict | None = None
    created_at: datetime
    updated_at: datetime


class WeeklyPlanDetailResponse(WeeklyPlanResponse):
    """Extended response including related meals and shopping list."""

    meals: list[MealResponse] = Field(default_factory=list)
    shopping_list: ShoppingListResponse | None = None


class PlanGenerateResponse(BaseModel):
    """Response from the plan generation endpoint."""

    plan: WeeklyPlanDetailResponse
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PlanPublishResponse(BaseModel):
    plan_id: uuid.UUID
    status: str
    calendar_events_created: int
    calendar_event_ids: list[str] = Field(default_factory=list)
