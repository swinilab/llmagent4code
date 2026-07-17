"""
Invoice REST API controller.
Handles HTTP requests for invoice operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from oms.config.database import get_db
from oms.models.invoice import InvoiceCreate, InvoiceUpdate, InvoiceIssueRequest, InvoiceResponse, InvoiceStatus
from oms.services.invoice_service import InvoiceService

invoice_router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@invoice_router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: InvoiceStatus = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all invoices with optional filters."""
    service = InvoiceService(db)
    if status:
        return await service.get_invoices_by_status(status, skip=skip, limit=limit)
    return await service.get_all_invoices(skip=skip, limit=limit)


@invoice_router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Get an invoice by ID."""
    service = InvoiceService(db)
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@invoice_router.get("/order/{order_id}", response_model=InvoiceResponse)
async def get_invoice_by_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Get an invoice by order ID."""
    service = InvoiceService(db)
    invoice = await service.get_invoice_by_order_id(order_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@invoice_router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(invoice_data: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    """
    Create an invoice for an accepted order (Accountant workflow step 3).
    """
    service = InvoiceService(db)
    try:
        return await service.create_invoice(invoice_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@invoice_router.post("/{invoice_id}/issue", response_model=InvoiceResponse)
async def issue_invoice(
    invoice_id: int,
    issue_data: Optional[InvoiceIssueRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """Issue an invoice."""
    service = InvoiceService(db)
    issue_date = issue_data.issue_date if issue_data else None
    due_date = issue_data.due_date if issue_data else None
    invoice = await service.issue_invoice(invoice_id, issue_date, due_date)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@invoice_router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an invoice as paid."""
    service = InvoiceService(db)
    invoice = await service.mark_invoice_paid(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@invoice_router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Cancel an invoice."""
    service = InvoiceService(db)
    invoice = await service.cancel_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@invoice_router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(invoice_id: int, invoice_data: InvoiceUpdate, db: AsyncSession = Depends(get_db)):
    """Update an invoice."""
    service = InvoiceService(db)
    update_data = invoice_data.model_dump(exclude_unset=True)
    invoice = await service.update_invoice(invoice_id, **update_data)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@invoice_router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an invoice."""
    service = InvoiceService(db)
    deleted = await service.delete_invoice(invoice_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return None


@invoice_router.get("/count")
async def get_invoice_count(db: AsyncSession = Depends(get_db)):
    """Get total number of invoices."""
    service = InvoiceService(db)
    return {"count": await service.get_invoice_count()}
