"""
Shared domain models for OMS - used by both backend and can be used by FE.
These are pure Python dataclasses with validation.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4, UUID


class OrderStatus(str, Enum):
    """Complete order lifecycle states."""
    PENDING = "pending"           # Customer submitted, awaiting review
    ACCEPTED = "accepted"         # Order staff approved
    REJECTED = "rejected"         # Order staff rejected
    INVOICED = "invoiced"         # Invoice created
    PAID = "paid"                 # Payment verified
    SHIPPED = "shipped"           # Order shipped
    COMPLETED = "completed"       # Order closed successfully
    CANCELLED = "cancelled"       # Order cancelled


class PaymentStatus(str, Enum):
    """Payment lifecycle states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatus(str, Enum):
    """Invoice lifecycle states."""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    """User roles in the system."""
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"


def _utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class Address:
    """Shipping/billing address."""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"

    def to_dict(self) -> dict:
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Address":
        return cls(
            street=data.get("street", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
            country=data.get("country", "US")
        )


@dataclass
class BankingDetails:
    """Banking information for payments."""
    bank_name: str
    account_number: str
    routing_number: str
    account_type: str = "checking"

    def to_dict(self) -> dict:
        return {
            "bank_name": self.bank_name,
            "account_number": "****" + self.account_number[-4:],
            "routing_number": "****" + self.routing_number[-4:],
            "account_type": self.account_type
        }


@dataclass
class LineItem:
    """Order line item - product reference with quantity and price."""
    id: str = field(default_factory=lambda: str(uuid4()))
    product_id: str = ""
    product_description: str = ""
    quantity: int = 1
    unit_price: float = 0.0
    currency: str = "USD"

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_description": self.product_description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "subtotal": self.subtotal
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineItem":
        return cls(
            id=data.get("id", str(uuid4())),
            product_id=data.get("product_id", ""),
            product_description=data.get("product_description", ""),
            quantity=data.get("quantity", 1),
            unit_price=data.get("unit_price", 0.0),
            currency=data.get("currency", "USD")
        )


@dataclass
class Customer:
    """Customer entity with profile and preferences."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    email: str = ""
    phone: str = ""
    address: Optional[Address] = None
    banking_details: Optional[BankingDetails] = None
    role: UserRole = UserRole.CUSTOMER
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address.to_dict() if self.address else None,
            "banking_details": self.banking_details.to_dict() if self.banking_details else None,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Customer":
        address = None
        if data.get("address"):
            address = Address.from_dict(data["address"])
        banking = None
        if data.get("banking_details"):
            banking = BankingDetails(
                bank_name=data["banking_details"]["bank_name"],
                account_number=data["banking_details"].get("account_number", ""),
                routing_number=data["banking_details"].get("routing_number", ""),
                account_type=data["banking_details"].get("account_type", "checking")
            )
        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            address=address,
            banking_details=banking,
            role=UserRole(data.get("role", "customer")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        )


@dataclass
class Product:
    """Product catalog item."""
    id: str = field(default_factory=lambda: str(uuid4()))
    sku: str = ""
    description: str = ""
    base_price: float = 0.0
    currency: str = "USD"
    stock_quantity: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sku": self.sku,
            "description": self.description,
            "base_price": self.base_price,
            "currency": self.currency,
            "stock_quantity": self.stock_quantity,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        return cls(
            id=data.get("id", str(uuid4())),
            sku=data.get("sku", ""),
            description=data.get("description", ""),
            base_price=data.get("base_price", 0.0),
            currency=data.get("currency", "USD"),
            stock_quantity=data.get("stock_quantity", 0),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        )


@dataclass
class Order:
    """Order entity with full lifecycle support."""
    id: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    line_items: List[LineItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    subtotal: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    invoice_id: Optional[str] = None
    shipping_address: Optional[Address] = None
    notes: str = ""
    idempotency_key: Optional[str] = None
    tracking_number: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    accepted_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def recalculate_totals(self):
        """Recalculate order totals from line items."""
        self.subtotal = sum(item.subtotal for item in self.line_items)
        self.tax = self.subtotal * 0.1  # 10% tax
        self.total = self.subtotal + self.tax + self.shipping

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "line_items": [item.to_dict() for item in self.line_items],
            "status": self.status.value,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "shipping": self.shipping,
            "total": self.total,
            "currency": self.currency,
            "invoice_id": self.invoice_id,
            "shipping_address": self.shipping_address.to_dict() if self.shipping_address else None,
            "notes": self.notes,
            "idempotency_key": self.idempotency_key,
            "tracking_number": self.tracking_number,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        line_items = [LineItem.from_dict(li) for li in data.get("line_items", [])]
        shipping_address = None
        if data.get("shipping_address"):
            shipping_address = Address.from_dict(data["shipping_address"])
        order = cls(
            id=data.get("id", str(uuid4())),
            customer_id=data.get("customer_id", ""),
            line_items=line_items,
            status=OrderStatus(data.get("status", "pending")),
            subtotal=data.get("subtotal", 0.0),
            tax=data.get("tax", 0.0),
            shipping=data.get("shipping", 0.0),
            total=data.get("total", 0.0),
            currency=data.get("currency", "USD"),
            invoice_id=data.get("invoice_id"),
            shipping_address=shipping_address,
            notes=data.get("notes", ""),
            idempotency_key=data.get("idempotency_key"),
            tracking_number=data.get("tracking_number", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc),
            accepted_at=datetime.fromisoformat(data["accepted_at"]) if data.get("accepted_at") else None,
            shipped_at=datetime.fromisoformat(data["shipped_at"]) if data.get("shipped_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )
        return order


@dataclass
class Payment:
    """Payment entity for order payments."""
    id: str = field(default_factory=lambda: str(uuid4()))
    order_id: str = ""
    invoice_id: str = ""
    customer_id: str = ""
    amount: float = 0.0
    currency: str = "USD"
    method: str = "bank_transfer"
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_ref: str = ""
    idempotency_key: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    processed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "invoice_id": self.invoice_id,
            "customer_id": self.customer_id,
            "amount": self.amount,
            "currency": self.currency,
            "method": self.method,
            "status": self.status.value,
            "transaction_ref": self.transaction_ref,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Payment":
        return cls(
            id=data.get("id", str(uuid4())),
            order_id=data.get("order_id", ""),
            invoice_id=data.get("invoice_id", ""),
            customer_id=data.get("customer_id", ""),
            amount=data.get("amount", 0.0),
            currency=data.get("currency", "USD"),
            method=data.get("method", "bank_transfer"),
            status=PaymentStatus(data.get("status", "pending")),
            transaction_ref=data.get("transaction_ref", ""),
            idempotency_key=data.get("idempotency_key"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            processed_at=datetime.fromisoformat(data["processed_at"]) if data.get("processed_at") else None
        )


@dataclass
class Invoice:
    """Invoice entity for billing."""
    id: str = field(default_factory=lambda: str(uuid4()))
    order_id: str = ""
    customer_id: str = ""
    billing_address: Optional[Address] = None
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: datetime = field(default_factory=_utcnow)
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "billing_address": self.billing_address.to_dict() if self.billing_address else None,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total": self.total,
            "currency": self.currency,
            "status": self.status.value,
            "issue_date": self.issue_date.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_date": self.paid_date.isoformat() if self.paid_date else None,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Invoice":
        billing_address = None
        if data.get("billing_address"):
            billing_address = Address.from_dict(data["billing_address"])
        return cls(
            id=data.get("id", str(uuid4())),
            order_id=data.get("order_id", ""),
            customer_id=data.get("customer_id", ""),
            billing_address=billing_address,
            subtotal=data.get("subtotal", 0.0),
            tax=data.get("tax", 0.0),
            total=data.get("total", 0.0),
            currency=data.get("currency", "USD"),
            status=InvoiceStatus(data.get("status", "draft")),
            issue_date=datetime.fromisoformat(data["issue_date"]) if data.get("issue_date") else datetime.now(timezone.utc),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            paid_date=datetime.fromisoformat(data["paid_date"]) if data.get("paid_date") else None,
            idempotency_key=data.get("idempotency_key"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        )


@dataclass
class OrderSnapshot:
    """State snapshot for crash recovery (NFR 2.3)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: Optional[datetime] = None
    order_id: str = ""
    status: str = ""
    pending_operations: List[str] = field(default_factory=list)
    last_processed_event: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "order_id": self.order_id,
            "status": self.status,
            "pending_operations": self.pending_operations,
            "last_processed_event": self.last_processed_event
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrderSnapshot":
        return cls(
            id=data.get("id", str(uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(timezone.utc),
            order_id=data["order_id"],
            status=data["status"],
            pending_operations=data.get("pending_operations", []),
            last_processed_event=data.get("last_processed_event", "")
        )
