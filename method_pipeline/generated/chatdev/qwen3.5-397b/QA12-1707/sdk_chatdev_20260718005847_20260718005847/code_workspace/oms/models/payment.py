"""
Payment domain model.
Represents a payment in the OMS system.
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


class PaymentStatus(str, enum.Enum):
    """Payment status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    """Payment method enum."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    OTHER = "other"


class Payment(Base):
    """
    SQLAlchemy model for Payment entity.
    
    Attributes:
        id: Primary key
        order_id: Foreign key to Order
        invoice_id: Foreign key to Invoice
        amount: Payment amount
        currency: Currency code
        method: Payment method
        status: Current payment status
        transaction_id: External transaction reference
        notes: Payment notes
        processed_at: Timestamp when payment was processed
        created_at: Timestamp of record creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    method = Column(SQLEnum(PaymentMethod), default=PaymentMethod.CREDIT_CARD, nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    transaction_id = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    order = relationship("Order", back_populates="payment")
    
    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, order_id={self.order_id}, status={self.status.value})>"


class PaymentCreate(BaseModel):
    """Pydantic model for creating a payment."""
    order_id: int = Field(..., gt=0)
    invoice_id: Optional[int] = Field(None, gt=0)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    method: PaymentMethod = Field(default=PaymentMethod.CREDIT_CARD)
    notes: Optional[str] = None


class PaymentProcessRequest(BaseModel):
    """Pydantic model for processing a payment."""
    transaction_id: Optional[str] = None
    notes: Optional[str] = None


class PaymentVerifyRequest(BaseModel):
    """Pydantic model for verifying a payment."""
    confirmed: bool = Field(..., description="Whether payment is confirmed")
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    """Pydantic model for payment response."""
    id: int
    order_id: int
    invoice_id: Optional[int] = None
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    transaction_id: Optional[str] = None
    notes: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
