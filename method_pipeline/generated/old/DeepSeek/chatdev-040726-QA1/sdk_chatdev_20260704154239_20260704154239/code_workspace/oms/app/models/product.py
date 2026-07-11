"""
Product ORM model.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Text, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    base_price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    order_items = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Product {self.id} {self.name}>"
