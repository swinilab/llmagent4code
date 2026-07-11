"""
Customer ORM model.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import CustomerRole


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    banking_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    role: Mapped[CustomerRole] = mapped_column(Enum(CustomerRole), nullable=False, default=CustomerRole.CUSTOMER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    orders = relationship("Order", back_populates="customer", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Customer {self.id} {self.name}>"
