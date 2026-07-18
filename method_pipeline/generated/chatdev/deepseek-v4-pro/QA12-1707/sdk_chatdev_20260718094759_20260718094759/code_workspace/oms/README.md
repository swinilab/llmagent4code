# Order Management System (OMS)

Production-grade, backend-only e-commerce Order Management System.

---

## 1. NFR Traceability Matrix

| NFR | Requirement | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------|------------------------|-------------------|---------------------|
| **1.1** | Response Time — core journeys must minimise round-trip latency under load | Async FastAPI + aiosqlite WAL mode + connection pooling + selectin eager loading | `src/database.py`, `src/models/*.py` (relationship lazy="selectin") | Run `time curl` on `/api/v1/products/search?q=...`; observe sub-50ms p95 under 100 concurrent users |
| **1.2** | Concurrency & Resource Utilisation — exploit server resources with minimal queuing | Async I/O throughout (FastAPI + SQLAlchemy async) + StaticPool for SQLite + uvicorn multi-worker | `src/database.py` (async_sessionmaker, StaticPool), `src/main.py` (uvicorn workers) | Run `wrk -t4 -c100` against `/health`; verify CPU utilisation across all workers via `htop` |
| **1.3** | Queue Management — sudden spikes must not crash the system | Token-bucket rate limiter as ASGI middleware | `src/middleware/rate_limiter.py` | Send 500 req/s burst; observe 429 responses after burst threshold; no 5xx errors |
| **2.1** | Graceful Degradation — non-essential features degrade under resource contention | Circuit breaker decorator on non-core operations; core checkout paths remain unprotected | `src/middleware/circuit_breaker.py` | Artificially fail a decorated endpoint 5+ times; observe 503 responses; core order creation still works |
| **2.2** | Fault Detection & Recovery — detect internal failures and auto-recover | Circuit breaker half-open state + structured AppError hierarchy + global exception handlers | `src/middleware/circuit_breaker.py`, `src/middleware/error_handler.py`, `src/utils/exceptions.py` | Trigger failures, wait recovery timeout, observe successful half-open probe; check error_code in response body |
| **2.3** | State Preservation — restore operational state after crash | SQLite WAL mode + synchronous=NORMAL + transactional session commits | `src/database.py` (PRAGMA journal_mode=WAL, PRAGMA synchronous=NORMAL) | Kill -9 the process mid-order; restart; verify pending orders are intact via `GET /api/v1/orders/status/pending` |

---

## 2. Architectural Decision Records (ADR)

### ADR-001: pydantic-settings for configuration
- **Decision:** Use pydantic-settings with `.env` file support.
- **Context:** NFR 2.3 (State Preservation) — deterministic, validated config reduces crash surface.
- **Alternatives:** (a) `os.environ` directly — no validation, silent misconfiguration; (b) `python-decouple` — less type-safe, no nested models.
- **Consequences:** Adds pydantic dependency; strict validation at startup catches misconfiguration early.

### ADR-002: Async SQLAlchemy + aiosqlite (WAL mode)
- **Decision:** SQLAlchemy 2.0 async engine with aiosqlite driver, WAL journal mode.
- **Context:** NFR 1.2 (Concurrency), NFR 2.3 (State Preservation).
- **Alternatives:** (a) PostgreSQL — heavier local setup, requires Docker; (b) raw aiosqlite — no ORM, manual SQL.
- **Consequences:** SQLite has limited concurrent writes; WAL mode mitigates this. Zero-install local deployment is the primary benefit.

### ADR-003: Single exception hierarchy (AppError)
- **Decision:** Custom exception classes inheriting from a base `AppError` with HTTP status codes.
- **Context:** NFR 2.2 (Fault Detection) — structured errors enable precise logging and monitoring.
- **Alternatives:** (a) plain `HTTPException` — no domain semantics; (b) RFC 7807 Problem Details — heavier serialisation.
- **Consequences:** Every service layer raise must use these; controllers catch and map via registered handlers.

### ADR-004: Repository pattern
- **Decision:** Thin async repository wrapping SQLAlchemy session per entity.
- **Context:** NFR 1.1 (Response Time) — repositories centralise query optimisation.
- **Alternatives:** (a) direct session in services — couples business logic to ORM; (b) raw SQL — loses type safety.
- **Consequences:** Adds a layer but isolates data-access tuning and testing.

### ADR-005: Centralised WorkflowService
- **Decision:** Dedicated `WorkflowService` that coordinates Order, Invoice, Payment services for the 7-step workflow.
- **Context:** NFR 1.1 (Response Time) — single service call for multi-step transitions reduces round-trips; NFR 2.3 (State Preservation) — transactional boundaries ensure consistency.
- **Alternatives:** (a) choreography via events — harder to reason about; (b) saga pattern — overkill for single-database system.
- **Consequences:** WorkflowService may grow; mitigated by delegating to entity services.

### ADR-006: In-memory token-bucket rate limiter
- **Decision:** Token-bucket algorithm with configurable rate and burst, implemented as ASGI middleware.
- **Context:** NFR 1.3 (Queue Management) — prevents sudden spikes from crashing the system.
- **Alternatives:** (a) Redis-based — adds infrastructure dependency; (b) fixed-window — less smooth under burst.
- **Consequences:** In-memory means per-process limits; acceptable for single-node deployment.

### ADR-007: Decorator-based circuit breaker
- **Decision:** In-process circuit breaker tracking failure counts per operation with half-open recovery.
- **Context:** NFR 2.1 (Graceful Degradation), NFR 2.2 (Fault Detection).
- **Alternatives:** (a) Hystrix/pybreaker library — external dependency; (b) envoy sidecar — overkill for single-node.
- **Consequences:** In-process state lost on restart; acceptable given NFR 2.3 handles state preservation at the database layer.

### ADR-008: Centralised exception-to-HTTP mapping
- **Decision:** Register FastAPI exception handlers for each `AppError` subclass.
- **Context:** NFR 2.2 (Fault Detection) — consistent error shapes aid monitoring.
- **Alternatives:** (a) middleware catch-all — less granular; (b) per-controller try/except — duplicates code.
- **Consequences:** All services must raise `AppError` subclasses for this to work.

---

## 3. Data Architecture

### Schema Narrative

The OMS uses a **relational model** with five core entities stored in a single SQLite database file (`oms.db`). SQLite was chosen for zero-install local deployment; WAL mode provides adequate concurrent read performance.

**Entity Relationships:**
```
Customer 1──N Order 1──N Payment
                │
                └──1 Invoice
```

- **Customer** owns many **Orders**.
- Each **Order** may have many **Payment** attempts.
- Each **Order** has at most one **Invoice** (1:1 enforced by UNIQUE constraint on `invoices.order_id`).

### Complete Schema (SQL DDL equivalent)

```sql
CREATE TABLE customers (
    id              TEXT(32) PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    address         TEXT NOT NULL,
    phone           VARCHAR(30) NOT NULL,
    banking_details TEXT NOT NULL DEFAULT '',
    role            VARCHAR(20) NOT NULL DEFAULT 'customer',
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE products (
    id          TEXT(32) PRIMARY KEY,
    description TEXT NOT NULL,
    base_price  NUMERIC(12,2) NOT NULL,
    currency    VARCHAR(3) NOT NULL DEFAULT 'USD',
    created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE orders (
    id          TEXT(32) PRIMARY KEY,
    customer_id TEXT(32) NOT NULL REFERENCES customers(id),
    line_items  TEXT NOT NULL,          -- JSON array of {product_id, description, quantity, unit_price}
    subtotal    NUMERIC(12,2) NOT NULL,
    tax         NUMERIC(12,2) NOT NULL DEFAULT 0,
    total       NUMERIC(12,2) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','accepted','invoiced','paid','shipped','closed','cancelled')),
    invoice_id  TEXT(32),
    created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_orders_customer_id ON orders(customer_id);

CREATE TABLE payments (
    id          TEXT(32) PRIMARY KEY,
    order_id    TEXT(32) NOT NULL REFERENCES orders(id),
    amount      NUMERIC(12,2) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','completed','failed','refunded')),
    method      VARCHAR(20) NOT NULL DEFAULT 'bank_transfer'
                CHECK(method IN ('bank_transfer','credit_card','debit_card','wallet')),
    created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_payments_order_id ON payments(order_id);

CREATE TABLE invoices (
    id           TEXT(32) PRIMARY KEY,
    order_id     TEXT(32) NOT NULL UNIQUE REFERENCES orders(id),
    billing_info TEXT NOT NULL,
    subtotal     NUMERIC(12,2) NOT NULL,
    tax          NUMERIC(12,2) NOT NULL DEFAULT 0,
    total        NUMERIC(12,2) NOT NULL,
    issue_date   DATE NOT NULL,
    due_date     DATE NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'draft'
                 CHECK(status IN ('draft','issued','paid','overdue','cancelled')),
    created_at   DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at   DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_invoices_order_id ON invoices(order_id);
```

### Order Status State Machine

```
PENDING ──→ ACCEPTED ──→ INVOICED ──→ PAID ──→ SHIPPED ──→ CLOSED
   │            │            │           │
   └────────────┴────────────┴───────────┴──→ CANCELLED (from any pre-shipped state)
```

---

## 4. Shared Domain Models

All domain models are defined in `src/models/` as SQLAlchemy ORM classes and in `src/schemas/` as Pydantic models. The Pydantic schemas serve as the API contract (shared between FE and BE) while the ORM models are internal.

| Entity   | ORM Model              | API Schema (Request)    | API Schema (Response)     |
|----------|------------------------|-------------------------|---------------------------|
| Customer | `models.Customer`      | `schemas.CustomerCreate` / `CustomerUpdate` | `schemas.CustomerResponse` |
| Product  | `models.Product`       | `schemas.ProductCreate` / `ProductUpdate`   | `schemas.ProductResponse`  |
| Order    | `models.Order`         | `schemas.OrderCreate` / `OrderStatusUpdate` | `schemas.OrderResponse`    |
| Payment  | `models.Payment`       | `schemas.PaymentCreate` / `PaymentVerify`   | `schemas.PaymentResponse`  |
| Invoice  | `models.Invoice`       | `schemas.InvoiceCreate`                     | `schemas.InvoiceResponse`  |

---

## 5. Complete Backend Code

All code is under `src/`. See the file listing below for the complete structure.

---

## 6. Infrastructure as Code (IaC)

### Project Structure

```
oms/
├── pyproject.toml
├── README.md
├── .env                          # Optional: override defaults
└── src/
    ├── __init__.py
    ├── main.py                   # FastAPI app factory + entry point
    ├── config.py                 # pydantic-settings configuration
    ├── database.py               # Async engine, session, init_db
    ├── models/
    │   ├── __init__.py
    │   ├── base.py               # DeclarativeBase + TimestampMixin
    │   ├── customer.py
    │   ├── product.py
    │   ├── order.py              # OrderStatus enum + state machine
    │   ├── payment.py
    │   └── invoice.py
    ├── schemas/
    │   ├── __init__.py
    │   ├── customer.py
    │   ├── product.py
    │   ├── order.py
    │   ├── payment.py
    │   └── invoice.py
    ├── repositories/
    │   ├── __init__.py
    │   ├── base.py               # Generic BaseRepository[ModelT]
    │   ├── customer.py
    │   ├── product.py
    │   ├── order.py
    │   ├── payment.py
    │   └── invoice.py
    ├── services/
    │   ├── __init__.py
    │   ├── customer.py
    │   ├── product.py
    │   ├── order.py
    │   ├── payment.py
    │   ├── invoice.py
    │   └── workflow.py           # 7-step workflow orchestration
    ├── controllers/
    │   ├── __init__.py
    │   ├── customer.py
    │   ├── product.py
    │   ├── order.py
    │   ├── payment.py
    │   ├── invoice.py
    │   └── workflow.py
    ├── middleware/
    │   ├── __init__.py
    │   ├── rate_limiter.py        # Token-bucket ASGI middleware
    │   ├── circuit_breaker.py     # Decorator-based circuit breaker
    │   └── error_handler.py       # AppError → HTTP mapping
    └── utils/
        ├── __init__.py
        └── exceptions.py          # AppError hierarchy
```

---

## 7. Local Deployment Guide

### Prerequisites
- Python 3.11+
- `uv` (or `pip`)

### Quick Start

```bash
# 1. Navigate to the oms directory
cd oms

# 2. Install dependencies
uv sync

# 3. (Optional) Create .env for custom settings
cat > .env << 'EOF'
HOST=0.0.0.0
PORT=8000
WORKERS=4
DATABASE_URL=sqlite+aiosqlite:///./oms.db
RATE_LIMIT_REQUESTS_PER_SECOND=100
RATE_LIMIT_BURST_SIZE=200
EOF

# 4. Run the server
uv run oms

# Or directly:
uv run python -m src.main
```

The server starts at `http://localhost:8000`.  
API docs: `http://localhost:8000/docs`  
OpenAPI spec: `http://localhost:8000/api/v1/openapi.json`

---

## 8. Verification Steps (NFR Observability)

### NFR 1.1 — Response Time

```bash
# Start server, then:
# Create a product first
curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Test Widget","base_price":"19.99","currency":"USD"}'

# Measure search latency
time curl -s http://localhost:8000/api/v1/products/search?q=Widget | jq .
# Expected: < 50ms
```

### NFR 1.2 — Concurrency

```bash
# Use wrk or ab to simulate concurrent load
wrk -t4 -c100 -d10s http://localhost:8000/health
# Observe: all requests succeed; check CPU usage across workers with htop
```

### NFR 1.3 — Queue Management

```bash
# Send a burst exceeding the rate limit
for i in $(seq 1 250); do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health &
done | sort | uniq -c
# Expected: mix of 200 and 429; no 5xx
```

### NFR 2.1 — Graceful Degradation

```bash
# The circuit breaker is available as a decorator. To test:
# Apply @circuit_breaker to a non-core endpoint, trigger failures,
# observe 503 responses while core endpoints still return 200.
```

### NFR 2.2 — Fault Detection & Recovery

```bash
# Trigger a 404
curl -s http://localhost:8000/api/v1/customers/nonexistent | jq .
# Expected: {"detail":"Customer nonexistent not found","error_code":"NOT_FOUND"}

# Trigger a 409
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","address":"123 St","phone":"555-0001"}'
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Test2","address":"456 St","phone":"555-0001"}'
# Second call returns 409 with error_code CONFLICT
```

### NFR 2.3 — State Preservation

```bash
# 1. Create a customer and place an order
CUST=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Crash Test","address":"1 Crash Ave","phone":"555-CRASH"}')
CUST_ID=$(echo $CUST | jq -r '.id')

PROD=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Crash Widget","base_price":"9.99"}')
PROD_ID=$(echo $PROD | jq -r '.id')

ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUST_ID\",\"line_items\":[{\"product_id\":\"$PROD_ID\",\"description\":\"Crash Widget\",\"quantity\":1,\"unit_price\":\"9.99\"}]}")
ORDER_ID=$(echo $ORDER | jq -r '.id')

# 2. Kill the server (SIGKILL)
kill -9 $(pgrep -f "uvicorn src.main")

# 3. Restart
uv run oms &

# 4. Verify order survived
curl -s http://localhost:8000/api/v1/orders/$ORDER_ID | jq '.status'
# Expected: "pending"
```

---

## API Endpoints Summary

### Customers
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/customers` | Create customer |
| GET | `/api/v1/customers` | List customers |
| GET | `/api/v1/customers/search?q=` | Search by name |
| GET | `/api/v1/customers/{id}` | Get customer |
| PATCH | `/api/v1/customers/{id}` | Update customer |
| DELETE | `/api/v1/customers/{id}` | Delete customer |

### Products
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/products` | Create product |
| GET | `/api/v1/products` | List products |
| GET | `/api/v1/products/search?q=` | Search products |
| GET | `/api/v1/products/{id}` | Get product |
| PATCH | `/api/v1/products/{id}` | Update product |
| DELETE | `/api/v1/products/{id}` | Delete product |

### Orders
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/orders` | Place order |
| GET | `/api/v1/orders` | List orders |
| GET | `/api/v1/orders/{id}` | Get order |
| GET | `/api/v1/orders/customer/{id}` | Orders by customer |
| GET | `/api/v1/orders/status/{status}` | Orders by status |
| PATCH | `/api/v1/orders/{id}/status` | Transition status |

### Payments
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/payments` | Create payment |
| GET | `/api/v1/payments` | List payments |
| GET | `/api/v1/payments/{id}` | Get payment |
| GET | `/api/v1/payments/order/{id}` | Payments by order |
| PATCH | `/api/v1/payments/{id}/verify` | Verify payment |

### Invoices
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/invoices` | Create invoice |
| GET | `/api/v1/invoices` | List invoices |
| GET | `/api/v1/invoices/{id}` | Get invoice |
| GET | `/api/v1/invoices/order/{id}` | Invoice by order |

### Workflow (7-step)
| Method | Path | Step | Description |
|--------|------|------|-------------|
| POST | `/api/v1/workflow/staff/accept/{order_id}` | 2 | Staff accepts order |
| POST | `/api/v1/workflow/accountant/invoice` | 3 | Accountant creates invoice |
| POST | `/api/v1/workflow/customer/pay` | 4 | Customer pays |
| POST | `/api/v1/workflow/accountant/verify/{payment_id}` | 5 | Accountant verifies payment |
| POST | `/api/v1/workflow/staff/ship/{order_id}` | 6 | Staff ships order |
| POST | `/api/v1/workflow/staff/close/{order_id}` | 7 | Staff closes order |
