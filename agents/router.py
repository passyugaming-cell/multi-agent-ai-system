"""Agent router abstraction enforcing strict allowlists."""

import logging
from typing import List, Optional, Set

from agents.base import BaseAgent
from agents.registry import AgentRegistry
from core.exceptions import AgentNotFoundError, ToolExecutionError

logger = logging.getLogger(__name__)

# Strict allowlist of permissible agent string identifiers
ALLOWED_AGENT_IDS: Set[str] = {
    "owner",
    "owner-agent",
    "cs",
    "cs-agent",
    "ads",
    "ads-agent",
    "debugger",
    "debugger-agent",
}


class AgentRouter:
    """Router mapping validated agent IDs to registered agent instances."""

    def __init__(self, registry: AgentRegistry) -> None:
        """Initialize AgentRouter.

        Args:
            registry: AgentRegistry containing active system agents.
        """
        self.registry = registry

    def resolve_agent(self, agent_id: str) -> BaseAgent:
        """Resolve an agent ID against the security allowlist and registry.

        Args:
            agent_id: Target agent string identifier.

        Returns:
            BaseAgent: Registered agent instance.

        Raises:
            ToolExecutionError: If agent_id is not in security allowlist.
            AgentNotFoundError: If agent is not registered in registry.
        """
        if agent_id not in ALLOWED_AGENT_IDS:
            logger.warning("Routing attempt to unallowed agent ID '%s' rejected.", agent_id)
            raise ToolExecutionError(
                f"Agent routing rejected: ID '{agent_id}' is not in allowed agent list."
            )

        return self.registry.get(agent_id)

    def is_allowed(self, agent_id: str) -> bool:
        """Check if an agent ID is in the security allowlist."""
        return agent_id in ALLOWED_AGENT_IDS
