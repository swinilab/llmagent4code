"""
Invoice Controller - REST endpoints for invoice management.
Workflow: create invoice -> issue -> customer pays -> accountant verifies
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from ..infrastructure.database import get_db
from ..services.invoice_service import InvoiceService, InvoiceWorkflowError
from ..domain.models import Address, InvoiceStatus

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


class AddressModel(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str


class CreateInvoiceRequest(BaseModel):
    order_id: str
    customer_id: str
    billing_address: AddressModel
    due_date_days: int = Field(default=30, ge=1)
    idempotency_key: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: str
    order_id: str
    customer_id: str
    billing_address: Optional[dict]
    subtotal: float
    tax: float
    total: float
    currency: str
    status: str
    issue_date: str
    due_date: Optional[str]
    paid_date: Optional[str]
    created_at: str
    updated_at: str


def _to_response(invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        order_id=invoice.order_id,
        customer_id=invoice.customer_id,
        billing_address=invoice.billing_address.to_dict() if invoice.billing_address else None,
        subtotal=invoice.subtotal,
        tax=invoice.tax,
        total=invoice.total,
        currency=invoice.currency,
        status=invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
        issue_date=invoice.issue_date.isoformat(),
        due_date=invoice.due_date.isoformat() if invoice.due_date else None,
        paid_date=invoice.paid_date.isoformat() if invoice.paid_date else None,
        created_at=invoice.created_at.isoformat(),
        updated_at=invoice.updated_at.isoformat()
    )


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    request: CreateInvoiceRequest,
    db: Session = Depends(get_db)
):
    """Step 3: Accountant creates invoice for accepted order."""
    service = InvoiceService(db)
    
    try:
        billing_address = Address.from_dict(request.billing_address.dict())
        
        invoice = service.create_invoice(
            order_id=request.order_id,
            customer_id=request.customer_id,
            billing_address=billing_address,
            due_date_days=request.due_date_days,
            idempotency_key=request.idempotency_key
        )
        return _to_response(invoice)
    except InvoiceWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Get invoice by ID."""
    service = InvoiceService(db)
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _to_response(invoice)


@router.get("/by-order/{order_id}", response_model=InvoiceResponse)
def get_invoice_by_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Get invoice for an order."""
    service = InvoiceService(db)
    invoice = service.get_invoice_by_order(order_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _to_response(invoice)


@router.patch("/{invoice_id}/issue", response_model=InvoiceResponse)
def issue_invoice(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Issue a draft invoice (change status to issued)."""
    service = InvoiceService(db)
    try:
        invoice = service.issue_invoice(invoice_id)
        return _to_response(invoice)
    except InvoiceWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
def mark_invoice_paid(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Mark invoice as paid."""
    service = InvoiceService(db)
    try:
        invoice = service.mark_invoice_paid(invoice_id)
        return _to_response(invoice)
    except InvoiceWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{invoice_id}/mark-overdue", response_model=InvoiceResponse)
def mark_invoice_overdue(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Mark an issued invoice as overdue."""
    service = InvoiceService(db)
    try:
        invoice = service.mark_invoice_overdue(invoice_id)
        return _to_response(invoice)
    except InvoiceWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a draft or issued invoice."""
    service = InvoiceService(db)
    try:
        invoice = service.cancel_invoice(invoice_id)
        return _to_response(invoice)
    except InvoiceWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[InvoiceResponse])
def list_invoices(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List invoices with optional customer filter."""
    service = InvoiceService(db)
    
    if customer_id:
        invoices = service.get_invoices_by_customer(customer_id, skip=skip, limit=limit)
    else:
        invoices = service.repo.get_all(skip=skip, limit=limit)
    
    return [_to_response(i) for i in invoices]


@router.get("/outstanding/list", response_model=List[InvoiceResponse])
def list_outstanding_invoices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all outstanding (issued or overdue) invoices."""
    service = InvoiceService(db)
    invoices = service.get_outstanding_invoices(skip=skip, limit=limit)
    return [_to_response(i) for i in invoices]
