"""
REST controller for Invoice entity.
Provides CRUD + workflow endpoints under /api/v1/invoices.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceUpdate
from app.services.invoice_service import InvoiceService
from app.workflows.order_workflow import OrderWorkflow

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


@router.post("/", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(data: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    """Accountant creates an invoice for an accepted order (step 3).
    Uses OrderWorkflow to create, issue, and update order status to INVOICED.
    """
    try:
        invoice = await OrderWorkflow.create_and_issue_invoice(
            db,
            order_id=data.order_id,
            billing_info=data.billing_info,
            issue_date=data.issue_date,
            due_date=data.due_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve an invoice by ID."""
    invoice = await InvoiceService.get_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/", response_model=List[InvoiceRead])
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List invoices with pagination."""
    invoices = await InvoiceService.get_all(db, skip=skip, limit=limit)
    return invoices


@router.get("/by-order/{order_id}", response_model=List[InvoiceRead])
async def get_invoices_by_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Get all invoices for a specific order."""
    invoices = await InvoiceService.get_by_order(db, order_id)
    return invoices


@router.post("/{invoice_id}/issue", response_model=InvoiceRead)
async def issue_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    """Issue a draft invoice (DRAFT -> ISSUED)."""
    try:
        invoice = await InvoiceService.issue_invoice(db, invoice_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceRead)
async def mark_invoice_paid(invoice_id: str, db: AsyncSession = Depends(get_db)):
    """Mark an invoice as paid (ISSUED -> PAID)."""
    try:
        invoice = await InvoiceService.mark_paid(db, invoice_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceRead)
async def update_invoice(invoice_id: str, data: InvoiceUpdate, db: AsyncSession = Depends(get_db)):
    """Update invoice fields."""
    invoice = await InvoiceService.update(db, invoice_id, data)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an invoice by ID."""
    deleted = await InvoiceService.delete(db, invoice_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Invoice not found")
