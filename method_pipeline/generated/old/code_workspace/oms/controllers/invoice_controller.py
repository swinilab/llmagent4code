"""
Invoice controller for handling invoice-related HTTP requests.

Provides REST API endpoints for invoice management.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from oms.config.database import get_db_session
from oms.models.entities import InvoiceStatus
from oms.models.schemas import (
    InvoiceCreate,
    InvoiceResponse,
    ErrorResponse,
)
from oms.services.invoice_service import InvoiceService

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


def get_service(session=Depends(get_db_session)) -> InvoiceService:
    """Dependency injection for InvoiceService."""
    return InvoiceService(session)


@router.post(
    "",
    response_model=InvoiceResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Create a new invoice",
    description="Accountant creates an invoice for an accepted order.",
)
async def create_invoice(
    invoice_data: InvoiceCreate,
    service: InvoiceService = Depends(get_service),
) -> InvoiceResponse:
    """
    Create a new invoice for an order (Accountant action).
    
    Args:
        invoice_data: Invoice creation data
        service: Invoice service instance
        
    Returns:
        Created invoice response
        
    Raises:
        HTTPException: If order not found or not in correct status
    """
    try:
        return await service.create_invoice(invoice_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=List[InvoiceResponse],
    summary="Get all invoices",
    description="Retrieve all invoices.",
)
async def get_all_invoices(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: InvoiceService = Depends(get_service),
) -> List[InvoiceResponse]:
    """
    Get all invoices with pagination.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Invoice service instance
        
    Returns:
        List of invoices
    """
    return await service.get_all_invoices(limit=limit, offset=offset)


@router.get(
    "/overdue",
    response_model=List[InvoiceResponse],
    summary="Get overdue invoices",
    description="Retrieve all overdue invoices.",
)
async def get_overdue_invoices(
    limit: int = Query(default=100, ge=1, le=1000),
    service: InvoiceService = Depends(get_service),
) -> List[InvoiceResponse]:
    """
    Get all overdue invoices.
    
    Args:
        limit: Maximum number of records to return
        service: Invoice service instance
        
    Returns:
        List of overdue invoices
    """
    return await service.get_overdue_invoices(limit=limit)


@router.get(
    "/status/{status}",
    response_model=List[InvoiceResponse],
    summary="Get invoices by status",
    description="Retrieve invoices filtered by status.",
)
async def get_invoices_by_status(
    status: InvoiceStatus,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: InvoiceService = Depends(get_service),
) -> List[InvoiceResponse]:
    """
    Get invoices by status.
    
    Args:
        status: Invoice status to filter by
        limit: Maximum number of records to return
        offset: Number of records to skip
        service: Invoice service instance
        
    Returns:
        List of invoices with the specified status
    """
    return await service.get_invoices_by_status(status, limit=limit, offset=offset)


@router.get(
    "/order/{order_id}",
    response_model=InvoiceResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get invoice by order ID",
    description="Retrieve the invoice for a specific order.",
)
async def get_invoice_by_order(
    order_id: int,
    service: InvoiceService = Depends(get_service),
) -> InvoiceResponse:
    """
    Get invoice by order ID.
    
    Args:
        order_id: Order ID
        service: Invoice service instance
        
    Returns:
        Invoice response
        
    Raises:
        HTTPException: If invoice not found
    """
    invoice = await service.get_invoice_by_order(order_id)
    if invoice is None:
        raise HTTPException(
            status_code=404, detail=f"Invoice for order {order_id} not found"
        )
    return invoice


@router.get(
    "/number/{invoice_number}",
    response_model=InvoiceResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get invoice by number",
    description="Retrieve an invoice by its unique number.",
)
async def get_invoice_by_number(
    invoice_number: str,
    service: InvoiceService = Depends(get_service),
) -> InvoiceResponse:
    """
    Get invoice by invoice number.
    
    Args:
        invoice_number: Unique invoice number
        service: Invoice service instance
        
    Returns:
        Invoice response
        
    Raises:
        HTTPException: If invoice not found
    """
    invoice = await service.get_invoice_by_number(invoice_number)
    if invoice is None:
        raise HTTPException(
            status_code=404, detail=f"Invoice {invoice_number} not found"
        )
    return invoice


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get invoice by ID",
    description="Retrieve a specific invoice by its ID.",
)
async def get_invoice(
    invoice_id: int,
    service: InvoiceService = Depends(get_service),
) -> InvoiceResponse:
    """
    Get invoice by ID.
    
    Args:
        invoice_id: Invoice ID
        service: Invoice service instance
        
    Returns:
        Invoice response
        
    Raises:
        HTTPException: If invoice not found
    """
    invoice = await service.get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return invoice


@router.post(
    "/{invoice_id}/mark-paid",
    response_model=InvoiceResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Mark invoice as paid",
    description="Mark an invoice as paid.",
)
async def mark_invoice_paid(
    invoice_id: int,
    service: InvoiceService = Depends(get_service),
) -> InvoiceResponse:
    """
    Mark an invoice as paid.
    
    Args:
        invoice_id: Invoice ID
        service: Invoice service instance
        
    Returns:
        Updated invoice response
        
    Raises:
        HTTPException: If invoice not found
    """
    invoice = await service.mark_invoice_paid(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return invoice


@router.post(
    "/{invoice_id}/mark-overdue",
    response_model=InvoiceResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Mark invoice as overdue",
    description="Mark an invoice as overdue.",
)
async def mark_invoice_overdue(
    invoice_id: int,
    service: InvoiceService = Depends(get_service),
) -> InvoiceResponse:
    """
    Mark an invoice as overdue.
    
    Args:
        invoice_id: Invoice ID
        service: Invoice service instance
        
    Returns:
        Updated invoice response
        
    Raises:
        HTTPException: If invoice not found
    """
    invoice = await service.mark_invoice_overdue(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return invoice


@router.post(
    "/{invoice_id}/cancel",
    response_model=InvoiceResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Cancel invoice",
    description="Cancel an invoice.",
)
async def cancel_invoice(
    invoice_id: int,
    service: InvoiceService = Depends(get_service),
) -> InvoiceResponse:
    """
    Cancel an invoice.
    
    Args:
        invoice_id: Invoice ID
        service: Invoice service instance
        
    Returns:
        Updated invoice response
        
    Raises:
        HTTPException: If invoice not found or already paid
    """
    try:
        invoice = await service.cancel_invoice(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/check-overdue",
    response_model=dict,
    summary="Check and update overdue invoices",
    description="Check all issued invoices and update overdue status.",
)
async def check_and_update_overdue(
    service: InvoiceService = Depends(get_service),
) -> dict:
    """
    Check all issued invoices and update overdue status.
    
    Args:
        service: Invoice service instance
        
    Returns:
        Number of invoices updated
    """
    count = await service.check_and_update_overdue()
    return {"updated_count": count}


@router.get(
    "/analytics/total-invoiced",
    response_model=dict,
    summary="Get total invoiced amount",
    description="Get total invoiced amount.",
)
async def get_total_invoiced(
    service: InvoiceService = Depends(get_service),
) -> dict:
    """
    Get total invoiced amount.
    
    Args:
        service: Invoice service instance
        
    Returns:
        Total invoiced amount
    """
    amount = await service.get_total_invoiced_amount()
    return {"total_invoiced": amount}


@router.get(
    "/analytics/total-paid",
    response_model=dict,
    summary="Get total paid invoice amount",
    description="Get total paid invoice amount.",
)
async def get_total_paid_invoices(
    service: InvoiceService = Depends(get_service),
) -> dict:
    """
    Get total paid invoice amount.
    
    Args:
        service: Invoice service instance
        
    Returns:
        Total paid amount
    """
    amount = await service.get_total_paid_amount()
    return {"total_paid": amount}
