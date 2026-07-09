"""Tests for the Order state machine."""

import pytest

from app.domain.enums import OrderStatus
from app.domain.state_machine import IllegalTransitionError, validate_transition


class TestOrderStateMachine:
    """Verify all valid and invalid state transitions."""

    def test_forward_flow(self):
        """Test the complete forward flow: CREATED → CLOSED."""
        state = OrderStatus.CREATED
        for event, expected in [
            ("accept", OrderStatus.ACCEPTED),
            ("invoice", OrderStatus.INVOICED),
            ("pay", OrderStatus.PAID),
            ("ship", OrderStatus.SHIPPED),
            ("close", OrderStatus.CLOSED),
        ]:
            state = validate_transition(state, event)
            assert state == expected

    def test_cancel_from_created(self):
        """Cancellation from CREATED is valid."""
        result = validate_transition(OrderStatus.CREATED, "cancel")
        assert result == OrderStatus.CANCELLED

    def test_cancel_from_accepted(self):
        """Cancellation from ACCEPTED is valid."""
        result = validate_transition(OrderStatus.ACCEPTED, "cancel")
        assert result == OrderStatus.CANCELLED

    def test_cancel_from_invoiced(self):
        """Cancellation from INVOICED is valid."""
        result = validate_transition(OrderStatus.INVOICED, "cancel")
        assert result == OrderStatus.CANCELLED

    def test_cancel_from_paid(self):
        """Cancellation from PAID is valid."""
        result = validate_transition(OrderStatus.PAID, "cancel")
        assert result == OrderStatus.CANCELLED

    def test_cancel_from_shipped_invalid(self):
        """Cancellation from SHIPPED is invalid."""
        with pytest.raises(IllegalTransitionError):
            validate_transition(OrderStatus.SHIPPED, "cancel")

    def test_cancel_from_closed_invalid(self):
        """Cancellation from CLOSED is invalid."""
        with pytest.raises(IllegalTransitionError):
            validate_transition(OrderStatus.CLOSED, "cancel")

    def test_skip_state_invalid(self):
        """Cannot skip from CREATED directly to PAID."""
        with pytest.raises(IllegalTransitionError):
            validate_transition(OrderStatus.CREATED, "pay")

    def test_invalid_event(self):
        """Unknown event raises error."""
        with pytest.raises(IllegalTransitionError):
            validate_transition(OrderStatus.CREATED, "nonexistent")

    def test_cancelled_is_terminal(self):
        """CANCELLED has no outgoing transitions."""
        for event in ["accept", "invoice", "pay", "ship", "close", "cancel"]:
            with pytest.raises(IllegalTransitionError):
                validate_transition(OrderStatus.CANCELLED, event)
