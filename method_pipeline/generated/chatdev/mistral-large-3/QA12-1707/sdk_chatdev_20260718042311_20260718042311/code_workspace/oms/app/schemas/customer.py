"""
Pydantic schemas for Customer.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from app.schemas.order import OrderRead


class CustomerBase(BaseModel):
    """Base customer schema."""
    name: str
    address: str
    phone: str
    role: str


class CustomerCreate(CustomerBase):
    """Customer creation schema."""
    banking_details: dict


class CustomerRead(CustomerBase):
    """Customer read schema."""
    id: int
    orders: Optional[List[OrderRead]] = Field(default_factory=list)

    class Config:
        from_attributes = True