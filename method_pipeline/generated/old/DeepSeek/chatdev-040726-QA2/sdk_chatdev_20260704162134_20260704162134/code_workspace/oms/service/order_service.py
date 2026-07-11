"""
Order service: full order lifecycle management.
"""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from oms.domain.enums import OrderStatus, Currency
from oms.domain.events import (
    OrderPlaced,
    OrderAccepted,
    OrderCancelled,
    OrderShipped,
    OrderCompleted,
)
from oms.domain.models import Order, LineItem, Money, CreateOrderRequest
from oms.repository.in_memory import InMemoryOrderRepository, InMemoryCustomerRepository, InMemoryProductRepository
from oms.service.event_bus import event_bus


class OrderService:
    """Business logic for Order operations and lifecycle transitions."""

    def __init__(
        self,
        order_repo: InMemoryOrderRepository,
        customer_repo: InMemoryCustomerRepository,
        product_repo: InMemoryProductRepository,
    ) -> None:
        self._order_repo = order_repo
        self._customer_repo = customer_repo
        self._product_repo = product_repo

    def _compute_total(self, line_items: list[LineItem]) -> Money:
        """Compute the total amount from line items, rounded to 2 decimal places."""
        total = Decimal("0.00")
        currency = None
        for item in line_items:
            if currency is None:
                currency = item.unit_price.currency
            elif currency != item.unit_price.currency:
                raise ValueError("All line items must have the same currency")
            total += item.unit_price.amount * item.quantity
        # Round to 2 decimal places for financial integrity
        total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Money(amount=total, currency=currency or Currency.USD)

    def place_order(self, request: CreateOrderRequest) -> Order:
        """Step 1: Customer places an order."""
        customer = self._customer_repo.find_by_id(request.customer_id)
        if customer is None:
            raise ValueError(f"Customer {request.customer_id} not found")

        # Validate products exist and unit prices match catalog
        for item in request.line_items:
            product = self._product_repo.find_by_id(item.product_id)
            if product is None:
                raise ValueError(f"Product {item.product_id} not found")
            if item.unit_price.amount != product.base_price.amount:
                raise ValueError(
                    f"Unit price {item.unit_price.amount} for product {item.product_id} "
                    f"does not match catalog price {product.base_price.amount}"
                )
            if item.unit_price.currency != product.base_price.currency:
                raise ValueError(
                    f"Unit price currency {item.unit_price.currency} for product {item.product_id} "
                    f"does not match catalog currency {product.base_price.currency}"
                )

        total = self._compute_total(request.line_items)
        order = Order(
            customer_id=request.customer_id,
            line_items=request.line_items,
            total=total,
            status=OrderStatus.PENDING,
        )
        saved = self._order_repo.save(order)

        # Update customer order history
        customer.order_history.append(saved.id)
        self._customer_repo.save(customer)

        event_bus.publish(OrderPlaced(order_id=saved.id, customer_id=request.customer_id))
        return saved

    def accept_order(self, order_id: UUID, staff_id: UUID) -> Order:
        """Step 2: Order Staff reviews and accepts an order."""
        order = self._order_repo.find_by_id(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order {order_id} is in status {order.status.value}, expected pending")

        order.status = OrderStatus.ACCEPTED
        order.updated_at = datetime.now(timezone.utc)
        saved = self._order_repo.save(order)
        event_bus.publish(OrderAccepted(order_id=order_id, staff_id=staff_id))
        return saved

    def ship_order(self, order_id: UUID, staff_id: UUID) -> Order:
        """Step 6: Order Staff ships a paid order."""
        order = self._order_repo.find_by_id(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.PAID:
            raise ValueError(f"Order {order_id} is in status {order.status.value}, expected paid")

        order.status = OrderStatus.SHIPPED
        order.updated_at = datetime.now(timezone.utc)
        saved = self._order_repo.save(order)
        event_bus.publish(OrderShipped(order_id=order_id, staff_id=staff_id))
        return saved

    def close_order(self, order_id: UUID, staff_id: UUID) -> Order:
        """Step 7: Order Staff closes a completed (shipped) order."""
        order = self._order_repo.find_by_id(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.SHIPPED:
            raise ValueError(f"Order {order_id} is in status {order.status.value}, expected shipped")

        order.status = OrderStatus.COMPLETED
        order.updated_at = datetime.now(timezone.utc)
        saved = self._order_repo.save(order)
        event_bus.publish(OrderCompleted(order_id=order_id, staff_id=staff_id))
        return saved

    def cancel_order(self, order_id: UUID, reason: str = "Cancelled by customer") -> Order:
        """Cancel an order at any stage before completion."""
        order = self._order_repo.find_by_id(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            raise ValueError(
                f"Order {order_id} is in status {order.status.value}, cannot cancel"
            )

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)
        saved = self._order_repo.save(order)
        event_bus.publish(OrderCancelled(order_id=order_id, reason=reason))
        return saved

    def get_by_id(self, order_id: UUID) -> Order | None:
        """Retrieve an order by ID."""
        return self._order_repo.find_by_id(order_id)

    def list_by_customer(self, customer_id: UUID) -> list[Order]:
        """List orders for a given customer."""
        return self._order_repo.find_by_customer(customer_id)

    def list_all(self) -> list[Order]:
        """List all orders."""
        return self._order_repo.find_all()
