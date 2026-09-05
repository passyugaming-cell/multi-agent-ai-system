"""Debugger Agent implementation."""

import logging
import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

try:
    from app.agents.base import BaseAgent
    from app.agents.context import AgentContext
    from app.agents.contracts import AgentResult
    from app.agents.debugging_models import DebugAnalysis, DebuggerRequest, ErrorReport
    from app.agents.message_bus import MessageBus
    from app.agents.prompts.debugger_prompt import DEBUGGER_SYSTEM_INSTRUCTION
    from app.core.ai.genai_client import GenAIClient
except ImportError:
    from agents.base import BaseAgent
    from agents.context import AgentContext
    from agents.contracts import AgentResult
    from agents.debugging_models import DebugAnalysis, DebuggerRequest, ErrorReport
    from agents.message_bus import MessageBus
    from agents.prompts.debugger_prompt import DEBUGGER_SYSTEM_INSTRUCTION
    from core.ai.genai_client import GenAIClient

logger = logging.getLogger(__name__)


class DebuggerAgent(BaseAgent):
    """Debugger Agent for root cause error analysis and non-executing patch generation."""

    def __init__(
        self,
        genai_client: GenAIClient,
        message_bus: Optional[MessageBus] = None,
        agent_id: str = "debugger-agent",
        name: str = "Debugger Agent",
        description: str = "Automated error root-cause analysis and non-executing patch recommendation agent.",
        system_instruction: str = DEBUGGER_SYSTEM_INSTRUCTION,
    ) -> None:
        """Initialize DebuggerAgent.

        Args:
            genai_client: Centralized GenAIClient dependency.
            message_bus: Optional MessageBus instance.
            agent_id: Agent string identifier (default 'debugger-agent').
            name: Agent name.
            description: Agent description.
            system_instruction: System prompt for debugging analysis.
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            system_instruction=system_instruction,
        )
        self.genai_client = genai_client
        self.message_bus = message_bus

    async def execute(
        self,
        request: Any,
        context: AgentContext,
    ) -> AgentResult:
        """Execute error analysis and generate non-executing patch recommendations asynchronously."""
        if isinstance(request, DebuggerRequest):
            debug_req = request
        elif isinstance(request, ErrorReport):
            debug_req = DebuggerRequest(error_report=request)
        elif isinstance(request, dict):
            if "error_report" in request:
                debug_req = DebuggerRequest.model_validate(request)
            else:
                err_report = ErrorReport.model_validate(request)
                debug_req = DebuggerRequest(error_report=err_report)
        else:
            return AgentResult(
                status="FAILED",
                finding=f"Invalid request type '{type(request).__name__}' provided to DebuggerAgent.",
                confidence=0.0,
                success=False,
                agent_id=self.agent_id,
                request_id=context.request_id,
                error=f"Invalid request type '{type(request).__name__}' provided to DebuggerAgent.",
            )

        report = debug_req.error_report

        formatted_prompt = (
            f"ERROR REPORT:\n"
            f"Component: {report.component}\n"
            f"Exception Type: {report.exception_type}\n"
            f"Message: {report.message}\n"
            f"Severity: {report.severity}\n"
            f"Stack Trace:\n{report.stack_trace}\n\n"
            f"RELEVANT EXECUTION CONTEXT:\n{debug_req.relevant_context}\n\n"
            f"REPOSITORY CODE CONTEXT:\n{debug_req.repository_context or 'None provided'}\n\n"
            f"PREVIOUS ATTEMPTS: {debug_req.previous_attempts}\n"
        )

        try:
            analysis: DebugAnalysis = await self.genai_client.generate_structured_async(
                prompt=formatted_prompt,
                response_schema=DebugAnalysis,
                system_instruction=self.system_instruction,
            )

            analysis.requires_human_review = True

            return AgentResult(
                status="WAITING_APPROVAL",
                finding=analysis.root_cause_analysis,
                evidence=analysis.affected_components,
                confidence=analysis.confidence,
                recommendation=analysis.patch_recommendation,
                next_action="Human Review Required for Patch",
                success=True,
                agent_id=self.agent_id,
                request_id=context.request_id,
                output=analysis.model_dump(),
                metadata={"model_used": self.genai_client.default_model},
            )
        except Exception as e:
            logger.error(
                "DebuggerAgent execution failed for request_id %s: %s",
                context.request_id,
                str(e),
                exc_info=True,
            )
            return AgentResult(
                status="FAILED",
                finding=f"DebuggerAgent execution failed: {e}",
                confidence=0.0,
                success=False,
                agent_id=self.agent_id,
                request_id=context.request_id,
                error=f"DebuggerAgent execution failed: {e}",
            )
