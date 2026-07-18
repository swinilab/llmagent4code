"""
Invoice schemas — request and response models.
"""
import datetime as dt

from pydantic import BaseModel, Field

from oms.enums import InvoiceStatus


class InvoiceCreate(BaseModel):
    """Schema for creating an invoice for an accepted order."""
    order_id: str
    billing_info: dict = Field(
        default_factory=dict,
        description="Billing address / company info JSON",
    )
    issue_date: dt.date | None = Field(default=None, description="Defaults to today")
    due_date: dt.date | None = Field(default=None, description="Defaults to +30 days")


class InvoiceStatusUpdate(BaseModel):
    """Schema for manually updating invoice status."""
    status: InvoiceStatus


class InvoiceRead(BaseModel):
    """Schema for reading an invoice."""
    id: str
    order_id: str
    billing_info: dict
    subtotal: float
    tax: float
    total: float
    currency: str
    issue_date: dt.date
    due_date: dt.date
    status: InvoiceStatus
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}