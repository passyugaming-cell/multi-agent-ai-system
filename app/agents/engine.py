"""Agent Engine orchestrator responsible for agent execution and context management."""

import logging
import time
import uuid
from typing import Any, Optional

from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.message_bus import MessageBus
from agents.registry import AgentRegistry
from core.exceptions import AgentExecutionError, AgentNotFoundError

logger = logging.getLogger(__name__)

MAX_EXECUTION_DEPTH = 5


class AgentEngine:
    """Agent Engine orchestrating registration, execution, and contextual boundaries."""

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        message_bus: Optional[MessageBus] = None,
        max_depth: int = MAX_EXECUTION_DEPTH,
    ) -> None:
        """Initialize AgentEngine.

        Args:
            registry: Agent registry instance. Defaults to new AgentRegistry.
            message_bus: Optional message bus instance.
            max_depth: Maximum call recursion depth allowed per request.
        """
        self.registry = registry or AgentRegistry()
        self.message_bus = message_bus
        self.max_depth = max_depth

    async def execute_agent(
        self,
        agent_id: str,
        request: Any,
        context: Optional[AgentContext] = None,
    ) -> AgentResult:
        """Execute an agent by ID with execution boundary and error handling.

        Args:
            agent_id: Unique string ID of registered agent.
            request: Agent request data.
            context: Execution context. Auto-generated if None.

        Returns:
            AgentResult: Standardized execution result.
        """
        if not self.registry.exists(agent_id):
            raise AgentNotFoundError(f"Cannot execute unknown agent '{agent_id}'.")

        agent = self.registry.get(agent_id)

        # Prepare context with propagated or generated request_id
        if context is None:
            context = AgentContext(request_id=str(uuid.uuid4()))
        else:
            # Create updated context copy incrementing execution depth
            context = AgentContext(
                request_id=context.request_id,
                conversation_id=context.conversation_id,
                user_id=context.user_id,
                tenant_id=context.tenant_id,
                source_agent=context.source_agent,
                execution_depth=context.execution_depth + 1,
                metadata=dict(context.metadata),
            )

        # Recursion safety guard
        if context.execution_depth > self.max_depth:
            error_msg = f"Maximum execution depth ({self.max_depth}) exceeded for request_id {context.request_id}."
            logger.error(error_msg)
            return AgentResult(
                success=False,
                agent_id=agent_id,
                request_id=context.request_id,
                error=error_msg,
            )

        start_time = time.perf_counter()
        logger.info(
            "Executing agent '%s' (request_id=%s, depth=%d)",
            agent_id,
            context.request_id,
            context.execution_depth,
        )

        try:
            result = await agent.execute(request, context)
            duration = time.perf_counter() - start_time
            result.metadata["execution_duration_sec"] = duration
            logger.info(
                "Agent '%s' finished execution in %.3f seconds (success=%s)",
                agent_id,
                duration,
                result.success,
            )
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                "Unhandled error executing agent '%s': %s", agent_id, str(e), exc_info=True
            )
            return AgentResult(
                success=False,
                agent_id=agent_id,
                request_id=context.request_id,
                error=f"Execution failed: {e}",
                metadata={"execution_duration_sec": duration},
            )
