"""Order service — orchestrates the complete order workflow."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import LineItem, Order, OrderStatus
from app.entities import CustomerEntity, OrderEntity
from app.repositories.order_repo import OrderRepository


class OrderService:
    """Manages order lifecycle from placement to closure."""

    def __init__(self, session: AsyncSession) -> None:
        self._order_repo = OrderRepository(session)
        self._session = session

    # ── Customer workflow ─────────────────────────────────────────────────────

    async def place_order(
        self, customer_id: str, line_items: list[LineItem]
    ) -> Order:
        # Validate customer exists
        stmt = select(CustomerEntity).where(CustomerEntity.id == customer_id)
        result = await self._session.execute(stmt)
        customer = result.scalar_one_or_none()
        if customer is None:
            raise ValueError(f"Customer {customer_id} does not exist")

        total = sum(item.subtotal for item in line_items)
        order_id = str(uuid.uuid4())
        entity = OrderEntity(
            id=order_id,
            customer_id=customer_id,
            total_amount=total,
            status=OrderStatus.PENDING.value,
        )
        saved = await self._order_repo.save(entity)

        # Save line items
        item_dicts = [
            {
                "product_id": li.product_id,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "subtotal": li.subtotal,
            }
            for li in line_items
        ]
        await self._order_repo.save_line_items(order_id, item_dicts)

        # Reload with items
        full = await self._order_repo.get_with_items(order_id)
        return self._entity_to_order(full)

    async def _get_order_with_items(self, order_id: str) -> OrderEntity | None:
        """Helper to load order with eagerly loaded line items."""
        stmt = (
            select(OrderEntity)
            .options(selectinload(OrderEntity.line_items))
            .where(OrderEntity.id == order_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_order(self, order_id: str) -> Optional[Order]:
        entity = await self._get_order_with_items(order_id)
        if entity is None:
            return None
        return self._entity_to_order(entity)

    async def list_orders(self, status: Optional[OrderStatus] = None) -> list[Order]:
        if status:
            entities = await self._order_repo.list_by_status(status)
        else:
            entities = await self._order_repo.list_all()
        return [self._entity_to_order(e) for e in entities]

    # ── Order Staff workflow ──────────────────────────────────────────────────

    async def accept_order(self, order_id: str) -> Optional[Order]:
        """Staff reviews & accepts -> PENDING -> ACCEPTED."""
        entity = await self._order_repo.get(order_id)
        if entity is None:
            return None
        if entity.status != OrderStatus.PENDING.value:
            return None
        entity.status = OrderStatus.ACCEPTED.value
        await self._session.flush()
        full = await self._get_order_with_items(order_id)
        return self._entity_to_order(full)

    async def ship_order(self, order_id: str) -> Optional[Order]:
        """Staff ships a paid order -> VERIFIED -> SHIPPED."""
        entity = await self._order_repo.get(order_id)
        if entity is None or entity.status != OrderStatus.VERIFIED.value:
            return None
        entity.status = OrderStatus.SHIPPED.value
        await self._session.flush()
        full = await self._get_order_with_items(order_id)
        return self._entity_to_order(full)

    async def close_order(self, order_id: str) -> Optional[Order]:
        """Staff closes completed order -> SHIPPED -> COMPLETED."""
        entity = await self._order_repo.get(order_id)
        if entity is None or entity.status != OrderStatus.SHIPPED.value:
            return None
        entity.status = OrderStatus.COMPLETED.value
        await self._session.flush()
        full = await self._get_order_with_items(order_id)
        return self._entity_to_order(full)

    # ── Accountant workflow ───────────────────────────────────────────────────

    async def mark_paid(self, order_id: str) -> Optional[Order]:
        """Payment made -> INVOICED -> PAID."""
        entity = await self._order_repo.get(order_id)
        if entity is None or entity.status != OrderStatus.INVOICED.value:
            return None
        entity.status = OrderStatus.PAID.value
        await self._session.flush()
        full = await self._get_order_with_items(order_id)
        return self._entity_to_order(full)

    async def mark_invoiced(self, order_id: str, invoice_id: str) -> Optional[Order]:
        """Accountant created invoice -> ACCEPTED -> INVOICED."""
        entity = await self._order_repo.get(order_id)
        if entity is None or entity.status != OrderStatus.ACCEPTED.value:
            return None
        entity.status = OrderStatus.INVOICED.value
        entity.invoice_id = invoice_id
        await self._session.flush()
        full = await self._get_order_with_items(order_id)
        return self._entity_to_order(full)

    async def mark_verified(self, order_id: str) -> Optional[Order]:
        """Accountant verifies payment -> PAID -> VERIFIED."""
        entity = await self._order_repo.get(order_id)
        if entity is None or entity.status != OrderStatus.PAID.value:
            return None
        entity.status = OrderStatus.VERIFIED.value
        await self._session.flush()
        full = await self._get_order_with_items(order_id)
        return self._entity_to_order(full)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _entity_to_order(entity: OrderEntity) -> Order:
        """Convert ORM entity to domain model, using model_validate for consistency."""
        order = Order.model_validate(entity)
        # LineItems are not auto-converted via from_attributes because LineItemEntity
        # has different field names/structure; convert manually
        order.line_items = [
            LineItem(
                product_id=li.product_id,
                quantity=li.quantity,
                unit_price=li.unit_price,
                subtotal=li.subtotal,
            )
            for li in entity.line_items
        ]
        return order