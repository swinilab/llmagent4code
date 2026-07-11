"""
Pydantic schemas for Invoice API.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import InvoiceStatus


class InvoiceCreate(BaseModel):
    order_id: str
    billing_info: str = Field(..., min_length=1)
    due_days: int = Field(default=30, ge=1)


class InvoiceResponse(BaseModel):
    id: str
    order_id: str
    customer_id: str
    billing_info: str
    total_amount: float
    currency: str
    issue_date: datetime
    due_date: datetime
    status: InvoiceStatus
    paid_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceResponse]
    total: int
