"""Plan management router.

Endpoints for generating, listing, viewing, publishing,
and deleting weekly meal plans.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.db.models import PlanStatus
from kitchen_pilot.dependencies import get_household_id
from kitchen_pilot.schemas.plan import WeeklyPlan
from kitchen_pilot.schemas.plan_api import (
    ChecklistUpdateRequest,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanPublishRequest,
    PlanPublishResponse,
    ShoppingItemWithLinks,
    ShoppingListDetailResponse,
    ShoppingListResponse,
    WeeklyPlanDetailResponse,
    WeeklyPlanResponse,
)
from kitchen_pilot.services import calendar_service, grocery_export
from kitchen_pilot.services import plan as plan_svc

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/generate", response_model=PlanGenerateResponse, status_code=201)
async def generate_plan(
    request: PlanGenerateRequest,
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Generate a weekly meal plan using the LLM pipeline."""
    try:
        db_plan, warnings, errors = await plan_svc.generate_plan(
            session=session,
            household_id=household_id,
            week_start_date=request.week_start_date,
            overrides=request.overrides,
            max_cook_time_min=request.max_cook_time_min,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    plan = await plan_svc.get_plan(session, db_plan.id)
    return PlanGenerateResponse(
        plan=WeeklyPlanDetailResponse.model_validate(plan),
        warnings=warnings,
        errors=errors,
    )


@router.get("", response_model=list[WeeklyPlanResponse])
async def list_plans(
    limit: int = 20,
    offset: int = 0,
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """List weekly plans for the household, newest first."""
    plans = await plan_svc.list_plans(session, household_id, limit, offset)
    return [WeeklyPlanResponse.model_validate(p) for p in plans]


@router.get("/{plan_id}", response_model=WeeklyPlanDetailResponse)
async def get_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Get a weekly plan with its meals and shopping list."""
    plan = await plan_svc.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return WeeklyPlanDetailResponse.model_validate(plan)


@router.get("/{plan_id}/shopping-list", response_model=ShoppingListResponse)
async def get_shopping_list(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Get the shopping list for a plan."""
    shopping = await plan_svc.get_plan_shopping_list(session, plan_id)
    if shopping is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return ShoppingListResponse.model_validate(shopping)


@router.post("/publish", response_model=PlanPublishResponse)
async def publish_plan(
    request: PlanPublishRequest,
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Publish a plan's meals to Google Calendar."""
    if not await calendar_service.is_available(session, household_id):
        raise HTTPException(
            status_code=400,
            detail=(
                "Google Calendar is not connected. "
                "Please connect it from your profile."
            ),
        )

    plan = await plan_svc.get_plan(session, request.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    weekly_plan = WeeklyPlan.model_validate(plan.plan_json)

    events_created, event_ids = await calendar_service.publish_plan_to_calendar(
        session=session,
        household_id=household_id,
        day_plans=weekly_plan.days,
        weekly_plan_id=str(plan.id),
        calendar_id=request.calendar_id,
    )

    await plan_svc.update_plan_status(session, plan.id, PlanStatus.PUBLISHED)

    return PlanPublishResponse(
        plan_id=plan.id,
        status="published",
        calendar_events_created=events_created,
        calendar_event_ids=event_ids,
    )


@router.get(
    "/{plan_id}/shopping-list/detail",
    response_model=ShoppingListDetailResponse,
)
async def get_shopping_list_detail(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Get the shopping list with retailer links and checked state."""
    shopping = await plan_svc.get_plan_shopping_list(session, plan_id)
    if shopping is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    raw_items = shopping.items_json or []
    checked = (shopping.exports_json or {}).get("checked_indices", [])

    items = [
        ShoppingItemWithLinks(
            name=grocery_export.normalize_ingredient(item.get("name", "")),
            quantity=item.get("quantity", 0),
            unit=item.get("unit", ""),
            category=item.get("category", "Other"),
            checked=i in checked,
            retailer_links=grocery_export.get_retailer_links(item.get("name", "")),
        )
        for i, item in enumerate(raw_items)
    ]

    return ShoppingListDetailResponse(
        id=shopping.id,
        items=items,
        checked_indices=checked,
    )


@router.patch("/{plan_id}/shopping-list/checklist")
async def update_checklist(
    plan_id: uuid.UUID,
    request: ChecklistUpdateRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Update the checked state of shopping list items."""
    shopping = await plan_svc.update_checklist(
        session, plan_id, request.checked_indices
    )
    if shopping is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return {"checked_indices": request.checked_indices}


@router.get("/{plan_id}/shopping-list/export/csv")
async def export_shopping_list_csv(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Export the shopping list as a CSV file."""
    shopping = await plan_svc.get_plan_shopping_list(session, plan_id)
    if shopping is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    items = shopping.items_json or []
    csv_content = grocery_export.generate_csv(items)

    plan = await plan_svc.get_plan(session, plan_id)
    week = plan.week_start_date if plan else "unknown"
    filename = f"shopping-list-{week}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    """Delete a weekly plan and all associated meals/shopping list."""
    deleted = await plan_svc.delete_plan(session, plan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Plan not found")
