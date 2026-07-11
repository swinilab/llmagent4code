"""
Pydantic schemas for Invoice entity.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from oms.models.enums import InvoiceStatus


class InvoiceCreate(BaseModel):
    order_id: str
    billing_name: str = Field(..., min_length=1)
    billing_address: str = Field(..., min_length=1)
    total_amount: float = Field(..., gt=0)
    currency: str = "USD"
    due_date: Optional[datetime] = None


class InvoiceResponse(BaseModel):
    id: str
    order_id: str
    billing_name: str
    billing_address: str
    total_amount: float
    currency: str
    status: InvoiceStatus
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
