"""
Product ORM model.

Stores description and pricing (base price + currency).
"""
import uuid

from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oms.database import Base
from oms.models.base import TimestampMixin


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    def __repr__(self) -> str:
        return f"<Product {self.id} {self.description[:30]}>"