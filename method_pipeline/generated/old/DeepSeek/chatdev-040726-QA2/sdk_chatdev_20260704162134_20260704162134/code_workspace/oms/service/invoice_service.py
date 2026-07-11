"""
Invoice service: creation and lifecycle management.
"""

from datetime import datetime, date, timezone
from uuid import UUID

from oms.domain.enums import OrderStatus, InvoiceStatus
from oms.domain.events import InvoiceCreated
from oms.domain.models import Invoice, CreateInvoiceRequest
from oms.repository.in_memory import InMemoryInvoiceRepository, InMemoryOrderRepository
from oms.service.event_bus import event_bus


class InvoiceService:
    """Business logic for Invoice operations."""

    def __init__(
        self,
        invoice_repo: InMemoryInvoiceRepository,
        order_repo: InMemoryOrderRepository,
    ) -> None:
        self._invoice_repo = invoice_repo
        self._order_repo = order_repo

    def create_invoice(self, request: CreateInvoiceRequest) -> Invoice:
        """Step 3: Accountant creates an invoice for an accepted order.

        Creates a financial snapshot with fully independent copies of
        order data to guarantee immutability of the invoice record.
        """
        order = self._order_repo.find_by_id(request.order_id)
        if order is None:
            raise ValueError(f"Order {request.order_id} not found")
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(
                f"Order {request.order_id} is in status {order.status.value}, expected accepted"
            )

        # Deep-copy line items so the invoice holds its own independent data.
        # This prevents future mutations to order.line_items from corrupting
        # the invoice's financial record (data integrity).
        line_items_copy = [item.model_copy(deep=True) for item in order.line_items]
        subtotal_copy = order.total.model_copy()

        invoice = Invoice(
            order_id=request.order_id,
            customer_id=request.customer_id,
            billing_address=request.billing_address,
            line_items=line_items_copy,
            subtotal=subtotal_copy,
            tax=request.tax,
            total=subtotal_copy + request.tax,
            due_date=request.due_date,
            status=InvoiceStatus.ISSUED,
        )
        saved = self._invoice_repo.save(invoice)

        # Link invoice to order
        order.invoice_ref = saved.id
        order.status = OrderStatus.INVOICED
        order.updated_at = datetime.now(timezone.utc)
        self._order_repo.save(order)

        event_bus.publish(InvoiceCreated(invoice_id=saved.id, order_id=request.order_id))
        return saved

    def mark_overdue(self, invoice_id: UUID) -> Invoice:
        """Mark an issued invoice as overdue if past due date."""
        invoice = self._invoice_repo.find_by_id(invoice_id)
        if invoice is None:
            raise ValueError(f"Invoice {invoice_id} not found")
        if invoice.status != InvoiceStatus.ISSUED:
            raise ValueError(
                f"Invoice {invoice_id} is in status {invoice.status.value}, expected issued"
            )
        if date.today() <= invoice.due_date:
            raise ValueError(
                f"Invoice {invoice_id} is not yet past due (due: {invoice.due_date})"
            )

        invoice.status = InvoiceStatus.OVERDUE
        invoice.updated_at = datetime.now(timezone.utc)
        return self._invoice_repo.save(invoice)

    def get_by_id(self, invoice_id: UUID) -> Invoice | None:
        """Retrieve an invoice by ID."""
        return self._invoice_repo.find_by_id(invoice_id)

    def get_by_order(self, order_id: UUID) -> list[Invoice]:
        """List invoices for a given order."""
        return self._invoice_repo.find_by_order(order_id)

    def list_all(self) -> list[Invoice]:
        """List all invoices."""
        return self._invoice_repo.find_all()
