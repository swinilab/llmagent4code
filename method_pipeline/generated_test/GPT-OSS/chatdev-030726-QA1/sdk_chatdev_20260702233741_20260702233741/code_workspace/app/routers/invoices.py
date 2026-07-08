# app/routers/invoices.py
"""Invoice endpoints (read‑only for demo)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, services, database

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])

def get_invoice_service(db: Session = Depends(database.get_db)):
    return services.InvoiceService(db)

@router.get("/{invoice_id}", response_model=schemas.InvoiceRead)
def get_invoice(invoice_id: int, svc: services.InvoiceService = Depends(get_invoice_service)):
    inv = svc.get_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv
