"""
Pydantic schemas for Payment entity.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from oms.models.enums import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    order_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    method: PaymentMethod


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    amount: float
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    paid_at: Optional[datetime] = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
