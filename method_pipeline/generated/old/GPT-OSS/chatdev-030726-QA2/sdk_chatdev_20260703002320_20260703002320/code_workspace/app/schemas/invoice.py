"""
Pydantic schemas for Invoice.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"

class InvoiceBase(BaseModel):
    order_id: int
    billing_info: str
    amount: float
    due_date: Optional[datetime] = None
    status: InvoiceStatus = InvoiceStatus.DRAFT

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceOut(InvoiceBase):
    id: int
    issue_date: datetime
    class Config:
        orm_mode = True
