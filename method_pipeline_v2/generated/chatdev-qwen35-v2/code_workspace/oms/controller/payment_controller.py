"""
Payment controller with REST endpoints
Implements NFR 2.1 Exception Detection via validation and error handling
Implements NFR 2.4 Transactions via service layer
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from oms.infrastructure.database import get_async_session
from oms.service.payment_service import PaymentService
from oms.domain.models import Payment, PaymentCreate, PaymentVerify, PaymentStatus
from oms.infrastructure.exceptions import NotFoundException, ConflictException
from oms.infrastructure.event.rate_limiter import RateLimiter

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

def get_payment_service(session: AsyncSession = Depends(get_async_session)) -> PaymentService:
    """Get payment service instance"""
    return PaymentService(session)

@router.get("", response_model=List[Payment])
async def list_payments(
    service: PaymentService = Depends(get_payment_service)
):
    """List all payments"""
    return await service.get_all()

@router.get("/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: str,
    service: PaymentService = Depends(get_payment_service)
):
    """Get payment by ID"""
    return await service.get_by_id(payment_id)

@router.get("/order/{order_id}", response_model=List[Payment])
async def get_payments_by_order(
    order_id: str,
    service: PaymentService = Depends(get_payment_service)
):
    """Get payments by order ID"""
    return await service.get_by_order(order_id)

@router.post("", response_model=Payment, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment: PaymentCreate,
    service: PaymentService = Depends(get_payment_service)
):
    """
    Create new payment (Customer)
    NFR 1.1: Rate limited
    NFR 2.4: Transactional
    """
    # Check rate limit (NFR 1.1)
    rate_limiter = RateLimiter.get_instance()
    if not await rate_limiter.is_allowed("payment_create"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return await service.create(payment)

@router.put("/{payment_id}/verify", response_model=Payment)
async def verify_payment(
    payment_id: str,
    verify: PaymentVerify,
    service: PaymentService = Depends(get_payment_service)
):
    """
    Verify payment (Accountant only)
    NFR 2.4: Transactional state update
    """
    return await service.verify_payment(payment_id, verify)

@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: str,
    service: PaymentService = Depends(get_payment_service)
):
    """Delete payment"""
    success = await service.delete(payment_id)
    if not success:
        raise NotFoundException(f"Payment {payment_id} not found")

payment_router = router
