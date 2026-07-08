"""
Pydantic schemas for Payment.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models.payment import PaymentStatus, PaymentMethod


class PaymentBase(BaseModel):
    order_id: str
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    method: PaymentMethod


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    id: str
    status: PaymentStatus
    paid_at: datetime | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentVerification(BaseModel):
    verified: bool
