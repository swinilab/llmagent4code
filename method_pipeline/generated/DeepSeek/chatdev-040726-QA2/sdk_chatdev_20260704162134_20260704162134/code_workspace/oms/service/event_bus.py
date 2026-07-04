"""
Simple in-process event bus for domain events.
Allows services to react to events without direct coupling.
"""

import logging
from collections.abc import Callable
from typing import Any

from oms.domain.events import DomainEvent

logger = logging.getLogger(__name__)


class EventBus:
    """In-process pub/sub event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Register a handler for a domain event type."""
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers."""
        handlers = self._subscribers.get(type(event), [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Handler %s failed for event %s", handler.__name__, event)


# Global singleton
event_bus = EventBus()
