"""
Invoice service layer.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.invoice import InvoiceRepository
from app.models.invoice import InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceRead


class InvoiceService:
    """Invoice service."""

    def __init__(self, db: Session):
        self.repo = InvoiceRepository(db)

    def create_invoice(self, order_id: int) -> InvoiceRead:
        """Create a new invoice (Accountant) and log to outbox."""
        from app.models.outbox.outbox import Outbox
        db_invoice = self.repo.create_for_order(order_id)
        if not db_invoice:
            raise HTTPException(status_code=404, detail="Order not found")

        # Log to outbox
        outbox_event = Outbox(
            event_type="INVOICE_GENERATED",
            payload={"order_id": order_id, "invoice_id": db_invoice.id},
            processed=False
        )
        self.repo.db.add(outbox_event)
        self.repo.db.commit()
        return InvoiceRead.model_validate(db_invoice)
    def get_invoice(self, invoice_id: int) -> Optional[InvoiceRead]:
        """Get invoice by ID."""
        db_invoice = self.repo.get_by_id(invoice_id)
        if not db_invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceRead.model_validate(db_invoice)

    def update_invoice_status(self, invoice_id: int, status: InvoiceStatus) -> Optional[InvoiceRead]:
        """Update invoice status."""
        db_invoice = self.repo.update_status(invoice_id, status)
        if not db_invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceRead.model_validate(db_invoice)

    def list_invoices_by_order(self, order_id: int) -> list[InvoiceRead]:
        """List all invoices for an order."""
        db_invoices = self.repo.list_by_order(order_id)
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.invoice import InvoiceRepository
from app.models.invoice import InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceRead
from datetime import datetime, timedelta


class InvoiceService:
    """Invoice service with workflow logic."""

    def __init__(self, db: Session):
        self.repo = InvoiceRepository(db)

    def create_invoice(self, invoice: InvoiceCreate) -> InvoiceRead:
        """Create a new invoice (Accountant)."""
        db_invoice = self.repo.create(invoice)
        return InvoiceRead.model_validate(db_invoice)

    def verify_payment(self, invoice_id: int) -> InvoiceRead:
        """Verify payment for an invoice (Accountant)."""
        db_invoice = self.repo.update_status(invoice_id, InvoiceStatus.PAID)
        if not db_invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceRead.model_validate(db_invoice)

    def get_invoice(self, invoice_id: int) -> Optional[InvoiceRead]:
        """Get invoice by ID."""
        db_invoice = self.repo.get_by_id(invoice_id)
        if not db_invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceRead.model_validate(db_invoice)

    def update_invoice_status(self, invoice_id: int, status: InvoiceStatus) -> Optional[InvoiceRead]:
        """Update invoice status."""
        db_invoice = self.repo.update_status(invoice_id, status)
        if not db_invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceRead.model_validate(db_invoice)

    def list_invoices_by_order(self, order_id: int) -> list[InvoiceRead]:
        """List all invoices for an order."""
        db_invoices = self.repo.list_by_order(order_id)
        return [InvoiceRead.model_validate(invoice) for invoice in db_invoices]