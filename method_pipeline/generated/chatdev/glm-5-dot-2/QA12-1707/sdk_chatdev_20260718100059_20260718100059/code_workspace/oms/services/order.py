"""
Order service — the core business logic for order lifecycle management.

Implements the full workflow:
  1. Customer places order (PENDING)
  2. Order Staff reviews & accepts (ACCEPTED)
  3. Accountant creates invoice (INVOICED)
  4. Customer pays invoice → payment verified (PAID)
  5. Order Staff ships (SHIPPED)
  6. Order Staff closes (CLOSED)

Also handles order creation with line items, amount calculation,
and status transitions with validation.
"""
import logging
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from oms.config import settings
from oms.enums import OrderStatus, ORDER_TRANSITIONS
from oms.schemas.order import OrderCreate, OrderUpdate, OrderStatusUpdate, OrderLineItemCreate
from oms.models.order import Order, OrderLineItem
from oms.models.product import Product
from oms.repositories.order import OrderRepository
from oms.repositories.product import ProductRepository

logger = logging.getLogger(__name__)


class OrderTransitionError(Exception):
    """Raised when an invalid order status transition is attempted."""
    pass


class OrderService:
    """Business logic for Order entities and lifecycle transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OrderRepository(session)
        self.product_repo = ProductRepository(session)

    async def _resolve_line_items(
        self, items: Sequence[OrderLineItemCreate],
    ) -> tuple[list[OrderLineItem], float, str]:
        """
        Validate every referenced product exists and that all products share
        a single currency, then build line items with price snapshots.

        Returns (line_items, subtotal, currency).
        Raises ValueError if a product is missing or currencies differ.
        """
        line_items: list[OrderLineItem] = []
        subtotal = 0.0
        currency: str | None = None

        for item_data in items:
            product = await self.product_repo.get_by_id(item_data.product_id)
            if product is None:
                raise ValueError(f"Product {item_data.product_id} not found")
            if currency is None:
                currency = product.currency
            elif product.currency != currency:
                raise ValueError(
                    f"Cannot mix currencies in one order: "
                    f"product {product.id} is {product.currency}, "
                    f"order currency is {currency}"
                )
            line_total = float(product.base_price) * item_data.quantity
            subtotal += line_total
            line_items.append(OrderLineItem(
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=float(product.base_price),
                currency=currency,
            ))

        # currency is guaranteed non-None because OrderCreate enforces min_length=1
        assert currency is not None
        return line_items, subtotal, currency

    async def create_order(self, data: OrderCreate) -> Order:
        """
        Create a new order with line items.

        Validates that all referenced products exist and share a single
        currency, snapshots their current prices, and calculates
        subtotal/tax/total.
        """
        line_items, subtotal, currency = await self._resolve_line_items(data.items)

        tax = round(subtotal * settings.default_tax_rate, 2)
        total = round(subtotal + tax, 2)

        order = await self.repo.create(
            customer_id=data.customer_id,
            status=OrderStatus.PENDING,
            subtotal=round(subtotal, 2),
            tax=tax,
            total=total,
            currency=currency,
        )

        # Attach line items
        for li in line_items:
            li.order_id = order.id
            await self.repo.add_line_item(li)

        await self.session.commit()
        await self.session.refresh(order)
        logger.info("Created order %s with %d line items (total=%s %s)",
                    order.id, len(line_items), total, currency)
        return order

    async def get_order(self, order_id: str) -> Order | None:
        """Fetch an order with all relationships."""
        return await self.repo.get_full(order_id)

    async def list_orders(
        self, page: int = 1, page_size: int = 20,
        status: OrderStatus | None = None,
    ) -> tuple[Sequence[Order], int]:
        """List orders with optional status filter and pagination."""
        offset = (page - 1) * page_size
        filters = {}
        if status is not None:
            filters["status"] = status
        return await self.repo.get_all(offset=offset, limit=page_size, filters=filters)

    async def list_customer_orders(
        self, customer_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[Sequence[Order], int]:
        """List orders for a specific customer."""
        offset = (page - 1) * page_size
        return await self.repo.get_by_customer(customer_id, offset=offset, limit=page_size)

    async def update_order_items(
        self, order_id: str, data: OrderUpdate
    ) -> Order | None:
        """
        Replace all line items on a PENDING order.

        Only allowed when the order is in PENDING state.  Reuses the
        shared currency-uniformity guard from ``_resolve_line_items`` so the
        same invariant enforced at creation applies here too.
        """
        order = await self.repo.get_full(order_id)
        if order is None:
            return None
        if order.status != OrderStatus.PENDING:
            raise OrderTransitionError(
                f"Cannot modify items of order in state {order.status.value} "
                f"(only PENDING allowed)"
            )

        # Delete existing line items
        await self.repo.delete_line_items(order_id)

        # Re-create line items with shared validation helper
        line_items, subtotal, currency = await self._resolve_line_items(data.items)
        for li in line_items:
            li.order_id = order_id
            await self.repo.add_line_item(li)

        tax = round(subtotal * settings.default_tax_rate, 2)
        total = round(subtotal + tax, 2)
        order = await self.repo.update(
            order, subtotal=round(subtotal, 2), tax=tax, total=total, currency=currency
        )
        await self.session.commit()
        await self.session.refresh(order)
        logger.info("Updated order %s items (total=%s %s)", order_id, total, currency)
        return order

    async def transition_status(
        self, order_id: str, data: OrderStatusUpdate, commit: bool = True,
    ) -> Order | None:
        """
        Transition an order to a new status.

        Validates the transition is allowed per ORDER_TRANSITIONS.
        Sets lifecycle timestamps (accepted_at, shipped_at, closed_at).

        When *commit* is True (the default) the change is committed
        immediately.  Callers that need to group several mutations into a
        single atomic transaction pass ``commit=False`` and commit the
        shared session themselves once every side-effect has succeeded.
        This prevents partial writes when an order transition is part of a
        larger workflow step (e.g. payment verification also flips the
        invoice status, so all three writes must commit together).
        """
        order = await self.repo.get_full(order_id)
        if order is None:
            return None

        current = order.status
        target = data.status

        if target not in ORDER_TRANSITIONS.get(current, set()):
            raise OrderTransitionError(
                f"Invalid transition: {current.value} → {target.value}. "
                f"Allowed: {[s.value for s in ORDER_TRANSITIONS.get(current, set())]}"
            )

        updates = {"status": target}

        import datetime as dt
        now = dt.datetime.now(dt.timezone.utc)
        if target == OrderStatus.ACCEPTED:
            updates["accepted_at"] = now
        elif target == OrderStatus.SHIPPED:
            updates["shipped_at"] = now
        elif target == OrderStatus.CLOSED:
            updates["closed_at"] = now

        order = await self.repo.update(order, **updates)
        if commit:
            await self.session.commit()
            await self.session.refresh(order)
        logger.info("Order %s transitioned %s → %s", order_id, current.value, target.value)
        return order

    async def cancel_order(self, order_id: str, reason: str | None = None) -> Order | None:
        """Cancel an order (only from PENDING or ACCEPTED)."""
        return await self.transition_status(
            order_id,
            OrderStatusUpdate(status=OrderStatus.CANCELLED, reason=reason),
        )

    async def delete_order(self, order_id: str) -> bool:
        """Delete an order. Returns True if deleted, False if not found."""
        order = await self.repo.get_by_id(order_id)
        if order is None:
            return False
        await self.repo.delete(order)
        await self.session.commit()
        logger.info("Deleted order %s", order_id)
        return True