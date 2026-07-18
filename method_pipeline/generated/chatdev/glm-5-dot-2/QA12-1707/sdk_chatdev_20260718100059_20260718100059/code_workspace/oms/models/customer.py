"""
Customer ORM model.

Stores identity, contact, banking, and role information.
Order history is accessed via the Order relationship.
"""
import datetime as dt
import uuid

from sqlalchemy import JSON, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oms.database import Base
from oms.enums import Role
from oms.models.base import TimestampMixin


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    banking_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=20),
        nullable=False,
        default=Role.CUSTOMER,
    )

    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="customer",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Customer {self.id} {self.name}>"