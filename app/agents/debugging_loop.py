"""Self-debugging loop orchestration."""

import logging
from typing import Any, Dict, Optional

from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.debugger_agent import DebuggerAgent
from agents.debugging_models import DebugAnalysis, DebuggerRequest, ErrorReport, ErrorSeverity
from core.debugging.error_capture import capture_exception

logger = logging.getLogger(__name__)

DEFAULT_MAX_DEBUG_ATTEMPTS = 3


class SelfDebuggingLoop:
    """Self-debugging analysis loop orchestrating exception capture and analysis via DebuggerAgent.

    NOTE: The loop generates root cause analysis and patch recommendations.
    It DOES NOT modify source code or execute commands automatically.
    """

    def __init__(
        self,
        debugger_agent: DebuggerAgent,
        max_attempts: int = DEFAULT_MAX_DEBUG_ATTEMPTS,
    ) -> None:
        """Initialize SelfDebuggingLoop.

        Args:
            debugger_agent: DebuggerAgent instance.
            max_attempts: Hard maximum analysis attempt limit (default 3).
        """
        self.debugger_agent = debugger_agent
        self.max_attempts = max_attempts

    async def analyze_exception(
        self,
        exc: Exception,
        component: str,
        context: AgentContext,
        relevant_context: Optional[Dict[str, Any]] = None,
        repository_context: Optional[str] = None,
        attempt_count: int = 1,
    ) -> AgentResult:
        """Capture exception, sanitize secrets, and trigger DebuggerAgent analysis.

        Args:
            exc: Caught Python exception.
            component: Name of failing component/module.
            context: Current AgentContext.
            relevant_context: Context dictionary leading to failure.
            repository_context: Code snippet or context string.
            attempt_count: Current debugging attempt iteration.

        Returns:
            AgentResult: Execution result containing DebugAnalysis output or failure result.
        """
        # Hard limit enforcement against infinite debugging recursion
        if attempt_count > self.max_attempts:
            err_msg = (
                f"SelfDebuggingLoop exceeded max attempts ({self.max_attempts}) "
                f"for request_id {context.request_id} on component '{component}'."
            )
            logger.error(err_msg)
            return AgentResult(
                success=False,
                agent_id=self.debugger_agent.agent_id,
                request_id=context.request_id,
                error=err_msg,
                metadata={"max_attempts_exceeded": True, "attempt_count": attempt_count},
            )

        # STEP 1 & 2 & 3: Capture exception, create ErrorReport, sanitize sensitive data
        error_report: ErrorReport = capture_exception(
            exc=exc,
            component=component,
            request_id=context.request_id,
            severity=ErrorSeverity.HIGH,
            metadata={"execution_depth": context.execution_depth},
        )

        # STEP 4: Build DebuggerRequest
        debug_request = DebuggerRequest(
            error_report=error_report,
            relevant_context=relevant_context or {},
            previous_attempts=attempt_count - 1,
            repository_context=repository_context,
        )

        # STEP 5 & 6 & 7: Trigger DebuggerAgent execution
        logger.info(
            "Invoking DebuggerAgent via SelfDebuggingLoop (attempt %d/%d) for request_id %s",
            attempt_count,
            self.max_attempts,
            context.request_id,
        )

        result = await self.debugger_agent.execute(debug_request, context)

        # STEP 8: Return DebugAnalysis result to caller
        return result
