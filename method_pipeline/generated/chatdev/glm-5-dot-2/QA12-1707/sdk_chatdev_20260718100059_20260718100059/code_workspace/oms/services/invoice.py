"""
Invoice service — business logic for invoice creation and management.

Implements step 3 of the workflow:
  3. Accountant creates invoice for accepted order

Creates an invoice from an accepted order, copying amounts and
billing info. Links the invoice to the order and transitions the
order to INVOICED.
"""
import datetime as dt
import logging
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from oms.enums import InvoiceStatus, OrderStatus
from oms.models.invoice import Invoice
from oms.repositories.invoice import InvoiceRepository
from oms.repositories.order import OrderRepository
from oms.schemas.invoice import InvoiceCreate, InvoiceStatusUpdate
from oms.services.order import OrderService

logger = logging.getLogger(__name__)


class InvoiceError(Exception):
    """Raised when an invoice operation fails business validation."""
    pass


class InvoiceService:
    """Business logic for Invoice entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = InvoiceRepository(session)
        self.order_repo = OrderRepository(session)
        self.order_service = OrderService(session)

    async def create_invoice(self, data: InvoiceCreate) -> Invoice:
        """
        Create an invoice for an accepted order.

        The order must be in ACCEPTED status. The invoice copies the
        order's amounts and billing info, then transitions the order
        to INVOICED.  Both the invoice creation and the order transition
        are committed in a single transaction so the order is never left
        ACCEPTED with a dangling invoice record.
        """
        order = await self.order_repo.get_full(data.order_id)
        if order is None:
            raise InvoiceError(f"Order {data.order_id} not found")

        if order.status != OrderStatus.ACCEPTED:
            raise InvoiceError(
                f"Order must be ACCEPTED to create invoice (current: {order.status.value})"
            )

        # Check for existing invoice
        existing = await self.repo.get_by_order(data.order_id)
        if existing is not None:
            raise InvoiceError(f"Order {data.order_id} already has an invoice")

        issue_date = data.issue_date or dt.date.today()
        due_date = data.due_date or (issue_date + dt.timedelta(days=30))

        billing_info = data.billing_info or {
            "customer_name": order.customer.name if order.customer else "Unknown",
            "address": order.customer.address if order.customer else "",
        }

        invoice = await self.repo.create(
            order_id=data.order_id,
            billing_info=billing_info,
            subtotal=float(order.subtotal),
            tax=float(order.tax),
            total=float(order.total),
            currency=order.currency,
            issue_date=issue_date,
            due_date=due_date,
            status=InvoiceStatus.ISSUED,
        )

        # Link invoice to order and transition order to INVOICED.
        # Both writes are committed together below so the order is never
        # left ACCEPTED with a dangling invoice record if the second
        # write fails.
        await self.order_repo.update(order, invoice_id=invoice.id)
        from oms.schemas.order import OrderStatusUpdate
        await self.order_service.transition_status(
            data.order_id,
            OrderStatusUpdate(status=OrderStatus.INVOICED, reason="Invoice created"),
            commit=False,
        )

        await self.session.commit()
        await self.session.refresh(invoice)
        logger.info("Created invoice %s for order %s (total=%s %s)",
                     invoice.id, data.order_id, invoice.total, invoice.currency)
        return invoice

    async def get_invoice(self, invoice_id: str) -> Invoice | None:
        """Fetch an invoice by ID."""
        return await self.repo.get_by_id(invoice_id)

    async def get_invoice_by_order(self, order_id: str) -> Invoice | None:
        """Fetch the invoice for a given order."""
        return await self.repo.get_by_order(order_id)

    async def list_invoices(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[Sequence[Invoice], int]:
        """List invoices with pagination."""
        offset = (page - 1) * page_size
        return await self.repo.get_all(offset=offset, limit=page_size)

    async def update_invoice_status(
        self, invoice_id: str, data: InvoiceStatusUpdate
    ) -> Invoice | None:
        """Manually update an invoice's status."""
        invoice = await self.repo.get_by_id(invoice_id)
        if invoice is None:
            return None
        invoice = await self.repo.update(invoice, status=data.status)
        await self.session.commit()
        logger.info("Updated invoice %s status to %s", invoice_id, data.status.value)
        return invoice

    async def mark_overdue_invoices(self) -> list[Invoice]:
        """Mark all issued invoices past their due date as OVERDUE."""
        overdue = await self.repo.get_overdue()
        updated: list[Invoice] = []
        for inv in overdue:
            inv = await self.repo.update(inv, status=InvoiceStatus.OVERDUE)
            updated.append(inv)
        if updated:
            await self.session.commit()
            logger.info("Marked %d invoice(s) as OVERDUE", len(updated))
        return updated