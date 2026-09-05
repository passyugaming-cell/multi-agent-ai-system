"""Abstract base class for all system agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from agents.context import AgentContext
from agents.contracts import AgentResult


class BaseAgent(ABC):
    """Abstract base class establishing common contracts for specialized agents."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        system_instruction: str,
    ) -> None:
        """Initialize BaseAgent.

        Args:
            agent_id: Unique string identifier for the agent (e.g. 'owner', 'cs').
            name: Human-readable name.
            description: Description of agent responsibilities.
            system_instruction: Core system prompt guiding AI behavior.
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.system_instruction = system_instruction

    @abstractmethod
    async def execute(
        self,
        request: Any,
        context: AgentContext,
    ) -> AgentResult:
        """Execute agent workflow asynchronously.

        Args:
            request: Typed request data or string query.
            context: Execution context containing IDs and metadata.

        Returns:
            AgentResult: Execution result model.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_id={self.agent_id!r}, name={self.name!r})"
