"""Agent registry for managing agent instances."""

import logging
from typing import Dict, List, Optional

from agents.base import BaseAgent
from core.exceptions import AgentNotFoundError, DuplicateAgentError

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry maintaining active agent instances in memory."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register a new agent instance.

        Args:
            agent: BaseAgent instance to register.

        Raises:
            DuplicateAgentError: If an agent with the same agent_id already exists.
        """
        if agent.agent_id in self._agents:
            raise DuplicateAgentError(f"Agent with ID '{agent.agent_id}' is already registered.")
        self._agents[agent.agent_id] = agent
        logger.info("Registered agent: %s (%s)", agent.name, agent.agent_id)

    def get(self, agent_id: str) -> BaseAgent:
        """Retrieve registered agent by ID.

        Args:
            agent_id: Agent string identifier.

        Returns:
            BaseAgent: Registered agent instance.

        Raises:
            AgentNotFoundError: If agent_id is not found in registry.
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found in registry.")
        return self._agents[agent_id]

    def exists(self, agent_id: str) -> bool:
        """Check if agent exists in registry."""
        return agent_id in self._agents

    def list_agents(self) -> List[BaseAgent]:
        """List all registered agents."""
        return list(self._agents.values())

    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
