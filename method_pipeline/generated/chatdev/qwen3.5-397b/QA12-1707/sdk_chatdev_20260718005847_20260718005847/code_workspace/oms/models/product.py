"""
Product domain model.
Represents a product in the OMS system.
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime

from oms.config.database import Base


class Product(Base):
    """
    SQLAlchemy model for Product entity.
    
    Attributes:
        id: Primary key
        name: Product name
        description: Product description
        base_price: Base price in cents (to avoid floating point issues)
        currency: Currency code (e.g., USD, EUR)
        stock_quantity: Available stock
        created_at: Timestamp of record creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', price={self.base_price})>"


class ProductCreate(BaseModel):
    """Pydantic model for creating a product."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    base_price: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    stock_quantity: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    """Pydantic model for updating a product."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    stock_quantity: Optional[int] = Field(None, ge=0)


class ProductResponse(BaseModel):
    """Pydantic model for product response."""
    id: int
    name: str
    description: Optional[str] = None
    base_price: Decimal
    currency: str
    stock_quantity: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
