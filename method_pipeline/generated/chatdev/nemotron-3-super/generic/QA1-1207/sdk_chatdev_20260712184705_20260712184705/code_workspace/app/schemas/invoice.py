from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.db.models import InvoiceStatus

class InvoiceBase(BaseModel):
    order_id: int
    billing_info: Optional[str] = None
    amount: float = Field(..., gt=0)
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: InvoiceStatus = InvoiceStatus.draft

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    order_id: Optional[int] = None
    billing_info: Optional[str] = None
    amount: Optional[float] = None
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: Optional[InvoiceStatus] = None

class InvoiceInDBBase(InvoiceBase):
    id: int
    issue_date: datetime
    # due_date already in base

    class Config:
        orm_mode = True

class InvoiceInDB(InvoiceInDBBase):
    pass

class InvoiceResponse(InvoiceInDBBase):
    pass