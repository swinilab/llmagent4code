"""
Invoice repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceCreate


class InvoiceRepository:
    """Invoice repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, invoice: InvoiceCreate) -> Invoice:
        """Create a new invoice."""
        db_invoice = Invoice(**invoice.model_dump())
        self.db.add(db_invoice)
        self.db.commit()
        self.db.refresh(db_invoice)
        return db_invoice

    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID."""
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def update_status(self, invoice_id: int, status: InvoiceStatus) -> Optional[Invoice]:
        """Update invoice status."""
        db_invoice = self.get_by_id(invoice_id)
        if db_invoice:
            db_invoice.status = status
            self.db.commit()
            self.db.refresh(db_invoice)
        return db_invoice

    def list_by_order(self, order_id: int) -> list[Invoice]:
        """List all invoices for an order."""
        return self.db.query(Invoice).filter(Invoice.order_id == order_id).all()