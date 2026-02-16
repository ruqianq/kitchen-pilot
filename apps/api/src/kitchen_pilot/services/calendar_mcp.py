"""Google Calendar MCP client.

Communicates with the Google Calendar MCP sidecar via Streamable HTTP.
All calls are optional and fail gracefully if the MCP server is not available.
"""

import asyncio
import logging

import httpx

from kitchen_pilot.config import settings
from kitchen_pilot.schemas.plan import DayPlan

logger = logging.getLogger(__name__)

MCP_TIMEOUT = 30
MCP_MAX_RETRIES = 3


class CalendarMCPError(Exception):
    """Raised when MCP call fails after retries."""


async def _mcp_call(
    method: str,
    params: dict,
    timeout: float = MCP_TIMEOUT,
) -> dict:
    """Make an MCP JSON-RPC call to the calendar sidecar.

    Uses Streamable HTTP transport. Retries with exponential backoff.
    """
    url = settings.gcal_mcp_url
    if not url:
        raise CalendarMCPError("gcal_mcp_url not configured")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    last_error: Exception | None = None
    for attempt in range(MCP_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await asyncio.wait_for(
                    client.post(f"{url}/mcp", json=payload),
                    timeout=timeout,
                )
                resp.raise_for_status()
                result = resp.json()
                if "error" in result:
                    raise CalendarMCPError(f"MCP error: {result['error']}")
                return result.get("result", {})
        except CalendarMCPError:
            raise
        except Exception as e:
            last_error = e
            if attempt < MCP_MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)

    raise CalendarMCPError(
        f"MCP call '{method}' failed after {MCP_MAX_RETRIES} attempts: {last_error}"
    )


async def is_available() -> bool:
    """Check if the Calendar MCP sidecar is reachable."""
    url = settings.gcal_mcp_url
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            return resp.status_code < 500
    except Exception:
        return False


async def publish_plan_to_calendar(
    day_plans: list[DayPlan],
    weekly_plan_id: str,
    calendar_id: str = "primary",
) -> tuple[int, list[str]]:
    """Publish cooking events to Google Calendar.

    Creates one event per meal with:
      - title: "Cook: <meal title>"
      - description: ingredients + nutrition summary
      - metadata tag: weekly_plan_id for update/remove semantics

    Returns (events_created, event_ids).
    """
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

            params = {
                "name": "create_event",
                "arguments": {
                    "calendarId": calendar_id,
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
                },
            }

            try:
                result = await _mcp_call("tools/call", params)
                event_id = result.get("content", [{}])[0].get("text", "")
                if event_id:
                    event_ids.append(event_id)
            except CalendarMCPError as e:
                logger.warning(
                    "Failed to create calendar event for %s: %s",
                    meal.title,
                    e,
                )

    return len(event_ids), event_ids


async def remove_plan_events(
    weekly_plan_id: str,
    calendar_id: str = "primary",
) -> int:
    """Remove all calendar events tagged with the given plan ID.

    Returns number of events removed.
    """
    try:
        result = await _mcp_call(
            "tools/call",
            {
                "name": "list_events",
                "arguments": {
                    "calendarId": calendar_id,
                    "privateExtendedProperty": (
                        f"kitchen_pilot_plan_id={weekly_plan_id}"
                    ),
                },
            },
        )
        events = result.get("content", [])
        removed = 0
        for event in events:
            event_id = event.get("id")
            if event_id:
                try:
                    await _mcp_call(
                        "tools/call",
                        {
                            "name": "delete_event",
                            "arguments": {
                                "calendarId": calendar_id,
                                "eventId": event_id,
                            },
                        },
                    )
                    removed += 1
                except CalendarMCPError:
                    pass
        return removed
    except CalendarMCPError as e:
        logger.warning("Failed to remove plan events: %s", e)
        return 0
