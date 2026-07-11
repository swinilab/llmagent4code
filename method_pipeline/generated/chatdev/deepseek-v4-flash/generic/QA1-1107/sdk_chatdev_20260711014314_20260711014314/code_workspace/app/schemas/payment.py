"""
Pydantic schemas for Payment entity.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.enums import PaymentStatus, PaymentMethod


class PaymentCreate(BaseModel):
    order_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    method: PaymentMethod
    transaction_ref: Optional[str] = None


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    transaction_ref: Optional[str] = None


class PaymentRead(BaseModel):
    id: str
    order_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    method: PaymentMethod
    transaction_ref: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
