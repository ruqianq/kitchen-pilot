"""Tests for the agent foundation: BaseAgent, registry, context agent, plan agent."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from kitchen_pilot.agents.base import AgentContext, AgentResult, BaseAgent
from kitchen_pilot.agents.context_agent import ContextAgent, ContextAgentInput
from kitchen_pilot.agents.plan_agent import PlanAgent, PlanAgentInput
from kitchen_pilot.agents.registry import AgentRegistry
from kitchen_pilot.schemas.household import HouseholdContext


# ── AgentContext ──────────────────────────────────────────


def test_agent_context_creates_correlation_id():
    ctx = AgentContext(household_id=uuid.uuid4())
    assert ctx.correlation_id
    assert len(ctx.correlation_id) == 12


def test_agent_context_accepts_session():
    ctx = AgentContext(household_id=uuid.uuid4(), session="mock_session")
    assert ctx.session == "mock_session"


# ── AgentResult ───────────────────────────────────────────


def test_agent_result_success():
    class SomeOutput(BaseModel):
        value: int

    result = AgentResult[SomeOutput](success=True, data=SomeOutput(value=42))
    assert result.success is True
    assert result.data.value == 42
    assert result.error is None


def test_agent_result_failure():
    result = AgentResult(success=False, error="Something broke")
    assert result.success is False
    assert result.data is None
    assert result.error == "Something broke"


def test_agent_result_with_warnings():
    result = AgentResult(success=True, warnings=["heads up"])
    assert len(result.warnings) == 1


# ── AgentRegistry ─────────────────────────────────────────


class _DummyInput(BaseModel):
    pass


class _DummyOutput(BaseModel):
    msg: str


class _DummyAgent(BaseAgent[_DummyInput, _DummyOutput]):
    name = "dummy"
    description = "A test agent"

    async def run(self, input, context):
        return AgentResult(success=True, data=_DummyOutput(msg="ok"))


def test_registry_register_and_get():
    AgentRegistry.clear()
    agent = _DummyAgent()
    AgentRegistry.register(agent)
    assert AgentRegistry.get("dummy") is agent


def test_registry_get_unknown_returns_none():
    AgentRegistry.clear()
    assert AgentRegistry.get("nonexistent") is None


def test_registry_list_agents():
    AgentRegistry.clear()
    AgentRegistry.register(_DummyAgent())
    agents = AgentRegistry.list_agents()
    assert len(agents) == 1
    assert agents[0]["name"] == "dummy"
    assert agents[0]["description"] == "A test agent"


def test_registry_clear():
    AgentRegistry.clear()
    AgentRegistry.register(_DummyAgent())
    assert len(AgentRegistry.list_agents()) == 1
    AgentRegistry.clear()
    assert len(AgentRegistry.list_agents()) == 0


# ── ContextAgent ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_context_agent_success():
    mock_context = HouseholdContext(
        household_name="Test",
        timezone="UTC",
        people=[],
        allergies=[],
        dietary_rules=[],
        preferences=[],
        nutrition_goals=[],
    )

    with patch(
        "kitchen_pilot.agents.context_agent.get_household_context",
        new=AsyncMock(return_value=mock_context),
    ):
        agent = ContextAgent()
        ctx = AgentContext(household_id=uuid.uuid4(), session=AsyncMock())
        result = await agent.run(ContextAgentInput(), ctx)

    assert result.success is True
    assert result.data.household_name == "Test"


@pytest.mark.asyncio
async def test_context_agent_failure():
    with patch(
        "kitchen_pilot.agents.context_agent.get_household_context",
        new=AsyncMock(side_effect=RuntimeError("DB down")),
    ):
        agent = ContextAgent()
        ctx = AgentContext(household_id=uuid.uuid4(), session=AsyncMock())
        result = await agent.run(ContextAgentInput(), ctx)

    assert result.success is False
    assert "DB down" in result.error


# ── PlanAgent ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_plan_agent_success():
    mock_plan = AsyncMock()
    mock_plan.id = uuid.uuid4()
    mock_plan.summary_md = "A great week!"

    with patch(
        "kitchen_pilot.agents.plan_agent.generate_plan",
        new=AsyncMock(return_value=(mock_plan, ["warning1"], [])),
    ):
        agent = PlanAgent()
        ctx = AgentContext(household_id=uuid.uuid4(), session=AsyncMock())
        input_data = PlanAgentInput(week_start_date="2026-03-02")
        result = await agent.run(input_data, ctx)

    assert result.success is True
    assert result.data.plan_id == str(mock_plan.id)
    assert result.data.summary_md == "A great week!"
    assert "warning1" in result.data.warnings


@pytest.mark.asyncio
async def test_plan_agent_failure():
    with patch(
        "kitchen_pilot.agents.plan_agent.generate_plan",
        new=AsyncMock(side_effect=RuntimeError("LLM timeout")),
    ):
        agent = PlanAgent()
        ctx = AgentContext(household_id=uuid.uuid4(), session=AsyncMock())
        input_data = PlanAgentInput(week_start_date="2026-03-02")
        result = await agent.run(input_data, ctx)

    assert result.success is False
    assert "LLM timeout" in result.error
