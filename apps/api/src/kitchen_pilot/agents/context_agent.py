"""Context agent — wraps household context service."""

from pydantic import BaseModel

from kitchen_pilot.agents.base import AgentContext, AgentResult, BaseAgent
from kitchen_pilot.schemas.household import HouseholdContext
from kitchen_pilot.services.household import get_household_context


class ContextAgentInput(BaseModel):
    """No input needed — context is loaded from DB."""

    pass


class ContextAgent(BaseAgent[ContextAgentInput, HouseholdContext]):
    name = "context"
    description = "Fetch household context including people, allergies, rules, preferences, goals, and health profiles."

    async def run(
        self, input: ContextAgentInput, context: AgentContext
    ) -> AgentResult[HouseholdContext]:
        try:
            ctx = await get_household_context(context.session)
            return AgentResult(success=True, data=ctx)
        except Exception as e:
            return AgentResult(success=False, error=str(e))
