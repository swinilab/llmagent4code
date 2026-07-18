from sqlalchemy import Column, String, Float, Enum, DateTime
from sqlalchemy.sql import func
from .base import Base
import enum

class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    method = Column(String, nullable=False)