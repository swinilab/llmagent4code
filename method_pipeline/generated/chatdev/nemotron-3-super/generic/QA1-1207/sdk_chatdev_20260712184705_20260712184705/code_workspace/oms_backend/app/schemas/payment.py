from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum as PyEnum

class PaymentStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentMethod(str, PyEnum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"

class PaymentBase(BaseModel):
    order_id: int
    amount: float
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    order_id: Optional[int] = None
    amount: Optional[float] = None
    method: Optional[PaymentMethod] = None
    status: Optional[PaymentStatus] = None

class PaymentInDBBase(PaymentBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True

class PaymentInDB(PaymentInDBBase):
    pass

class Payment(PaymentInDBBase):
    pass

class PaymentList(BaseModel):
    items: List[Payment]
    total: int
    page: int
    size: int