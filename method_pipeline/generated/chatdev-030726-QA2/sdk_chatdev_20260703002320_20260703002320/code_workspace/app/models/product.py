"""
SQLAlchemy model for Product.
"""

from sqlalchemy import Column, Integer, String, Float, JSON
from app.db import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    base_price = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    # additional pricing rules could be stored as JSON if needed
