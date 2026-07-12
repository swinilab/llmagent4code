"""
Async repositories — one file per entity to keep concerns separated.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oms_backend.models.orm_models import (
    AuditLog, Customer, Invoice, LineItem, Order, Payment, Product, Sequence,
)
from oms_backend.repositories.base import BaseRepository

# ─────────────────────────────────────────────────────────────────────────────
# AuditLogRepository
# ─────────────────────────────────────────────────────────────────────────────

class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def log(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        actor_id: uuid.UUID | None = None,
        payload: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        instance = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            payload=payload or {},
            ip_address=ip_address,
        )
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def by_entity(self, entity_type: str, entity_id: uuid.UUID) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# CustomerRepository
# ─────────────────────────────────────────────────────────────────────────────

class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession):
        super().__init__(Customer, session)

    async def get_by_email(self, email: str) -> Customer | None:
        stmt = select(Customer).where(
            Customer.email == email.lower(),
            Customer.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Customer | None:
        stmt = select(Customer).where(Customer.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def next_code(self) -> str:
        """Atomically increment sequence and return next code."""
        result = await self.session.execute(
            update(Sequence)
            .where(Sequence.name == "customer")
            .values(current_value=Sequence.current_value + 1)
            .returning(Sequence.current_value)
        )
        seq = result.scalar_one()
        return f"CUST-{seq:05d}"


# ─────────────────────────────────────────────────────────────────────────────
# ProductRepository
# ─────────────────────────────────────────────────────────────────────────────

class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def get_by_sku(self, sku: str) -> Product | None:
        stmt = select(Product).where(Product.sku == sku)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        """Full-text search via gin index."""
        stmt = select(Product).where(Product.is_active == True)
        count_stmt = select(func.count()).select_from(Product).where(Product.is_active == True)

        if query:
            stmt = stmt.where(
                func.to_tsvector("english", Product.name + " " + func.coalesce(Product.description, "")).matches(query)
            )
            count_stmt = count_stmt.where(
                func.to_tsvector("english", Product.name + " " + func.coalesce(Product.description, "")).matches(query)
            )

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_bulk(self, ids: list[uuid.UUID]) -> list[Product]:
        if not ids:
            return []
        stmt = select(Product).where(Product.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reserve_stock(self, product_id: uuid.UUID, quantity: int) -> bool:
        """Atomically reserve stock — fails if insufficient quantity remains. Returns True if reserved."""
        result = await self.session.execute(
            update(Product)
            .where(Product.id == product_id)
            .where(Product.stock_qty >= quantity)
            .values(stock_qty=Product.stock_qty - quantity)
        )
        return result.rowcount > 0

    async def restore_stock(self, product_id: uuid.UUID, quantity: int) -> bool:
        """Atomically restore stock after order cancellation."""
        result = await self.session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(stock_qty=Product.stock_qty + quantity)
        )
        return result.rowcount > 0


# ─────────────────────────────────────────────────────────────────────────────
# OrderRepository
# ─────────────────────────────────────────────────────────────────────────────

class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_with_items(self, id: uuid.UUID) -> Order | None:
        stmt = (
            select(Order)
            .options(selectinload(Order.line_items).selectinload(LineItem.product))
            .options(selectinload(Order.customer))
            .where(Order.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Order | None:
        stmt = select(Order).where(Order.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def next_code(self) -> str:
        """Atomically increment sequence and return next code."""
        result = await self.session.execute(
            update(Sequence)
            .where(Sequence.name == "order")
            .values(current_value=Sequence.current_value + 1)
            .returning(Sequence.current_value)
        )
        seq = result.scalar_one()
        return f"ORD-{seq:06d}"

    async def list_by_customer(
        self, customer_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Order], int]:
        stmt = (
            select(Order)
            .options(selectinload(Order.line_items).selectinload(LineItem.product))
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )
        count_stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.customer_id == customer_id)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_by_status(
        self, status: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[Order], int]:
        stmt = (
            select(Order)
            .options(selectinload(Order.line_items).selectinload(LineItem.product))
            .options(selectinload(Order.customer))
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
        )
        count_stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.status == status)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def update_status(self, id: uuid.UUID, status: str) -> Order | None:
        """Update order status with automatic timestamp transitions."""
        vals: dict[str, Any] = {"status": status, "updated_at": datetime.utcnow()}
        if status == "accepted":
            vals["accepted_at"] = datetime.utcnow()
        elif status == "paid":
            vals["paid_at"] = datetime.utcnow()
        elif status == "shipped":
            vals["shipped_at"] = datetime.utcnow()
        elif status == "delivered":
            vals["delivered_at"] = datetime.utcnow()
        elif status == "closed":
            vals["closed_at"] = datetime.utcnow()
        stmt = update(Order).where(Order.id == id).values(**vals).returning(Order)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# LineItemRepository
# ─────────────────────────────────────────────────────────────────────────────

class LineItemRepository(BaseRepository[LineItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(LineItem, session)

    async def get_by_order(self, order_id: uuid.UUID) -> list[LineItem]:
        stmt = (
            select(LineItem)
            .options(selectinload(LineItem.product))
            .where(LineItem.order_id == order_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_bulk(self, order_id: uuid.UUID, items: list[dict[str, Any]]) -> list[LineItem]:
        created = []
        for item in items:
            instance = LineItem(order_id=order_id, **item)
            self.session.add(instance)
            created.append(instance)
        await self.session.flush()
        for c in created:
            await self.session.refresh(c)
        return created


# ─────────────────────────────────────────────────────────────────────────────
# InvoiceRepository
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, session: AsyncSession):
        super().__init__(Invoice, session)

    async def get_by_order(self, order_id: uuid.UUID) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.order_id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_relations(self, id: uuid.UUID) -> Invoice | None:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.order))
            .options(selectinload(Invoice.customer))
            .options(selectinload(Invoice.payments))
            .where(Invoice.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def next_code(self) -> str:
        result = await self.session.execute(
            update(Sequence)
            .where(Sequence.name == "invoice")
            .values(current_value=Sequence.current_value + 1)
            .returning(Sequence.current_value)
        )
        seq = result.scalar_one()
        date_part = datetime.utcnow().strftime("%Y%m%d")
        return f"INV-{date_part}-{seq:04d}"

    async def list_by_customer(
        self, customer_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Invoice], int]:
        stmt = (
            select(Invoice)
            .where(Invoice.customer_id == customer_id)
            .order_by(Invoice.created_at.desc())
        )
        count_stmt = (
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.customer_id == customer_id)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


# ─────────────────────────────────────────────────────────────────────────────
# PaymentRepository
# ─────────────────────────────────────────────────────────────────────────────

class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    async def get_by_invoice(self, invoice_id: uuid.UUID) -> list[Payment]:
        stmt = select(Payment).where(Payment.invoice_id == invoice_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_reference(self, reference: str) -> Payment | None:
        stmt = select(Payment).where(Payment.reference == reference)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def next_code(self) -> str:
        result = await self.session.execute(
            update(Sequence)
            .where(Sequence.name == "payment")
            .values(current_value=Sequence.current_value + 1)
            .returning(Sequence.current_value)
        )
        seq = result.scalar_one()
        date_part = datetime.utcnow().strftime("%Y%m%d")
        return f"PAY-{date_part}-{seq:04d}"
