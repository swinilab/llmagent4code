from sqlalchemy.orm import Session
from oms_backend.app.models.invoice import Invoice, InvoiceStatus
from oms_backend.app.schemas.invoice import InvoiceCreate, InvoiceUpdate

def get_invoice(db: Session, invoice_id: int):
    return db.query(Invoice).filter(Invoice.id == invoice_id).first()

def get_invoices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Invoice).offset(skip).limit(limit).all()

def create_invoice(db: Session, invoice: InvoiceCreate):
    db_invoice = Invoice(**invoice.dict())
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def update_invoice(db: Session, invoice_id: int, invoice: InvoiceUpdate):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if db_invoice:
        update_data = invoice.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_invoice, field, value)
        db.commit()
        db.refresh(db_invoice)
    return db_invoice

def delete_invoice(db: Session, invoice_id: int):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if db_invoice:
        db.delete(db_invoice)
        db.commit()
    return db_invoice