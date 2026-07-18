"""
Payment schemas — request and response models.
"""
import datetime as dt

from pydantic import BaseModel, Field

from oms.enums import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    """Schema for creating a payment against an order's invoice."""
    order_id: str
    amount: float = Field(..., gt=0)
    method: PaymentMethod


class PaymentVerify(BaseModel):
    """Schema for verifying (approving/rejecting) a payment."""
    verified: bool = Field(..., description="True = verified, False = failed")


class PaymentRead(BaseModel):
    """Schema for reading a payment."""
    id: str
    order_id: str
    amount: float
    timestamp: dt.datetime
    status: PaymentStatus
    method: PaymentMethod

    model_config = {"from_attributes": True}