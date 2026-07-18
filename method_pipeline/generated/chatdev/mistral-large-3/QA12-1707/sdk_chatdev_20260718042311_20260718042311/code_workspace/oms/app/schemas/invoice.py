"""
Pydantic schemas for Invoice.
"""
from datetime import datetime
from pydantic import BaseModel
from app.models.invoice import InvoiceStatus


class InvoiceBase(BaseModel):
    """Base invoice schema."""
    order_id: int
    billing_info: str
    total_amount: float
    due_date: datetime


class InvoiceCreate(InvoiceBase):
    """Invoice creation schema."""
    order_id: int
    issue_date: datetime
    due_date: datetime
    tax_rate: float = 0.0
    discount: float = 0.0


class InvoiceRead(InvoiceBase):
    """Invoice read schema."""
    id: int
    issue_date: datetime
    status: InvoiceStatus

    class Config:
        from_attributes = True