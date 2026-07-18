"""
Invoice ORM model.

Created by the accountant for accepted orders; tracks billing info,
amounts, issue/due dates, and status.
"""
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oms.database import Base
from oms.enums import InvoiceStatus
from oms.models.base import TimestampMixin

if TYPE_CHECKING:
    from oms.models.order import Order


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False,
        unique=True,
    )
    billing_info: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    issue_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    due_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, native_enum=False, length=20),
        nullable=False,
        default=InvoiceStatus.ISSUED,
    )

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="invoice",
        lazy="selectin",
        foreign_keys="Order.invoice_id",
    )

    def __repr__(self) -> str:
        return f"<Invoice {self.id} {self.status.value}>"