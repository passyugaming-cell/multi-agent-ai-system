"""Application Orchestrator and orchestration models.

Coordinates request routing, trace logging, agent execution via AgentEngine,
and self-debugging workflows.
"""

from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field

from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.debugging_loop import SelfDebuggingLoop
from agents.engine import AgentEngine
from agents.message_bus import MessageBus
from agents.owner_agent import OwnerDecision
from agents.registry import AgentRegistry
from agents.router import AgentRouter
from core.exceptions import ApplicationError, ToolExecutionError

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status for requests and traces."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEBUGGING = "DEBUGGING"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class ExecutionTraceEntry(BaseModel):
    """Typed execution trace record."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the trace event.",
    )
    request_id: str = Field(..., description="Correlated request ID.")
    agent_id: str = Field(..., description="ID of agent or component involved.")
    event: str = Field(..., description="Trace event description.")
    status: ExecutionStatus = Field(..., description="Status at this step.")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Event metadata (secrets omitted)."
    )


class OrchestrationRequest(BaseModel):
    """Input request for application orchestration."""

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Correlation ID for request tracing across agents.",
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Optional conversation session ID."
    )
    tenant_id: Optional[str] = Field(
        default=None, description="Optional tenant or organization ID."
    )
    user_id: Optional[str] = Field(
        default=None, description="Optional requesting user ID."
    )
    instruction: str = Field(
        ..., description="User instruction or prompt statement."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata."
    )


class OrchestrationResult(BaseModel):
    """Structured response from ApplicationOrchestrator."""

    request_id: str = Field(..., description="Correlated request ID.")
    success: bool = Field(
        ..., description="Indicates whether overall orchestration succeeded."
    )
    final_response: str = Field(
        ..., description="Human-facing executive summary or output string."
    )
    status: ExecutionStatus = Field(
        default=ExecutionStatus.COMPLETED,
        description="Final execution status of the request.",
    )
    owner_decision: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured decision produced by Owner Agent."
    )
    agent_results: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Structured execution outputs keyed by agent_id.",
    )
    debug_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Debug analysis result if an error occurred and debugger ran.",
    )
    errors: List[str] = Field(
        default_factory=list, description="List of error messages encountered."
    )
    execution_trace: List[ExecutionTraceEntry] = Field(
        default_factory=list, description="Ordered trace of execution events."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Orchestration metadata."
    )


# Callback type for real-time trace events
TraceCallback = Callable[[ExecutionTraceEntry], None]


class ApplicationOrchestrator:
    """Application-level coordinator connecting agents, routing, and self-debugging."""

    def __init__(
        self,
        engine: AgentEngine,
        registry: AgentRegistry,
        message_bus: MessageBus,
        debugging_loop: Optional[SelfDebuggingLoop] = None,
        trace_callback: Optional[TraceCallback] = None,
    ) -> None:
        """Initialize ApplicationOrchestrator.

        Args:
            engine: AgentEngine instance for agent execution.
            registry: AgentRegistry containing active agents.
            message_bus: MessageBus instance for inter-agent messaging.
            debugging_loop: Optional SelfDebuggingLoop for error handling.
            trace_callback: Optional real-time callback for trace entries.
        """
        self.engine = engine
        self.registry = registry
        self.message_bus = message_bus
        self.debugging_loop = debugging_loop
        self.router = AgentRouter(registry)
        self.trace_callback = trace_callback

    def _add_trace(
        self,
        trace_list: List[ExecutionTraceEntry],
        request_id: str,
        agent_id: str,
        event: str,
        status: ExecutionStatus,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an execution trace entry and notify callback if present."""
        entry = ExecutionTraceEntry(
            request_id=request_id,
            agent_id=agent_id,
            event=event,
            status=status,
            metadata=metadata or {},
        )
        trace_list.append(entry)
        if self.trace_callback:
            try:
                self.trace_callback(entry)
            except Exception as e:
                logger.warning("Trace callback error: %s", e)

    async def handle_request(
        self,
        request: OrchestrationRequest | str,
    ) -> OrchestrationResult:
        """Process a user instruction through Owner decision, specialist routing, and debugging.

        Args:
            request: OrchestrationRequest instance or prompt string.

        Returns:
            OrchestrationResult: Complete structured execution result.
        """
        if isinstance(request, str):
            req = OrchestrationRequest(instruction=request)
        else:
            req = request

        execution_trace: List[ExecutionTraceEntry] = []
        agent_results: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []

        # Step 0: Initialize context
        context = AgentContext(
            request_id=req.request_id,
            conversation_id=req.conversation_id,
            user_id=req.user_id,
            tenant_id=req.tenant_id,
            metadata=req.metadata,
        )

        self._add_trace(
            execution_trace,
            req.request_id,
            "orchestrator",
            f"Received request: '{req.instruction[:50]}...'",
            ExecutionStatus.RUNNING,
        )

        # Step 1: Execute Owner Agent for initial decision and routing
        self._add_trace(
            execution_trace,
            req.request_id,
            "owner-agent",
            "Owner Agent analyzing instruction...",
            ExecutionStatus.RUNNING,
        )

        owner_agent_id = "owner-agent" if self.registry.exists("owner-agent") else "owner"
        owner_result: AgentResult = await self.engine.execute_agent(
            agent_id=owner_agent_id,
            request=req.instruction,
            context=context,
        )

        if not owner_result.success or not owner_result.output:
            err = owner_result.error or "Owner Agent failed to generate decision."
            errors.append(err)
            self._add_trace(
                execution_trace,
                req.request_id,
                owner_agent_id,
                f"Owner Agent failed: {err}",
                ExecutionStatus.FAILED,
            )
            return await self._handle_failure(
                req=req,
                context=context,
                failing_agent=owner_agent_id,
                error_msg=err,
                exc=Exception(err),
                execution_trace=execution_trace,
                agent_results=agent_results,
                errors=errors,
            )

        agent_results[owner_agent_id] = owner_result.output
        owner_decision_dict = owner_result.output
        target_agent = owner_decision_dict.get("target_agent")

        self._add_trace(
            execution_trace,
            req.request_id,
            owner_agent_id,
            f"Owner Agent completed decision. Target agent: {target_agent or 'None'}",
            ExecutionStatus.COMPLETED,
        )

        # Step 2: Route to Specialist Agent if specified
        if target_agent and target_agent.strip():
            target_agent_id = target_agent.strip()

            # Security Allowlist Check via AgentRouter
            if not self.router.is_allowed(target_agent_id):
                err = f"Agent routing rejected: Target agent ID '{target_agent_id}' is not in security allowlist."
                errors.append(err)
                self._add_trace(
                    execution_trace,
                    req.request_id,
                    "orchestrator",
                    err,
                    ExecutionStatus.FAILED,
                )
                return OrchestrationResult(
                    request_id=req.request_id,
                    success=False,
                    final_response=f"Routing error: {err}",
                    status=ExecutionStatus.FAILED,
                    owner_decision=owner_decision_dict,
                    agent_results=agent_results,
                    errors=errors,
                    execution_trace=execution_trace,
                )

            # Resolve canonical agent in registry
            try:
                resolved_agent = self.router.resolve_agent(target_agent_id)
                canonical_agent_id = resolved_agent.agent_id
            except Exception as e:
                err = f"Failed to resolve target agent '{target_agent_id}': {e}"
                errors.append(err)
                self._add_trace(
                    execution_trace,
                    req.request_id,
                    "orchestrator",
                    err,
                    ExecutionStatus.FAILED,
                )
                return OrchestrationResult(
                    request_id=req.request_id,
                    success=False,
                    final_response=f"Agent lookup error: {err}",
                    status=ExecutionStatus.FAILED,
                    owner_decision=owner_decision_dict,
                    agent_results=agent_results,
                    errors=errors,
                    execution_trace=execution_trace,
                )

            self._add_trace(
                execution_trace,
                req.request_id,
                canonical_agent_id,
                f"Specialist agent '{canonical_agent_id}' executing...",
                ExecutionStatus.RUNNING,
            )

            specialist_result: AgentResult = await self.engine.execute_agent(
                agent_id=canonical_agent_id,
                request=req.instruction,
                context=context,
            )

            if not specialist_result.success or not specialist_result.output:
                err = specialist_result.error or f"Specialist agent '{canonical_agent_id}' failed execution."
                errors.append(err)
                self._add_trace(
                    execution_trace,
                    req.request_id,
                    canonical_agent_id,
                    f"Agent execution failed: {err}",
                    ExecutionStatus.FAILED,
                )
                return await self._handle_failure(
                    req=req,
                    context=context,
                    failing_agent=canonical_agent_id,
                    error_msg=err,
                    exc=Exception(err),
                    execution_trace=execution_trace,
                    agent_results=agent_results,
                    errors=errors,
                    owner_decision=owner_decision_dict,
                )

            agent_results[canonical_agent_id] = specialist_result.output
            self._add_trace(
                execution_trace,
                req.request_id,
                canonical_agent_id,
                f"Specialist agent '{canonical_agent_id}' completed execution successfully.",
                ExecutionStatus.COMPLETED,
            )

            # Build final response text
            final_summary = self._build_final_summary(owner_decision_dict, specialist_result.output, canonical_agent_id)

            self._add_trace(
                execution_trace,
                req.request_id,
                "orchestrator",
                "Orchestration completed successfully.",
                ExecutionStatus.COMPLETED,
            )

            return OrchestrationResult(
                request_id=req.request_id,
                success=True,
                final_response=final_summary,
                status=ExecutionStatus.COMPLETED,
                owner_decision=owner_decision_dict,
                agent_results=agent_results,
                execution_trace=execution_trace,
            )

        # No target agent requested, return Owner decision as final response
        summary_text = owner_decision_dict.get("decision", "Instruction processed.")
        self._add_trace(
            execution_trace,
            req.request_id,
            "orchestrator",
            "Orchestration completed with Owner Agent decision.",
            ExecutionStatus.COMPLETED,
        )

        return OrchestrationResult(
            request_id=req.request_id,
            success=True,
            final_response=summary_text,
            status=ExecutionStatus.COMPLETED,
            owner_decision=owner_decision_dict,
            agent_results=agent_results,
            execution_trace=execution_trace,
        )

    async def _handle_failure(
        self,
        req: OrchestrationRequest,
        context: AgentContext,
        failing_agent: str,
        error_msg: str,
        exc: Exception,
        execution_trace: List[ExecutionTraceEntry],
        agent_results: Dict[str, Dict[str, Any]],
        errors: List[str],
        owner_decision: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """Handle agent execution failure by invoking SelfDebuggingLoop if available."""
        debug_result_dict: Optional[Dict[str, Any]] = None

        if self.debugging_loop:
            self._add_trace(
                execution_trace,
                req.request_id,
                "debugger-agent",
                f"Invoking SelfDebuggingLoop for failure in '{failing_agent}'...",
                ExecutionStatus.DEBUGGING,
            )

            try:
                debug_agent_result: AgentResult = await self.debugging_loop.analyze_exception(
                    exc=exc,
                    component=failing_agent,
                    context=context,
                    relevant_context={"instruction": req.instruction, "error": error_msg},
                )

                if debug_agent_result.success and debug_agent_result.output:
                    debug_result_dict = debug_agent_result.output
                    self._add_trace(
                        execution_trace,
                        req.request_id,
                        "debugger-agent",
                        "Debugger Agent completed analysis. Human review required.",
                        ExecutionStatus.REQUIRES_HUMAN_REVIEW,
                    )
                else:
                    dbg_err = debug_agent_result.error or "Debugger Agent failed analysis."
                    errors.append(f"Debugger error: {dbg_err}")
                    self._add_trace(
                        execution_trace,
                        req.request_id,
                        "debugger-agent",
                        f"SelfDebuggingLoop failed: {dbg_err}",
                        ExecutionStatus.FAILED,
                    )
            except Exception as debug_exc:
                dbg_err = f"SelfDebuggingLoop unexpected failure: {debug_exc}"
                errors.append(dbg_err)
                self._add_trace(
                    execution_trace,
                    req.request_id,
                    "debugger-agent",
                    dbg_err,
                    ExecutionStatus.FAILED,
                )

        final_msg = f"Execution failed in '{failing_agent}'. Original error: {error_msg}"
        if debug_result_dict:
            rc = debug_result_dict.get("root_cause_analysis", "No root cause provided.")
            rec = debug_result_dict.get("patch_recommendation", "No patch recommendation.")
            final_msg += f"\n\n[DEBUGGER ANALYSIS]\nRoot Cause: {rc}\nPatch Recommendation: {rec}\n(Human review required)"

        return OrchestrationResult(
            request_id=req.request_id,
            success=False,
            final_response=final_msg,
            status=ExecutionStatus.REQUIRES_HUMAN_REVIEW if debug_result_dict else ExecutionStatus.FAILED,
            owner_decision=owner_decision,
            agent_results=agent_results,
            debug_result=debug_result_dict,
            errors=errors,
            execution_trace=execution_trace,
        )

    def _build_final_summary(
        self,
        owner_decision: Dict[str, Any],
        specialist_output: Dict[str, Any],
        specialist_id: str,
    ) -> str:
        """Build a clean final summary text from owner decision and specialist agent output."""
        owner_dec = owner_decision.get("decision", "")
        if "cs" in specialist_id:
            cs_response = specialist_output.get("response", "")
            next_step = specialist_output.get("recommended_next_step", "")
            return f"{cs_response}\n\n[Recommended Next Step]: {next_step}"
        elif "ads" in specialist_id:
            summary = specialist_output.get("summary", "")
            recs = specialist_output.get("recommendations", [])
            recs_text = "\n- ".join(recs) if recs else "None"
            return f"{summary}\n\n[Recommendations]:\n- {recs_text}"
        else:
            return str(specialist_output)
