"""
Pydantic schemas for Invoice.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models.invoice import InvoiceStatus


class InvoiceBase(BaseModel):
    order_id: str
    billing_info: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceResponse(InvoiceBase):
    id: str
    status: InvoiceStatus
    issue_date: datetime | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus
