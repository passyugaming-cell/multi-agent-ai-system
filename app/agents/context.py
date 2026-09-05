"""Typed execution context for multi-agent workflows."""

import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

try:
    from app.tenants.context import TenantContext
except ImportError:
    from tenants.context import TenantContext


class AgentContext(BaseModel):
    """Contextual information provided during agent execution."""

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier tracking a request across agents.",
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Optional conversation session ID."
    )
    user_id: Optional[str] = Field(default=None, description="Optional requesting user ID.")
    tenant_id: str = Field(
        default_factory=lambda: TenantContext.get_tenant_id(),
        description="Tenant or organization ID.",
    )
    source_agent: Optional[str] = Field(
        default=None, description="Agent ID that initiated this request if applicable."
    )
    execution_depth: int = Field(
        default=0, description="Recursion depth counter to prevent infinite agent call loops."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary safe execution metadata."
    )
