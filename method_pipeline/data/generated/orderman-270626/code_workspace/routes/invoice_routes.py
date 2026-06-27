"""
Invoice Routes - API endpoints for Invoice operations.
Defines RESTful endpoints for invoice management and workflow.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.models import get_session
from controllers.invoice_controller import InvoiceController
from shared.models import (
    Invoice,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceListResponse,
    InvoiceStatus,
    APIResponse,
)

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    status: Optional[InvoiceStatus] = Query(None, description="Filter by invoice status"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    overdue: Optional[bool] = Query(None, description="Filter for overdue invoices only"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all invoices with pagination, optionally filtered by status, customer, or overdue.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **status**: Optional filter by invoice status
    - **customer_id**: Optional filter by customer ID
    - **overdue**: Optional filter for overdue invoices only
    """
    controller = InvoiceController(db)
    
    if overdue:
        return await controller.get_overdue_invoices(skip=skip, limit=limit)
    
    if customer_id:
        return await controller.get_invoices_by_customer(customer_id=customer_id, skip=skip, limit=limit)
    
    if status:
        return await controller.get_invoices_by_status(status=status, skip=skip, limit=limit)
    
    return await controller.get_all_invoices(skip=skip, limit=limit)


@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a specific invoice by ID.
    
    - **invoice_id**: The unique invoice identifier
    """
    controller = InvoiceController(db)
    invoice = await controller.get_invoice(invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


@router.get("/order/{order_id}", response_model=Invoice)
async def get_invoice_by_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Get an invoice by order ID.
    
    - **order_id**: The order identifier
    """
    controller = InvoiceController(db)
    invoice = await controller.get_invoice_by_order_id(order_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found for this order")
    
    return invoice


@router.get("/number/{invoice_number}", response_model=Invoice)
async def get_invoice_by_number(
    invoice_number: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get an invoice by invoice number.
    
    - **invoice_number**: Human-readable invoice number
    """
    controller = InvoiceController(db)
    invoice = await controller.get_invoice_by_number(invoice_number)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


@router.post("", response_model=Invoice, status_code=201)
async def create_invoice(
    invoice_data: InvoiceCreate,
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new invoice (Accountant action).
    
    - **order_id**: Associated order identifier
    - **customer_id**: Customer identifier
    - **amount**: Invoice amount (must be > 0)
    - **due_date**: Payment due date
    - **billing_address**: Billing address
    """
    controller = InvoiceController(db)
    
    try:
        return await controller.create_invoice(invoice_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{invoice_id}", response_model=Invoice)
async def update_invoice(
    invoice_id: int,
    invoice_data: InvoiceUpdate,
    db: AsyncSession = Depends(get_session),
):
    """
    Update an existing invoice.
    
    - **invoice_id**: The unique invoice identifier
    - **status**: Optional new status
    - **amount**: Optional new amount
    - **due_date**: Optional new due date
    - **billing_address**: Optional new billing address
    """
    controller = InvoiceController(db)
    
    invoice = await controller.update_invoice(invoice_id, invoice_data)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


@router.post("/{invoice_id}/pay", response_model=Invoice)
async def mark_invoice_paid(
    invoice_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Mark an invoice as paid.
    
    - **invoice_id**: The unique invoice identifier
    """
    controller = InvoiceController(db)
    
    invoice = await controller.mark_invoice_paid(invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


@router.post("/{invoice_id}/cancel", response_model=Invoice)
async def cancel_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Cancel an invoice.
    
    - **invoice_id**: The unique invoice identifier
    """
    controller = InvoiceController(db)
    
    try:
        invoice = await controller.cancel_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{invoice_id}", response_model=APIResponse)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Delete an invoice.
    
    - **invoice_id**: The unique invoice identifier
    """
    controller = InvoiceController(db)
    
    try:
        success = await controller.delete_invoice(invoice_id)
        if not success:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return APIResponse(success=True, message="Invoice deleted successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check-overdue", response_model=dict)
async def check_overdue_invoices(
    db: AsyncSession = Depends(get_session),
):
    """
    Check and update all overdue invoices.
    This should be called periodically (e.g., daily).
    """
    controller = InvoiceController(db)
    return await controller.check_overdue_invoices()
