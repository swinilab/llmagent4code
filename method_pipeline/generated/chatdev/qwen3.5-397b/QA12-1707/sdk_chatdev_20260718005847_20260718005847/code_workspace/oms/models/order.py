from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import enum

from oms.config.database import Base


class OrderStatus(str, enum.Enum):
    """
    Order lifecycle status enum.
    Represents the complete workflow from placement to closure.
    """
    PENDING = "pending"  # Initial state when customer places order
    REVIEWING = "reviewing"  # Order staff is reviewing
    ACCEPTED = "accepted"  # Order staff accepted
    REJECTED = "rejected"  # Order staff rejected
    INVOICED = "invoiced"  # Accountant created invoice
    PAYMENT_PENDING = "payment_pending"  # Waiting for customer payment
    PAID = "paid"  # Payment verified
    SHIPPING = "shipping"  # Order staff is shipping
    SHIPPED = "shipped"  # Order has been shipped
    COMPLETED = "completed"  # Order closed successfully
    CANCELLED = "cancelled"  # Order cancelled


class Order(Base):
    """
    SQLAlchemy model for Order entity.
    
    Attributes:
        id: Primary key
        customer_id: Foreign key to Customer
        status: Current order status
        total_amount: Total order amount
        currency: Currency code
        invoice_id: Foreign key to Invoice (when created)
        notes: Internal notes
        created_at: Timestamp of order creation
        updated_at: Timestamp of last update
        reviewed_at: Timestamp when order was reviewed
        shipped_at: Timestamp when order was shipped
        completed_at: Timestamp when order was completed
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    total_amount = Column(Numeric(10, 2), default=0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    line_items = relationship("OrderLineItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False, cascade="all, delete-orphan")
    # One-to-one relationship with Invoice (Order holds the FK) - no back_populates since Invoice doesn't define reciprocal
    invoice = relationship("Invoice", foreign_keys=[invoice_id])


class OrderLineItem(Base):
    """
    SQLAlchemy model for Order Line Item entity.
    Represents individual items within an order.
    
    Attributes:
        id: Primary key
        order_id: Foreign key to Order
        product_id: Foreign key to Product
        quantity: Number of units
        unit_price: Price per unit at time of order
        subtotal: Calculated subtotal (quantity * unit_price)
    """
    __tablename__ = "order_line_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    
    order = relationship("Order", back_populates="line_items")
    product = relationship("Product")
    
    def __repr__(self) -> str:
        return f"<OrderLineItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id})>"


class OrderLineItemCreate(BaseModel):
    """Pydantic model for creating an order line item."""
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderLineItemResponse(BaseModel):
    """Pydantic model for order line item response."""
    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    
    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Pydantic model for creating an order."""
    customer_id: int = Field(..., gt=0)
    line_items: List[OrderLineItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    """Pydantic model for updating an order."""
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class OrderReviewRequest(BaseModel):
    """Pydantic model for order review request."""
    accept: bool = Field(..., description="Whether to accept or reject the order")
    notes: Optional[str] = None


class OrderShipRequest(BaseModel):
    """Pydantic model for order shipping request."""
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    """Pydantic model for order response."""
    id: int
    customer_id: int
    status: OrderStatus
    total_amount: Decimal
    currency: str
    invoice_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    line_items: Optional[List[OrderLineItemResponse]] = None
    
    class Config:
        from_attributes = True
