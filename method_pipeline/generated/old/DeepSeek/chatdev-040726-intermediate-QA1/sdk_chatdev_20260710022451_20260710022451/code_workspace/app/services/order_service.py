"""
Order service — handles the complete order lifecycle with state-machine
enforcement at the domain layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.domain.enums import OrderStatus
from app.domain.exceptions import (
    DomainError,
    EntityNotFound,
    InsufficientStock,
    InvalidOrderStateTransition,
    OptimisticLockError,
)
from app.domain.models import Order, OrderLineItem
from app.domain.schemas import OrderCreate, OrderStatusUpdate
from app.infrastructure.cache import invalidate_product_cache
from app.infrastructure.queue import publish_message
from app.repositories.customer import CustomerRepository
from app.repositories.order import OrderRepository
from app.repositories.product import ProductRepository


class OrderService:
    """Encapsulates all order-related business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_repo = OrderRepository(session)
        self._product_repo = ProductRepository(session)
        self._customer_repo = CustomerRepository(session)

    # ── Checkout (hot path for NFR 1.1) ────────────────────────────────

    async def create_order(self, data: OrderCreate) -> Order:
        """Place a new order (CREATED).  This is on the critical path for
        the checkout journey — must complete within p95 ≤ 300 ms."""
        # Validate customer exists
        customer = await self._customer_repo.get(data.customer_id)
        if customer is None:
            raise EntityNotFound("Customer", data.customer_id)

        # Build line items, check stock, compute total
        line_items: list[OrderLineItem] = []
        total = Decimal("0.00")
        currency: str | None = None

        for item_data in data.line_items:
            product = await self._product_repo.get(item_data.product_id)
            if product is None:
                raise EntityNotFound("Product", item_data.product_id)
            if product.stock_available < item_data.quantity:
                raise InsufficientStock(
                    product.id, item_data.quantity, product.stock_available
                )

            unit_price = product.base_price
            total += unit_price * item_data.quantity

            # Validate that all line items share the same currency
            if currency is None:
                currency = product.currency
            elif product.currency != currency:
                raise DomainError(
                    f"Line item currency '{product.currency}' does not match "
                    f"order currency '{currency}'. All items must use the same currency."
                )

            line_items.append(
                OrderLineItem(
                    product_id=product.id,
                    quantity=item_data.quantity,
                    unit_price=unit_price,
                    currency=product.currency,
                )
            )

            # Decrement stock (optimistic — we'll commit in a transaction)
            product.stock_available -= item_data.quantity

        order = Order(
            customer_id=data.customer_id,
            status=OrderStatus.CREATED,
            total_amount=total,
            currency=currency or "USD",
            line_items=line_items,
        )
        created = await self._order_repo.add(order)

        # Invalidate product caches for changed products
        for item in data.line_items:
            await invalidate_product_cache(item.product_id)

        # Publish async notification
        await publish_message(
            "oms.notifications",
            {"type": "order.created", "order_id": created.id, "customer_id": data.customer_id},
        )

        return created

    # ── Read operations ─────────────────────────────────────────────────

    async def get_order(self, order_id: int) -> Order:
        """Retrieve an order by ID with line items loaded."""
        return await self._order_repo.get_with_items_or_fail(order_id)

    async def list_orders(
        self, customer_id: int | None, page: int = 1, page_size: int = 20
    ) -> tuple[list[Order], int]:
        """List orders, optionally filtered by customer_id."""
        if customer_id is not None:
            return await self._order_repo.list_by_customer(customer_id, page, page_size)
        # No customer filter — use generic list from BaseRepository
        offset = (page - 1) * page_size
        return await self._order_repo.list(
            offset=offset,
            limit=page_size,
            order_by=Order.id,
        )

    async def update_status(self, order_id: int, data: OrderStatusUpdate) -> Order:
        """Transition the order to a new status with optimistic locking."""
        order = await self._order_repo.get_with_items_or_fail(order_id)

        # Optimistic lock check
        if order.version != data.version:
            raise OptimisticLockError()

        if not order.status.can_transition_to(data.new_status):
            raise InvalidOrderStateTransition(order.status.value, data.new_status.value)

        # Capture old status BEFORE mutation (critical for event payload correctness)
        old_status = order.status.value

        order.status = data.new_status
        order.updated_at = datetime.now(timezone.utc)

        self._session.add(order)
        try:
            await self._session.flush()
        except StaleDataError:
            raise OptimisticLockError()

        # Publish event with correct old_status
        await publish_message(
            "oms.notifications",
            {
                "type": "order.status_changed",
                "order_id": order.id,
                "old_status": old_status,
                "new_status": data.new_status.value,
            },
        )

        return order
