"""Agent registry for discovery and routing."""

from kitchen_pilot.agents.base import BaseAgent


class AgentRegistry:
    """Simple dict-based registry for agent instances."""

    _agents: dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, agent: BaseAgent) -> None:
        cls._agents[agent.name] = agent

    @classmethod
    def get(cls, name: str) -> BaseAgent | None:
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> list[dict[str, str]]:
        return [
            {"name": a.name, "description": a.description}
            for a in cls._agents.values()
        ]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered agents (useful for testing)."""
        cls._agents = {}
