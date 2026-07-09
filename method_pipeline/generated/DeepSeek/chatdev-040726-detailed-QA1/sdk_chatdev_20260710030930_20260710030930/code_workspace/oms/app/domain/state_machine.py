"""Order state machine enforcing valid transitions with guard conditions."""

from dataclasses import dataclass
from typing import Callable, Optional

from app.domain.enums import OrderStatus


@dataclass(frozen=True)
class Transition:
    """A single allowed state transition."""
    from_state: OrderStatus
    event: str
    to_state: OrderStatus
    guard: Optional[Callable[[], bool]] = None


# State-transition table for Order status.
# from_state, event, to_state, guard condition (None = always allowed)
ORDER_TRANSITIONS: list[Transition] = [
    # Forward flow
    Transition(OrderStatus.CREATED, "accept", OrderStatus.ACCEPTED),
    Transition(OrderStatus.ACCEPTED, "invoice", OrderStatus.INVOICED),
    Transition(OrderStatus.INVOICED, "pay", OrderStatus.PAID),
    Transition(OrderStatus.PAID, "ship", OrderStatus.SHIPPED),
    Transition(OrderStatus.SHIPPED, "close", OrderStatus.CLOSED),

    # Cancellation (reachable from any pre-SHIPPED state)
    Transition(OrderStatus.CREATED, "cancel", OrderStatus.CANCELLED),
    Transition(OrderStatus.ACCEPTED, "cancel", OrderStatus.CANCELLED),
    Transition(OrderStatus.INVOICED, "cancel", OrderStatus.CANCELLED),
    Transition(OrderStatus.PAID, "cancel", OrderStatus.CANCELLED),
]


class IllegalTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current: OrderStatus, event: str) -> None:
        self.current = current
        self.event = event
        super().__init__(f"Illegal transition: {current.value} --[{event}]--> ?")


def validate_transition(current: OrderStatus, event: str) -> OrderStatus:
    """Validate and return the target state for a given event.

    Args:
        current: The current order status.
        event: The event name to apply.

    Returns:
        The resulting OrderStatus if the transition is valid.

    Raises:
        IllegalTransitionError: If no valid transition exists for the given
            current state and event.
    """
    for t in ORDER_TRANSITIONS:
        if t.from_state == current and t.event == event:
            if t.guard is None or t.guard():
                return t.to_state
    raise IllegalTransitionError(current, event)
