"""Base agent protocol and shared types."""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class AgentContext(BaseModel):
    """Shared context passed to all agents."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    household_id: uuid.UUID
    session: Any = None  # AsyncSession — not serializable
    correlation_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])


TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class AgentResult(BaseModel, Generic[TOutput]):
    """Standard agent output wrapper."""

    success: bool
    data: TOutput | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC, Generic[TInput, TOutput]):
    """Base class for all Kitchen Pilot agents."""

    name: str
    description: str

    @abstractmethod
    async def run(
        self, input: TInput, context: AgentContext
    ) -> AgentResult[TOutput]:
        ...
