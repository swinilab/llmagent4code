"""
Order state machine — enforces legal transitions with guard conditions.
"""
from __future__ import annotations

from oms.domain.enums import OrderStatus


# State-transition table: (from_status, event, to_status, guard_description)
TRANSITION_TABLE: list[tuple[OrderStatus, str, OrderStatus, str]] = [
    (OrderStatus.CREATED,   "accept",  OrderStatus.ACCEPTED,  "Order staff reviews and accepts"),
    (OrderStatus.CREATED,   "cancel",  OrderStatus.CANCELLED, "Customer or staff cancels before acceptance"),
    (OrderStatus.ACCEPTED, "invoice", OrderStatus.INVOICED,  "Accountant creates invoice"),
    (OrderStatus.ACCEPTED, "cancel",  OrderStatus.CANCELLED, "Cancelled before invoicing"),
    (OrderStatus.INVOICED, "pay",     OrderStatus.PAID,      "Customer pays invoice"),
    (OrderStatus.INVOICED, "cancel",  OrderStatus.CANCELLED, "Cancelled before payment"),
    (OrderStatus.PAID,     "ship",    OrderStatus.SHIPPED,   "Order staff ships paid order"),
    (OrderStatus.PAID,     "cancel",  OrderStatus.CANCELLED,  "Cancelled before shipping (refund needed)"),
    (OrderStatus.PAID,     "verify",  OrderStatus.PAID,      "Accountant verifies payment (no-op transition)"),
    (OrderStatus.SHIPPED,  "close",   OrderStatus.CLOSED,    "Order staff closes completed order"),
]

# Build lookup: (from, event) -> (to, guard)
_TRANSITION_MAP: dict[tuple[OrderStatus, str], tuple[OrderStatus, str]] = {}
for from_s, event, to_s, guard in TRANSITION_TABLE:
    _TRANSITION_MAP[(from_s, event)] = (to_s, guard)


class OrderStateMachine:
    """Stateless validator; raises ValueError on illegal transitions."""

    @staticmethod
    def allowed_events(status: OrderStatus) -> list[str]:
        """Return list of events that can be applied from *status*."""
        return [ev for (st, ev) in _TRANSITION_MAP if st == status]

    @staticmethod
    def next_status(current: OrderStatus, event: str) -> OrderStatus:
        """Return the target status if the transition is legal; raise ValueError otherwise."""
        key = (current, event)
        if key not in _TRANSITION_MAP:
            allowed = OrderStateMachine.allowed_events(current)
            raise ValueError(
                f"Illegal transition: {current.value} --[{event}]--> ?. "
                f"Allowed events from {current.value}: {allowed}"
            )
        return _TRANSITION_MAP[key][0]

    @staticmethod
    def can_transition(current: OrderStatus, event: str) -> bool:
        """Check legality without raising."""
        return (current, event) in _TRANSITION_MAP
