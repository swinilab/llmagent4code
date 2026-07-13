from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.db.models import PaymentStatus, PaymentMethod

class PaymentBase(BaseModel):
    order_id: int
    amount: float = Field(..., gt=0)
    method: Optional[PaymentMethod] = None
    status: PaymentStatus = PaymentStatus.pending

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

class PaymentResponse(PaymentInDBBase):
    pass