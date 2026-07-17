"""
Invoice domain model.
Represents an invoice in the OMS system.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime
import enum

from oms.config.database import Base


class InvoiceStatus(str, enum.Enum):
    """Invoice status enum."""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    """
    SQLAlchemy model for Invoice entity.
    
    Attributes:
        id: Primary key
        order_id: Foreign key to Order
        billing_name: Name on the invoice
        billing_address: Billing address
        subtotal: Sum of line items
        tax_amount: Tax amount
        total_amount: Total amount including tax
        currency: Currency code
        issue_date: Date invoice was issued
        due_date: Date payment is due
        status: Current invoice status
        notes: Invoice notes
        created_at: Timestamp of record creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    billing_name = Column(String(255), nullable=False)
    billing_address = Column(Text, nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Note: Order.invoice provides the relationship back to Order
    # We don't define a reciprocal relationship here to avoid ambiguity
    # since both tables have FKs to each other

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, order_id={self.order_id}, status={self.status.value})>"


class InvoiceCreate(BaseModel):
    order_id: int = Field(..., gt=0)
    billing_name: str = Field(..., min_length=1, max_length=255)
    billing_address: Optional[str] = None
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=1)
    notes: Optional[str] = None
    due_days: int = Field(default=30, gt=0)


class InvoiceUpdate(BaseModel):
    """Pydantic model for updating an invoice."""
    billing_name: Optional[str] = Field(None, min_length=1, max_length=255)
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[InvoiceStatus] = None


class InvoiceIssueRequest(BaseModel):
    """Pydantic model for issuing an invoice."""
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class InvoiceResponse(BaseModel):
    """Pydantic model for invoice response."""
    id: int
    order_id: int
    billing_name: str
    billing_address: Optional[str] = None
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: InvoiceStatus
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
