"""
Unit tests for domain-layer state machine and exceptions.
"""

from __future__ import annotations

import pytest

from app.domain.enums import OrderStatus
from app.domain.exceptions import (
    InvalidOrderStateTransition,
    EntityNotFound,
    InsufficientStock,
    OptimisticLockError,
)


class TestOrderStatusTransitions:
    def test_valid_transitions(self) -> None:
        assert OrderStatus.CREATED.can_transition_to(OrderStatus.ACCEPTED)
        assert OrderStatus.CREATED.can_transition_to(OrderStatus.CANCELLED)
        assert OrderStatus.ACCEPTED.can_transition_to(OrderStatus.INVOICED)
        assert OrderStatus.ACCEPTED.can_transition_to(OrderStatus.CANCELLED)
        assert OrderStatus.INVOICED.can_transition_to(OrderStatus.PAID)
        assert OrderStatus.INVOICED.can_transition_to(OrderStatus.CANCELLED)
        assert OrderStatus.PAID.can_transition_to(OrderStatus.SHIPPED)
        assert OrderStatus.PAID.can_transition_to(OrderStatus.CANCELLED)
        assert OrderStatus.SHIPPED.can_transition_to(OrderStatus.CLOSED)

    def test_invalid_transitions(self) -> None:
        assert not OrderStatus.CREATED.can_transition_to(OrderStatus.PAID)
        assert not OrderStatus.CREATED.can_transition_to(OrderStatus.SHIPPED)
        assert not OrderStatus.CREATED.can_transition_to(OrderStatus.CLOSED)
        assert not OrderStatus.ACCEPTED.can_transition_to(OrderStatus.PAID)
        assert not OrderStatus.INVOICED.can_transition_to(OrderStatus.ACCEPTED)
        assert not OrderStatus.PAID.can_transition_to(OrderStatus.INVOICED)
        assert not OrderStatus.SHIPPED.can_transition_to(OrderStatus.PAID)
        assert not OrderStatus.CLOSED.can_transition_to(OrderStatus.CREATED)
        assert not OrderStatus.CANCELLED.can_transition_to(OrderStatus.CREATED)

    def test_terminal_states(self) -> None:
        assert OrderStatus.CLOSED.allowed_transitions(OrderStatus.CLOSED) == set()
        assert OrderStatus.CANCELLED.allowed_transitions(OrderStatus.CANCELLED) == set()

    def test_exception_creation(self) -> None:
        exc = InvalidOrderStateTransition("CREATED", "PAID")
        assert "CREATED" in str(exc)
        assert "PAID" in str(exc)

        exc2 = EntityNotFound("Order", 42)
        assert "42" in str(exc2)

        exc3 = InsufficientStock(1, 10, 5)
        assert "10" in str(exc3)

        exc4 = OptimisticLockError()
        assert "retry" in str(exc4)
