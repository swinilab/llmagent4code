"""
Pydantic schemas for Customer.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class RoleEnum(str, Enum):
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"

class CustomerBase(BaseModel):
    name: str
    address: str
    phone: str
    banking_details: Optional[dict] = None
    role: RoleEnum = RoleEnum.CUSTOMER

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    banking_details: Optional[dict] = None
    role: Optional[RoleEnum] = None

class CustomerOut(CustomerBase):
    id: int

    class Config:
        orm_mode = True
