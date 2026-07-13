from sqlalchemy import Column, Integer, String, Text, Numeric
from sqlalchemy.orm import relationship
from oms_backend.app.db.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    base_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)  # ISO 4217

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")