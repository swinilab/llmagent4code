"""
Service layer for Invoice entity.
Handles invoice creation, status management, and number generation.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import InvoiceStatus, OrderStatus
from app.models.invoice import Invoice
from app.models.order import Order
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate


class InvoiceService:
    """Business logic for invoice operations."""

    @staticmethod
    async def _generate_invoice_number(db: AsyncSession) -> str:
        """Generate a sequential invoice number (INV-YYYYMMDD-XXXXX)."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        result = await db.execute(
            select(func.count(Invoice.id)).where(Invoice.invoice_number.like(f"INV-{today}-%"))
        )
        count = result.scalar() or 0
        return f"INV-{today}-{count + 1:05d}"

    @staticmethod
    async def create(db: AsyncSession, data: InvoiceCreate) -> Invoice:
        """Create a new invoice for an order, copying financial data from the order.

        Validates that:
        - The order exists and is in ACCEPTED status.
        - No invoice already exists for this order (prevents duplicate invoicing).
        """
        # Fetch the order to copy amounts and validate status
        result = await db.execute(select(Order).where(Order.id == data.order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Order {data.order_id} not found")
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(
                f"Cannot create invoice for order {data.order_id} in status {order.status.value}. "
                f"Order must be in ACCEPTED status."
            )

        # Prevent duplicate invoicing: check if an invoice already exists for this order
        existing = await db.execute(
            select(Invoice).where(Invoice.order_id == data.order_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError(
                f"An invoice already exists for order {data.order_id}. "
                f"Duplicate invoicing is not allowed."
            )

        invoice_number = await InvoiceService._generate_invoice_number(db)

        invoice = Invoice(
            order_id=data.order_id,
            invoice_number=invoice_number,
            billing_info=data.billing_info,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            shipping_cost=order.shipping_cost,
            total_amount=order.total_amount,
            currency=order.currency,
            status=InvoiceStatus.DRAFT,
            issue_date=data.issue_date,
            due_date=data.due_date,
        )
        db.add(invoice)
        await db.flush()
        return invoice

    @staticmethod
    async def get_by_id(db: AsyncSession, invoice_id: str) -> Optional[Invoice]:
        """Retrieve an invoice by ID."""
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_order(db: AsyncSession, order_id: str) -> List[Invoice]:
        """Get all invoices for a given order."""
        result = await db.execute(
            select(Invoice).where(Invoice.order_id == order_id).order_by(Invoice.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """List invoices with pagination."""
        result = await db.execute(
            select(Invoice).offset(skip).limit(limit).order_by(Invoice.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def issue_invoice(db: AsyncSession, invoice_id: str) -> Optional[Invoice]:
        """Issue a draft invoice (transition DRAFT -> ISSUED)."""
        invoice = await InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            return None
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Invoice {invoice_id} is in status {invoice.status.value}, expected DRAFT")
        invoice.status = InvoiceStatus.ISSUED
        await db.flush()
        # Refresh to load server-side defaults (updated_at)
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def mark_paid(db: AsyncSession, invoice_id: str) -> Optional[Invoice]:
        """Mark an invoice as paid (ISSUED -> PAID)."""
        invoice = await InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            return None
        if invoice.status not in (InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE):
            raise ValueError(
                f"Invoice {invoice_id} is in status {invoice.status.value}, expected ISSUED or OVERDUE"
            )
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.now(timezone.utc)
        await db.flush()
        # Refresh to load server-side defaults (updated_at)
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def update(db: AsyncSession, invoice_id: str, data: InvoiceUpdate) -> Optional[Invoice]:
        """Update invoice fields."""
        invoice = await InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(invoice, field, value)
        await db.flush()
        await db.refresh(invoice)
        return invoice

    @staticmethod
    async def delete(db: AsyncSession, invoice_id: str) -> bool:
        """Delete an invoice by ID."""
        invoice = await InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            return False
        await db.delete(invoice)
        await db.flush()
        return True
