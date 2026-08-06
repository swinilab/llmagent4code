"""
Invoice controller
REST endpoints for invoice operations
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.infrastructure.database import get_db
from oms_backend.service import InvoiceService
from oms_backend.domain.models import Invoice, InvoiceCreate
from oms_backend.controller.responses import ErrorResponse
from oms_backend.utils.exceptions import OMSException, NotFoundException, ValidationException, ConflictException
from oms_backend.utils.rate_limiter import rate_limiter


router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post(
    "",
    response_model=Invoice,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Order not in ACCEPTED state"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Create a new invoice",
    description="Create a new invoice (Accountant creates invoice for accepted order). Order must be in ACCEPTED state.",
)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new invoice.
    NFR 1.1: Rate limiting applied.
    NFR 2.4: Transaction ensures ACID properties.
    """
    if not rate_limiter.is_allowed("create_invoice"):
        raise HTTPException(
            status_code=429,
            detail={"message": "Rate limit exceeded", "retry_after_seconds": 60}
        )
    
    service = InvoiceService(db)
    try:
        return service.create_invoice(data)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ConflictException as e:
        raise HTTPException(
            status_code=409,
            detail={"message": e.message, "current_state": e.current_state, "expected_state": e.expected_state}
        )
    except ValidationException as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "field": e.field})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.get(
    "",
    response_model=List[Invoice],
    summary="Get all invoices",
    description="Retrieve a list of all invoices.",
)
def get_all_invoices(db: Session = Depends(get_db)):
    """Get all invoices."""
    service = InvoiceService(db)
    return service.get_all_invoices()


@router.get(
    "/{invoice_id}",
    response_model=Invoice,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Invoice not found"},
    },
    summary="Get invoice by ID",
    description="Retrieve an invoice by their unique ID.",
)
def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Get invoice by ID."""
    try:
        uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = InvoiceService(db)
    try:
        return service.get_invoice(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.get(
    "/order/{order_id}",
    response_model=Optional[Invoice],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
    },
    summary="Get invoice by order",
    description="Retrieve the invoice for a specific order.",
)
def get_invoice_by_order(order_id: str, db: Session = Depends(get_db)):
    """Get invoice by order ID."""
    try:
        uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = InvoiceService(db)
    return service.get_invoice_by_order(uuid)


@router.post(
    "/{invoice_id}/mark-paid",
    response_model=Invoice,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Invoice not found"},
    },
    summary="Mark invoice as paid",
    description="Mark an invoice as paid. Transitions from ISSUED to PAID.",
)
def mark_invoice_paid(invoice_id: str, db: Session = Depends(get_db)):
    """Mark invoice as paid."""
    try:
        uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = InvoiceService(db)
    try:
        return service.mark_invoice_paid(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.post(
    "/{invoice_id}/mark-overdue",
    response_model=Invoice,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Invoice not found"},
    },
    summary="Mark invoice as overdue",
    description="Mark an invoice as overdue. Transitions to OVERDUE state.",
)
def mark_invoice_overdue(invoice_id: str, db: Session = Depends(get_db)):
    """Mark invoice as overdue."""
    try:
        uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = InvoiceService(db)
    try:
        return service.mark_invoice_overdue(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.post(
    "/{invoice_id}/cancel",
    response_model=Invoice,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Invoice not found"},
    },
    summary="Cancel invoice",
    description="Cancel an invoice. Transitions to CANCELLED state.",
)
def cancel_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Cancel invoice."""
    try:
        uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = InvoiceService(db)
    try:
        return service.cancel_invoice(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})
