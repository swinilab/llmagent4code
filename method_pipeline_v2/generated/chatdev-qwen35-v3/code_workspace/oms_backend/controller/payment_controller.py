"""
Payment REST API controller
Implements validation and workflow actions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from oms_backend.repository.base import get_db
from oms_backend.service.payment_service import PaymentService
from oms_backend.domain.schemas import PaymentCreate, PaymentResponse
from oms_backend.domain.models import Payment, PaymentStatus

payment_router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def payment_to_response(payment: Payment) -> PaymentResponse:
    """Convert Payment model to response schema"""
    return PaymentResponse(
        id=payment.id,
        orderRef=payment.order_ref,
        amount=float(payment.amount),
        timestamp=payment.timestamp,
        status=payment.status,
        method=payment.method
    )


@payment_router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentCreate,
    session: AsyncSession = Depends(get_db)
) -> PaymentResponse:
    """Create a new payment"""
    service = PaymentService(session)
    try:
        payment = await service.create_payment(data)
        return payment_to_response(payment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@payment_router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    session: AsyncSession = Depends(get_db)
) -> PaymentResponse:
    """Get payment by ID"""
    import uuid
    try:
        uuid.UUID(payment_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = PaymentService(session)
    payment = await service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment_to_response(payment)


@payment_router.get("", response_model=List[PaymentResponse])
async def get_all_payments(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
) -> List[PaymentResponse]:
    """Get all payments with pagination"""
    service = PaymentService(session)
    payments = await service.get_all_payments(limit, offset)
    return [payment_to_response(p) for p in payments]


@payment_router.get("/order/{order_ref}", response_model=List[PaymentResponse])
async def get_payments_by_order(
    order_ref: str,
    session: AsyncSession = Depends(get_db)
) -> List[PaymentResponse]:
    """Get all payments for an order"""
    import uuid
    try:
        uuid.UUID(order_ref, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = PaymentService(session)
    payments = await service.get_payments_by_order(order_ref)
    return [payment_to_response(p) for p in payments]


# Workflow endpoints
@payment_router.post("/{payment_id}/verify", response_model=PaymentResponse)
async def verify_payment(
    payment_id: str,
    session: AsyncSession = Depends(get_db)
) -> PaymentResponse:
    """Verify payment (Accountant action: PENDING -> VERIFIED)"""
    import uuid
    try:
        uuid.UUID(payment_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = PaymentService(session)
    try:
        payment = await service.verify_payment(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment_to_response(payment)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@payment_router.post("/{payment_id}/reject", response_model=PaymentResponse)
async def reject_payment(
    payment_id: str,
    session: AsyncSession = Depends(get_db)
) -> PaymentResponse:
    """Reject payment (PENDING -> REJECTED)"""
    import uuid
    try:
        uuid.UUID(payment_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    service = PaymentService(session)
    try:
        payment = await service.reject_payment(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment_to_response(payment)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
