"""
Payment controller for handling payment-related HTTP requests.

Provides REST API endpoints for payment processing and verification.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from oms.config.database import get_db_session
from oms.models.schemas import (
    PaymentCreate,
    PaymentResponse,
    ErrorResponse,
)
from oms.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def get_service(session=Depends(get_db_session)) -> PaymentService:
    """Dependency injection for PaymentService."""
    return PaymentService(session)


@router.post(
    "",
    response_model=PaymentResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Create a new payment",
    description="Customer makes a payment for an order.",
)
async def create_payment(
    payment_data: PaymentCreate,
    service: PaymentService = Depends(get_service),
) -> PaymentResponse:
    """
    Create a new payment for an order.
    
    Args:
        payment_data: Payment creation data
        service: Payment service instance
        
    Returns:
        Created payment response
        
    Raises:
        HTTPException: If order not found or not in correct status
    """
    try:
        return await service.create_payment(payment_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=List[PaymentResponse],
    summary="Get pending payments",
    description="Retrieve all pending payments awaiting verification.",
)
async def get_pending_payments(
    limit: int = Query(default=100, ge=1, le=1000),
    service: PaymentService = Depends(get_service),
) -> List[PaymentResponse]:
    """
    Get all pending payments awaiting verification.
    
    Args:
        limit: Maximum number of records to return
        service: Payment service instance
        
    Returns:
        List of pending payments
    """
    return await service.get_pending_payments(limit=limit)


@router.get(
    "/order/{order_id}",
    response_model=List[PaymentResponse],
    summary="Get payments by order",
    description="Retrieve all payments for a specific order.",
)
async def get_payments_by_order(
    order_id: int,
    service: PaymentService = Depends(get_service),
) -> List[PaymentResponse]:
    """
    Get all payments for an order.
    
    Args:
        order_id: Order ID
        service: Payment service instance
        
    Returns:
        List of payments for the order
    """
    return await service.get_payments_by_order(order_id)


@router.get(
    "/transaction/{transaction_id}",
    response_model=PaymentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get payment by transaction ID",
    description="Retrieve a payment by external transaction ID.",
)
async def get_payment_by_transaction(
    transaction_id: str,
    service: PaymentService = Depends(get_service),
) -> PaymentResponse:
    """
    Get payment by transaction ID.
    
    Args:
        transaction_id: External transaction ID
        service: Payment service instance
        
    Returns:
        Payment response
        
    Raises:
        HTTPException: If payment not found
    """
    payment = await service.get_payment_by_transaction(transaction_id)
    if payment is None:
        raise HTTPException(
            status_code=404, detail=f"Payment with transaction {transaction_id} not found"
        )
    return payment


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get payment by ID",
    description="Retrieve a specific payment by its ID.",
)
async def get_payment(
    payment_id: int,
    service: PaymentService = Depends(get_service),
) -> PaymentResponse:
    """
    Get payment by ID.
    
    Args:
        payment_id: Payment ID
        service: Payment service instance
        
    Returns:
        Payment response
        
    Raises:
        HTTPException: If payment not found
    """
    payment = await service.get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    return payment


@router.post(
    "/{payment_id}/verify",
    response_model=PaymentResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Verify payment",
    description="Accountant verifies and completes a payment.",
)
async def verify_payment(
    payment_id: int,
    service: PaymentService = Depends(get_service),
) -> PaymentResponse:
    """
    Verify and complete a payment (Accountant action).
    
    Args:
        payment_id: Payment ID
        service: Payment service instance
        
    Returns:
        Updated payment response
        
    Raises:
        HTTPException: If payment not found or not in PENDING status
    """
    try:
        payment = await service.verify_payment(payment_id)
        if payment is None:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{payment_id}/fail",
    response_model=PaymentResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Fail payment",
    description="Mark a payment as failed.",
)
async def fail_payment(
    payment_id: int,
    reason: str = Query(None, description="Failure reason"),
    service: PaymentService = Depends(get_service),
) -> PaymentResponse:
    """
    Mark a payment as failed.
    
    Args:
        payment_id: Payment ID
        reason: Optional failure reason
        service: Payment service instance
        
    Returns:
        Updated payment response
        
    Raises:
        HTTPException: If payment not found
    """
    payment = await service.fail_payment(payment_id, reason)
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    return payment


@router.post(
    "/{payment_id}/refund",
    response_model=PaymentResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Refund payment",
    description="Refund a completed payment.",
)
async def refund_payment(
    payment_id: int,
    service: PaymentService = Depends(get_service),
) -> PaymentResponse:
    """
    Refund a completed payment.
    
    Args:
        payment_id: Payment ID
        service: Payment service instance
        
    Returns:
        Updated payment response
        
    Raises:
        HTTPException: If payment not found or not completed
    """
    try:
        payment = await service.refund_payment(payment_id)
        if payment is None:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/order/{order_id}/total-paid",
    response_model=dict,
    summary="Get total paid amount for order",
    description="Get total paid amount for a specific order.",
)
async def get_total_paid_amount(
    order_id: int,
    service: PaymentService = Depends(get_service),
) -> dict:
    """
    Get total paid amount for an order.
    
    Args:
        order_id: Order ID
        service: Payment service instance
        
    Returns:
        Total paid amount
    """
    amount = await service.get_total_paid_amount(order_id)
    return {"order_id": order_id, "total_paid": amount}
