from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.app.db.session import get_db
from oms_backend.app.services import invoice_service
from oms_backend.app.schemas.invoice import InvoiceCreate, InvoiceUpdate, Invoice

router = APIRouter()

@router.get("/", response_model=list[Invoice])
def read_invoices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    invoices = invoice_service.get_invoices(db, skip=skip, limit=limit)
    return invoices

@router.post("/", response_model=Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice_in: InvoiceCreate, db: Session = Depends(get_db)):
    return invoice_service.create_invoice(db, invoice_in)

@router.get("/{invoice_id}", response_model=Invoice)
def read_invoice(invoice_id: int, db: Session = Depends(get_db)):
    db_obj = invoice_service.get_invoice(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_obj

@router.put("/{invoice_id}", response_model=Invoice)
def update_invoice(invoice_id: int, invoice_in: InvoiceUpdate, db: Session = Depends(get_db)):
    db_obj = invoice_service.get_invoice(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Invoice not found")
    updated = invoice_service.update_invoice(db, invoice_id, invoice_in)
    return updated

@router.delete("/{invoice_id}", response_model=Invoice)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    db_obj = invoice_service.get_invoice(db, invoice_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Invoice not found")
    deleted = invoice_service.delete_invoice(db, db_obj.id)
    return deleted