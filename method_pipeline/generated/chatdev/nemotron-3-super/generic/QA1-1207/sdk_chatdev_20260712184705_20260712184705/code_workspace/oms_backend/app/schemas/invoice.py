from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum as PyEnum

class InvoiceStatus(str, PyEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class InvoiceBase(BaseModel):
    order_id: int
    billing_info: str  # JSON or text
    amount: float
    due_date: datetime
    status: InvoiceStatus = InvoiceStatus.DRAFT

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    order_id: Optional[int] = None
    billing_info: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    status: Optional[InvoiceStatus] = None

class InvoiceInDBBase(InvoiceBase):
    id: int
    issue_date: datetime

    class Config:
        orm_mode = True

class InvoiceInDB(InvoiceInDBBase):
    pass

class Invoice(InvoiceInDBBase):
    pass

class InvoiceList(BaseModel):
    items: List[Invoice]
    total: int
    page: int
    size: int