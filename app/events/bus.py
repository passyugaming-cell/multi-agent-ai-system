"""Asynchronous typed Event Bus with multi-tenant filtering."""

import asyncio
import inspect
import logging
from typing import Awaitable, Callable, Dict, List, Optional, Union

try:
    from app.events.models import Event, EventType
except ImportError:
    from events.models import Event, EventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Union[Awaitable[None], None]]


class Subscription:
    """Subscription record holding subscriber callback and tenant filter."""

    def __init__(self, handler: EventHandler, tenant_id: str = "*") -> None:
        self.handler = handler
        self.tenant_id = tenant_id


class EventBus:
    """Async event bus managing subscriptions and tenant-isolated event dispatching."""

    def __init__(self, max_history: int = 1000) -> None:
        """Initialize EventBus."""
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._event_history: List[Event] = []
        self._max_history = max_history

    def subscribe(
        self,
        event_type: Union[EventType, str],
        handler: EventHandler,
        tenant_id: str = "*",
    ) -> None:
        """Register a callback for an event type with optional tenant filter.

        Args:
            event_type: EventType or "*" for all event types.
            handler: Sync or async callable taking an Event.
            tenant_id: Tenant ID to filter on, or "*" for all tenants.
        """
        type_key = str(event_type.value if isinstance(event_type, EventType) else event_type)
        if type_key not in self._subscriptions:
            self._subscriptions[type_key] = []
        self._subscriptions[type_key].append(Subscription(handler, tenant_id))

    def unsubscribe(
        self,
        event_type: Union[EventType, str],
        handler: EventHandler,
    ) -> None:
        """Remove a callback subscription."""
        type_key = str(event_type.value if isinstance(event_type, EventType) else event_type)
        if type_key in self._subscriptions:
            self._subscriptions[type_key] = [
                s for s in self._subscriptions[type_key] if s.handler != handler
            ]

    async def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers in current tenant context."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        type_key = event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)
        relevant_subscribers: List[Subscription] = []

        for key in (type_key, "*"):
            if key in self._subscriptions:
                for sub in self._subscriptions[key]:
                    if sub.tenant_id == "*" or sub.tenant_id == event.tenant_id:
                        relevant_subscribers.append(sub)

        for sub in relevant_subscribers:
            try:
                res = sub.handler(event)
                if inspect.isawaitable(res):
                    await res
            except Exception as e:
                logger.error("Error executing event handler for event %s: %s", event.event_id, e)

    def get_history(self, tenant_id: Optional[str] = None) -> List[Event]:
        """Get past published events, optionally filtered by tenant_id."""
        if tenant_id is None or tenant_id == "*":
            return list(self._event_history)
        return [e for e in self._event_history if e.tenant_id == tenant_id]
