"""
OMS Invoice Service - Business logic for invoice management.
"""
from typing import List, Optional
import uuid
from datetime import datetime
from decimal import Decimal
from app.domain.entities.models import Invoice, InvoiceStatus, LineItem, Money, Currency, Address
from app.domain.repositories.interfaces import InvoiceRepository, OrderRepository


class InvoiceService:
    """Service for invoice operations."""

    def __init__(self, invoice_repo: InvoiceRepository, order_repo: OrderRepository = None):
        self._repo = invoice_repo
        self._order_repo = order_repo
        self._invoice_counter = 0

    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        self._invoice_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        return f"INV-{timestamp}-{self._invoice_counter:04d}"

    def create_invoice(
        self,
        order_id: str,
        customer_id: str,
        line_items: List[LineItem],
        subtotal: Money,
        tax_total: Money,
        discount_total: Money,
        total: Money,
        billing_address: Optional[Address] = None,
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        terms: str = "Net 30"
    ) -> Invoice:
        """Create a new invoice."""
        invoice = Invoice(
            id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            billing_address=billing_address,
            invoice_number=self._generate_invoice_number(),
            line_items=line_items,
            subtotal=subtotal,
            tax_total=tax_total,
            discount_total=discount_total,
            total=total,
            currency=total.currency,
            status=InvoiceStatus.DRAFT,
            issue_date=datetime.utcnow(),
            due_date=due_date,
            notes=notes,
            terms=terms
        )
        return self._repo.save(invoice)

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        return self._repo.find_by_id(invoice_id)

    def get_invoice_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        return self._repo.find_by_invoice_number(invoice_number)

    def get_invoice_for_order(self, order_id: str) -> Optional[Invoice]:
        """Get invoice for an order."""
        return self._repo.find_by_order(order_id)

    def get_invoices_by_status(self, status: InvoiceStatus) -> List[Invoice]:
        """Get invoices by status."""
        return self._repo.find_by_status(status)

    def get_invoices_by_customer(self, customer_id: str) -> List[Invoice]:
        """Get all invoices for a customer."""
        return self._repo.find_by_customer(customer_id)

    def issue_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Issue a draft invoice."""
        invoice = self._repo.find_by_id(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.DRAFT:
            return None
        
        return self._repo.update(invoice_id, {
            'status': InvoiceStatus.ISSUED,
            'issue_date': datetime.utcnow()
        })

    def mark_invoice_paid(self, invoice_id: str, payment_id: str) -> Optional[Invoice]:
        """Mark issued invoice as paid."""
        invoice = self._repo.find_by_id(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.ISSUED:
            return None
        
        result = self._repo.update(invoice_id, {
            'status': InvoiceStatus.PAID,
            'paid_date': datetime.utcnow(),
            'payment_id': payment_id
        })
        
        if result and self._order_repo:
            self._order_repo.update(invoice.order_id, {'invoice_id': invoice_id})
        
        return result

    def mark_invoice_overdue(self, invoice_id: str) -> Optional[Invoice]:
        """Mark issued invoice as overdue."""
        invoice = self._repo.find_by_id(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.ISSUED:
            return None
        
        return self._repo.update(invoice_id, {
            'status': InvoiceStatus.OVERDUE
        })

    def cancel_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Cancel an invoice."""
        invoice = self._repo.find_by_id(invoice_id)
        if not invoice or invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            return None
        
        return self._repo.update(invoice_id, {
            'status': InvoiceStatus.CANCELLED
        })
