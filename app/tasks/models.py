"""Task system data models and status enumeration."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field

try:
    from app.tenants.context import TenantContext
except ImportError:
    from tenants.context import TenantContext


class TaskStatus(str, Enum):
    """Lifecycle status for system tasks."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    WAITING_APPROVAL = "WAITING_APPROVAL"


class Task(BaseModel):
    """Task unit assigned to an agent or system component."""

    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique task identifier.",
    )
    title: str = Field(..., description="Short title describing task.")
    description: Optional[str] = Field(default=None, description="Detailed description.")
    assigned_agent: Optional[str] = Field(
        default=None, description="Agent ID assigned to execute task."
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current execution status of task."
    )
    tenant_id: str = Field(
        default_factory=lambda: TenantContext.get_tenant_id(),
        description="Tenant or organization ID owning task.",
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Input payload or instruction parameters."
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Output payload or AgentResult dictionary."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC task creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC task last updated timestamp.",
    )
