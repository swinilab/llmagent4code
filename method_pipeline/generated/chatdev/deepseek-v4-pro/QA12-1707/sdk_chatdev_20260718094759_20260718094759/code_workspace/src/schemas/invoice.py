"""Invoice schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class InvoiceCreate(BaseModel):
    """Payload to create an invoice for an accepted order."""

    order_id: str
    billing_info: str = Field(..., min_length=1)
    due_date: date | None = None


class InvoiceResponse(BaseModel):
    """Invoice as returned by the API."""

    id: str
    order_id: str
    billing_info: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    issue_date: date
    due_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
