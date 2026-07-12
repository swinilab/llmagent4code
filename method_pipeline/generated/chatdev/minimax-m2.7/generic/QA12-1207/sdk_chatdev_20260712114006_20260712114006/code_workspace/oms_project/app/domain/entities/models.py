"""
OMS Domain Models - Shared entity definitions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid


class UserRole(str, Enum):
    """User roles in the system."""
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class PaymentMethod(str, Enum):
    """Payment methods."""
    BANK_TRANSFER = "BANK_TRANSFER"
    CREDIT_CARD = "CREDIT_CARD"
    PAYPAL = "PAYPAL"


class OrderStatus(str, Enum):
    """Order lifecycle status."""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


@dataclass
class Address:
    """Address information."""
    street: str
    city: str
    state: str
    postal_code: str
    country: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> Address:
        return cls(
            street=data.get("street", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
            country=data.get("country", "")
        )


@dataclass
class BankingDetails:
    """Banking information for payments."""
    bank_name: str
    account_number: str
    routing_number: str
    swift_code: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        return {
            "bank_name": self.bank_name,
            "account_number": self.account_number,
            "routing_number": self.routing_number,
            "swift_code": self.swift_code
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> BankingDetails:
        return cls(
            bank_name=data.get("bank_name", ""),
            account_number=data.get("account_number", ""),
            routing_number=data.get("routing_number", ""),
            swift_code=data.get("swift_code")
        )


@dataclass
class Money:
    """Monetary value with currency."""
    amount: Decimal
    currency: Currency

    def to_dict(self) -> Dict[str, str]:
        return {
            "amount": str(self.amount),
            "currency": self.currency.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> Money:
        return cls(
            amount=Decimal(data.get("amount", "0")),
            currency=Currency(data.get("currency", "USD"))
        )

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __mul__(self, multiplier: Decimal) -> Money:
        return Money(amount=self.amount * multiplier, currency=self.currency)


@dataclass
class LineItem:
    """Order line item."""
    product_id: str
    product_name: str
    sku: str
    quantity: int
    unit_price: Money
    subtotal: Money

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "sku": self.sku,
            "quantity": self.quantity,
            "unit_price": self.unit_price.to_dict(),
            "subtotal": self.subtotal.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineItem:
        return cls(
            product_id=data.get("product_id", ""),
            product_name=data.get("product_name", ""),
            sku=data.get("sku", ""),
            quantity=data.get("quantity", 1),
            unit_price=Money.from_dict(data.get("unit_price", {"amount": "0", "currency": "USD"})),
            subtotal=Money.from_dict(data.get("subtotal", {"amount": "0", "currency": "USD"}))
        )


@dataclass
class Customer:
    """Customer entity."""
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[Address] = None
    banking_details: Optional[BankingDetails] = None
    role: UserRole = UserRole.CUSTOMER
    order_history: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address.to_dict() if self.address else None,
            "banking_details": self.banking_details.to_dict() if self.banking_details else None,
            "role": self.role.value,
            "order_history": self.order_history,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Customer:
        address = None
        if data.get("address"):
            address = Address.from_dict(data["address"]) if isinstance(data["address"], dict) else data["address"]
        
        banking_details = None
        if data.get("banking_details"):
            banking_details = BankingDetails.from_dict(data["banking_details"]) if isinstance(data["banking_details"], dict) else data["banking_details"]
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            email=data["email"],
            phone=data.get("phone"),
            address=address,
            banking_details=banking_details,
            role=UserRole(data.get("role", "CUSTOMER")),
            order_history=data.get("order_history", []),
            is_active=data.get("is_active", True),
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class Product:
    """Product entity."""
    id: str
    sku: str
    name: str
    description: Optional[str] = None
    price: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    stock_quantity: int = 0
    is_active: bool = True
    category: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price": self.price.to_dict() if isinstance(self.price, Money) else self.price,
            "stock_quantity": self.stock_quantity,
            "is_active": self.is_active,
            "category": self.category,
            "weight": self.weight,
            "dimensions": self.dimensions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Product:
        price = data.get("price", {"amount": "0", "currency": "USD"})
        if isinstance(price, dict):
            price = Money.from_dict(price)
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            sku=data["sku"],
            name=data["name"],
            description=data.get("description"),
            price=price,
            stock_quantity=data.get("stock_quantity", 0),
            is_active=data.get("is_active", True),
            category=data.get("category"),
            weight=data.get("weight"),
            dimensions=data.get("dimensions"),
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class Order:
    """Order entity."""
    id: str
    customer_id: str
    line_items: List[LineItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    subtotal: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    tax_total: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    discount_total: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    total: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    currency: Currency = Currency.USD
    invoice_id: Optional[str] = None
    payment_id: Optional[str] = None
    shipping_address: Optional[Address] = None
    notes: Optional[str] = None
    accepted_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        def serialize_money(m):
            return m.to_dict() if isinstance(m, Money) else m
        
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "line_items": [item.to_dict() if isinstance(item, LineItem) else item for item in self.line_items],
            "status": self.status.value if isinstance(self.status, OrderStatus) else self.status,
            "subtotal": serialize_money(self.subtotal),
            "tax_total": serialize_money(self.tax_total),
            "discount_total": serialize_money(self.discount_total),
            "total": serialize_money(self.total),
            "currency": self.currency.value if isinstance(self.currency, Currency) else self.currency,
            "invoice_id": self.invoice_id,
            "payment_id": self.payment_id,
            "shipping_address": self.shipping_address.to_dict() if isinstance(self.shipping_address, Address) else self.shipping_address,
            "notes": self.notes,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Order:
        def deserialize_money(m):
            if isinstance(m, Money):
                return m
            return Money.from_dict(m) if isinstance(m, dict) else Money(Decimal("0"), Currency.USD)
        
        def deserialize_line_item(item):
            if isinstance(item, LineItem):
                return item
            return LineItem.from_dict(item) if isinstance(item, dict) else item
        
        shipping_address = data.get("shipping_address")
        if isinstance(shipping_address, dict):
            shipping_address = Address.from_dict(shipping_address)
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        accepted_at = data.get("accepted_at")
        if isinstance(accepted_at, str):
            accepted_at = datetime.fromisoformat(accepted_at)
        
        shipped_at = data.get("shipped_at")
        if isinstance(shipped_at, str):
            shipped_at = datetime.fromisoformat(shipped_at)
        
        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            customer_id=data["customer_id"],
            line_items=[deserialize_line_item(item) for item in data.get("line_items", [])],
            status=OrderStatus(data.get("status", "PENDING")),
            subtotal=deserialize_money(data.get("subtotal", {"amount": "0", "currency": "USD"})),
            tax_total=deserialize_money(data.get("tax_total", {"amount": "0", "currency": "USD"})),
            discount_total=deserialize_money(data.get("discount_total", {"amount": "0", "currency": "USD"})),
            total=deserialize_money(data.get("total", {"amount": "0", "currency": "USD"})),
            currency=Currency(data.get("currency", "USD")),
            invoice_id=data.get("invoice_id"),
            payment_id=data.get("payment_id"),
            shipping_address=shipping_address,
            notes=data.get("notes"),
            accepted_at=accepted_at,
            shipped_at=shipped_at,
            completed_at=completed_at,
            metadata=data.get("metadata"),
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class Payment:
    """Payment entity."""
    id: str
    order_id: str
    customer_id: str
    amount: Money
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    transaction_ref: Optional[str] = None
    payment_timestamp: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "amount": self.amount.to_dict() if isinstance(self.amount, Money) else self.amount,
            "status": self.status.value if isinstance(self.status, PaymentStatus) else self.status,
            "method": self.method.value if isinstance(self.method, PaymentMethod) else self.method,
            "transaction_ref": self.transaction_ref,
            "payment_timestamp": self.payment_timestamp.isoformat() if self.payment_timestamp else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "failure_reason": self.failure_reason,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Payment:
        amount = data.get("amount", {"amount": "0", "currency": "USD"})
        if isinstance(amount, dict):
            amount = Money.from_dict(amount)
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        payment_timestamp = data.get("payment_timestamp")
        if isinstance(payment_timestamp, str):
            payment_timestamp = datetime.fromisoformat(payment_timestamp)
        
        processed_at = data.get("processed_at")
        if isinstance(processed_at, str):
            processed_at = datetime.fromisoformat(processed_at)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            order_id=data["order_id"],
            customer_id=data["customer_id"],
            amount=amount,
            status=PaymentStatus(data.get("status", "PENDING")),
            method=PaymentMethod(data.get("method", "BANK_TRANSFER")),
            transaction_ref=data.get("transaction_ref"),
            payment_timestamp=payment_timestamp,
            processed_at=processed_at,
            failure_reason=data.get("failure_reason"),
            metadata=data.get("metadata"),
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class Invoice:
    """Invoice entity."""
    id: str
    order_id: str
    customer_id: str
    invoice_number: str
    line_items: List[LineItem] = field(default_factory=list)
    subtotal: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    tax_total: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    discount_total: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    total: Money = field(default_factory=lambda: Money(Decimal("0"), Currency.USD))
    currency: Currency = Currency.USD
    status: InvoiceStatus = InvoiceStatus.DRAFT
    billing_address: Optional[Address] = None
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    payment_id: Optional[str] = None
    notes: Optional[str] = None
    terms: str = "Net 30"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        def serialize_money(m):
            return m.to_dict() if isinstance(m, Money) else m
        
        return {
            "id": self.id,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "invoice_number": self.invoice_number,
            "line_items": [item.to_dict() if isinstance(item, LineItem) else item for item in self.line_items],
            "subtotal": serialize_money(self.subtotal),
            "tax_total": serialize_money(self.tax_total),
            "discount_total": serialize_money(self.discount_total),
            "total": serialize_money(self.total),
            "currency": self.currency.value if isinstance(self.currency, Currency) else self.currency,
            "status": self.status.value if isinstance(self.status, InvoiceStatus) else self.status,
            "billing_address": self.billing_address.to_dict() if isinstance(self.billing_address, Address) else self.billing_address,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_date": self.paid_date.isoformat() if self.paid_date else None,
            "payment_id": self.payment_id,
            "notes": self.notes,
            "terms": self.terms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Invoice:
        def deserialize_money(m):
            if isinstance(m, Money):
                return m
            return Money.from_dict(m) if isinstance(m, dict) else Money(Decimal("0"), Currency.USD)
        
        def deserialize_line_item(item):
            if isinstance(item, LineItem):
                return item
            return LineItem.from_dict(item) if isinstance(item, dict) else item
        
        billing_address = data.get("billing_address")
        if isinstance(billing_address, dict):
            billing_address = Address.from_dict(billing_address)
        
        issue_date = data.get("issue_date")
        if isinstance(issue_date, str):
            issue_date = datetime.fromisoformat(issue_date)
        
        due_date = data.get("due_date")
        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date)
        
        paid_date = data.get("paid_date")
        if isinstance(paid_date, str):
            paid_date = datetime.fromisoformat(paid_date)
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            order_id=data["order_id"],
            customer_id=data["customer_id"],
            invoice_number=data["invoice_number"],
            line_items=[deserialize_line_item(item) for item in data.get("line_items", [])],
            subtotal=deserialize_money(data.get("subtotal", {"amount": "0", "currency": "USD"})),
            tax_total=deserialize_money(data.get("tax_total", {"amount": "0", "currency": "USD"})),
            discount_total=deserialize_money(data.get("discount_total", {"amount": "0", "currency": "USD"})),
            total=deserialize_money(data.get("total", {"amount": "0", "currency": "USD"})),
            currency=Currency(data.get("currency", "USD")),
            status=InvoiceStatus(data.get("status", "DRAFT")),
            billing_address=billing_address,
            issue_date=issue_date,
            due_date=due_date,
            paid_date=paid_date,
            payment_id=data.get("payment_id"),
            notes=data.get("notes"),
            terms=data.get("terms", "Net 30"),
            created_at=created_at,
            updated_at=updated_at
        )
