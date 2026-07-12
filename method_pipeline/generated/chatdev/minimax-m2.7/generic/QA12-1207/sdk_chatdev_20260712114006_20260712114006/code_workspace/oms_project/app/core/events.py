"""
OMS Core Events - Event bus and event types for cross-cutting concerns.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Callable, List
import threading


class EventType(str, Enum):
    """OMS Event Types."""
    # Order events
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_SHIPPED = "ORDER_SHIPPED"
    ORDER_COMPLETED = "ORDER_COMPLETED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    
    # Payment events
    PAYMENT_CREATED = "PAYMENT_CREATED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_REFUNDED = "PAYMENT_REFUNDED"
    
    # Invoice events
    INVOICE_CREATED = "INVOICE_CREATED"
    INVOICE_ISSUED = "INVOICE_ISSUED"
    INVOICE_PAID = "INVOICE_PAID"
    INVOICE_OVERDUE = "INVOICE_OVERDUE"
    
    # Customer events
    CUSTOMER_CREATED = "CUSTOMER_CREATED"
    CUSTOMER_UPDATED = "CUSTOMER_UPDATED"
    
    # Product events
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_UPDATED = "PRODUCT_UPDATED"
    STOCK_LOW = "STOCK_LOW"
    STOCK_OUT = "STOCK_OUT"
    
    # System events
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    CIRCUIT_CLOSED = "CIRCUIT_CLOSED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CHECKPOINT_CREATED = "CHECKPOINT_CREATED"


@dataclass
class Event:
    """Base event class."""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Simple event bus for publish-subscribe pattern."""
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subscribers = {}
                cls._instance._subscriber_lock = threading.RLock()
            return cls._instance
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """Subscribe to an event type."""
        with self._subscriber_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """Unsubscribe from an event type."""
        with self._subscriber_lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(handler)
    
    def publish(self, event: Event):
        """Publish an event to all subscribers."""
        with self._subscriber_lock:
            handlers = self._subscribers.get(event.event_type, []).copy()
        
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # Swallow handler exceptions


_event_bus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish_event(event_type: EventType, data: Dict[str, Any] = None):
    """Convenience function to publish an event."""
    event = Event(
        event_type=event_type,
        data=data or {}
    )
    get_event_bus().publish(event)
