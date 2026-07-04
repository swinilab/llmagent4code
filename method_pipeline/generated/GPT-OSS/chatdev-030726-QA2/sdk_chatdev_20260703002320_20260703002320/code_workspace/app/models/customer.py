"""
SQLAlchemy model for Customer.
"""

from sqlalchemy import Column, Integer, String, Enum, JSON
from app.db import Base
import enum

class RoleEnum(str, enum.Enum):
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    banking_details = Column(JSON, nullable=True)  # store as JSON dict
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.CUSTOMER)
    # order history will be derived via relationship in Order model
