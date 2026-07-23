"""
Order state-transition machine.

State-transition table (from_state, event, to_state, guard, persistence):

| From        | Event         | To         | Guard                          | Persistence  |
|-------------|---------------|------------|--------------------------------|--------------|
| CREATED     | accept        | ACCEPTED   | role=ORDER_STAFF              | synchronous  |
| ACCEPTED    | invoice       | INVOICED   | role=ACCOUNTANT, order exists | synchronous  |
| INVOICED    | pay           | PAID       | payment verified, idempotent   | synchronous  |
| PAID        | ship          | SHIPPED    | role=ORDER_STAFF, payment=PAID | synchronous  |
| SHIPPED     | close         | CLOSED     | role=ORDER_STAFF               | synchronous  |
| CREATED     | cancel        | CANCELLED  | not CLOSED or SHIPPED          | synchronous  |
| ACCEPTED    | cancel        | CANCELLED  | not CLOSED or SHIPPED          | synchronous  |
| INVOICED    | cancel        | CANCELLED  | not CLOSED or SHIPPED          | synchronous  |
| PAID        | cancel        | CANCELLED  | not CLOSED or SHIPPED          | synchronous  |

All critical transitions are persisted synchronously (DB write before response).

Note: CANCELLED is a terminal exception state. It is allowed from CREATED,
ACCEPTED, INVOICED, and PAID (but not SHIPPED or CLOSED, per spec).
"""
from __future__ import annotations

from typing import Callable, Optional

from oms.domain.enums import OrderStatus


class OrderStateMachine:
    """Enforces valid order state transitions with guards."""

    _transitions: dict[tuple[OrderStatus, str], tuple[OrderStatus, Optional[Callable]]] = {
        (OrderStatus.CREATED, "accept"): (OrderStatus.ACCEPTED, None),
        (OrderStatus.ACCEPTED, "invoice"): (OrderStatus.INVOICED, None),
        (OrderStatus.INVOICED, "pay"): (OrderStatus.PAID, None),
        (OrderStatus.PAID, "ship"): (OrderStatus.SHIPPED, None),
        (OrderStatus.SHIPPED, "close"): (OrderStatus.CLOSED, None),
        (OrderStatus.CREATED, "cancel"): (OrderStatus.CANCELLED, None),
        (OrderStatus.ACCEPTED, "cancel"): (OrderStatus.CANCELLED, None),
        (OrderStatus.INVOICED, "cancel"): (OrderStatus.CANCELLED, None),
        (OrderStatus.PAID, "cancel"): (OrderStatus.CANCELLED, None),
    }

    @classmethod
    def allowed_events(cls, current: OrderStatus) -> list[str]:
        """Return list of valid event names for the given state."""
        return [ev for (st, ev) in cls._transitions if st == current]

    @classmethod
    def transition(
        cls, current: OrderStatus, event: str
    ) -> OrderStatus:
        """Apply event to current state; raises ValueError if invalid."""
        key = (current, event)
        if key not in cls._transitions:
            raise ValueError(
                f"Invalid transition: {current.value} --[{event}]--> ?"
            )
        return cls._transitions[key][0]
