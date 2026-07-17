"""
Customer domain model.
Represents a customer in the OMS system.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from oms.config.database import Base


class Customer(Base):
    """
    SQLAlchemy model for Customer entity.
    
    Attributes:
        id: Primary key
        name: Customer full name
        email: Customer email address
        phone: Customer phone number
        address: Customer shipping/billing address
        banking_details: Encrypted banking information
        created_at: Timestamp of record creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    banking_details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}')>"


class CustomerCreate(BaseModel):
    """Pydantic model for creating a customer."""
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    banking_details: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Pydantic model for updating a customer."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    banking_details: Optional[str] = None


class CustomerResponse(BaseModel):
    """Pydantic model for customer response."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    banking_details: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
