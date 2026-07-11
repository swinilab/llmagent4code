"""
Domain events for cross-context communication.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base class for all domain events."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrderPlaced(DomainEvent):
    """Emitted when a customer places an order."""
    order_id: UUID
    customer_id: UUID


class OrderAccepted(DomainEvent):
    """Emitted when Order Staff accepts an order."""
    order_id: UUID
    staff_id: UUID


class OrderCancelled(DomainEvent):
    """Emitted when an order is cancelled."""
    order_id: UUID
    reason: str


class InvoiceCreated(DomainEvent):
    """Emitted when an invoice is created for an order."""
    invoice_id: UUID
    order_id: UUID


class PaymentReceived(DomainEvent):
    """Emitted when a customer submits a payment."""
    payment_id: UUID
    order_id: UUID
    invoice_id: UUID


class PaymentVerified(DomainEvent):
    """Emitted when an Accountant verifies a payment."""
    payment_id: UUID
    order_id: UUID
    accountant_id: UUID


class OrderShipped(DomainEvent):
    """Emitted when Order Staff ships an order."""
    order_id: UUID
    staff_id: UUID


class OrderCompleted(DomainEvent):
    """Emitted when Order Staff closes a completed order."""
    order_id: UUID
    staff_id: UUID
