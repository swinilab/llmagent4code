from datetime import datetime, timedelta
from typing import List, Optional
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel
class Role(str, Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ACCOUNTANT = "accountant"


class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: str
    phone: str
    banking_details: str
    role: Role = Field(default=Role.CUSTOMER)

    orders: List["Order"] = Relationship(back_populates="customer")


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    unit_price: float
    currency: str = Field(default="USD")
    # inventory quantity
    quantity: int = Field(default=0)
    total_price: Optional[float] = None

    def compute_total(self) -> None:
        """Calculate total price based on unit price and quantity."""
        self.total_price = round(self.unit_price * self.quantity, 2)


class OrderLineItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int = Field(default=1, ge=1)
    unit_price: float
    total_price: float = Field(default=0)

    product: Optional[Product] = Relationship()
    order: Optional["Order"] = Relationship(back_populates="line_items")

    def compute_total(self) -> None:
        self.total_price = round(self.unit_price * self.quantity, 2)


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    total_amount: float = Field(default=0)

    customer: Optional[Customer] = Relationship(back_populates="orders")
    line_items: List[OrderLineItem] = Relationship(back_populates="order")
    invoice: Optional["Invoice"] = Relationship(back_populates="order")
    payment: Optional["Payment"] = Relationship(back_populates="order")

    def recompute_total(self) -> None:
        self.total_amount = round(sum(item.total_price for item in self.line_items), 2)
        self.updated_at = datetime.utcnow()


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    amount: float
    method: str
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    order: Optional[Order] = Relationship(back_populates="payment")


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    billing_info: str
    amount: float
    issue_date: datetime = Field(default_factory=datetime.utcnow)
    due_date: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT)

    order: Optional[Order] = Relationship(back_populates="invoice")
