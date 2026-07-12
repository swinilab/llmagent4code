"""
Payment Controller - REST endpoints for payment management.
Workflow: customer pays invoice -> accountant verifies
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from ..infrastructure.database import get_db
from ..services.payment_service import PaymentService, PaymentProcessingError
from ..domain.models import PaymentStatus

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class CreatePaymentRequest(BaseModel):
    order_id: str
    invoice_id: str
    customer_id: str
    amount: float = Field(..., gt=0)
    method: str = "bank_transfer"
    idempotency_key: Optional[str] = None


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    invoice_id: str
    customer_id: str
    amount: float
    currency: str
    method: str
    status: str
    transaction_ref: str
    created_at: str
    processed_at: Optional[str]


def _to_response(payment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        invoice_id=payment.invoice_id,
        customer_id=payment.customer_id,
        amount=payment.amount,
        currency=payment.currency,
        method=payment.method,
        status=payment.status.value if hasattr(payment.status, 'value') else payment.status,
        transaction_ref=payment.transaction_ref,
        created_at=payment.created_at.isoformat(),
        processed_at=payment.processed_at.isoformat() if payment.processed_at else None
    )


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db)
):
    """Step 4: Create a payment for an invoice."""
    service = PaymentService(db)
    
    try:
        payment = service.create_payment(
            order_id=request.order_id,
            invoice_id=request.invoice_id,
            customer_id=request.customer_id,
            amount=request.amount,
            method=request.method,
            idempotency_key=request.idempotency_key
        )
        return _to_response(payment)
    except PaymentProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{payment_id}/process", response_model=PaymentResponse)
def process_payment(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """Process a pending payment (calls payment gateway)."""
    service = PaymentService(db)
    
    try:
        payment = service.process_payment(payment_id)
        return _to_response(payment)
    except PaymentProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{payment_id}/verify", response_model=PaymentResponse)
def verify_payment(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """Step 5: Accountant verifies payment."""
    service = PaymentService(db)
    
    try:
        payment = service.verify_payment(payment_id)
        return _to_response(payment)
    except PaymentProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment(
    payment_id: str,
    reason: str = "",
    db: Session = Depends(get_db)
):
    """Refund a completed payment."""
    service = PaymentService(db)
    
    try:
        payment = service.refund_payment(payment_id, reason)
        return _to_response(payment)
    except PaymentProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """Get payment by ID."""
    service = PaymentService(db)
    payment = service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return _to_response(payment)


@router.get("/by-order/{order_id}", response_model=List[PaymentResponse])
def get_payments_by_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Get all payments for an order."""
    service = PaymentService(db)
    payments = service.get_payments_by_order(order_id)
    return [_to_response(p) for p in payments]


@router.get("/by-invoice/{invoice_id}", response_model=List[PaymentResponse])
def get_payments_by_invoice(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Get all payments for an invoice."""
    service = PaymentService(db)
    payments = service.get_payments_by_invoice(invoice_id)
    return [_to_response(p) for p in payments]
