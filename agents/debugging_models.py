"""Data models and contracts for error analysis and debugging."""

from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorSeverity(str, Enum):
    """Severity classification for system errors."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ErrorReport(BaseModel):
    """Structured error report schema generated from captured runtime errors."""

    error_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique error report ID.",
    )
    request_id: str = Field(
        ..., description="Traceable request ID associated with the failure."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the error occurrence.",
    )
    service: str = Field(
        default="multi-agent-system", description="Service or system name."
    )
    component: str = Field(
        ..., description="Module or component where the exception occurred."
    )
    exception_type: str = Field(
        ..., description="Python exception class name."
    )
    message: str = Field(
        ..., description="Sanitized error message string."
    )
    stack_trace: str = Field(
        ..., description="Sanitized traceback string."
    )
    environment: str = Field(
        default="production", description="Runtime environment."
    )
    severity: ErrorSeverity = Field(
        default=ErrorSeverity.HIGH, description="Estimated severity level."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata."
    )


class DebuggerRequest(BaseModel):
    """Input request contract for DebuggerAgent."""

    error_report: ErrorReport = Field(
        ..., description="Sanitized structured error report."
    )
    relevant_context: Dict[str, Any] = Field(
        default_factory=dict, description="Execution context or payload leading to error."
    )
    previous_attempts: int = Field(
        default=0, ge=0, description="Count of previous debugging analysis attempts."
    )
    repository_context: Optional[str] = Field(
        default=None, description="Explicitly provided code snippet or repository context."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata."
    )


class PatchRecommendation(BaseModel):
    """Structured, non-executing code patch recommendation."""

    file_path: str = Field(
        ..., description="Target file path relative to repo root."
    )
    description: str = Field(
        ..., description="High-level summary of recommended change."
    )
    change_type: str = Field(
        ..., description="Type of change (e.g. 'BUG_FIX', 'REFACTOR', 'GUARD_CHECK')."
    )
    old_behavior: str = Field(
        ..., description="Description of existing flawed code behavior."
    )
    new_behavior: str = Field(
        ..., description="Description of proposed fixed behavior."
    )
    rationale: str = Field(
        ..., description="Technical rationale supporting proposed fix."
    )
    validation_steps: List[str] = Field(
        default_factory=list, description="Instructions to verify proposed fix."
    )
    diff_text: Optional[str] = Field(
        default=None, description="Optional text diff/code patch recommendation for human review."
    )


class DebugAnalysis(BaseModel):
    """Structured output output contract for DebuggerAgent."""

    classification: str = Field(
        ..., description="Error classification category."
    )
    severity: ErrorSeverity = Field(
        ..., description="Assessed error severity."
    )
    root_cause: str = Field(
        ..., description="Identified root cause hypothesis."
    )
    affected_components: List[str] = Field(
        default_factory=list, description="List of components impacted by this error."
    )
    evidence: List[str] = Field(
        default_factory=list, description="Observed facts and evidence supporting analysis."
    )
    recommended_fix: str = Field(
        ..., description="Clear textual description of recommended repair."
    )
    patch: Optional[PatchRecommendation] = Field(
        default=None, description="Structured non-executing patch proposal."
    )
    tests_to_add: List[str] = Field(
        default_factory=list, description="Suggested test cases to add."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0."
    )
    requires_human_review: bool = Field(
        default=True,
        description="Always True: patch recommendations require human or authorized review.",
    )
    safety_notes: List[str] = Field(
        default_factory=list, description="Safety considerations regarding the proposed change."
    )
