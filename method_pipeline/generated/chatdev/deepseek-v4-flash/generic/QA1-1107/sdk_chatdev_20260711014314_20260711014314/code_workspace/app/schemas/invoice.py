"""
Pydantic schemas for Invoice entity.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.enums import InvoiceStatus


class InvoiceCreate(BaseModel):
    order_id: str = Field(..., min_length=1)
    billing_info: dict = Field(default_factory=dict)
    issue_date: date
    due_date: date


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    billing_info: Optional[dict] = None
    due_date: Optional[date] = None


class InvoiceRead(BaseModel):
    id: str
    order_id: str
    invoice_number: str
    billing_info: dict
    subtotal: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    total_amount: Decimal
    currency: str
    status: InvoiceStatus
    issue_date: date
    due_date: date
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
