"""
Customer schemas — request and response models.
"""
import datetime as dt

from pydantic import BaseModel, Field, field_validator

from oms.enums import Role
from oms.schemas.order import OrderRead


class CustomerBase(BaseModel):
    """Shared customer fields."""
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1, max_length=50)
    banking_details: dict = Field(default_factory=dict,
                                   description="Banking details JSON, e.g. {iban, bank_name}")
    role: Role = Field(default=Role.CUSTOMER)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "")
        if not cleaned.isdigit() and not cleaned.startswith("+"):
            raise ValueError("phone must contain digits and optional + prefix")
        return v


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a customer (all fields optional)."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, min_length=1, max_length=50)
    banking_details: dict | None = None
    role: Role | None = None


class CustomerRead(CustomerBase):
    """Schema for reading a customer."""
    id: str
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class CustomerWithOrders(CustomerRead):
    """Customer with embedded order history."""
    orders: list[OrderRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}