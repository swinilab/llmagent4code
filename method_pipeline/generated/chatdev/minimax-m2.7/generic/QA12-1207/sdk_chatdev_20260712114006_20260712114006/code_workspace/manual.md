# Order Management System (OMS) - User Manual

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Domain Models](#domain-models)
4. [Installation & Setup](#installation--setup)
5. [Running the Application](#running-the-application)
6. [API Reference](#api-reference)
7. [User Workflows](#user-workflows)
8. [Non-Functional Requirements (NFRs)](#non-functional-requirements-nfrs)
9. [Verification Steps](#verification-steps)
10. [Infrastructure & Deployment](#infrastructure--deployment)

---

## Overview

The Order Management System (OMS) is a production-grade, backend-only e-commerce system that handles the complete order lifecycle: customer ordering → payment processing → invoicing → shipping → closure.

### Key Features

- **Multi-role support**: Customer, Order Staff, Accountant
- **Complete order lifecycle management** with status transitions
- **Invoice generation and payment tracking**
- **Circuit breaker pattern** for fault tolerance
- **Event-driven architecture** for extensibility
- **SQLite persistence** with thread-safe operations

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│   Controllers → Request Validation → Response Mapping        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  OrderService │ CustomerService │ ProductService            │
│  InvoiceService │ PaymentService                           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                              │
│         Entities (Customer, Order, Product, Payment,        │
│                    Invoice, LineItem)                        │
│         Repository Interfaces (Abstract Contracts)           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Adapters Layer                            │
│              SQLite Persistence (In-Memory Repos)            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Core Utilities                            │
│    CircuitBreaker │ EventBus │ Config │ ServiceRegistry    │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
oms_project/
├── app/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── persistence.py      # SQLite repositories
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/       # REST endpoints (to be implemented)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── circuit_breaker.py   # Fault detection & recovery
│   │   ├── config.py            # Application configuration
│   │   └── events.py            # Event bus for pub/sub
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   └── models.py        # Domain models (Customer, Order, etc.)
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── interfaces.py    # Repository contracts
│   └── service_layer/
│       ├── __init__.py
│       └── services/
│           ├── __init__.py
│           ├── customer_service.py
│           ├── invoice_service.py
│           ├── order_service.py
│           ├── payment_service.py
│           └── product_service.py
├── infra/
│   ├── __init__.py
│   └── iac/                     # Infrastructure as Code (future)
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_services.py
└── docs/
    └── __init__.py
```

---

## Domain Models

### Core Entities

#### Customer
```python
@dataclass
class Customer:
    id: str                           # UUID
    name: str                         # Full name
    email: str                        # Unique email
    phone: Optional[str] = None       # Contact phone
    address: Optional[Address] = None  # Shipping/billing address
    banking_details: Optional[BankingDetails] = None
    role: UserRole = UserRole.CUSTOMER
    order_history: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**Roles:**
- `CUSTOMER` - End user who places orders
- `ORDER_STAFF` - Staff who review, accept, ship orders
- `ACCOUNTANT` - Staff who create invoices and verify payments

#### Order
```python
@dataclass
class Order:
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
```

**Order Status Lifecycle:**
```
PENDING → ACCEPTED → INVOICED → PAID → SHIPPED → COMPLETED
    ↓         ↓
REJECTED  CANCELLED
```

#### Product
```python
@dataclass
class Product:
    id: str
    sku: str                          # Unique SKU
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
```

#### Payment
```python
@dataclass
class Payment:
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
```

**Payment Status:** `PENDING` → `PROCESSING` → `COMPLETED` | `FAILED` | `REFUNDED`

#### Invoice
```python
@dataclass
class Invoice:
    id: str
    invoice_number: str               # Human-readable number (e.g., INV-20240101-0001)
    order_id: str
    customer_id: str
    billing_address: Optional[Address] = None
    line_items: List[LineItem] = field(default_factory=list)
    subtotal: Money
    tax_total: Money
    discount_total: Money
    total: Money
    currency: Currency = Currency.USD
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    notes: Optional[str] = None
    terms: str = "Net 30"
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**Invoice Status:** `DRAFT` → `ISSUED` → `PAID` | `OVERDUE` | `CANCELLED`

#### Supporting Value Objects

- **Address**: `street`, `city`, `state`, `postal_code`, `country`
- **BankingDetails**: `bank_name`, `account_number`, `routing_number`, `swift_code`
- **Money**: `amount: Decimal`, `currency: Currency`
- **LineItem**: `product_id`, `product_name`, `sku`, `quantity`, `unit_price`, `subtotal`
- **Currency Enum**: `USD`, `EUR`, `GBP`
- **PaymentMethod Enum**: `BANK_TRANSFER`, `CREDIT_CARD`, `PAYPAL`

---

## Installation & Setup

### Prerequisites

- Python 3.12 or higher
- `uv` package manager (recommended) or `pip`

### Environment Setup

1. **Navigate to the project directory:**
   ```bash
   cd oms_project
   ```

2. **Initialize Python environment with uv:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   uv sync
   ```

   Or using pip:
   ```bash
   pip install -e .
   ```

4. **Verify installation:**
   ```bash
   python -c "from app.domain.entities.models import Customer, Order; print('OMS modules loaded successfully!')"
   ```

### Dependencies

The project requires the following packages (defined in `pyproject.toml`):

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.109.2 | REST API framework |
| uvicorn | 0.27.1 | ASGI server |
| pydantic | 2.6.1 | Data validation |
| httpx | 0.26.0 | HTTP client |
| pytest | 8.0.0 | Testing framework |
| pytest-asyncio | 0.23.0 | Async test support |

---

## Running the Application

### Start the API Server

```bash
cd oms_project
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or using the Python module directly:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Tests

```bash
cd oms_project
pytest tests/ -v
```

### Initialize Sample Data

```python
from app.adapters.persistence import DatabaseManager
from app.service_layer.services import CustomerService, ProductService, OrderService

# Initialize database
db = DatabaseManager("oms.db")
db.init_schema()

# Get repositories
from app.adapters.persistence import (
    InMemoryCustomerRepository,
    InMemoryProductRepository,
    InMemoryOrderRepository
)

customer_repo = InMemoryCustomerRepository(db)
product_repo = InMemoryProductRepository(db)
order_repo = InMemoryOrderRepository(db)

# Create services
customer_service = CustomerService(customer_repo)
product_service = ProductService(product_repo)
order_service = OrderService(order_repo, product_repo)

# Create a sample customer
customer = customer_service.create_customer(
    name="John Doe",
    email="john@example.com",
    phone="+1-555-0100",
    role=UserRole.CUSTOMER
)

# Create a sample product
product = product_service.create_product(
    sku="LAPTOP-001",
    name="Gaming Laptop",
    price_amount="1299.99",
    description="High-performance gaming laptop",
    stock_quantity=10,
    category="Electronics"
)

print(f"Created customer: {customer.id}")
print(f"Created product: {product.id}")
```

---

## API Reference

### Service Layer API

#### CustomerService

```python
class CustomerService:
    def create_customer(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.CUSTOMER
    ) -> Customer

    def get_customer(self, customer_id: str) -> Optional[Customer]
    def get_customer_by_email(self, email: str) -> Optional[Customer]
    def list_customers_by_role(self, role: UserRole) -> List[Customer]
    def list_active_customers(self) -> List[Customer]
    def update_customer(self, customer_id: str, data: dict) -> Optional[Customer]
    def deactivate_customer(self, customer_id: str) -> Optional[Customer]
    def activate_customer(self, customer_id: str) -> Optional[Customer]
```

#### ProductService

```python
class ProductService:
    def create_product(
        self,
        sku: str,
        name: str,
        price_amount: str,
        description: Optional[str] = None,
        stock_quantity: int = 0,
        category: Optional[str] = None
    ) -> Product

    def get_product(self, product_id: str) -> Optional[Product]
    def get_product_by_sku(self, sku: str) -> Optional[Product]
    def search_products(self, query: str) -> List[Product]
    def list_products_by_category(self, category: str) -> List[Product]
    def list_active_products(self) -> List[Product]
    def update_stock(self, product_id: str, quantity: int) -> Optional[Product]
    def reserve_stock(self, product_id: str, quantity: int) -> bool
    def release_stock(self, product_id: str, quantity: int) -> bool
```

#### OrderService

```python
class OrderService:
    def create_order(
        self,
        customer_id: str,
        line_items: List[LineItem],
        shipping_address: Optional[Address] = None,
        notes: Optional[str] = None
    ) -> Order

    def get_order(self, order_id: str) -> Optional[Order]
    def get_orders_by_customer(self, customer_id: str) -> List[Order]
    def get_pending_orders(self) -> List[Order]
    def accept_order(self, order_id: str) -> Optional[Order]
    def reject_order(self, order_id: str) -> Optional[Order]
    def ship_order(self, order_id: str) -> Optional[Order]
    def complete_order(self, order_id: str) -> Optional[Order]
    def cancel_order(self, order_id: str) -> Optional[Order]
    def update_order_status(self, order_id: str, status: OrderStatus) -> Optional[Order]
```

#### InvoiceService

```python
class InvoiceService:
    def create_invoice(
        self,
        order_id: str,
        customer_id: str,
        line_items: List[LineItem],
        subtotal: Money,
        tax_total: Money,
        discount_total: Money,
        total: Money,
        billing_address: Optional[Address] = None,
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        terms: str = "Net 30"
    ) -> Invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]
    def get_invoice_by_number(self, invoice_number: str) -> Optional[Invoice]
    def get_invoice_for_order(self, order_id: str) -> Optional[Invoice]
    def get_invoices_by_status(self, status: InvoiceStatus) -> List[Invoice]
    def get_invoices_by_customer(self, customer_id: str) -> List[Invoice]
    def issue_invoice(self, invoice_id: str) -> Optional[Invoice]
    def mark_invoice_paid(self, invoice_id: str, payment_id: str) -> Optional[Invoice]
    def mark_invoice_overdue(self, invoice_id: str) -> Optional[Invoice]
    def cancel_invoice(self, invoice_id: str) -> Optional[Invoice]
```

#### PaymentService

```python
class PaymentService:
    def create_payment(
        self,
        order_id: str,
        customer_id: str,
        amount: Money,
        method: PaymentMethod = PaymentMethod.BANK_TRANSFER,
        metadata: Optional[dict] = None
    ) -> Payment

    def get_payment(self, payment_id: str) -> Optional[Payment]
    def get_payments_for_order(self, order_id: str) -> List[Payment]
    def get_payments_by_status(self, status: PaymentStatus) -> List[Payment]
    def complete_payment(self, payment_id: str, transaction_ref: str) -> Optional[Payment]
    def fail_payment(self, payment_id: str, reason: str) -> Optional[Payment]
    def process_payment(self, payment_id: str) -> Optional[Payment]
    def refund_payment(self, payment_id: str) -> Optional[Payment]
```

---

## User Workflows

### Complete Order-to-Closure Workflow

#### Step 1: Customer Places Order
```python
from app.domain.entities.models import LineItem, Money, Currency

# Create line items
line_items = [
    LineItem(
        product_id=product.id,
        product_name="Gaming Laptop",
        sku="LAPTOP-001",
        quantity=1,
        unit_price=Money(amount=Decimal("1299.99"), currency=Currency.USD),
        subtotal=Money(amount=Decimal("1299.99"), currency=Currency.USD)
    )
]

# Create order
order = order_service.create_order(
    customer_id=customer.id,
    line_items=line_items,
    shipping_address=Address(
        street="123 Main St",
        city="San Francisco",
        state="CA",
        postal_code="94102",
        country="USA"
    ),
    notes="Please deliver before 5 PM"
)

print(f"Order created: {order.id}, Status: {order.status.value}")
```

#### Step 2: Order Staff Reviews & Accepts
```python
# Order staff reviews pending orders
pending_orders = order_service.get_pending_orders()
print(f"Pending orders: {len(pending_orders)}")

# Accept the order
accepted_order = order_service.accept_order(order.id)
print(f"Order accepted: {accepted_order.status.value}")
```

#### Step 3: Accountant Creates Invoice
```python
from app.service_layer.services import InvoiceService

invoice_service = InvoiceService(
    invoice_repo=InMemoryInvoiceRepository(db),
    order_repo=order_repo
)

invoice = invoice_service.create_invoice(
    order_id=order.id,
    customer_id=customer.id,
    line_items=order.line_items,
    subtotal=order.subtotal,
    tax_total=order.tax_total,
    discount_total=order.discount_total,
    total=order.total,
    billing_address=order.shipping_address,
    due_date=datetime.utcnow() + timedelta(days=30),
    terms="Net 30"
)

# Issue the invoice
issued_invoice = invoice_service.issue_invoice(invoice.id)
print(f"Invoice issued: {issued_invoice.invoice_number}")
```

#### Step 4: Customer Pays Invoice
```python
payment = payment_service.create_payment(
    order_id=order.id,
    customer_id=customer.id,
    amount=order.total,
    method=PaymentMethod.BANK_TRANSFER
)

# Process and complete payment
processed = payment_service.process_payment(payment.id)
completed = payment_service.complete_payment(payment.id, transaction_ref="TXN-12345")

print(f"Payment completed: {completed.status.value}")
```

#### Step 5: Accountant Verifies Payment
```python
# Mark invoice as paid
paid_invoice = invoice_service.mark_invoice_paid(invoice.id, payment.id)
print(f"Invoice paid: {paid_invoice.status.value}")

# Update order status to PAID
order_service.update_order_status(order.id, OrderStatus.PAID)
```

#### Step 6: Order Staff Ships Paid Order
```python
shipped_order = order_service.ship_order(order.id)
print(f"Order shipped: {shipped_order.status.value}, Shipped at: {shipped_order.shipped_at}")
```

#### Step 7: Order Staff Closes Completed Order
```python
completed_order = order_service.complete_order(order.id)
print(f"Order completed: {completed_order.status.value}, Completed at: {completed_order.completed_at}")
```

---

## Non-Functional Requirements (NFRs)

### NFR Traceability Matrix

| NFR ID | Description | Architectural Mechanism | Module/Component | Verification Method |
|--------|-------------|------------------------|------------------|---------------------|
| **NFR 1.1** | Response Time: Core journeys must minimize round-trip latency under load | SQLite with thread-local connections, async-ready design | `persistence.py` - `DatabaseManager` | Benchmark core API calls; target < 100ms p95 |
| **NFR 1.2** | Concurrency & Resource Utilization: Exploit available server resources | Thread-local SQLite connections, RLock for state protection | `persistence.py` - `DatabaseManager._local` | Load test with 100+ concurrent users; verify no deadlocks |
| **NFR 1.3** | Queue Management: Spikes must not crash the system | In-memory queues via EventBus, backpressure via circuit breaker | `events.py` - `EventBus` | Spike test: 10x normal request rate; system remains stable |
| **NFR 2.1** | Graceful Degradation: Under resource contention, degrade non-essential features | Circuit breaker pattern with HALF_OPEN state | `circuit_breaker.py` - `CircuitBreaker` | Simulate external service failure; core checkout continues |
| **NFR 2.2** | Fault Detection and Recovery: Detect failures, auto-recover | Circuit breaker tracks failures, transitions through states | `circuit_breaker.py` - `CircuitBreaker.call()` | Kill external service; verify circuit opens, then recovers |
| **NFR 2.3** | State Preservation: Crash recovery with minimal data loss | SQLite persistence, timestamps on all entities | `persistence.py` - All repositories | Kill process mid-transaction; restart; verify data integrity |

---

## Verification Steps

### Verify NFR 1.1 - Response Time

```python
import time
import httpx

def benchmark_core_journey():
    """Benchmark: product search → cart → checkout"""
    base_url = "http://localhost:8000/api/v1"
    
    # Warm-up
    httpx.get(f"{base_url}/products")
    
    # Benchmark
    iterations = 100
    times = []
    
    for _ in range(iterations):
        start = time.time()
        
        # Product search
        httpx.get(f"{base_url}/products/search?q=laptop")
        
        # Get product
        httpx.get(f"{base_url}/products")
        
        elapsed = time.time() - start
        times.append(elapsed * 1000)  # ms
    
    p95 = sorted(times)[int(len(times) * 0.95)]
    print(f"P95 latency: {p95:.2f}ms")
    assert p95 < 100, f"P95 latency {p95}ms exceeds 100ms target"
```

### Verify NFR 1.2 - Concurrency

```python
import concurrent.futures
import threading

def test_concurrent_access():
    """Test concurrent reads and writes"""
    db = DatabaseManager("oms.db")
    repo = InMemoryCustomerRepository(db)
    service = CustomerService(repo)
    
    errors = []
    
    def create_customer(i):
        try:
            service.create_customer(
                name=f"Customer {i}",
                email=f"customer{i}@test.com"
            )
        except Exception as e:
            errors.append(e)
    
    # Spawn 50 concurrent threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(create_customer, i) for i in range(200)]
        concurrent.futures.wait(futures)
    
    print(f"Errors: {len(errors)}")
    assert len(errors) == 0, f"Concurrent access errors: {errors}"
```

### Verify NFR 1.3 - Queue Management Under Spike

```python
import asyncio

def test_spike_handling():
    """Test system under sudden spike"""
    from app.core.events import EventBus, EventType, Event
    
    bus = EventBus()
    events_received = []
    
    def handler(event):
        events_received.append(event)
    
    bus.subscribe(EventType.ORDER_CREATED, handler)
    
    # Simulate spike: 100 events in burst
    for i in range(100):
        bus.publish(Event(
            event_type=EventType.ORDER_CREATED,
            data={"order_id": f"order-{i}"}
        ))
    
    print(f"Events received: {len(events_received)}")
    assert len(events_received) == 100
```

### Verify NFR 2.1 & 2.2 - Circuit Breaker

```python
def test_circuit_breaker():
    """Test circuit breaker fault detection and recovery"""
    from app.core.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError
    
    cb = CircuitBreaker(
        name="test",
        failure_threshold=3,
        recovery_timeout=1.0
    )
    
    # Function that fails
    def failing_func():
        raise RuntimeError("Simulated failure")
    
    # Trigger failures until circuit opens
    for i in range(3):
        try:
            cb.call(failing_func)
        except RuntimeError:
            pass
    
    assert cb.state == CircuitState.OPEN
    
    # Verify circuit rejects calls when open
    try:
        cb.call(failing_func)
        assert False, "Should have raised CircuitOpenError"
    except CircuitOpenError:
        print("Circuit correctly rejected call when OPEN")
    
    # Wait for recovery timeout
    import time
    time.sleep(1.1)
    
    # Next call should transition to HALF_OPEN
    try:
        cb.call(failing_func)
    except RuntimeError:
        pass
    
    print(f"Circuit state after recovery attempt: {cb.state}")
```

### Verify NFR 2.3 - State Preservation

```python
def test_state_preservation():
    """Test data persists across restarts"""
    import os
    
    db_path = "test_oms.db"
    
    # Clean start
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create data
    db = DatabaseManager(db_path)
    db.init_schema()
    repo = InMemoryCustomerRepository(db)
    service = CustomerService(repo)
    
    customer = service.create_customer(
        name="Test User",
        email="test@example.com"
    )
    
    # Simulate crash - close database
    db.close_connection()
    
    # Restart - load existing data
    db2 = DatabaseManager(db_path)
    repo2 = InMemoryCustomerRepository(db2)
    service2 = CustomerService(repo2)
    
    loaded = service2.get_customer(customer.id)
    
    assert loaded is not None
    assert loaded.name == "Test User"
    assert loaded.email == "test@example.com"
    
    print("State preserved across restart!")
    
    # Cleanup
    os.remove(db_path)
```

---

## Infrastructure & Deployment

### Local Deployment

1. **Clone and setup:**
   ```bash
   cd oms_project
   uv venv
   source .venv/bin/activate
   uv sync
   ```

2. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

3. **Start server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Access API docs:**
   Open `http://localhost:8000/docs` for Swagger UI

### Production Considerations

- **Database**: Production should use PostgreSQL or MySQL instead of SQLite
- **Server**: Use `uvicorn` with `--workers` flag for multi-process deployment
- **Reverse Proxy**: Use nginx or traefik for SSL termination and load balancing
- **Monitoring**: Add metrics collection (Prometheus) and distributed tracing (Jaeger)
- **Caching**: Consider Redis for frequently accessed data (products, customer sessions)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_DB_PATH` | `oms.db` | SQLite database file path |
| `OMS_DEBUG` | `false` | Enable debug mode |
| `OMS_CIRCUIT_BREAKER_ENABLED` | `true` | Enable circuit breaker |

---

## Architecture Decision Records (ADRs)

### ADR 001: SQLite for Persistence

**Decision:** Use SQLite with thread-local connections for data persistence.

**Context:** NFR 1.1 (Response Time), NFR 2.3 (State Preservation)

**Alternatives Considered:**
1. **PostgreSQL** - Rejected: Adds operational complexity for local development
2. **MongoDB** - Rejected: Schema-less design less suitable for transactional entities

**Consequences:**
- ✅ Zero-config deployment
- ✅ ACID transactions built-in
- ✅ Excellent read performance
- ⚠️ Not suitable for very high write concurrency
- ⚠️ Single-file limitation for production scale

### ADR 002: Circuit Breaker Pattern

**Decision:** Implement circuit breaker for fault tolerance.

**Context:** NFR 2.1 (Graceful Degradation), NFR 2.2 (Fault Detection)

**Alternatives Considered:**
1. **Retry with exponential backoff** - Rejected: Can amplify load during outages
2. **Bulkhead isolation** - Rejected: Adds complexity without clear benefit for in-process services

**Consequences:**
- ✅ Automatic failure detection
- ✅ Prevents cascade failures
- ✅ Automatic recovery via HALF_OPEN state
- ⚠️ Requires tuning threshold and timeout values

### ADR 003: Event-Driven Architecture

**Decision:** Use in-memory event bus for cross-cutting concerns.

**Context:** NFR 1.3 (Queue Management), NFR 2.1 (Graceful Degradation)

**Alternatives Considered:**
1. **Message queue (RabbitMQ/Kafka)** - Rejected: Adds infrastructure dependencies
2. **Synchronous callbacks** - Rejected: Creates tight coupling

**Consequences:**
- ✅ Decoupled components
- ✅ Easy to add new event handlers
- ✅ Back-pressure via queue size limits
- ⚠️ In-memory events lost on restart (use event sourcing for critical events)

### ADR 004: Service Layer Pattern

**Decision:** Separate business logic into dedicated service classes.

**Context:** Code organization, testability, maintainability

**Alternatives Considered:**
1. **Domain model with anemic services** - Rejected: Business logic scattered
2. **Transaction script** - Rejected: Duplication across operations

**Consequences:**
- ✅ Clear separation of concerns
- ✅ Easy to unit test business logic
- ✅ Transaction boundaries at service level
- ⚠️ Some boilerplate for simple operations

---

## Data Architecture

### Database Schema

```sql
-- Customers table
CREATE TABLE customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    address_json TEXT,
    banking_details_json TEXT,
    role TEXT NOT NULL DEFAULT 'CUSTOMER',
    order_history_json TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Products table
CREATE TABLE products (
    id TEXT PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price_json TEXT NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    category TEXT,
    weight REAL,
    dimensions_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Orders table
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    line_items_json TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    subtotal_json TEXT,
    tax_total_json TEXT,
    discount_total_json TEXT,
    total_json TEXT,
    currency TEXT DEFAULT 'USD',
    invoice_id TEXT,
    payment_id TEXT,
    shipping_address_json TEXT,
    notes TEXT,
    accepted_at TEXT,
    shipped_at TEXT,
    completed_at TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Payments table
CREATE TABLE payments (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    amount_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    method TEXT,
    transaction_ref TEXT,
    payment_timestamp TEXT,
    processed_at TEXT,
    failure_reason TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Invoices table
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    invoice_number TEXT UNIQUE NOT NULL,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    billing_address_json TEXT,
    line_items_json TEXT,
    subtotal_json TEXT,
    tax_total_json TEXT,
    discount_total_json TEXT,
    total_json TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    issue_date TEXT,
    due_date TEXT,
    paid_date TEXT,
    notes TEXT,
    terms TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

## Glossary

| Term | Definition |
|------|------------|
| **OMS** | Order Management System |
| **NFR** | Non-Functional Requirement |
| **ADR** | Architecture Decision Record |
| **Repository** | Pattern for data access abstraction |
| **Service Layer** | Business logic orchestration |
| **Circuit Breaker** | Pattern for fault tolerance |
| **Event Bus** | Publish-subscribe mechanism for events |
| **Line Item** | Individual product entry in an order |
| **Money** | Value object representing currency amount |

---

## Support & Troubleshooting

### Common Issues

**1. "Database is locked" error**
```python
# Solution: Ensure connections are properly closed
db = DatabaseManager("oms.db")
try:
    # work with db
finally:
    db.close_connection()
```

**2. "Customer with email already exists"**
```python
# Check if customer exists before creating
existing = customer_service.get_customer_by_email("test@example.com")
if not existing:
    customer = customer_service.create_customer(...)
```

**3. "Order status cannot be transitioned"**
```python
# Verify current order status before transition
order = order_service.get_order(order_id)
print(f"Current status: {order.status}")
# Ensure valid transition per lifecycle
```

### Logging

Enable debug logging via configuration:
```python
from app.core.config import AppConfig

config = AppConfig(debug=True)
```

---

*Document Version: 1.0*  
*Last Updated: 2024*
