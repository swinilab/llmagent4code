"""
Pydantic schemas for Payment.
"""

from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class PaymentBase(BaseModel):
    order_id: int
    amount: float
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING

class PaymentCreate(PaymentBase):
    pass

class PaymentOut(PaymentBase):
    id: int
    timestamp: datetime
    class Config:
        orm_mode = True
