"""
Payment REST endpoints (v1).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from oms.domain.models import Payment, CreatePaymentRequest, AccountantActionRequest
from oms.service.payment_service import PaymentService
from oms.api.deps import get_payment_service

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=Payment, status_code=status.HTTP_201_CREATED)
def create_payment(
    request: CreatePaymentRequest,
    service: PaymentService = Depends(get_payment_service),
) -> Payment:
    """Step 4: Customer pays an invoice."""
    try:
        return service.create_payment(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{payment_id}/verify", response_model=Payment)
def verify_payment(
    payment_id: UUID,
    request: AccountantActionRequest,
    service: PaymentService = Depends(get_payment_service),
) -> Payment:
    """Step 5: Accountant verifies a payment."""
    try:
        return service.verify_payment(payment_id, request.accountant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[Payment])
def list_payments(
    order_id: UUID | None = None,
    service: PaymentService = Depends(get_payment_service),
) -> list[Payment]:
    """List payments, optionally filtered by order_id."""
    if order_id:
        return service.get_by_order(order_id)
    return service.list_all()


@router.get("/{payment_id}", response_model=Payment)
def get_payment(
    payment_id: UUID,
    service: PaymentService = Depends(get_payment_service),
) -> Payment:
    """Get a payment by ID."""
    payment = service.get_by_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment
