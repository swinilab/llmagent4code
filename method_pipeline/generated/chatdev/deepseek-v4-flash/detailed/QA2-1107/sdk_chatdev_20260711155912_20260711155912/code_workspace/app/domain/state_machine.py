"""
Order state-transition machine enforced in the domain layer.

State-transition table:
┌──────────────┬──────────────────┬──────────────┬──────────────────────────────────┬──────────────┐
│ From         │ Event            │ To           │ Guard                            │ Persistence  │
├──────────────┼──────────────────┼──────────────┼──────────────────────────────────┼──────────────┤
│ CREATED      │ review_accept    │ ACCEPTED     │ Order Staff role                │ Synchronous  │
│ ACCEPTED     │ create_invoice   │ INVOICED     │ Accountant role; invoice exists  │ Synchronous  │
│ INVOICED     │ pay              │ PAID         │ Payment completed; amount match  │ Synchronous  │
│ PAID         │ ship             │ SHIPPED      │ Order Staff role                 │ Synchronous  │
│ SHIPPED      │ close            │ CLOSED       │ Order Staff role                 │ Synchronous  │
│ *            │ cancel           │ CANCELLED    │ Any role; terminal state         │ Synchronous  │
└──────────────┴──────────────────┴──────────────┴──────────────────────────────────┴──────────────┘

All critical transitions are persisted synchronously (NFR 2.3). Non-essential
side-effects (recommendation logging, analytics) are handled asynchronously
via the outbox pattern and can be degraded (NFR 2.1).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from app.domain.enums import OrderStatus


class TransitionEvent(str, Enum):
    REVIEW_ACCEPT = "review_accept"
    CREATE_INVOICE = "create_invoice"
    PAY = "pay"
    SHIP = "ship"
    CLOSE = "close"
    CANCEL = "cancel"


# Guard function type: (current_status, event) -> bool
GuardFn = Callable[[OrderStatus, TransitionEvent], bool]


@dataclass(frozen=True)
class Transition:
    from_status: OrderStatus
    event: TransitionEvent
    to_status: OrderStatus
    guard: GuardFn | None = None


def _default_guard(_from: OrderStatus, _event: TransitionEvent) -> bool:
    """Default guard that always allows the transition."""
    return True


TRANSITIONS: list[Transition] = [
    Transition(OrderStatus.CREATED, TransitionEvent.REVIEW_ACCEPT, OrderStatus.ACCEPTED),
    Transition(OrderStatus.ACCEPTED, TransitionEvent.CREATE_INVOICE, OrderStatus.INVOICED),
    Transition(OrderStatus.INVOICED, TransitionEvent.PAY, OrderStatus.PAID),
    Transition(OrderStatus.PAID, TransitionEvent.SHIP, OrderStatus.SHIPPED),
    Transition(OrderStatus.SHIPPED, TransitionEvent.CLOSE, OrderStatus.CLOSED),
    # Cancel is allowed from any non-terminal state
    Transition(OrderStatus.CREATED, TransitionEvent.CANCEL, OrderStatus.CANCELLED),
    Transition(OrderStatus.ACCEPTED, TransitionEvent.CANCEL, OrderStatus.CANCELLED),
    Transition(OrderStatus.INVOICED, TransitionEvent.CANCEL, OrderStatus.CANCELLED),
    Transition(OrderStatus.PAID, TransitionEvent.CANCEL, OrderStatus.CANCELLED),
    Transition(OrderStatus.SHIPPED, TransitionEvent.CANCEL, OrderStatus.CANCELLED),
]


# Build lookup: (from_status, event) -> Transition
_TRANSITION_MAP: dict[tuple[OrderStatus, TransitionEvent], Transition] = {
    (t.from_status, t.event): t for t in TRANSITIONS
}


# Map transition events to their timestamp field names on the Order model.
# This mapping is used by services to record when each transition occurred.
TRANSITION_TIMESTAMP_FIELDS: dict[TransitionEvent, str] = {
    TransitionEvent.REVIEW_ACCEPT: "accepted_at_ts",
    TransitionEvent.CREATE_INVOICE: "invoiced_at_ts",
    TransitionEvent.PAY: "paid_at_ts",
    TransitionEvent.SHIP: "shipped_at_ts",
    TransitionEvent.CLOSE: "closed_at_ts",
    TransitionEvent.CANCEL: "cancelled_at_ts",
}


class IllegalTransitionError(ValueError):
    """Raised when an order state transition is not allowed."""

    def __init__(self, from_status: OrderStatus, event: TransitionEvent) -> None:
        self.from_status = from_status
        self.event = event
        super().__init__(f"Cannot transition from {from_status.value} via event {event.value}")


def apply_transition(
    current_status: OrderStatus, event: TransitionEvent
) -> OrderStatus:
    """
    Compute the next status given the current status and event.

    Raises IllegalTransitionError if the transition is not defined.
    """
    key = (current_status, event)
    transition = _TRANSITION_MAP.get(key)
    if transition is None:
        raise IllegalTransitionError(current_status, event)
    if transition.guard and not transition.guard(current_status, event):
        raise IllegalTransitionError(current_status, event)
    return transition.to_status
