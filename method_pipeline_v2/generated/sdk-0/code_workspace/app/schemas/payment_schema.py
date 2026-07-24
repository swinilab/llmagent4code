"""
Pydantic schemas for Payment API.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PaymentStatus


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
    transaction_id: str | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    payments: list[PaymentResponse]
    total: int
