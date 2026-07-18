"""
Customer domain model.
"""
from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class Customer(Base):
    """Customer domain model."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    banking_details = Column(JSON, nullable=False)
    role = Column(String, nullable=False)

    orders = relationship("Order", back_populates="customer")