"""Typed contract for agent execution results."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Typed result returned by an agent execution."""

    success: bool = Field(..., description="Indicates if the agent execution succeeded.")
    agent_id: str = Field(..., description="ID of the agent that performed execution.")
    request_id: str = Field(..., description="Request ID associated with execution.")
    output: Optional[Any] = Field(
        default=None, description="Structured output payload or response from the agent."
    )
    error: Optional[str] = Field(
        default=None, description="Error message if execution failed."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata and timing info."
    )
