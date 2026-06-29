"""
Payment Routes - API endpoints for Payment operations.
Defines RESTful endpoints for payment management and workflow.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.models import get_session
from controllers.payment_controller import PaymentController
from shared.models import (
    Payment,
    PaymentCreate,
    PaymentUpdate,
    PaymentListResponse,
    PaymentStatus,
    APIResponse,
)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all payments with pagination, optionally filtered by status, customer, or invoice.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **status**: Optional filter by payment status
    - **customer_id**: Optional filter by customer ID
    - **invoice_id**: Optional filter by invoice ID
    """
    controller = PaymentController(db)
    
    if invoice_id:
        return await controller.get_payments_by_invoice(invoice_id=invoice_id, skip=skip, limit=limit)
    
    if customer_id:
        return await controller.get_payments_by_customer(customer_id=customer_id, skip=skip, limit=limit)
    
    if status:
        return await controller.get_payments_by_status(status=status, skip=skip, limit=limit)
    
    return await controller.get_all_payments(skip=skip, limit=limit)


@router.get("/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a specific payment by ID.
    
    - **payment_id**: The unique payment identifier
    """
    controller = PaymentController(db)
    payment = await controller.get_payment(payment_id)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return payment


@router.post("", response_model=Payment, status_code=201)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new payment (Customer action on issued invoice).
    
    - **invoice_id**: Associated invoice identifier
    - **customer_id**: Customer identifier
    - **amount**: Payment amount (must match invoice amount)
    - **payment_method**: Payment method (e.g., "credit_card", "bank_transfer")
    - **transaction_id**: Optional transaction reference
    """
    controller = PaymentController(db)
    
    try:
        return await controller.create_payment(payment_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{payment_id}", response_model=Payment)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    db: AsyncSession = Depends(get_session),
):
    """
    Update an existing payment.
    
    - **payment_id**: The unique payment identifier
    - **status**: Optional new status
    - **amount**: Optional new amount
    - **transaction_id**: Optional new transaction ID
    """
    controller = PaymentController(db)
    
    payment = await controller.update_payment(payment_id, payment_data)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return payment


@router.post("/{payment_id}/refund", response_model=Payment)
async def refund_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Refund a payment.
    
    - **payment_id**: The unique payment identifier
    """
    controller = PaymentController(db)
    
    try:
        payment = await controller.refund_payment(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{payment_id}/fail", response_model=Payment)
async def fail_payment(
    payment_id: int,
    reason: Optional[str] = Query(None, description="Reason for payment failure"),
    db: AsyncSession = Depends(get_session),
):
    """
    Mark a payment as failed.
    
    - **payment_id**: The unique payment identifier
    - **reason**: Optional reason for failure
    """
    controller = PaymentController(db)
    
    payment = await controller.fail_payment(payment_id, reason)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return payment


@router.delete("/{payment_id}", response_model=APIResponse)
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_session),
):
    """
    Delete a payment.
    
    - **payment_id**: The unique payment identifier
    """
    controller = PaymentController(db)
    
    try:
        success = await controller.delete_payment(payment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Payment not found")
        return APIResponse(success=True, message="Payment deleted successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
