"""
Payment REST controller.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.payment import PaymentService
from app.models.payment import PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentRead
from app.db.session import get_db

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentRead)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """Create a new payment."""
    service = PaymentService(db)
    return service.create_payment(payment)


@router.get("/{payment_id}", response_model=PaymentRead)
def read_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get payment by ID."""
    service = PaymentService(db)
    return service.get_payment(payment_id)


@router.patch("/{payment_id}/status", response_model=PaymentRead)
def update_payment_status(payment_id: int, status: PaymentStatus, db: Session = Depends(get_db)):
    """Update payment status."""
    service = PaymentService(db)
    return service.update_payment_status(payment_id, status)


@router.get("/order/{order_id}", response_model=list[PaymentRead])
def read_payments_by_order(order_id: int, db: Session = Depends(get_db)):
    """List all payments for an order."""
    service = PaymentService(db)
"""
@router.post("", response_model=PaymentRead)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """Create a new payment (Customer)."""
    service = PaymentService(db)
    return service.create_payment(payment)


@router.patch("/{payment_id}/verify", response_model=PaymentRead)
def verify_payment(payment_id: int, db: Session = Depends(get_db)):
    """Verify a payment (Accountant)."""
    service = PaymentService(db)
    return service.verify_payment(payment_id)


@router.get("/{payment_id}", response_model=PaymentRead)
def read_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get payment by ID."""
    service = PaymentService(db)
    return service.get_payment(payment_id)


@router.patch("/{payment_id}/status", response_model=PaymentRead)
def update_payment_status(payment_id: int, status: PaymentStatus, db: Session = Depends(get_db)):
    """Update payment status."""
    service = PaymentService(db)
    return service.update_payment_status(payment_id, status)


@router.get("/order/{order_id}", response_model=list[PaymentRead])
def read_payments_by_order(order_id: int, db: Session = Depends(get_db)):
    """List all payments for an order."""
    service = PaymentService(db)
    return service.list_payments_by_order(order_id)