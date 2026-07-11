"""
Invoice REST router.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from oms.database import get_db
from oms.schemas.invoice import InvoiceCreate, InvoiceResponse
from oms.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


@router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    try:
        invoice = service.create_invoice(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/by-order/{order_id}", response_model=List[InvoiceResponse])
def list_invoices_by_order(order_id: str, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    return service.list_by_order(order_id)


@router.get("", response_model=List[InvoiceResponse])
def list_invoices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    return service.list_all(skip, limit)
