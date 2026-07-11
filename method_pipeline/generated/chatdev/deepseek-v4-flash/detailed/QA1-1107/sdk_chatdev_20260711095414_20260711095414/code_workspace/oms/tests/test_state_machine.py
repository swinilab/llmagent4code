"""
Unit tests for the OMS domain layer.
"""
from __future__ import annotations

import pytest
from oms.domain.enums import OrderStatus
from oms.domain.state_machine import OrderStateMachine


class TestOrderStateMachine:
    def test_legal_transitions(self) -> None:
        assert OrderStateMachine.can_transition(OrderStatus.CREATED, "accept")
        assert OrderStateMachine.can_transition(OrderStatus.CREATED, "cancel")
        assert OrderStateMachine.can_transition(OrderStatus.ACCEPTED, "invoice")
        assert OrderStateMachine.can_transition(OrderStatus.ACCEPTED, "cancel")
        assert OrderStateMachine.can_transition(OrderStatus.INVOICED, "pay")
        assert OrderStateMachine.can_transition(OrderStatus.INVOICED, "cancel")
        assert OrderStateMachine.can_transition(OrderStatus.PAID, "ship")
        assert OrderStateMachine.can_transition(OrderStatus.PAID, "cancel")
        assert OrderStateMachine.can_transition(OrderStatus.PAID, "verify")
        assert OrderStateMachine.can_transition(OrderStatus.SHIPPED, "close")

    def test_illegal_transitions(self) -> None:
        assert not OrderStateMachine.can_transition(OrderStatus.CREATED, "ship")
        assert not OrderStateMachine.can_transition(OrderStatus.CREATED, "close")
        assert not OrderStateMachine.can_transition(OrderStatus.ACCEPTED, "pay")
        assert not OrderStateMachine.can_transition(OrderStatus.PAID, "invoice")
        assert not OrderStateMachine.can_transition(OrderStatus.SHIPPED, "pay")
        assert not OrderStateMachine.can_transition(OrderStatus.CLOSED, "cancel")
        assert not OrderStateMachine.can_transition(OrderStatus.CREATED, "verify")

    def test_next_status(self) -> None:
        assert OrderStateMachine.next_status(OrderStatus.CREATED, "accept") == OrderStatus.ACCEPTED
        assert OrderStateMachine.next_status(OrderStatus.CREATED, "cancel") == OrderStatus.CANCELLED
        assert OrderStateMachine.next_status(OrderStatus.ACCEPTED, "invoice") == OrderStatus.INVOICED
        assert OrderStateMachine.next_status(OrderStatus.INVOICED, "pay") == OrderStatus.PAID
        assert OrderStateMachine.next_status(OrderStatus.PAID, "ship") == OrderStatus.SHIPPED
        assert OrderStateMachine.next_status(OrderStatus.PAID, "verify") == OrderStatus.PAID
        assert OrderStateMachine.next_status(OrderStatus.SHIPPED, "close") == OrderStatus.CLOSED

    def test_illegal_raises(self) -> None:
        with pytest.raises(ValueError, match="Illegal transition"):
            OrderStateMachine.next_status(OrderStatus.CREATED, "ship")

    def test_allowed_events(self) -> None:
        events = OrderStateMachine.allowed_events(OrderStatus.CREATED)
        assert "accept" in events
        assert "cancel" in events
        assert "ship" not in events
        events_paid = OrderStateMachine.allowed_events(OrderStatus.PAID)
        assert "verify" in events_paid


class TestTokenBucket:
    @pytest.mark.asyncio
    async def test_consume(self) -> None:
        from oms.infrastructure.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=10, refill_rate=10)
        assert await bucket.consume(5) is True
        assert await bucket.consume(5) is True
        assert await bucket.consume(1) is False  # empty

    @pytest.mark.asyncio
    async def test_refill(self) -> None:
        from oms.infrastructure.rate_limiter import TokenBucket
        import asyncio
        bucket = TokenBucket(capacity=10, refill_rate=100)  # fast refill
        await bucket.consume(10)
        assert await bucket.consume(1) is False
        await asyncio.sleep(0.02)  # allow refill
        assert await bucket.consume(1) is True
