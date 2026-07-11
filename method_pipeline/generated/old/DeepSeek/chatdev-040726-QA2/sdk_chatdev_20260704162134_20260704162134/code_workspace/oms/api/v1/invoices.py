"""
Invoice REST endpoints (v1).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from oms.domain.models import Invoice, CreateInvoiceRequest
from oms.service.invoice_service import InvoiceService
from oms.api.deps import get_invoice_service

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.post("", response_model=Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(
    request: CreateInvoiceRequest,
    service: InvoiceService = Depends(get_invoice_service),
) -> Invoice:
    """Step 3: Accountant creates an invoice for an accepted order."""
    try:
        return service.create_invoice(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{invoice_id}/mark-overdue", response_model=Invoice)
def mark_invoice_overdue(
    invoice_id: UUID,
    service: InvoiceService = Depends(get_invoice_service),
) -> Invoice:
    """Mark an issued invoice as overdue if past due date."""
    try:
        return service.mark_overdue(invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[Invoice])
def list_invoices(
    order_id: UUID | None = None,
    service: InvoiceService = Depends(get_invoice_service),
) -> list[Invoice]:
    """List invoices, optionally filtered by order_id."""
    if order_id:
        return service.get_by_order(order_id)
    return service.list_all()


@router.get("/{invoice_id}", response_model=Invoice)
def get_invoice(
    invoice_id: UUID,
    service: InvoiceService = Depends(get_invoice_service),
) -> Invoice:
    """Get an invoice by ID."""
    invoice = service.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice
