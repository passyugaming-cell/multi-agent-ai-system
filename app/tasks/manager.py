"""Task Manager for creating, tracking, updating, and querying agent tasks."""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

try:
    from app.tasks.models import Task, TaskStatus
    from app.tenants.context import TenantContext
except ImportError:
    from tasks.models import Task, TaskStatus
    from tenants.context import TenantContext

logger = logging.getLogger(__name__)


class TaskManager:
    """In-memory task state manager with tenant isolation."""

    def __init__(self) -> None:
        """Initialize TaskManager."""
        self._tasks: Dict[str, Task] = {}

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        assigned_agent: Optional[str] = None,
        tenant_id: Optional[str] = None,
        payload: Optional[Dict] = None,
    ) -> Task:
        """Create and store a new task."""
        tid = tenant_id or TenantContext.get_tenant_id()
        task = Task(
            title=title,
            description=description,
            assigned_agent=assigned_agent,
            tenant_id=tid,
            payload=payload or {},
        )
        self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str, tenant_id: Optional[str] = None) -> Optional[Task]:
        """Get task by task_id with optional tenant scope check."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        check_tenant = tenant_id or TenantContext.get_tenant_id()
        if check_tenant != "*" and task.tenant_id != check_tenant:
            logger.warning("Tenant mismatch attempting to access task %s", task_id)
            return None
        return task

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict] = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[Task]:
        """Update task status and store optional result."""
        task = self.get_task(task_id, tenant_id=tenant_id)
        if not task:
            return None
        task.status = status
        if result is not None:
            task.result = result
        task.updated_at = datetime.now(timezone.utc)
        return task

    def list_tasks(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        assigned_agent: Optional[str] = None,
    ) -> List[Task]:
        """List tasks matching filters."""
        tid = tenant_id or TenantContext.get_tenant_id()
        results: List[Task] = []
        for task in self._tasks.values():
            if tid != "*" and task.tenant_id != tid:
                continue
            if status is not None and task.status != status:
                continue
            if assigned_agent is not None and task.assigned_agent != assigned_agent:
                continue
            results.append(task)
        return results
