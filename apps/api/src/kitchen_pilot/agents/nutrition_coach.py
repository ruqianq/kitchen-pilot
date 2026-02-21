"""Nutrition coach agent.

Hybrid approach: deterministic calculations (Tier 1) always run,
LLM enrichment (Tier 2) only when invoked from chat with a question.
"""

import logging

from pydantic import BaseModel, Field

from kitchen_pilot.agents.base import AgentContext, AgentResult, BaseAgent
from kitchen_pilot.schemas.household import HouseholdContext
from kitchen_pilot.services.nutrition_coach import (
    NutritionRecommendation,
    compute_age,
    generate_recommendation,
)

logger = logging.getLogger(__name__)


class NutritionCoachInput(BaseModel):
    """Everything the coach needs to produce recommendations."""

    household_context: HouseholdContext
    question: str | None = None  # Free-text question from chat


class NutritionCoachOutput(BaseModel):
    """Coach output: per-person recommendations + optional chat summary."""

    recommendations: list[NutritionRecommendation] = Field(default_factory=list)
    chat_response: str | None = None


class NutritionCoachAgent(BaseAgent[NutritionCoachInput, NutritionCoachOutput]):
    name = "nutrition_coach"
    description = (
        "Analyze health profiles and produce personalized nutrition "
        "recommendations based on age, gender, activity level, and "
        "health conditions."
    )

    async def run(
        self, input: NutritionCoachInput, context: AgentContext
    ) -> AgentResult[NutritionCoachOutput]:
        try:
            recommendations = []
            for person in input.household_context.people:
                age_years = None
                if person.date_of_birth:
                    age_years = compute_age(person.date_of_birth)

                rec = generate_recommendation(
                    person_name=person.name,
                    gender=person.gender,
                    age_years=age_years,
                    date_of_birth=person.date_of_birth,
                    height_cm=person.height_cm,
                    weight_kg=person.weight_kg,
                    activity_level=person.activity_level,
                    age_band=person.age_band,
                    health_conditions=person.health_conditions or [],
                )
                recommendations.append(rec)

            # Build a natural-language summary for chat
            chat_response = None
            if input.question:
                chat_response = self._build_chat_summary(
                    recommendations, input.question
                )

            return AgentResult(
                success=True,
                data=NutritionCoachOutput(
                    recommendations=recommendations,
                    chat_response=chat_response,
                ),
            )
        except Exception as e:
            logger.error("Nutrition coach failed: %s", e)
            return AgentResult(success=False, error=str(e))

    def _build_chat_summary(
        self,
        recommendations: list[NutritionRecommendation],
        question: str,
    ) -> str:
        """Build a structured summary the LLM can use to answer the user."""
        lines = [
            "Nutrition Coach Analysis (based on household health profiles):",
            "",
        ]

        for rec in recommendations:
            lines.append(f"**{rec.person_name}**:")
            lines.append(f"- Daily calories: {rec.daily_calories} kcal")
            lines.append(f"  ({rec.calorie_rationale})")
            lines.append(
                f"- Macros: {rec.macro_split.protein_g}g protein "
                f"({rec.macro_split.protein_pct}%), "
                f"{rec.macro_split.carbs_g}g carbs "
                f"({rec.macro_split.carbs_pct}%), "
                f"{rec.macro_split.fat_g}g fat "
                f"({rec.macro_split.fat_pct}%)"
            )
            lines.append(f"- Fiber: {rec.macro_split.fiber_g}g")
            lines.append(
                f"- Sodium limit: {rec.micronutrient_limits.sodium_mg_max}mg"
            )
            lines.append(
                f"- Sugar limit: {rec.micronutrient_limits.sugar_g_max}g"
            )

            if rec.dietary_guidelines:
                lines.append("- Guidelines:")
                for g in rec.dietary_guidelines:
                    lines.append(f"  - {g}")

            if rec.foods_to_emphasize:
                lines.append(
                    f"- Foods to emphasize: {', '.join(rec.foods_to_emphasize[:8])}"
                )
            if rec.foods_to_limit:
                lines.append(
                    f"- Foods to limit: {', '.join(rec.foods_to_limit[:8])}"
                )

            for w in rec.warnings:
                lines.append(f"- Note: {w}")

            lines.append("")

        lines.append(
            "Use this analysis to answer the user's question. "
            "Present the information conversationally, not as raw data."
        )

        return "\n".join(lines)
