from sqlalchemy import Column, String, JSON
from .base import Base

class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(JSON, nullable=False)
    phone = Column(String, nullable=False)
    banking_details = Column(JSON, nullable=False)
    order_history = Column(JSON, default=[])
    role = Column(String, nullable=False)  # "CUSTOMER", "STAFF", "ACCOUNTANT"