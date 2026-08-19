# Order Management System (OMS) - Data Architecture

## Overview

The OMS uses a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  - REST endpoints                                           │
│  - Request/Response validation                              │
│  - Exception handling                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  - Business logic                                           │
│  - Transaction orchestration                                │
│  - Rate limiting (NFR 1.1)                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repository Layer                            │
│  - Data persistence (SQLite)                                │
│  - Thread-safe operations                                   │
│  - State resynchronization (NFR 2.3)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database (SQLite)                          │
│  - ACID transactions (NFR 2.4)                              │
│  - Persistent storage (NFR 1.2)                             │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### Table: customers
```sql
CREATE TABLE customers (
    id TEXT PRIMARY KEY,           -- UUIDv4
    data TEXT NOT NULL,            -- JSON serialized Customer
    created_at TEXT NOT NULL       -- ISO 8601 timestamp
);
```

### Table: products
```sql
CREATE TABLE products (
    id TEXT PRIMARY KEY,           -- UUIDv4
    data TEXT NOT NULL,            -- JSON serialized Product
    created_at TEXT NOT NULL       -- ISO 8601 timestamp
);
```

### Table: orders
```sql
CREATE TABLE orders (
    id TEXT PRIMARY KEY,           -- UUIDv4
    data TEXT NOT NULL,            -- JSON serialized Order
    created_at TEXT NOT NULL       -- ISO 8601 timestamp
);
```

### Table: payments
```sql
CREATE TABLE payments (
    id TEXT PRIMARY KEY,           -- UUIDv4
    data TEXT NOT NULL,            -- JSON serialized Payment
    created_at TEXT NOT NULL       -- ISO 8601 timestamp
);
```

### Table: invoices
```sql
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,           -- UUIDv4
    data TEXT NOT NULL,            -- JSON serialized Invoice
    created_at TEXT NOT NULL       -- ISO 8601 timestamp
);
```

## Entity Relationships

```
Customer (1) ──────< Order (N) >────── (1) Invoice
     │                   │                    │
     │                   │                    │
     └── orderHistory    │                    └── orderRef
                         │
                         │
                    Payment (N)
                         │
                         └── orderRef
```

## Data Flow

### Order Creation Flow
1. Customer POSTs to `/api/v1/orders`
2. Controller validates request body using Pydantic
3. OrderService validates customerRef and productRef existence
4. OrderService computes unitPriceSnapshot from Product.price
5. OrderService computes totalAmount from line items
6. OrderRepository saves order to SQLite
7. CustomerService adds order ID to customer's orderHistory
8. Response returns created Order with 201 status

### Invoice Creation Flow (Atomic Transaction)
1. Accountant POSTs to `/api/v1/invoices`
2. InvoiceService validates order is in ACCEPTED status
3. InvoiceService copies billing info from Customer
4. InvoiceService sets totalAmount from Order
5. InvoiceRepository saves invoice
6. OrderRepository updates order.invoiceRef and order.status
7. Both operations complete atomically (transaction)

### Payment Verification Flow
1. Accountant POSTs to `/api/v1/payments/{id}/verify`
2. PaymentService validates payment is PENDING
3. PaymentService updates payment status to VERIFIED
4. OrderRepository updates order status to PAID
5. InvoiceRepository updates invoice status to PAID

## NFR Implementation Details

### NFR 1.1 - Rate Limiting
- Token bucket algorithm in `RateLimiter` class
- 100 events per 60-second window (configurable)
- Thread-safe with `threading.Lock`
- Applied to all service create operations

### NFR 1.2 - Multiple Data Copies
- In-memory Python objects (Pydantic models)
- SQLite database persistence
- JSON serialization for storage
- Data survives application restarts

### NFR 2.1 - Exception Detection (Timeout)
- Middleware timeout of 30 seconds
- `asyncio.wait_for` for async timeout
- Returns 504 Gateway Timeout on exceedance
- X-Response-Time header for monitoring

### NFR 2.2 - Graceful Degradation
- Global exception handlers for ValueError (400) and KeyError (404)
- Prevents 500 Internal Server Error crashes
- Maintains API availability during validation failures

### NFR 2.3 - State Resynchronization
- Thread-safe repository operations with `threading.Lock`
- Database serves as single source of truth
- In-memory state rebuilt from database on startup

### NFR 2.4 - Transactions
- SQLite ACID transactions via `conn.commit()`
- Invoice creation updates both invoice and order atomically
- Payment verification updates payment, order, and invoice atomically
