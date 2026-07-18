"""Payment schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    """Payload to create a payment."""

    order_id: str
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    method: str = Field(default="bank_transfer", pattern=r"^(bank_transfer|credit_card|debit_card|wallet)$")


class PaymentVerify(BaseModel):
    """Payload to verify a payment."""

    status: str = Field(..., pattern=r"^(completed|failed)$")


class PaymentResponse(BaseModel):
    """Payment as returned by the API."""

    id: str
    order_id: str
    amount: Decimal
    status: str
    method: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
