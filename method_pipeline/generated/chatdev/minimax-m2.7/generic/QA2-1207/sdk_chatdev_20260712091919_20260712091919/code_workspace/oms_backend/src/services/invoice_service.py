"""
Invoice Service - business logic for invoice management.
Handles: create invoice -> issue -> mark paid workflow.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ..domain.models import Invoice, InvoiceStatus, Order, Address
from ..infrastructure.repositories import InvoiceRepository, OrderRepository
from ..utils.resilience import FeatureFlags

logger = logging.getLogger(__name__)


class InvoiceWorkflowError(Exception):
    """Raised when invoice workflow transition is invalid."""
    pass


class InvoiceService:
    """
    Service layer for invoice operations.
    Step 3 in workflow: Accountant creates invoice for accepted order.
    """

    def __init__(self, db_session=None, feature_flags: Optional[FeatureFlags] = None):
        self.db_session = db_session
        self._repo = None
        self._order_repo = None
        self._feature_flags = feature_flags or FeatureFlags()

    @property
    def repo(self) -> InvoiceRepository:
        if self._repo is None:
            if self.db_session:
                self._repo = InvoiceRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._repo

    @property
    def order_repo(self) -> OrderRepository:
        if self._order_repo is None:
            if self.db_session:
                self._order_repo = OrderRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._order_repo

    def create_invoice(self, order_id: str, customer_id: str,
                      billing_address: Address,
                      due_date_days: int = 30,
                      idempotency_key: Optional[str] = None) -> Invoice:
        """
        Step 3: Accountant creates invoice for accepted order.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise InvoiceWorkflowError(f"Order not found: {order_id}")

        if hasattr(order.status, 'value'):
            order_status = order.status.value
        else:
            order_status = str(order.status)
            
        if order_status not in ["accepted"]:
            raise InvoiceWorkflowError(
                f"Cannot create invoice for order in status: {order_status}. Expected: accepted"
            )

        existing = self.repo.get_by_order(order_id)
        if existing:
            raise InvoiceWorkflowError(f"Invoice already exists for order: {order_id}")

        due_date = datetime.now(timezone.utc) + timedelta(days=due_date_days)

        invoice = Invoice(
            order_id=order_id,
            customer_id=customer_id,
            billing_address=billing_address,
            subtotal=order.subtotal,
            tax=order.tax,
            total=order.total,
            currency=order.currency,
            status=InvoiceStatus.DRAFT,
            due_date=due_date,
            idempotency_key=idempotency_key
        )

        if idempotency_key:
            saved_invoice, created = self.repo.create_with_idempotency(invoice)
            if not created:
                logger.info(f"Returning existing invoice for idempotency key: {idempotency_key}")
                return saved_invoice
        else:
            saved_invoice = self.repo.create(invoice)

        logger.info(f"Invoice created: {saved_invoice.id} for order: {order_id}")
        return saved_invoice

    def issue_invoice(self, invoice_id: str) -> Invoice:
        """
        Issue a draft invoice (change status to issued).
        """
        invoice = self.repo.get_by_id(invoice_id)
        if not invoice:
            raise InvoiceWorkflowError(f"Invoice not found: {invoice_id}")

        if invoice.status != InvoiceStatus.DRAFT:
            raise InvoiceWorkflowError(
                f"Cannot issue invoice in status: {invoice.status}. Expected: {InvoiceStatus.DRAFT}"
            )

        invoice.status = InvoiceStatus.ISSUED
        updated_invoice = self.repo.update(invoice)

        logger.info(f"Invoice issued: {invoice_id}")
        return updated_invoice

    def mark_invoice_paid(self, invoice_id: str) -> Invoice:
        """
        Step 4: Mark invoice as paid after customer payment.
        """
        invoice = self.repo.get_by_id(invoice_id)
        if not invoice:
            raise InvoiceWorkflowError(f"Invoice not found: {invoice_id}")

        if invoice.status not in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]:
            raise InvoiceWorkflowError(
                f"Cannot mark as paid invoice in status: {invoice.status}. Expected: issued or overdue"
            )

        invoice.status = InvoiceStatus.PAID
        invoice.paid_date = datetime.now(timezone.utc)
        updated_invoice = self.repo.update(invoice)

        logger.info(f"Invoice marked as paid: {invoice_id}")
        return updated_invoice

    def mark_invoice_overdue(self, invoice_id: str) -> Invoice:
        """Mark an issued invoice as overdue."""
        invoice = self.repo.get_by_id(invoice_id)
        if not invoice:
            raise InvoiceWorkflowError(f"Invoice not found: {invoice_id}")

        if invoice.status != InvoiceStatus.ISSUED:
            raise InvoiceWorkflowError(
                f"Cannot mark as overdue invoice in status: {invoice.status}. Expected: issued"
            )

        invoice.status = InvoiceStatus.OVERDUE
        updated_invoice = self.repo.update(invoice)

        logger.info(f"Invoice marked as overdue: {invoice_id}")
        return updated_invoice

    def cancel_invoice(self, invoice_id: str) -> Invoice:
        """Cancel a draft or issued invoice."""
        invoice = self.repo.get_by_id(invoice_id)
        if not invoice:
            raise InvoiceWorkflowError(f"Invoice not found: {invoice_id}")

        non_cancellable = [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]
        if invoice.status in non_cancellable:
            raise InvoiceWorkflowError(
                f"Cannot cancel invoice in status: {invoice.status}"
            )

        invoice.status = InvoiceStatus.CANCELLED
        updated_invoice = self.repo.update(invoice)

        logger.info(f"Invoice cancelled: {invoice_id}")
        return updated_invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        return self.repo.get_by_id(invoice_id)

    def get_invoice_by_order(self, order_id: str) -> Optional[Invoice]:
        """Get invoice for an order."""
        return self.repo.get_by_order(order_id)

    def get_invoices_by_customer(self, customer_id: str, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Get invoices for a customer."""
        return self.repo.get_by_customer(customer_id, skip=skip, limit=limit)

    def get_outstanding_invoices(self, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Get all outstanding (issued or overdue) invoices."""
        all_invoices = self.repo.get_all(skip=skip, limit=limit)
        return [inv for inv in all_invoices 
                if inv.status in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]]
