"""Typed contracts for agent execution requests and results."""

from typing import Any, Dict, List, Literal, Optional, Union
import uuid
from pydantic import BaseModel, Field

try:
    from app.tenants.context import TenantContext
except ImportError:
    from tenants.context import TenantContext


class AgentRequest(BaseModel):
    """Structured request sent to an agent."""

    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Task identifier associated with request.",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Correlation request ID.",
    )
    instruction: str = Field(..., description="Prompt or instruction statement for agent.")
    tenant_id: str = Field(
        default_factory=lambda: TenantContext.get_tenant_id(),
        description="Tenant or organization ID.",
    )
    context_data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context or payload items."
    )


class AgentResult(BaseModel):
    """Standardized V1 execution result returned by all specialist AI agents."""

    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Task ID associated with this result.",
    )
    status: Literal["COMPLETED", "FAILED", "BLOCKED", "WAITING_APPROVAL"] = Field(
        default="COMPLETED",
        description="Lifecycle execution status of the task/result.",
    )
    finding: str = Field(
        default="",
        description="Core analytical finding, answer, or execution trace statement.",
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Supporting data points, facts, or metric references.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the finding (0.0 to 1.0).",
    )
    recommendation: Optional[str] = Field(
        default=None,
        description="Optional action recommendation.",
    )
    next_action: Optional[str] = Field(
        default=None,
        description="Optional recommended next action or workflow step.",
    )

    # Context & Backward Compatibility fields
    success: bool = Field(
        default=True,
        description="Boolean status indicating execution success.",
    )
    agent_id: str = Field(
        default="",
        description="ID of agent that generated this result.",
    )
    request_id: str = Field(
        default="",
        description="Request correlation ID.",
    )
    output: Optional[Any] = Field(
        default=None,
        description="Structured output payload dictionary or Pydantic object.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if status is FAILED.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution metadata.",
    )

    def model_post_init(self, __context: Any) -> None:
        """Sync legacy success boolean and output payload with finding/status."""
        if self.status == "FAILED" and self.success:
            self.success = False
        elif not self.success and self.status == "COMPLETED":
            self.status = "FAILED"

        if self.output is None and self.finding:
            self.output = {"finding": self.finding, "recommendation": self.recommendation}
        elif self.output is not None and not self.finding:
            if isinstance(self.output, dict):
                self.finding = self.output.get("finding") or self.output.get("decision") or self.output.get("response") or self.output.get("summary") or str(self.output)
            else:
                self.finding = str(self.output)
