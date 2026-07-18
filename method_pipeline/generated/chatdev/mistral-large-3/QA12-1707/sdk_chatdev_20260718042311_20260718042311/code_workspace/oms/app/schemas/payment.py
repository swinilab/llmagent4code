"""
Pydantic schemas for Payment.
"""
from datetime import datetime
from pydantic import BaseModel
from app.models.payment import PaymentStatus, PaymentMethod


class PaymentBase(BaseModel):
    """Base payment schema."""
    order_id: int
    amount: float
    method: PaymentMethod


class PaymentCreate(PaymentBase):
    """Payment creation schema."""
    order_id: int
    amount: float
    method: str
    status: PaymentStatus = PaymentStatus.PENDING


class PaymentRead(PaymentBase):
    """Payment read schema."""
    id: int
    timestamp: datetime
    status: PaymentStatus

    class Config:
        from_attributes = True