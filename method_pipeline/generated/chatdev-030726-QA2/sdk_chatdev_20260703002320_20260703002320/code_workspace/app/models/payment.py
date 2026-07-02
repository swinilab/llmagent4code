"""
SQLAlchemy model for Payment.
"""

from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, Enum
from datetime import datetime
import enum
from app.db import Base

class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
