"""
Invoice service handling creation and status updates.
"""

from sqlalchemy.orm import Session
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.invoice import InvoiceCreate

class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvoiceRepository()

    def create_invoice(self, payload: InvoiceCreate):
        return self.repo.create(self.db, payload.model_dump())

    def get_invoice(self, invoice_id: int):
        return self.repo.get(self.db, invoice_id)

    def update_status(self, invoice_id: int, status: str):
        invoice = self.repo.get(self.db, invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        return self.repo.update(self.db, invoice, {"status": status})
