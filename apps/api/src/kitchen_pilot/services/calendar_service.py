"""Native Google Calendar service.

Replaces calendar_mcp.py. Uses google-api-python-client directly
with tokens managed by the token service.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession

from kitchen_pilot.config import settings
from kitchen_pilot.schemas.plan import DayPlan
from kitchen_pilot.services import token_service

logger = logging.getLogger(__name__)


class CalendarServiceError(Exception):
    """Raised when a calendar operation fails."""


async def _execute(request: Any) -> Any:
    """Execute a Google API request in a thread to avoid blocking."""
    return await asyncio.to_thread(request.execute)


async def _get_calendar_service(
    session: AsyncSession,
    household_id: uuid.UUID,
) -> Any:
    """Build an authenticated Google Calendar API service object."""
    access_token = await token_service.get_valid_access_token(session, household_id)
    row = await token_service.get_tokens(session, household_id)

    creds = Credentials(
        token=access_token,
        refresh_token=token_service.decrypt_token(row.encrypted_refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
    )

    return await asyncio.to_thread(build, "calendar", "v3", credentials=creds)


async def is_available(
    session: AsyncSession,
    household_id: uuid.UUID,
) -> bool:
    """Check if Google Calendar is connected for this household."""
    row = await token_service.get_tokens(session, household_id)
    return row is not None


async def list_events(
    session: AsyncSession,
    household_id: uuid.UUID,
    calendar_id: str = "primary",
    time_min: datetime | None = None,
    time_max: datetime | None = None,
) -> list[dict[str, Any]]:
    """List events in a date range."""
    service = await _get_calendar_service(session, household_id)
    kwargs: dict[str, Any] = {
        "calendarId": calendar_id,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_min:
        kwargs["timeMin"] = time_min.isoformat()
    if time_max:
        kwargs["timeMax"] = time_max.isoformat()

    result = await _execute(service.events().list(**kwargs))
    return result.get("items", [])


async def get_free_windows(
    session: AsyncSession,
    household_id: uuid.UUID,
    calendar_id: str = "primary",
    time_min: datetime | None = None,
    time_max: datetime | None = None,
) -> list[dict[str, Any]]:
    """Get free time windows by finding gaps between existing events."""
    events = await list_events(session, household_id, calendar_id, time_min, time_max)

    windows: list[dict[str, Any]] = []
    cursor = time_min

    for event in events:
        start_str = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        end_str = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
        if not start_str or not end_str:
            continue

        event_start = datetime.fromisoformat(start_str)
        event_end = datetime.fromisoformat(end_str)

        if cursor and event_start > cursor:
            windows.append({"start": cursor.isoformat(), "end": event_start.isoformat()})
        cursor = max(cursor, event_end) if cursor else event_end

    if cursor and time_max and cursor < time_max:
        windows.append({"start": cursor.isoformat(), "end": time_max.isoformat()})

    return windows


async def publish_plan_to_calendar(
    session: AsyncSession,
    household_id: uuid.UUID,
    day_plans: list[DayPlan],
    weekly_plan_id: str,
    calendar_id: str = "primary",
) -> tuple[int, list[str]]:
    """Publish cooking events to Google Calendar.

    Creates one event per meal with:
      - title: "Cook: <meal title>"
      - description: ingredients + nutrition summary
      - extendedProperties.private.kitchen_pilot_plan_id for tagging

    Returns (events_created, event_ids).
    """
    service = await _get_calendar_service(session, household_id)
    event_ids: list[str] = []

    for day in day_plans:
        for meal in day.meals:
            desc_lines = [f"Meal: {meal.title}"]
            if meal.recipe and meal.recipe.url:
                desc_lines.append(f"Recipe: {meal.recipe.url}")
            desc_lines.append(f"Cook time: {meal.cook_time_min} min")
            desc_lines.append(f"Servings: {meal.servings}")
            desc_lines.append("")
            desc_lines.append("Ingredients:")
            for ing in meal.ingredients:
                desc_lines.append(f"  - {ing.quantity} {ing.unit} {ing.name}")
            desc_lines.append("")
            desc_lines.append(
                f"Nutrition: {meal.nutrition.calories} cal, "
                f"{meal.nutrition.protein_g}g protein, "
                f"{meal.nutrition.carbs_g}g carbs, "
                f"{meal.nutrition.fat_g}g fat"
            )

            event_body = {
                "summary": f"Cook: {meal.title}",
                "description": "\n".join(desc_lines),
                "start": {"date": day.date},
                "end": {"date": day.date},
                "extendedProperties": {
                    "private": {
                        "kitchen_pilot_plan_id": weekly_plan_id,
                        "meal_type": meal.meal_type.value,
                    }
                },
            }

            try:
                result = await _execute(
                    service.events().insert(calendarId=calendar_id, body=event_body)
                )
                event_id = result.get("id", "")
                if event_id:
                    event_ids.append(event_id)
            except Exception as e:
                logger.warning(
                    "Failed to create calendar event for %s: %s",
                    meal.title,
                    e,
                )

    return len(event_ids), event_ids


async def remove_plan_events(
    session: AsyncSession,
    household_id: uuid.UUID,
    weekly_plan_id: str,
    calendar_id: str = "primary",
) -> int:
    """Remove all calendar events tagged with the given plan ID.

    Returns number of events removed.
    """
    try:
        service = await _get_calendar_service(session, household_id)

        result = await _execute(
            service.events().list(
                calendarId=calendar_id,
                privateExtendedProperty=f"kitchen_pilot_plan_id={weekly_plan_id}",
            )
        )
        events = result.get("items", [])

        removed = 0
        for event in events:
            event_id = event.get("id")
            if event_id:
                try:
                    await _execute(
                        service.events().delete(
                            calendarId=calendar_id, eventId=event_id
                        )
                    )
                    removed += 1
                except Exception:
                    pass
        return removed
    except Exception as e:
        logger.warning("Failed to remove plan events: %s", e)
        return 0
