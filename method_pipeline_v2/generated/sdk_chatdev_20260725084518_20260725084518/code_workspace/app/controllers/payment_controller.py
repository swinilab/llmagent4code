"""
Payment controller with REST endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal
from app.db.connection_pool import get_db
from app.services.payment_service import PaymentService, PaymentValidationError, PaymentTransitionError
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class PaymentCreateRequest(BaseModel):
    """Request model for creating a payment"""
    orderRef: str
    amount: Decimal = Field(..., ge=Decimal("0.01"), le=Decimal("99999999.99"))
    method: str


class PaymentResponse(BaseModel):
    """Response model for payment"""
    id: str
    orderRef: str
    amount: str
    timestamp: str
    status: str
    method: str


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(request: PaymentCreateRequest, session: AsyncSession = Depends(get_db)):
    """Create a new payment for an invoiced order"""
    service = PaymentService(session)
    try:
        payment = await service.create_payment(
            order_ref=request.orderRef,
            amount=request.amount,
            method=request.method,
        )
        return PaymentResponse(
            id=str(payment.id),
            orderRef=str(payment.orderRef),
            amount=str(payment.amount),
            timestamp=payment.timestamp.isoformat(),
            status=payment.status,
            method=payment.method,
        )
    except PaymentValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PaymentTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=List[PaymentResponse])
async def list_payments(limit: int = 100, offset: int = 0, session: AsyncSession = Depends(get_db)):
    """List all payments"""
    service = PaymentService(session)
    payments = await service.get_all_payments(limit, offset)
    return [
        PaymentResponse(
            id=str(p.id),
            orderRef=str(p.orderRef),
            amount=str(p.amount),
            timestamp=p.timestamp.isoformat(),
            status=p.status,
            method=p.method,
        )
        for p in payments
    ]


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, session: AsyncSession = Depends(get_db)):
    """Get payment by ID"""
    service = PaymentService(session)
    payment = await service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return PaymentResponse(
        id=str(payment.id),
        orderRef=str(payment.orderRef),
        amount=str(payment.amount),
        timestamp=payment.timestamp.isoformat(),
        status=payment.status,
        method=payment.method,
    )


@router.get("/order/{order_ref}", response_model=PaymentResponse)
async def get_payment_by_order(order_ref: str, session: AsyncSession = Depends(get_db)):
    """Get payment by order reference"""
    service = PaymentService(session)
    payment = await service.get_payment_by_order(order_ref)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for order")
    
    return PaymentResponse(
        id=str(payment.id),
        orderRef=str(payment.orderRef),
        amount=str(payment.amount),
        timestamp=payment.timestamp.isoformat(),
        status=payment.status,
        method=payment.method,
    )


@router.put("/{payment_id}/verify", response_model=PaymentResponse)
async def verify_payment(payment_id: str, session: AsyncSession = Depends(get_db)):
    """Verify payment (PENDING -> VERIFIED)"""
    service = PaymentService(session)
    try:
        payment = await service.verify_payment(payment_id)
        return PaymentResponse(
            id=str(payment.id),
            orderRef=str(payment.orderRef),
            amount=str(payment.amount),
            timestamp=payment.timestamp.isoformat(),
            status=payment.status,
            method=payment.method,
        )
    except PaymentValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PaymentTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{payment_id}/reject", response_model=PaymentResponse)
async def reject_payment(payment_id: str, session: AsyncSession = Depends(get_db)):
    """Reject payment (PENDING -> REJECTED)"""
    service = PaymentService(session)
    try:
        payment = await service.reject_payment(payment_id)
        return PaymentResponse(
            id=str(payment.id),
            orderRef=str(payment.orderRef),
            amount=str(payment.amount),
            timestamp=payment.timestamp.isoformat(),
            status=payment.status,
            method=payment.method,
        )
    except PaymentValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PaymentTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
