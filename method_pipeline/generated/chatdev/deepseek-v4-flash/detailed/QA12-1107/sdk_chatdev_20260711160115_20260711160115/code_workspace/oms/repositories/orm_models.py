"""
SQLAlchemy ORM models (tables) and repository classes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.types import Numeric as SADecimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql import select

from oms.domain.enums import InvoiceStatus, OrderStatus, PaymentMethod, PaymentStatus, UserRole
from oms.infrastructure.database import Base


# ---------- ORM Models ----------

class CustomerORM(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(32), nullable=False)
    banking_details = Column(Text, nullable=False)
    role = Column(String(16), nullable=False, default=UserRole.CUSTOMER.value)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))

    orders = relationship("OrderORM", back_populates="customer")


class ProductORM(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=False, default="")
    base_price = Column(SADecimal(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    stock_available = Column(Integer, nullable=False, default=0)
    last_modified = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))


class OrderORM(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    line_items = Column(Text, nullable=False, default="[]")  # JSON array
    total_amount = Column(SADecimal(14, 2), nullable=False, default=Decimal("0.00"))
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(16), nullable=False, default=OrderStatus.CREATED.value)
    invoice_ref = Column(String(36), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    invoiced_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("CustomerORM", back_populates="orders")


class PaymentORM(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    amount = Column(SADecimal(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    method = Column(String(32), nullable=False, default=PaymentMethod.CREDIT_CARD.value)
    status = Column(String(16), nullable=False, default=PaymentStatus.PENDING.value)
    idempotency_key = Column(String(128), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)


class InvoiceORM(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    billing_address = Column(Text, nullable=False)
    total_amount = Column(SADecimal(14, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(16), nullable=False, default=InvoiceStatus.DRAFT.value)
    issue_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))


# ---------- Repositories ----------

class CustomerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, customer: dict) -> CustomerORM:
        orm = CustomerORM(**customer)
        self.session.add(orm)
        await self.session.flush()
        return orm

    async def get_by_id(self, customer_id: str) -> Optional[CustomerORM]:
        result = await self.session.execute(
            select(CustomerORM).where(CustomerORM.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[CustomerORM]:
        result = await self.session.execute(select(CustomerORM))
        return list(result.scalars().all())


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, product: dict) -> ProductORM:
        orm = ProductORM(**product)
        self.session.add(orm)
        await self.session.flush()
        return orm

    async def get_by_id(self, product_id: str) -> Optional[ProductORM]:
        result = await self.session.execute(
            select(ProductORM).where(ProductORM.id == product_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_lock(self, product_id: str) -> Optional[ProductORM]:
        """Get product with pessimistic lock (SELECT ... FOR UPDATE) to prevent TOCTOU races on stock."""
        result = await self.session.execute(
            select(ProductORM).where(ProductORM.id == product_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def search(self, query: str, limit: int = 20) -> list[ProductORM]:
        stmt = select(ProductORM).where(
            ProductORM.name.ilike(f"%{query}%")
        ).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> list[ProductORM]:
        result = await self.session.execute(select(ProductORM))
        return list(result.scalars().all())

    async def update_stock(self, product_id: str, delta: int) -> Optional[ProductORM]:
        """Update stock by delta (positive to add, negative to remove). Invalidates cache."""
        orm = await self.get_by_id(product_id)
        if orm:
            orm.stock_available += delta
            orm.last_modified = datetime.now(timezone.utc)
            await self.session.flush()
            # Invalidate product cache
            from oms.infrastructure.cache import cache
            await cache.delete(f"product:{product_id}")
        return orm


class OrderRepository:
    # Whitelist of allowed timestamp column names to prevent SQL injection
    ALLOWED_TIMESTAMP_FIELDS = frozenset({
        "accepted_at", "invoiced_at", "paid_at",
        "shipped_at", "closed_at", "cancelled_at",
    })

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, order: dict) -> OrderORM:
        orm = OrderORM(**order)
        self.session.add(orm)
        await self.session.flush()
        return orm

    async def get_by_id(self, order_id: str) -> Optional[OrderORM]:
        result = await self.session.execute(
            select(OrderORM).where(OrderORM.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_lock(self, order_id: str) -> Optional[OrderORM]:
        """Get order with pessimistic lock for version check."""
        result = await self.session.execute(
            select(OrderORM).where(OrderORM.id == order_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, order_id: str, new_status: str, version: int, timestamp_field: str = None
    ) -> bool:
        """Update order status with optimistic locking. Returns True if updated.

        timestamp_field is validated against a whitelist to prevent SQL injection.
        """
        if timestamp_field is not None and timestamp_field not in self.ALLOWED_TIMESTAMP_FIELDS:
            raise ValueError(
                f"Invalid timestamp field: {timestamp_field}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_TIMESTAMP_FIELDS))}"
            )

        if timestamp_field:
            stmt = text(
                f"UPDATE orders SET status = :status, version = version + 1, "
                f"{timestamp_field} = :ts "
                f"WHERE id = :id AND version = :version"
            )
        else:
            stmt = text(
                "UPDATE orders SET status = :status, version = version + 1 "
                "WHERE id = :id AND version = :version"
            )

        result = await self.session.execute(
            stmt,
            {
                "status": new_status,
                "id": order_id,
                "version": version,
                "ts": datetime.now(timezone.utc),
            },
        )
        await self.session.flush()
        return result.rowcount > 0

    async def list_by_customer(self, customer_id: str) -> list[OrderORM]:
        result = await self.session.execute(
            select(OrderORM).where(OrderORM.customer_id == customer_id)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[OrderORM]:
        result = await self.session.execute(select(OrderORM))
        return list(result.scalars().all())


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payment: dict) -> PaymentORM:
        orm = PaymentORM(**payment)
        self.session.add(orm)
        await self.session.flush()
        return orm

    async def get_by_id(self, payment_id: str) -> Optional[PaymentORM]:
        result = await self.session.execute(
            select(PaymentORM).where(PaymentORM.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Optional[PaymentORM]:
        result = await self.session.execute(
            select(PaymentORM).where(PaymentORM.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: str) -> Optional[PaymentORM]:
        result = await self.session.execute(
            select(PaymentORM).where(PaymentORM.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, payment_id: str, status: str) -> bool:
        stmt = (
            text("UPDATE payments SET status = :status, completed_at = :ts WHERE id = :id")
        )
        result = await self.session.execute(
            stmt,
            {"status": status, "id": payment_id, "ts": datetime.now(timezone.utc)},
        )
        await self.session.flush()
        return result.rowcount > 0


class InvoiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, invoice: dict) -> InvoiceORM:
        orm = InvoiceORM(**invoice)
        self.session.add(orm)
        await self.session.flush()
        return orm

    async def get_by_id(self, invoice_id: str) -> Optional[InvoiceORM]:
        result = await self.session.execute(
            select(InvoiceORM).where(InvoiceORM.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: str) -> Optional[InvoiceORM]:
        result = await self.session.execute(
            select(InvoiceORM).where(InvoiceORM.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, invoice_id: str, status: str) -> bool:
        stmt = text("UPDATE invoices SET status = :status WHERE id = :id")
        result = await self.session.execute(stmt, {"status": status, "id": invoice_id})
        await self.session.flush()
        return result.rowcount > 0
