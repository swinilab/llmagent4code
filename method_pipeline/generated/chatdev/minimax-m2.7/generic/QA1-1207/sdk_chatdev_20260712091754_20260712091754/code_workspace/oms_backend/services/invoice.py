"""
InvoiceService — business logic for invoice lifecycle.
Accountant creates and issues invoices; marks paid on payment verification.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from oms_backend.models.orm_models import Invoice, Order
from oms_backend.repositories.entities import CustomerRepository, InvoiceRepository, OrderRepository
from oms_backend.schemas.domain import InvoiceCreate, InvoiceIssue, InvoicePay, InvoiceStatus
from oms_backend.services.utils import audit_log, build_billing_address


class InvoiceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.invoice_repo = InvoiceRepository(session)
        self.order_repo = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)

    async def create_from_order(self, order_id: uuid.UUID, data: InvoiceCreate, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Invoice:
        """
        Accountant creates (draft) invoice for an accepted order.
        """
        order = await self.order_repo.get_with_items(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.status not in ("accepted", "invoiced"):
            raise ValueError(f"Cannot create invoice for order in {order.status} status; order must be accepted or invoiced")

        existing = await self.invoice_repo.get_by_order(order_id)
        if existing:
            raise ValueError(f"Invoice already exists for order {order.code}: {existing.code}")

        customer = await self.customer_repo.get_active(order.customer_id)
        if not customer:
            raise ValueError(f"Customer {order.customer_id} not found")

        code = await self.invoice_repo.next_code()

        invoice = await self.invoice_repo.create(
            code=code,
            order_id=order_id,
            customer_id=order.customer_id,
            status=InvoiceStatus.DRAFT.value,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            currency=order.currency,
            issue_date=data.issue_date,
            due_date=data.due_date,
            billing_name=customer.name,
            billing_address=build_billing_address(customer),
            created_by=actor_id,
        )

        # Attach invoice to order
        await self.order_repo.update(order_id, invoice_id=invoice.id)
        await self.order_repo.update_status(order_id, "invoiced")

        await audit_log(self.session, "invoice", invoice.id, "created",
                        actor_id=actor_id,
                        payload={"order_code": order.code, "total": str(invoice.total_amount)},
                        ip_address=ip_address)

        return await self.invoice_repo.get_with_relations(invoice.id)

    async def issue(self, id: uuid.UUID, data: InvoiceIssue, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Invoice | None:
        """
        Accountant issues a draft invoice (makes it enforceable).
        """
        invoice = await self.invoice_repo.get_with_relations(id)
        if not invoice:
            return None
        if invoice.status != InvoiceStatus.DRAFT.value:
            raise ValueError(f"Invoice {invoice.code} is {invoice.status}; only draft invoices can be issued")

        updated = await self.invoice_repo.update(
            id,
            status=InvoiceStatus.ISSUED.value,
            issue_date=data.issue_date,
            due_date=data.due_date,
        )
        if updated:
            await audit_log(self.session, "invoice", id, "issued", actor_id=actor_id, ip_address=ip_address)
        return await self.invoice_repo.get_with_relations(id)

    async def mark_paid(self, id: uuid.UUID, data: InvoicePay | None = None, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Invoice | None:
        """
        Accountant verifies payment and marks invoice as paid.
        Called after payment gateway confirmation.
        """
        invoice = await self.invoice_repo.get_with_relations(id)
        if not invoice:
            return None
        if invoice.status not in (InvoiceStatus.ISSUED.value, InvoiceStatus.OVERDUE.value):
            raise ValueError(f"Invoice {invoice.code} is {invoice.status}; only issued/overdue invoices can be marked paid")

        updated = await self.invoice_repo.update(
            id,
            status=InvoiceStatus.PAID.value,
            paid_date=date.today(),
        )
        if updated:
            # Update order status to paid
            await self.order_repo.update_status(invoice.order_id, "paid")
            await audit_log(self.session, "invoice", id, "paid", actor_id=actor_id, ip_address=ip_address)
        return await self.invoice_repo.get_with_relations(id)

    async def mark_overdue(self, id: uuid.UUID) -> Invoice | None:
        """Mark issued invoice overdue based on due_date check."""
        invoice = await self.invoice_repo.get_with_relations(id)
        if not invoice:
            return None
        if invoice.status == InvoiceStatus.ISSUED.value and invoice.due_date < date.today():
            await self.invoice_repo.update(id, status=InvoiceStatus.OVERDUE.value)
            await audit_log(self.session, "invoice", id, "overdue")
        return await self.invoice_repo.get_with_relations(id)

    async def cancel(self, id: uuid.UUID, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Invoice | None:
        """
        Cancel a draft or issued invoice; revert order to accepted only if currently invoiced.
        """
        invoice = await self.invoice_repo.get_with_relations(id)
        if not invoice:
            return None
        if invoice.status in (InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value):
            raise ValueError(f"Cannot cancel invoice {invoice.code} in {invoice.status} status")

        await self.invoice_repo.update(id, status=InvoiceStatus.CANCELLED.value)
        # Only revert order status if the order is currently "invoiced" (i.e., invoice was attached)
        current_order = await self.order_repo.get(invoice.order_id)
        if current_order and current_order.status == "invoiced":
            await self.order_repo.update_status(invoice.order_id, "accepted")
            await self.order_repo.update(invoice.order_id, invoice_id=None)
        await audit_log(self.session, "invoice", id, "cancelled", actor_id=actor_id, ip_address=ip_address)
        return await self.invoice_repo.get_with_relations(id)

    async def void(self, id: uuid.UUID, actor_id: uuid.UUID | None = None, ip_address: str | None = None) -> Invoice | None:
        """
        Accountant voids a paid invoice (issues credit note internally).
        Only paid invoices can be voided. Does NOT revert order status — void represents
        a credit note and should not roll back the order to an earlier state.
        """
        invoice = await self.invoice_repo.get_with_relations(id)
        if not invoice:
            return None
        if invoice.status != InvoiceStatus.PAID.value:
            raise ValueError(f"Cannot void invoice {invoice.code} in {invoice.status} status; only paid invoices can be voided")

        await self.invoice_repo.update(id, status=InvoiceStatus.CANCELLED.value)
        await audit_log(self.session, "invoice", id, "voided", actor_id=actor_id, ip_address=ip_address)
        return await self.invoice_repo.get_with_relations(id)

    async def get(self, id: uuid.UUID) -> Invoice | None:
        return await self.invoice_repo.get_with_relations(id)

    async def get_by_order(self, order_id: uuid.UUID) -> Invoice | None:
        return await self.invoice_repo.get_by_order(order_id)

    async def list_all(self, page: int = 1, page_size: int = 20) -> tuple[list[Invoice], int]:
        return await self.invoice_repo.list_all(page=page, page_size=page_size)

    async def list_by_customer(self, customer_id: uuid.UUID, page: int = 1, page_size: int = 20) -> tuple[list[Invoice], int]:
        return await self.invoice_repo.list_by_customer(customer_id, page=page, page_size=page_size)
