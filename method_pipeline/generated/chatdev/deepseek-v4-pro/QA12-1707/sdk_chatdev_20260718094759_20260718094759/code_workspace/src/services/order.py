"""Order business logic with status machine."""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.order import Order, OrderStatus
from src.repositories.order import OrderRepository
from src.schemas.order import OrderCreate
from src.utils.exceptions import ConflictError, NotFoundError, ValidationError

_VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.INVOICED, OrderStatus.CANCELLED},
    OrderStatus.INVOICED: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.CLOSED},
    OrderStatus.CLOSED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderService:
    """Orchestrates order lifecycle with status-machine enforcement."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = OrderRepository(session)

    async def create(self, payload: OrderCreate) -> Order:
        """Place a new order. Computes subtotal/total from line items."""
        line_items_json = json.dumps(
            [item.model_dump(mode="json") for item in payload.line_items]
        )
        subtotal = sum(
            item.unit_price * item.quantity for item in payload.line_items
        )
        total = subtotal + payload.tax
        order = Order(
            customer_id=payload.customer_id,
            line_items=line_items_json,
            subtotal=subtotal,
            tax=payload.tax,
            total=total,
            status=OrderStatus.PENDING,
        )
        return await self.repo.add(order)

    async def get(self, order_id: str) -> Order:
        """Retrieve an order by ID."""
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        return order

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Order]:
        """List all orders with pagination."""
        return await self.repo.list_all(limit=limit, offset=offset)

    async def list_by_customer(self, customer_id: str) -> list[Order]:
        """List orders for a customer."""
        return await self.repo.list_by_customer(customer_id)

    async def list_by_status(self, status: str) -> list[Order]:
        """List orders filtered by status."""
        try:
            st = OrderStatus(status)
        except ValueError:
            raise ValidationError(f"Invalid status: {status}") from None
        return await self.repo.list_by_status(st)

    async def transition_status(self, order_id: str, new_status: str) -> Order:
        """Transition an order to a new status, enforcing the state machine."""
        order = await self.get(order_id)
        try:
            target = OrderStatus(new_status)
        except ValueError:
            raise ValidationError(f"Invalid status: {new_status}") from None

        allowed = _VALID_TRANSITIONS.get(order.status, set())
        if target not in allowed:
            raise ConflictError(
                f"Cannot transition from {order.status.value} to {target.value}"
            )
        order.status = target
        await self.repo.session.flush()
        return order

    async def set_invoice_id(self, order_id: str, invoice_id: str) -> Order:
        """Attach an invoice reference to the order."""
        order = await self.get(order_id)
        order.invoice_id = invoice_id
        await self.repo.session.flush()
        return order
