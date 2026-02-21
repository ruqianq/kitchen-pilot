import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from kitchen_pilot.db.engine import get_session
from kitchen_pilot.dependencies import get_household_id
from kitchen_pilot.schemas.household import HouseholdContext
from kitchen_pilot.services.household import get_household_context
from kitchen_pilot.services.llm import generate_structured, stream_chat_completion

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


# ── Intent Detection ──────────────────────────────────────


_SEARCH_PATTERN = re.compile(
    r"\b(find|search|look\s*up|discover|browse|suggest)\b.*\b(recipe|meal|dish|dinner|lunch|breakfast|diet|snack|food|cuisine)\b"
    r"|\b(recipe\s+for)\b"
    r"|\b(diet\s+for)\b",
    re.IGNORECASE,
)

_PLAN_PATTERN = re.compile(
    r"\b(plan|schedule|meal\s*plan|weekly\s*plan|plan\s+meals"
    r"|create\s+.*plan|generate\s+.*plan|plan\s+my)\b",
    re.IGNORECASE,
)

_NUTRITION_PATTERN = re.compile(
    r"\b(calories|calorie|macros|nutrition|sodium|protein\s+goal"
    r"|how\s+many\s+calories|what\s+should\s+I\s+eat"
    r"|healthy\s+eating|my\s+diet|daily\s+intake"
    r"|how\s+much\s+protein|nutrient|bmi)\b",
    re.IGNORECASE,
)


def _should_search(message: str) -> bool:
    return bool(_SEARCH_PATTERN.search(message))


def _should_plan(message: str) -> bool:
    return bool(_PLAN_PATTERN.search(message))


def _should_nutrition_consult(message: str) -> bool:
    return bool(_NUTRITION_PATTERN.search(message))


def _extract_search_query(message: str) -> str:
    q = message.strip()
    q = re.sub(
        r"^(can you |please |could you )?(find|search|look\s*up|discover|browse|suggest)( me| for| some)?\s*",
        "",
        q,
        flags=re.IGNORECASE,
    )
    return q.strip() or message.strip()


# ── System Prompt ─────────────────────────────────────────


def _build_chat_system_prompt(ctx: HouseholdContext) -> str:
    """Build a context-aware system prompt from household data."""
    lines = [
        "You are Kitchen Pilot, a friendly meal planning assistant and nutrition coach.",
        f"You are helping the {ctx.household_name} household.",
        "",
    ]

    if ctx.people:
        members = ", ".join(f"{p.name} ({p.role})" for p in ctx.people)
        lines.append(f"Household members: {members}")

    if ctx.allergies:
        allergens = ", ".join(
            f"{a.person_name}: {a.allergen} ({a.severity})" for a in ctx.allergies
        )
        lines.append(f"CRITICAL ALLERGIES: {allergens}")

    if ctx.dietary_rules:
        rules = ", ".join(r.rule for r in ctx.dietary_rules)
        lines.append(f"Dietary rules: {rules}")

    conditions = []
    for p in ctx.people:
        if p.health_conditions:
            conditions.append(f"{p.name}: {', '.join(p.health_conditions)}")
    if conditions:
        lines.append(f"Health conditions: {'; '.join(conditions)}")

    if ctx.nutrition_goals:
        for g in ctx.nutrition_goals:
            parts = []
            if g.calories_min is not None:
                parts.append(f"min {g.calories_min} cal")
            if g.calories_max is not None:
                parts.append(f"max {g.calories_max} cal")
            if g.sodium_mg is not None:
                parts.append(f"sodium <{g.sodium_mg}mg")
            if parts:
                lines.append(f"Nutrition goals [{g.scope}]: {', '.join(parts)}")

    lines.extend([
        "",
        "CAPABILITIES:",
        "- Suggest individual meals or daily meal plans based on household constraints.",
        "- Provide nutrition advice based on household members' health profiles.",
        "- Search the web for recipes when asked.",
        "- When users want a full 7-day plan, tell them to visit [Plans](/plans).",
        "",
        "RULES:",
        "- Always respect allergies (HARD constraint — never suggest allergens).",
        "- Respect dietary rules strictly.",
        "- When nutrition analysis is provided, use it in your response.",
        "- Format links as markdown: [title](url).",
        "- Never say you cannot search the web or that your knowledge has a cutoff date.",
        "- Be concise and practical.",
    ])

    return "\n".join(lines)


# ── Plan Preview ──────────────────────────────────────────


async def _generate_plan_preview(
    ctx: HouseholdContext, message: str
) -> str | None:
    """Generate a single-day meal preview for the chat."""
    from kitchen_pilot.schemas.plan import DayPlan
    from kitchen_pilot.services.plan import _build_system_prompt

    try:
        target = date.today() + timedelta(days=1)
        system_prompt = _build_system_prompt(ctx)
        user_prompt = (
            f"Plan meals for {target.isoformat()} (tomorrow). "
            f"User's request: {message}\n"
            f"Generate breakfast, lunch, and dinner."
        )

        day_plan = await generate_structured(
            response_model=DayPlan,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_retries=2,
            temperature=0,
        )

        lines = [f"Here's a preview meal plan for {target.isoformat()}:"]
        for meal in day_plan.meals:
            lines.append(
                f"- **{meal.meal_type.value.title()}**: {meal.title} "
                f"({meal.nutrition.calories} cal, {meal.cook_time_min} min)"
            )
            ingredients = ", ".join(i.name for i in meal.ingredients[:5])
            lines.append(f"  Ingredients: {ingredients}")

        lines.append(
            "\nFor a full 7-day plan with shopping list, "
            "visit [Plans](/plans)."
        )
        return "\n".join(lines)
    except Exception as e:
        logger.warning("Plan preview failed: %s", e)
        return None


# ── Nutrition Context ─────────────────────────────────────


async def _get_nutrition_context(
    ctx: HouseholdContext, message: str, household_id: uuid.UUID
) -> str | None:
    """Generate nutrition coach analysis from household health profiles."""
    from kitchen_pilot.agents.base import AgentContext
    from kitchen_pilot.agents.nutrition_coach import (
        NutritionCoachAgent,
        NutritionCoachInput,
    )

    try:
        agent = NutritionCoachAgent()
        input_data = NutritionCoachInput(
            household_context=ctx,
            question=message,
        )
        context = AgentContext(household_id=household_id)
        result = await agent.run(input_data, context)
        if result.success and result.data and result.data.chat_response:
            return result.data.chat_response
    except Exception as e:
        logger.warning("Nutrition context failed: %s", e)
    return None


# ── Chat Endpoint ─────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


def _next_monday() -> str:
    """Return the next Monday as ISO date string."""
    today = date.today()
    days_ahead = 7 - today.weekday()  # Monday = 0
    if days_ahead == 7:
        days_ahead = 0  # today is Monday
    return (today + timedelta(days=days_ahead)).isoformat()


async def _stream_response(
    messages: list[dict[str, str]],
    plan_metadata: dict | None = None,
) -> AsyncGenerator[str, None]:
    if plan_metadata:
        yield json.dumps(plan_metadata)
    async for content in stream_chat_completion(messages):
        yield json.dumps({"content": content})


@router.post("/chat")
async def chat(
    request: ChatRequest,
    household_id: uuid.UUID = Depends(get_household_id),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> EventSourceResponse:
    # Load household context for personalized responses
    ctx = await get_household_context(session)

    # Build context-aware system prompt
    system_prompt = _build_chat_system_prompt(ctx)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(request.history)
    messages.append({"role": "user", "content": request.message})

    # Intent detection: web search
    if _should_search(request.message):
        try:
            from kitchen_pilot.services.web_search import search_recipes

            query = _extract_search_query(request.message)
            results, provider = await search_recipes(query, max_results=5)

            if results:
                search_context = f"Web search results ({provider}):\n"
                for r in results:
                    search_context += (
                        f"- **{r.title}** ({r.source}): "
                        f"{r.snippet[:200]}  \n  URL: {r.url}\n"
                    )
                search_context += (
                    "\nUse these results to answer the user's question. "
                    "Include source links as markdown."
                )
                messages.insert(
                    -1, {"role": "system", "content": search_context}
                )
        except Exception as e:
            logger.warning("Web search failed, continuing without: %s", e)

    # Intent detection: plan preview
    plan_meta = None
    if _should_plan(request.message):
        preview = await _generate_plan_preview(ctx, request.message)
        if preview:
            plan_meta = {"type": "plan_preview", "week_start": _next_monday()}
            messages.insert(
                -1,
                {
                    "role": "system",
                    "content": (
                        f"Plan preview generated:\n{preview}\n\n"
                        "Present this to the user. "
                        "Let them know they can generate a full 7-day plan "
                        "using the button below."
                    ),
                },
            )

    # Intent detection: nutrition advice
    if _should_nutrition_consult(request.message) and not _should_plan(
        request.message
    ):
        nutrition_ctx = await _get_nutrition_context(
            ctx, request.message, household_id
        )
        if nutrition_ctx:
            messages.insert(-1, {"role": "system", "content": nutrition_ctx})

    return EventSourceResponse(_stream_response(messages, plan_meta))
