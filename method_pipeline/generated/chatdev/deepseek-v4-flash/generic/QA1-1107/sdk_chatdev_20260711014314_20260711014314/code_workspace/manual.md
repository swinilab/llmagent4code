# Order Management System (OMS) — User Manual

> **Version:** 1.0.0  
> **Tech Stack:** FastAPI (async) · SQLAlchemy 2.0 · Pydantic v2 · SQLite/PostgreSQL · Celery + Redis  
> **API Base URL:** `http://localhost:8000`  
> **Interactive Docs:** `http://localhost:8000/docs` (Swagger UI) · `http://localhost:8000/redoc` (ReDoc)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Installation & Setup](#3-installation--setup)
4. [Quick Start Guide](#4-quick-start-guide)
5. [Complete 7-Step Workflow](#5-complete-7-step-workflow)
6. [API Reference](#6-api-reference)
7. [Roles & Permissions](#7-roles--permissions)
8. [Database Schema](#8-database-schema)
9. [Configuration](#9-configuration)
10. [Testing & Verification](#10-testing--verification)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that manages the complete order lifecycle:

1. **Customer** places an order
2. **Order Staff** reviews and accepts the order
3. **Accountant** creates an invoice
4. **Customer** pays the invoice
5. **Accountant** verifies the payment
6. **Order Staff** ships the paid order
7. **Order Staff** closes the completed order

The system serves three distinct roles — **Customer**, **Order Staff**, and **Accountant** — and is designed to handle non-trivial traffic with rate limiting, background task processing, and connection pooling.

---

## 2. System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Customer  │  │ Product  │  │  Order   │  │ Payment  │   │
│  │Controller│  │Controller│  │Controller│  │Controller│   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐    │
│  │              Service Layer (Business Logic)        │    │
│  └────┬─────────────┬─────────────┬─────────────┬────┘    │
│       │             │             │             │          │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐    │
│  │         Workflow Layer (Orchestration)               │    │
│  └────┬─────────────┬─────────────┬─────────────┬────┘    │
│       │             │             │             │          │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐    │
│  │              Data Layer (SQLAlchemy ORM)           │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Background Task Processor (asyncio)         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Middleware: Rate Limiter + Request Logger          │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure

```
oms/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration via pydantic-settings
│   ├── database.py          # Async engine, session, base model
│   ├── enums.py             # Domain enums (OrderStatus, etc.)
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── customer.py
│   │   ├── order.py
│   │   ├── product.py
│   │   ├── payment.py
│   │   └── invoice.py
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic layer
│   ├── controllers/         # REST API routers
│   ├── workflows/           # Order workflow orchestrator
│   ├── tasks/               # Background task processing
│   └── middleware/          # Rate limiter, request logger
├── alembic/                 # Database migrations
├── scripts/
│   ├── seed_data.py         # Populate sample data
│   ├── test_workflow.py     # Full 7-step workflow test
│   └── ...                  # Other utility scripts
├── docs/
│   ├── ADR.md               # Architectural Decision Records
│   ├── DATA_ARCHITECTURE.md # Data model documentation
│   ├── DEPLOYMENT_GUIDE.md  # Deployment instructions
│   └── NFR_TRACEABILITY_MATRIX.md
├── Dockerfile               # Production container
├── docker-compose.yml       # Local deployment
├── openapi.yaml             # OpenAPI specification
└── pyproject.toml           # Python project config
```

---

## 3. Installation & Setup

### Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.12+ | `python --version` |
| uv | Latest | `uv --version` |
| Docker (optional) | Latest | `docker --version` |

### Option A: Local Installation (No Docker)

#### Step 1: Create Virtual Environment & Install Dependencies

```bash
# Create virtual environment
uv venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install all dependencies
uv sync
```

#### Step 2: Seed the Database

```bash
uv run python scripts/seed_data.py
```

This creates:
- **3 customers:** Alice Johnson (CUSTOMER), Bob Smith (ORDER_STAFF), Carol Williams (ACCOUNTANT)
- **8 products:** Headphones, USB-C Cable, Laptop Stand, Keyboard, Mouse, Monitor, Webcam, Desk Lamp

#### Step 3: Start the Server

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Step 4: Verify It's Running

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"Order Management System","version":"1.0.0"}
```

### Option B: Docker Deployment

```bash
# Build and start all services
docker compose up --build

# This starts:
#   - oms-api (FastAPI on port 8000)
#   - oms-redis (Redis on port 6379)
#   - oms-celery-worker (Celery worker)

# Seed data (if needed)
docker exec -it oms-api python scripts/seed_data.py
```

### Accessing the API

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Swagger UI (interactive docs) |
| `http://localhost:8000/redoc` | ReDoc (alternative docs) |
| `http://localhost:8000/openapi.json` | OpenAPI JSON spec |
| `http://localhost:8000/health` | Health check |

---

## 4. Quick Start Guide

### 4.1 Run the Complete Workflow Test

The fastest way to see the system in action:

```bash
# Ensure the server is running, then:
uv run python scripts/test_workflow.py
```

This script executes all 7 steps automatically and prints progress.

### 4.2 Manual Workflow via curl

Here's a complete walkthrough using `curl` commands:

```bash
# ─── SETUP ───────────────────────────────────────────────

# Create a customer
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers/ \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","address":"123 Main St","phone":"+1-555-0000","role":"CUSTOMER"}')
CUSTOMER_ID=$(echo $CUSTOMER | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Customer ID: $CUSTOMER_ID"

# Create a product
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{"description":"Widget","pricing":{"base_price":49.99,"currency":"USD"}}')
PRODUCT_ID=$(echo $PRODUCT | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PRODUCT_ID"

# ─── STEP 1: Place Order ──────────────────────────────────
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"line_items\":[{\"product_id\":\"$PRODUCT_ID\",\"product_description\":\"Widget\",\"quantity\":2,\"unit_price\":49.99}]}")
ORDER_ID=$(echo $ORDER | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order ID: $ORDER_ID (Status: PENDING)"

# ─── STEP 2a: Review Order ───────────────────────────────
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/review" | python -m json.tool

# ─── STEP 2b: Accept Order ───────────────────────────────
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/accept" | python -m json.tool

# ─── STEP 3: Create Invoice ───────────────────────────────
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices/ \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"billing_info\":{\"name\":\"John Doe\"},\"issue_date\":\"$(date +%Y-%m-%d)\",\"due_date\":\"$(date -d '+30 days' +%Y-%m-%d)\"}")
INVOICE_ID=$(echo $INVOICE | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Invoice ID: $INVOICE_ID (Status: ISSUED)"

# ─── STEP 4: Pay Invoice ──────────────────────────────────
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments/ \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"amount\":118.95,\"method\":\"CREDIT_CARD\",\"transaction_ref\":\"TXN001\"}")
PAYMENT_ID=$(echo $PAYMENT | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Payment ID: $PAYMENT_ID (Status: PENDING)"

# ─── STEP 5: Verify Payment ──────────────────────────────
curl -s -X POST "http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify" | python -m json.tool

# ─── STEP 6: Ship Order ──────────────────────────────────
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/ship" | python -m json.tool

# ─── STEP 7: Close Order ─────────────────────────────────
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/close" | python -m json.tool

echo "✅ Workflow complete!"
```

---

## 5. Complete 7-Step Workflow

### Workflow State Machine

```
PENDING ──► REVIEW ──► ACCEPTED ──► INVOICED ──► PAID ──► SHIPPED ──► CLOSED
   │           │            │             │
   └──► CANCELLED ◄─────────┘             │
                                          │
                                    (CANCELLED also possible
                                     from INVOICED)
```

### Step Details

| Step | Action | Endpoint | Role | Description |
|------|--------|----------|------|-------------|
| 1 | Place Order | `POST /api/v1/orders/` | Customer | Creates order with line items, auto-calculates totals |
| 2a | Review | `POST /api/v1/orders/{id}/review` | Order Staff | Transitions PENDING → REVIEW |
| 2b | Accept | `POST /api/v1/orders/{id}/accept` | Order Staff | Transitions REVIEW → ACCEPTED |
| 3 | Create Invoice | `POST /api/v1/invoices/` | Accountant | Creates + issues invoice, updates order to INVOICED |
| 4 | Pay | `POST /api/v1/payments/` | Customer | Records payment against invoice |
| 5 | Verify | `POST /api/v1/payments/{id}/verify` | Accountant | Verifies payment, updates order to PAID, marks invoice paid |
| 6 | Ship | `POST /api/v1/orders/{id}/ship` | Order Staff | Transitions PAID → SHIPPED |
| 7 | Close | `POST /api/v1/orders/{id}/close` | Order Staff | Transitions SHIPPED → CLOSED |

### Key Business Rules

- **Immutable Terminal States:** Orders in `CLOSED` or `CANCELLED` status cannot be modified.
- **Duplicate Prevention:** Only one invoice per order. Only one pending payment per order.
- **Status Validation:** All transitions are validated against the state machine. Invalid transitions return `400 Bad Request`.
- **Amount Validation:** Payment amount must match the invoice total exactly.

---

## 6. API Reference

### 6.1 Customers

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/customers/` | Create a customer |
| `GET` | `/api/v1/customers/` | List customers (paginated) |
| `GET` | `/api/v1/customers/{id}` | Get customer by ID |
| `PATCH` | `/api/v1/customers/{id}` | Update customer |
| `DELETE` | `/api/v1/customers/{id}` | Delete customer |

**Create Customer Example:**
```json
{
  "name": "Alice Johnson",
  "address": "123 Main St, Springfield, IL",
  "phone": "+1-555-0101",
  "banking_details": {"bank": "Chase", "account": "****1234"},
  "role": "CUSTOMER"
}
```

**Roles:** `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT`

### 6.2 Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/products/` | Create a product |
| `GET` | `/api/v1/products/` | List/search products |
| `GET` | `/api/v1/products/{id}` | Get product by ID |
| `PATCH` | `/api/v1/products/{id}` | Update product |
| `DELETE` | `/api/v1/products/{id}` | Delete product |

**Search Products:** `GET /api/v1/products/?search=wireless` (case-insensitive search on description)

**Create Product Example:**
```json
{
  "description": "Wireless Bluetooth Headphones",
  "pricing": {"base_price": 79.99, "currency": "USD"}
}
```

### 6.3 Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/orders/` | Place order (Step 1) |
| `GET` | `/api/v1/orders/` | List orders (filterable) |
| `GET` | `/api/v1/orders/{id}` | Get order by ID |
| `PATCH` | `/api/v1/orders/{id}` | Update order |
| `POST` | `/api/v1/orders/{id}/review` | Review order (Step 2a) |
| `POST` | `/api/v1/orders/{id}/accept` | Accept order (Step 2b) |
| `POST` | `/api/v1/orders/{id}/ship` | Ship order (Step 6) |
| `POST` | `/api/v1/orders/{id}/close` | Close order (Step 7) |
| `DELETE` | `/api/v1/orders/{id}` | Delete order |

**Filtering:** `GET /api/v1/orders/?status=PAID&customer_id={id}`

**Place Order Example:**
```json
{
  "customer_id": "uuid-here",
  "line_items": [
    {
      "product_id": "uuid-here",
      "product_description": "Widget",
      "quantity": 2,
      "unit_price": 49.99,
      "currency": "USD"
    }
  ],
  "notes": "Please handle with care"
}
```

### 6.4 Invoices

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/invoices/` | Create invoice (Step 3) |
| `GET` | `/api/v1/invoices/` | List invoices |
| `GET` | `/api/v1/invoices/{id}` | Get invoice by ID |
| `GET` | `/api/v1/invoices/by-order/{order_id}` | Get invoices by order |
| `POST` | `/api/v1/invoices/{id}/issue` | Issue draft invoice |
| `POST` | `/api/v1/invoices/{id}/mark-paid` | Mark invoice as paid |
| `PATCH` | `/api/v1/invoices/{id}` | Update invoice |
| `DELETE` | `/api/v1/invoices/{id}` | Delete invoice |

**Create Invoice Example:**
```json
{
  "order_id": "uuid-here",
  "billing_info": {
    "customer_name": "John Doe",
    "customer_address": "123 Main St"
  },
  "issue_date": "2025-07-11",
  "due_date": "2025-08-10"
}
```

### 6.5 Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/payments/` | Record payment (Step 4) |
| `GET` | `/api/v1/payments/` | List payments |
| `GET` | `/api/v1/payments/{id}` | Get payment by ID |
| `GET` | `/api/v1/payments/by-order/{order_id}` | Get payments by order |
| `POST` | `/api/v1/payments/{id}/verify` | Verify payment (Step 5) |
| `PATCH` | `/api/v1/payments/{id}` | Update payment |
| `DELETE` | `/api/v1/payments/{id}` | Delete payment |

**Payment Methods:** `CREDIT_CARD`, `DEBIT_CARD`, `BANK_TRANSFER`, `CASH`

**Record Payment Example:**
```json
{
  "order_id": "uuid-here",
  "amount": 118.95,
  "currency": "USD",
  "method": "CREDIT_CARD",
  "transaction_ref": "TXN-001"
}
```

### 6.6 Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |

---

## 7. Roles & Permissions

The system defines three roles via the `CustomerRole` enum:

| Role | Enum Value | Typical Actions |
|------|-----------|----------------|
| **Customer** | `CUSTOMER` | Place orders, make payments |
| **Order Staff** | `ORDER_STAFF` | Review, accept, ship, close orders |
| **Accountant** | `ACCOUNTANT` | Create invoices, verify payments |

> **Note:** The current implementation does not enforce role-based access control (authentication). Roles are stored on the `Customer` entity for future authorization integration.

---

## 8. Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────┐
│  Customer   │       │   Product    │
├─────────────┤       ├──────────────┤
│ id (PK)     │       │ id (PK)      │
│ name        │       │ description  │
│ address     │       │ pricing (JSON)│
│ phone       │       │ created_at   │
│ banking_det │       │ updated_at   │
│ role        │       └──────────────┘
│ created_at  │              │
│ updated_at  │              │
└──────┬──────┘              │
       │                     │
       │ 1                   │ N
       │                     │
       │  ┌──────────────────┘
       │  │
       │  │  ┌──────────────────────┐
       │  │  │   OrderLineItem      │
       │  │  ├──────────────────────┤
       │  │  │ id (PK)              │
       │  │  │ order_id (FK)        │
       │  │  │ product_id (FK)      │
       │  │  │ product_description  │
       │  │  │ quantity             │
       │  │  │ unit_price           │
       │  │  │ currency             │
       │  │  │ line_total           │
       │  │  └──────────────────────┘
       │  │
       │  │         N
       └──┼─────────┼──┐
           │  Order  │  │
           ├─────────┤  │
           │ id (PK) │  │
           │ cust_id │  │
           │ status  │  │
           │ subtotal│  │
           │ tax_amt │  │
           │ ship_amt│  │
           │ total   │  │
           │ currency│  │
           │ inv_ref │  │
           │ notes   │  │
           │ created │  │
           │ updated │  │
           └────┬────┘  │
                │       │
       ┌────────┼───────┘
       │        │
       │  N     │  N
  ┌────┴───┐ ┌──┴────────┐
  │ Payment│ │  Invoice  │
  ├────────┤ ├───────────┤
  │ id(PK) │ │ id (PK)   │
  │order_id│ │ order_id  │
  │ amount │ │ inv_number│
  │ curr   │ │ bill_info │
  │ status │ │ subtotal  │
  │ method │ │ tax_amt   │
  │ tx_ref │ │ ship_amt  │
  │ paid_at│ │ total     │
  │ created│ │ currency  │
  │ updated│ │ status    │
  └────────┘ │ issue_dt  │
              │ due_dt    │
              │ paid_at   │
              │ created   │
              │ updated   │
              └───────────┘
```

### Key Design Decisions

- **UUID Primary Keys:** All entities use UUID v4 strings for distributed ID generation.
- **JSON for Flexible Fields:** `banking_details`, `pricing`, `billing_info` use JSON columns.
- **Decimal for Monetary Values:** All monetary fields use `Numeric(12, 2)` to avoid floating-point errors.
- **Audit Timestamps:** Every entity has `created_at` and `updated_at` with automatic server defaults.
- **Cascade Delete:** `OrderLineItem` cascades delete when an order is removed.

---

## 9. Configuration

All configuration is managed via environment variables or a `.env` file.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./oms.db` | Database connection string |
| `DATABASE_ECHO` | `false` | Log SQL queries |
| `DATABASE_POOL_SIZE` | `20` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Max overflow connections |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `4` | Number of uvicorn workers |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window (seconds) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery result backend |
| `BACKGROUND_QUEUE_MAXSIZE` | `1000` | Max background queue size |
| `BACKGROUND_WORKERS` | `4` | Background worker count |
| `TAX_RATE` | `0.08` | Tax rate (decimal) |
| `SHIPPING_COST` | `9.99` | Flat shipping cost |

### Production Configuration Example

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/oms
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## 10. Testing & Verification

### 10.1 Run the Automated Workflow Test

```bash
# Start the server first, then:
uv run python scripts/test_workflow.py
```

This script:
1. Creates a customer and product
2. Places an order
3. Reviews and accepts the order
4. Creates and issues an invoice
5. Records a payment
6. Verifies the payment
7. Ships the order
8. Closes the order

### 10.2 NFR Verification

#### NFR 1.1 — Response Time

```bash
# Start the server
uv run uvicorn app.main:app --port 8000 &

# Run load test
uv run python -c "
import asyncio, httpx, time

async def load_test():
    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        # Create a product first
        resp = await client.post('/api/v1/products/', json={
            'description': 'Test Product',
            'pricing': {'base_price': 10.0, 'currency': 'USD'}
        })
        product = resp.json()

        # Measure search response time
        times = []
        for _ in range(50):
            start = time.perf_counter()
            resp = await client.get(f'/api/v1/products/?search=Test')
            times.append((time.perf_counter() - start) * 1000)

        times.sort()
        print(f'Min: {times[0]:.2f}ms')
        print(f'p50: {times[25]:.2f}ms')
        print(f'p95: {times[47]:.2f}ms')
        print(f'p99: {times[49]:.2f}ms')
        print(f'Max: {times[-1]:.2f}ms')

asyncio.run(load_test())
"
```

**Expected:** p95 response time < 200ms.

#### NFR 1.2 — Concurrency & Resource Utilization

```bash
# Start with 4 workers
uv run uvicorn app.main:app --port 8000 --workers 4 &

# Monitor in another terminal
htop

# Run 500 concurrent requests
uv run python -c "
import asyncio, httpx

async def concurrent_test():
    async def make_request(client):
        resp = await client.get('/api/v1/products/')
        return resp.status_code

    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        tasks = [make_request(client) for _ in range(500)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if r == 200)
        print(f'Successful: {success}/{len(results)}')

asyncio.run(concurrent_test())
"
```

**Expected:** CPU utilization stays below 70% under load.

#### NFR 1.3 — Queue Management

```bash
# Start the server
uv run uvicorn app.main:app --port 8000 &

# Flood the background queue
uv run python -c "
import asyncio
from app.tasks.background import get_task_processor

async def flood_queue():
    processor = get_task_processor()
    await processor.start()

    async def dummy_task(msg):
        await asyncio.sleep(0.1)
        return msg

    count = 0
    for i in range(2000):
        try:
            await processor.enqueue(dummy_task, f'task-{i}')
            count += 1
        except asyncio.QueueFull:
            print(f'Queue full after {count} tasks (expected ~1000)')
            break
        except Exception as e:
            print(f'Error at task {i}: {e}')
            break

    await processor.stop()

asyncio.run(flood_queue())
"
```

**Expected:** Queue rejects at capacity (maxsize=1000) with "Background queue full" log message instead of crashing.

### 10.3 Database Migrations

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## 11. Troubleshooting

### Common Issues

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| `ModuleNotFoundError` | Dependencies not installed | Run `uv sync` |
| `sqlite3.OperationalError: no such table` | Database not initialized | Run `uv run python scripts/seed_data.py` |
| `Connection refused` on port 8000 | Server not running | Start with `uv run uvicorn app.main:app --port 8000` |
| `400 Bad Request: Cannot transition` | Invalid status transition | Check the order's current status and allowed transitions |
| `400 Bad Request: An invoice already exists` | Duplicate invoice | Each order can only have one invoice |
| `400 Bad Request: A pending payment already exists` | Duplicate payment | Wait for verification or cancel existing payment |
| `400 Bad Request: Cannot update order in terminal status` | Order is CLOSED or CANCELLED | Terminal orders are immutable |
| `429 Too Many Requests` | Rate limit exceeded | Wait 60 seconds or increase `RATE_LIMIT_REQUESTS` |
| `Queue full` in background tasks | Queue at capacity | Increase `BACKGROUND_QUEUE_MAXSIZE` or add more workers |

### Logs

The application logs to stdout with the format:
```
2025-07-11 12:34:56 [INFO] app.main: Starting Order Management System...
2025-07-11 12:34:56 [INFO] oms.access: POST /api/v1/orders/ -> 201 (45.23 ms)
```

### Getting Help

- **API Docs:** `http://localhost:8000/docs` (Swagger UI)
- **Architecture Decisions:** See `docs/ADR.md`
- **Data Architecture:** See `docs/DATA_ARCHITECTURE.md`
- **Deployment Guide:** See `docs/DEPLOYMENT_GUIDE.md`
- **NFR Traceability:** See `docs/NFR_TRACEABILITY_MATRIX.md`

---

*© ChatDev — Order Management System v1.0.0*
