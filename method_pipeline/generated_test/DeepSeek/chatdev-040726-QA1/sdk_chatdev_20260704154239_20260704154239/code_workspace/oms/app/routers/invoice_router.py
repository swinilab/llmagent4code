"""
Routers for Invoice endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceStatusUpdate
from app.services.invoice_service import InvoiceService, InvoiceStateError

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


@router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db)):
    return InvoiceService.create(db, data)


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(
    order_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if order_id:
        return InvoiceService.list_by_order(db, order_id)
    return InvoiceService.list_all(db, skip=skip, limit=limit)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = InvoiceService.get_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/{invoice_id}/issue", response_model=InvoiceResponse)
def issue_invoice(invoice_id: str, db: Session = Depends(get_db)):
    try:
        invoice = InvoiceService.issue(db, invoice_id)
    except InvoiceStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
def update_invoice_status(invoice_id: str, data: InvoiceStatusUpdate, db: Session = Depends(get_db)):
    try:
        invoice = InvoiceService.update_status(db, invoice_id, data)
    except InvoiceStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    if not InvoiceService.delete(db, invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
