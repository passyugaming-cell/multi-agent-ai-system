"""Event models and event types for asynchronous event bus."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field

try:
    from app.tenants.context import TenantContext
except ImportError:
    from tenants.context import TenantContext


class EventType(str, Enum):
    """Standardized event types across system components."""

    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_FAILED = "AGENT_FAILED"
    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    DEBUG_TRIGGERED = "DEBUG_TRIGGERED"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class Event(BaseModel):
    """Typed event payload for system event bus."""

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event ID.",
    )
    event_type: EventType = Field(..., description="Type of event.")
    tenant_id: str = Field(
        default_factory=lambda: TenantContext.get_tenant_id(),
        description="Tenant or organization ID scoping this event.",
    )
    source_component: str = Field(..., description="Component or agent that emitted the event.")
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="JSON-compatible event payload."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata associated with event."
    )
