"""
Product domain model.
"""
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from app.db.base import Base


class Product(Base):
    """Product domain model."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    base_price = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)

    order_line_items = relationship("OrderLineItem", back_populates="product")