"""
Invoice REST controller.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.invoice import InvoiceService
from app.models.invoice import InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceRead
from app.db.session import get_db

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceRead)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice."""
    service = InvoiceService(db)
    return service.create_invoice(invoice)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def read_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Get invoice by ID."""
    service = InvoiceService(db)
    return service.get_invoice(invoice_id)


@router.patch("/{invoice_id}/status", response_model=InvoiceRead)
def update_invoice_status(invoice_id: int, status: InvoiceStatus, db: Session = Depends(get_db)):
    """Update invoice status."""
    service = InvoiceService(db)
    return service.update_invoice_status(invoice_id, status)


@router.get("/order/{order_id}", response_model=list[InvoiceRead])
def read_invoices_by_order(order_id: int, db: Session = Depends(get_db)):
    """List all invoices for an order."""
    service = InvoiceService(db)
"""
@router.post("", response_model=InvoiceRead)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice (Accountant)."""
    service = InvoiceService(db)
    return service.create_invoice(invoice)


@router.patch("/{invoice_id}/verify", response_model=InvoiceRead)
def verify_invoice_payment(invoice_id: int, db: Session = Depends(get_db)):
    """Verify payment for an invoice (Accountant)."""
    service = InvoiceService(db)
    return service.verify_payment(invoice_id)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def read_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Get invoice by ID."""
    service = InvoiceService(db)
    return service.get_invoice(invoice_id)


@router.patch("/{invoice_id}/status", response_model=InvoiceRead)
def update_invoice_status(invoice_id: int, status: InvoiceStatus, db: Session = Depends(get_db)):
    """Update invoice status."""
    service = InvoiceService(db)
    return service.update_invoice_status(invoice_id, status)


@router.get("/order/{order_id}", response_model=list[InvoiceRead])
def read_invoices_by_order(order_id: int, db: Session = Depends(get_db)):
    """List all invoices for an order."""
    service = InvoiceService(db)
    return service.list_invoices_by_order(order_id)