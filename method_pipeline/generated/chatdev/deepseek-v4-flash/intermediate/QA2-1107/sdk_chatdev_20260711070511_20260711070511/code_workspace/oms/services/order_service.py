"""
Order service – business logic for the order lifecycle.

Every critical state transition is:
1. Validated (state machine + business preconditions)
2. Persisted in the DB (same transaction)
3. Recorded in the outbox (same transaction)
4. Only then is the HTTP response sent (NFR 2.3 – State Preservation)
"""
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from oms.models.entities import (
    CustomerModel,
    OrderLineItemModel,
    OrderModel,
    ProductModel,
)
from oms.models.enums import OrderStatus
from oms.repositories.order_repo import OrderRepository
from oms.schemas.order import LineItemCreate, OrderCreate

logger = logging.getLogger(__name__)


class OrderService:
    """Encapsulates order creation, status transitions, and outbox logging."""

    # Valid state transitions
    _ALLOWED_TRANSITIONS = {
        OrderStatus.CREATED: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
        OrderStatus.ACCEPTED: [OrderStatus.INVOICED, OrderStatus.CANCELLED],
        OrderStatus.INVOICED: [OrderStatus.PAID, OrderStatus.CANCELLED],
        OrderStatus.PAID: [OrderStatus.SHIPPED],
        OrderStatus.SHIPPED: [OrderStatus.CLOSED],
        OrderStatus.CLOSED: [],
        OrderStatus.CANCELLED: [],
    }

    # Business preconditions per target status
    _BUSINESS_PRECONDITIONS = {
        OrderStatus.ACCEPTED: {
            "check": lambda order, repo: len(repo.get_line_items(order.id)) > 0,
            "message": "Order must have at least one line item before acceptance",
        },
        OrderStatus.SHIPPED: {
            "check": lambda order, repo: order.status == OrderStatus.PAID,
            "message": "Order must be PAID before shipping",
        },
        OrderStatus.CLOSED: {
            "check": lambda order, repo: order.status == OrderStatus.SHIPPED,
            "message": "Order must be SHIPPED before closing",
        },
    }

    def __init__(self, db: Session):
        self.db = db
        self.repo = OrderRepository(db)

    def create_order(self, data: OrderCreate) -> OrderModel:
        """Create a new order with line items. Critical operation."""
        # Validate customer exists (NFR 2.1 – prevent 500 on bad input)
        customer = self.db.query(CustomerModel).filter(
            CustomerModel.id == data.customer_id
        ).first()
        if not customer:
            raise ValueError(f"Customer {data.customer_id} not found")

        # Validate all line items have the same currency
        currencies = {item.currency for item in data.line_items}
        if len(currencies) > 1:
            raise ValueError("All line items must have the same currency")
        order_currency = currencies.pop() if currencies else "USD"

        # Validate all products exist BEFORE creating the order
        # (prevents zombie orders with no line items – Fix 2)
        for item_data in data.line_items:
            product = self.db.query(ProductModel).filter(
                ProductModel.id == item_data.product_id
            ).first()
            if not product:
                raise ValueError(f"Product {item_data.product_id} not found")

        # Build order
        order = OrderModel(
            customer_id=data.customer_id,
            status=OrderStatus.CREATED,
            total_amount=0.0,
            currency=order_currency,
        )
        self.repo.create(order)

        # Add line items
        total = 0.0
        for item_data in data.line_items:
            # Product already validated above – no need to re-query
            line = OrderLineItemModel(
                order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                currency=item_data.currency,
            )
            self.repo.add_line_item(order.id, line)
            total += item_data.quantity * item_data.unit_price

        # Update total
        order.total_amount = total
        self.db.flush()

        # Write outbox message (same transaction – NFR 2.3)
        self.repo.write_outbox(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type="order.created",
            payload={
                "order_id": order.id,
                "customer_id": order.customer_id,
                "total_amount": order.total_amount,
                "status": order.status.value,
            },
        )
        self.db.commit()
        logger.info("Order %s created for customer %s", order.id, data.customer_id)
        return order

    def get_order(self, order_id: str) -> Optional[OrderModel]:
        return self.repo.get(order_id)

    def list_orders(self, skip: int = 0, limit: int = 100) -> List[OrderModel]:
        return self.repo.list_all(skip, limit)

    def list_by_customer(self, customer_id: str) -> List[OrderModel]:
        return self.repo.get_by_customer(customer_id)

    def list_by_status(self, status: OrderStatus) -> List[OrderModel]:
        return self.repo.get_by_status(status)

    def transition_status(
        self, order_id: str, new_status: OrderStatus
    ) -> OrderModel:
        """
        Transition an order to *new_status* if the transition is allowed
        AND business preconditions are met.
        Critical operation – persisted before returning.
        """
        order = self.repo.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # 1. Validate state machine transition
        allowed = self._ALLOWED_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from {order.status.value} to {new_status.value}"
            )

        # 2. Validate business preconditions for the target status
        precondition = self._BUSINESS_PRECONDITIONS.get(new_status)
        if precondition is not None:
            if not precondition["check"](order, self.repo):
                raise ValueError(precondition["message"])

        # 3. Use optimistic locking
        updated = self.repo.update_with_optimistic_lock(
            order_id,
            {"status": new_status},
            order.version,
        )
        if updated is None:
            raise ConcurrentModificationError(order_id)

        # 4. Write outbox message
        self.repo.write_outbox(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type=f"order.{new_status.value.lower()}",
            payload={
                "order_id": order.id,
                "previous_status": order.status.value,
                "new_status": new_status.value,
            },
        )
        self.db.commit()
        logger.info(
            "Order %s transitioned %s -> %s",
            order_id, order.status.value, new_status.value,
        )
        return updated

    def set_invoice_ref(self, order_id: str, invoice_id: str) -> OrderModel:
        """Associate an invoice with an order. Critical operation."""
        order = self.repo.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        updated = self.repo.update_with_optimistic_lock(
            order_id,
            {"invoice_ref": invoice_id},
            order.version,
        )
        if updated is None:
            raise ConcurrentModificationError(order_id)

        # Write outbox message for the invoice reference change
        self.repo.write_outbox(
            aggregate_type="order",
            aggregate_id=order_id,
            event_type="order.invoice_ref_set",
            payload={
                "order_id": order_id,
                "invoice_id": invoice_id,
                "previous_invoice_ref": order.invoice_ref,
            },
        )
        self.db.commit()
        logger.info(
            "Invoice ref %s set on order %s", invoice_id, order_id,
        )
        return updated


class ConcurrentModificationError(Exception):
    """Raised when optimistic locking detects a concurrent update."""
    def __init__(self, entity_id: str):
        super().__init__(f"Concurrent modification detected for {entity_id}")
