"""
Payment controller
REST endpoints for payment operations
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.infrastructure.database import get_db
from oms_backend.service import PaymentService
from oms_backend.domain.models import Payment, PaymentCreate
from oms_backend.controller.responses import ErrorResponse
from oms_backend.utils.exceptions import OMSException, NotFoundException, ValidationException, ConflictException
from oms_backend.utils.rate_limiter import rate_limiter


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "",
    response_model=Payment,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Order not in payable state"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Create a new payment",
    description="Create a new payment (Customer pays invoice). Order must be in INVOICED state.",
)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new payment.
    NFR 1.1: Rate limiting applied.
    NFR 2.4: Transaction ensures ACID properties.
    """
    if not rate_limiter.is_allowed("create_payment"):
        raise HTTPException(
            status_code=429,
            detail={"message": "Rate limit exceeded", "retry_after_seconds": 60}
        )
    
    service = PaymentService(db)
    try:
        return service.create_payment(data)
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
    response_model=List[Payment],
    summary="Get all payments",
    description="Retrieve a list of all payments.",
)
def get_all_payments(db: Session = Depends(get_db)):
    """Get all payments."""
    service = PaymentService(db)
    return service.get_all_payments()


@router.get(
    "/{payment_id}",
    response_model=Payment,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Payment not found"},
    },
    summary="Get payment by ID",
    description="Retrieve a payment by their unique ID.",
)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    """Get payment by ID."""
    try:
        uuid = UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = PaymentService(db)
    try:
        return service.get_payment(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.get(
    "/order/{order_id}",
    response_model=List[Payment],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
    },
    summary="Get payments by order",
    description="Retrieve all payments for a specific order.",
)
def get_payments_by_order(order_id: str, db: Session = Depends(get_db)):
    """Get payments by order ID."""
    try:
        uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = PaymentService(db)
    return service.get_payments_by_order(uuid)


@router.post(
    "/{payment_id}/verify",
    response_model=Payment,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Payment not found"},
        409: {"model": ErrorResponse, "description": "Payment not in PENDING state"},
    },
    summary="Verify payment",
    description="Accountant verifies payment. Transitions from PENDING to VERIFIED.",
)
def verify_payment(payment_id: str, db: Session = Depends(get_db)):
    """Verify payment (Accountant action)."""
    try:
        uuid = UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = PaymentService(db)
    try:
        return service.verify_payment(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ConflictException as e:
        raise HTTPException(
            status_code=409,
            detail={"message": e.message, "current_state": e.current_state, "expected_state": e.expected_state}
        )
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.post(
    "/{payment_id}/reject",
    response_model=Payment,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Payment not found"},
    },
    summary="Reject payment",
    description="Reject a payment. Transitions to REJECTED state.",
)
def reject_payment(payment_id: str, db: Session = Depends(get_db)):
    """Reject payment."""
    try:
        uuid = UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = PaymentService(db)
    try:
        return service.reject_payment(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})
