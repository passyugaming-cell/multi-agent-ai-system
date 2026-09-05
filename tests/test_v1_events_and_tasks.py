"""Unit tests for Event Bus and Task System."""

import pytest
from app.events.bus import EventBus
from app.events.models import Event, EventType
from app.tasks.manager import TaskManager
from app.tasks.models import Task, TaskStatus
from app.tenants.context import TenantContext


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    """Test EventBus async publish and subscribe with tenant isolation."""
    bus = EventBus()
    received_events = []

    def handler(event: Event):
        received_events.append(event)

    bus.subscribe(EventType.TASK_CREATED, handler, tenant_id="tenant_x")

    # Event for matching tenant
    e1 = Event(
        event_type=EventType.TASK_CREATED,
        tenant_id="tenant_x",
        source_component="test_component",
        payload={"task_id": "123"},
    )
    await bus.publish(e1)
    assert len(received_events) == 1

    # Event for different tenant should not be dispatched
    e2 = Event(
        event_type=EventType.TASK_CREATED,
        tenant_id="tenant_y",
        source_component="test_component",
        payload={"task_id": "456"},
    )
    await bus.publish(e2)
    assert len(received_events) == 1


def test_task_manager_lifecycle():
    """Test TaskManager creation, query, and status updates."""
    tm = TaskManager()

    with TenantContext.scope("tenant_alpha"):
        task = tm.create_task(
            title="Analyze campaign performance",
            description="ROAS drop analysis",
            assigned_agent="ads-agent",
        )

        assert task.status == TaskStatus.PENDING
        assert task.tenant_id == "tenant_alpha"

        updated = tm.update_task_status(
            task_id=task.task_id,
            status=TaskStatus.COMPLETED,
            result={"finding": "ROAS healthy"},
        )
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED
        assert updated.result == {"finding": "ROAS healthy"}

        tasks = tm.list_tasks(status=TaskStatus.COMPLETED)
        assert len(tasks) == 1
        assert tasks[0].task_id == task.task_id
