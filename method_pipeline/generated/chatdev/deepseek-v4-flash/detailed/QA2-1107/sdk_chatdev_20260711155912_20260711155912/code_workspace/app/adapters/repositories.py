"""
Data access repositories using SQLAlchemy async sessions.

Each repository encapsulates queries for a single aggregate root.
Optimistic locking is enforced via the `version` column — every update
checks that the version hasn't changed since the entity was loaded.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import InvoiceStatus, OrderStatus
from app.domain.models import (
    Customer,
    Invoice,
    Order,
    OrderLineItem,
    Payment,
    Product,
)
from app.infrastructure.retry import db_retry


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @db_retry
    async def create(self, customer: Customer) -> Customer:
        self._session.add(customer)
        await self._session.flush()
        return customer

    @db_retry
    async def get(self, customer_id: uuid.UUID) -> Customer | None:
        return await self._session.get(Customer, customer_id)

    @db_retry
    async def list_all(self) -> Sequence[Customer]:
        result = await self._session.execute(select(Customer).order_by(Customer.created_at))
        return result.scalars().all()


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @db_retry
    async def create(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.flush()
        return product

    @db_retry
    async def get(self, product_id: uuid.UUID) -> Product | None:
        return await self._session.get(Product, product_id)

    @db_retry
    async def list_available(self) -> Sequence[Product]:
        result = await self._session.execute(
            select(Product).where(Product.available.is_(True)).order_by(Product.created_at)
        )
        return result.scalars().all()


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @db_retry
    async def create(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.flush()
        return order

    @db_retry
    async def get(self, order_id: uuid.UUID) -> Order | None:
        return await self._session.get(Order, order_id)

    @db_retry
    async def list_all(self) -> Sequence[Order]:
        """Return all orders ordered by creation time (newest first)."""
        result = await self._session.execute(
            select(Order).order_by(Order.created_at.desc())
        )
        return result.scalars().all()

    @db_retry
    async def list_by_customer(self, customer_id: uuid.UUID) -> Sequence[Order]:
        result = await self._session.execute(
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )
        return result.scalars().all()

    @db_retry
    async def list_by_status(self, status: OrderStatus) -> Sequence[Order]:
        result = await self._session.execute(
            select(Order).where(Order.status == status).order_by(Order.created_at)
        )
        return result.scalars().all()

    @db_retry
    async def update_status(
        self,
        order_id: uuid.UUID,
        new_status: OrderStatus,
        current_version: int,
        timestamp_field: str | None = None,
        invoice_ref: str | None = None,
    ) -> Order | None:
        """
        Update order status with optimistic locking.

        Combines status transition and optional invoice_ref update in a single
        atomic SQL UPDATE to prevent race conditions (see NFR 2.3).

        Args:
            order_id: The order to update.
            new_status: The new status value.
            current_version: The version we loaded (for optimistic lock check).
            timestamp_field: Optional field name to set to now (e.g., "paid_at_ts").
            invoice_ref: Optional invoice reference to set on the order.

        Returns:
            The updated Order or None if version conflict.
        """
        now = datetime.now(timezone.utc)
        values: dict = {
            "status": new_status,
            "version": current_version + 1,
            "updated_at": now,
        }
        if timestamp_field:
            values[timestamp_field] = now
        if invoice_ref is not None:
            values["invoice_ref"] = invoice_ref

        stmt = (
            update(Order)
            .where(Order.id == order_id, Order.version == current_version)
            .values(**values)
            .returning(Order)
        )
        result = await self._session.execute(stmt)
        updated = result.scalar_one_or_none()
        if updated is None:
            # Version conflict — someone else modified the order
            return None
        await self._session.flush()
        return updated

    # NOTE: update_invoice_ref is REMOVED — its logic is now merged into
    # update_status() to guarantee atomicity of status + invoice_ref updates.


class OrderLineItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @db_retry
    async def create(self, item: OrderLineItem) -> OrderLineItem:
        self._session.add(item)
        await self._session.flush()
        return item

    @db_retry
    async def get_by_order(self, order_id: uuid.UUID) -> Sequence[OrderLineItem]:
        result = await self._session.execute(
            select(OrderLineItem)
            .where(OrderLineItem.order_id == order_id)
            .order_by(OrderLineItem.created_at)
        )
        return result.scalars().all()


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @db_retry
    async def create(self, payment: Payment) -> Payment:
        self._session.add(payment)
        await self._session.flush()
        return payment

    @db_retry
    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        return await self._session.get(Payment, payment_id)

    @db_retry
    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    @db_retry
    async def get_by_order(self, order_id: uuid.UUID) -> Sequence[Payment]:
        result = await self._session.execute(
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at)
        )
        return result.scalars().all()


class InvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @db_retry
    async def create(self, invoice: Invoice) -> Invoice:
        self._session.add(invoice)
        await self._session.flush()
        return invoice

    @db_retry
    async def get(self, invoice_id: uuid.UUID) -> Invoice | None:
        return await self._session.get(Invoice, invoice_id)

    @db_retry
    async def get_by_order(self, order_id: uuid.UUID) -> Sequence[Invoice]:
        result = await self._session.execute(
            select(Invoice)
            .where(Invoice.order_id == order_id)
            .order_by(Invoice.created_at)
        )
        return result.scalars().all()

    @db_retry
    async def update_status(
        self, invoice_id: uuid.UUID, new_status: InvoiceStatus, current_version: int
    ) -> Invoice | None:
        """
        Update invoice status with optimistic locking.

        Args:
            invoice_id: The invoice to update.
            new_status: The new InvoiceStatus value.
            current_version: The version we loaded (for optimistic lock check).

        Returns:
            The updated Invoice or None if version conflict.
        """
        stmt = (
            update(Invoice)
            .where(Invoice.id == invoice_id, Invoice.version == current_version)
            .values(
                status=new_status,
                version=current_version + 1,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(Invoice)
        )
        result = await self._session.execute(stmt)
        updated = result.scalar_one_or_none()
        if updated is None:
            return None
        await self._session.flush()
        return updated
