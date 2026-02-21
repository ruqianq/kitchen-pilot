"""Kitchen Pilot agent framework.

Minimal agent abstraction: BaseAgent protocol, registry, and agent wrappers
around existing services.
"""

from kitchen_pilot.agents.base import AgentContext, AgentResult, BaseAgent
from kitchen_pilot.agents.registry import AgentRegistry

__all__ = ["AgentContext", "AgentResult", "BaseAgent", "AgentRegistry"]
