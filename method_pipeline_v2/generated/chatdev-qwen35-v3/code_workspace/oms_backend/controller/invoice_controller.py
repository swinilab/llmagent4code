"""
Invoice REST API controller
Implements validation and workflow actions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from oms_backend.repository.base import get_db
from oms_backend.service.invoice_service import InvoiceService
from oms_backend.domain.schemas import InvoiceCreate, InvoiceResponse
from oms_backend.domain.models import Invoice, InvoiceStatus

invoice_router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


def invoice_to_response(invoice: Invoice) -> InvoiceResponse:
    """Convert Invoice model to response schema"""
    return InvoiceResponse(
        id=invoice.id,
        orderRef=invoice.order_ref,
        billingInfo=invoice.billing_info,
        totalAmount=float(invoice.total_amount),
        issueDate=invoice.issue_date,
        dueDate=invoice.due_date,
        status=invoice.status
    )


@invoice_router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    session: AsyncSession = Depends(get_db)
) -> InvoiceResponse:
    """Create a new invoice"""
    service = InvoiceService(session)
    try:
        invoice = await service.create_invoice(data)
        return invoice_to_response(invoice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@invoice_router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    session: AsyncSession = Depends(get_db)
) -> InvoiceResponse:
    """Get invoice by ID"""
    import uuid
    try:
        uuid.UUID(invoice_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = InvoiceService(session)
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice_to_response(invoice)


@invoice_router.get("/order/{order_ref}", response_model=InvoiceResponse)
async def get_invoice_by_order(
    order_ref: str,
    session: AsyncSession = Depends(get_db)
) -> InvoiceResponse:
    """Get invoice by order reference"""
    import uuid
    try:
        uuid.UUID(order_ref, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = InvoiceService(session)
    invoice = await service.get_invoice_by_order(order_ref)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice_to_response(invoice)


@invoice_router.get("", response_model=List[InvoiceResponse])
async def get_all_invoices(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
) -> List[InvoiceResponse]:
    """Get all invoices with pagination"""
    service = InvoiceService(session)
    invoices = await service.get_all_invoices(limit, offset)
    return [invoice_to_response(i) for i in invoices]


# Workflow endpoints
@invoice_router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: str,
    session: AsyncSession = Depends(get_db)
) -> InvoiceResponse:
    """Mark invoice as paid (ISSUED -> PAID)"""
    import uuid
    try:
        uuid.UUID(invoice_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = InvoiceService(session)
    try:
        invoice = await service.mark_invoice_paid(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice_to_response(invoice)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@invoice_router.post("/{invoice_id}/mark-overdue", response_model=InvoiceResponse)
async def mark_invoice_overdue(
    invoice_id: str,
    session: AsyncSession = Depends(get_db)
) -> InvoiceResponse:
    """Mark invoice as overdue (ISSUED -> OVERDUE)"""
    import uuid
    try:
        uuid.UUID(invoice_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = InvoiceService(session)
    try:
        invoice = await service.mark_invoice_overdue(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice_to_response(invoice)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@invoice_router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: str,
    session: AsyncSession = Depends(get_db)
) -> InvoiceResponse:
    """Cancel invoice (ISSUED/OVERDUE -> CANCELLED)"""
    import uuid
    try:
        uuid.UUID(invoice_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = InvoiceService(session)
    try:
        invoice = await service.cancel_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice_to_response(invoice)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
