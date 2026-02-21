"""Plan agent — wraps plan generation service."""

from pydantic import BaseModel, Field

from kitchen_pilot.agents.base import AgentContext, AgentResult, BaseAgent
from kitchen_pilot.schemas.plan import ConstraintOverride
from kitchen_pilot.services.plan import generate_plan


class PlanAgentInput(BaseModel):
    week_start_date: str
    overrides: list[ConstraintOverride] = Field(default_factory=list)
    max_cook_time_min: int | None = None
    notes: str | None = None


class PlanAgentOutput(BaseModel):
    plan_id: str
    summary_md: str
    warnings: list[str] = Field(default_factory=list)


class PlanAgent(BaseAgent[PlanAgentInput, PlanAgentOutput]):
    name = "plan_generator"
    description = "Generate a 7-day meal plan for the household."

    async def run(
        self, input: PlanAgentInput, context: AgentContext
    ) -> AgentResult[PlanAgentOutput]:
        try:
            db_plan, warnings, errors = await generate_plan(
                session=context.session,
                household_id=context.household_id,
                week_start_date=input.week_start_date,
                overrides=input.overrides or None,
                max_cook_time_min=input.max_cook_time_min,
                notes=input.notes,
            )
            return AgentResult(
                success=True,
                data=PlanAgentOutput(
                    plan_id=str(db_plan.id),
                    summary_md=db_plan.summary_md or "",
                    warnings=warnings,
                ),
                warnings=errors,
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
