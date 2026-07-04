"""
Invoice API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.invoice import InvoiceCreate, InvoiceOut
from app.services.invoice_service import InvoiceService
from app.controllers.dependencies import get_db

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("/", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    return service.create_invoice(payload)

@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.patch("/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(invoice_id: int, status: str, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    try:
        invoice = service.update_status(invoice_id, status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return invoice
