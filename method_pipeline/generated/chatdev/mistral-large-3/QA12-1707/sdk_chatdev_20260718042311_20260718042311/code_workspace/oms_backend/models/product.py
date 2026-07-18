from sqlalchemy import Column, String, Float
from .base import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True)
    description = Column(String, nullable=False)
    base_price = Column(Float, nullable=False)
    currency = Column(String, default="USD")