"""
Tests for the Order Management System domain layer.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from oms.domain.enums import OrderStatus, PaymentStatus, InvoiceStatus, PaymentMethod
from oms.domain.errors import InvalidStateTransitionError, BusinessRuleViolationError
from oms.domain.models import (
    Customer, Product, Order, OrderLineItem, Payment, Invoice,
)


class TestOrderStatusTransitions:
    """Verify that state transitions are enforced at the domain layer."""

    def test_valid_created_to_accepted(self):
        order = Order(id="1", customer_id="c1", line_items=[])
        order.transition_to(OrderStatus.ACCEPTED)
        assert order.status == OrderStatus.ACCEPTED

    def test_valid_created_to_cancelled(self):
        order = Order(id="1", customer_id="c1", line_items=[])
        order.transition_to(OrderStatus.CANCELLED)
        assert order.status == OrderStatus.CANCELLED

    def test_invalid_created_to_shipped(self):
        order = Order(id="1", customer_id="c1", line_items=[])
        with pytest.raises(InvalidStateTransitionError):
            order.transition_to(OrderStatus.SHIPPED)

    def test_invalid_created_to_closed(self):
        order = Order(id="1", customer_id="c1", line_items=[])
        with pytest.raises(InvalidStateTransitionError):
            order.transition_to(OrderStatus.CLOSED)

    def test_full_lifecycle(self):
        order = Order(id="1", customer_id="c1", line_items=[])
        order.transition_to(OrderStatus.ACCEPTED)
        order.transition_to(OrderStatus.INVOICED)
        order.transition_to(OrderStatus.PAID)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.CLOSED)
        assert order.status == OrderStatus.CLOSED

    def test_cancel_from_accepted(self):
        order = Order(id="1", customer_id="c1", line_items=[])
        order.transition_to(OrderStatus.ACCEPTED)
        order.transition_to(OrderStatus.CANCELLED)
        assert order.status == OrderStatus.CANCELLED

    def test_cannot_transition_from_cancelled(self):
        order = Order(id="1", customer_id="c1", line_items=[])
        order.transition_to(OrderStatus.CANCELLED)
        with pytest.raises(InvalidStateTransitionError):
            order.transition_to(OrderStatus.ACCEPTED)

    def test_cannot_transition_from_closed(self):
        order = Order(id="1", customer_id="c1", line_items=[])
        order.transition_to(OrderStatus.ACCEPTED)
        order.transition_to(OrderStatus.INVOICED)
        order.transition_to(OrderStatus.PAID)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.CLOSED)
        with pytest.raises(InvalidStateTransitionError):
            order.transition_to(OrderStatus.CANCELLED)


class TestOrderLineItems:
    """Verify order line item behavior."""

    def test_add_line_item(self):
        product = Product(
            id="p1", description="Test Product",
            base_price=Decimal("29.99"), currency="USD",
        )
        order = Order(id="1", customer_id="c1", line_items=[])
        order.add_line_item(product, 2)
        assert len(order.line_items) == 1
        assert order.line_items[0].product_id == "p1"
        assert order.line_items[0].quantity == 2
        assert order.line_items[0].unit_price == Decimal("29.99")

    def test_total_recalculation(self):
        product1 = Product(id="p1", description="Item 1", base_price=Decimal("10.00"), currency="USD")
        product2 = Product(id="p2", description="Item 2", base_price=Decimal("20.00"), currency="USD")
        order = Order(id="1", customer_id="c1", line_items=[])
        order.add_line_item(product1, 3)  # 30.00
        order.add_line_item(product2, 2)  # 40.00
        assert order.total_amount == Decimal("70.00")

    def test_cannot_add_line_item_after_acceptance(self):
        product = Product(id="p1", description="Test", base_price=Decimal("10.00"), currency="USD")
        order = Order(id="1", customer_id="c1", line_items=[])
        order.transition_to(OrderStatus.ACCEPTED)
        with pytest.raises(BusinessRuleViolationError):
            order.add_line_item(product, 1)


class TestOrderLineItemTotal:
    """Verify line item total calculation."""

    def test_line_item_total(self):
        item = OrderLineItem(
            product_id="p1", product_description="Test",
            quantity=5, unit_price=Decimal("19.99"),
        )
        assert item.total_price == Decimal("99.95")
