"""
Order repository — data access for Order and OrderLineItem entities.
"""
import datetime as dt
from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from oms.enums import OrderStatus
from oms.models.order import Order, OrderLineItem
from oms.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Repository for Order CRUD + lifecycle queries."""

    model = Order

    async def get_full(self, id: str) -> Order | None:
        """Fetch order with all relationships eagerly loaded."""
        stmt = (
            select(Order)
            .where(Order.id == id)
            .options(
                selectinload(Order.customer),
                selectinload(Order.line_items).selectinload(OrderLineItem.product),
                selectinload(Order.invoice),
                selectinload(Order.payments),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_customer(
        self, customer_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[Order], int]:
        """Fetch paginated orders for a customer."""
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .options(selectinload(Order.line_items))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        count_stmt = select(func.count()).select_from(Order).where(
            Order.customer_id == customer_id
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        return items, total

    async def get_by_status(self, status: OrderStatus) -> Sequence[Order]:
        """Fetch all orders in a given status (used by recovery worker)."""
        stmt = (
            select(Order)
            .where(Order.status == status)
            .options(selectinload(Order.line_items), selectinload(Order.invoice))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_line_item(self, item: OrderLineItem) -> OrderLineItem:
        """Add a line item to an order."""
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def delete_line_items(self, order_id: str) -> None:
        """Delete all line items for an order (used when replacing items on a PENDING order)."""
        stmt = delete(OrderLineItem).where(OrderLineItem.order_id == order_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_line_items(self, order_id: str) -> Sequence[OrderLineItem]:
        """Fetch all line items for an order."""
        stmt = (
            select(OrderLineItem)
            .where(OrderLineItem.order_id == order_id)
            .options(selectinload(OrderLineItem.product))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pending_since(self, since: dt.datetime) -> Sequence[Order]:
        """Fetch orders pending processing since the given timestamp (recovery)."""
        stmt = (
            select(Order)
            .where(Order.status == OrderStatus.PENDING, Order.created_at >= since)
            .options(selectinload(Order.line_items))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()