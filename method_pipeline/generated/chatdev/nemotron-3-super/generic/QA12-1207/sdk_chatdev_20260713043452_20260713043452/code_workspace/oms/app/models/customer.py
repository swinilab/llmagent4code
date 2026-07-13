from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(50))
    banking_details = Column(Text)  # In real app, this should be encrypted
    role = Column(String(50), default="customer")  # customer, order_staff, accountant
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="customer")