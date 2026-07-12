# OMS Backend — User Manual

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [Domain Model](#3-domain-model)
4. [Installation & Setup](#4-installation--setup)
5. [Running the Application](#5-running-the-application)
6. [API Reference](#6-api-reference)
7. [Workflow Walkthrough](#7-workflow-walkthrough)
8. [Configuration Reference](#8-configuration-reference)
9. [NFR Verification](#9-nfr-verification)
10. [Project Structure](#10-project-structure)

---

## 1. Overview

The **OMS Backend** is a production-grade, backend-only Order Management System built with Python 3.12, FastAPI, PostgreSQL 15, and Redis 7. It implements the complete e-commerce order lifecycle:

```
Customer places order → Staff accepts → Accountant invoices → Customer pays
→ Accountant verifies → Staff ships → Staff closes
```

### Key Capabilities

| Capability | Technology | NFR Addressed |
|---|---|---|
| Async non-blocking I/O | FastAPI + asyncpg + uvloop | NFR 1.1, NFR 1.2 |
| Connection pooling | asyncpg (20 min / 100 max per worker) | NFR 1.1 |
| Multi-worker concurrency | Gunicorn + Uvicorn workers (2×CPU+1) | NFR 1.2 |
| Rate limiting | Redis sliding-window counters | NFR 1.3 |
| Circuit breaker | In-memory (PaymentService) | NFR 1.3 |
| Background jobs | Arq (async Redis queue) | NFR 1.3 |
| Graceful shutdown | Gunicorn SIGTERM handling | NFR 1.3 |
| In-memory LRU cache | `cachetools` (product catalog) | NFR 1.1 |
| Schema validation | Pydantic v2 (shared domain models) | NFR 1.2 |

---

## 2. Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐        ┌────▼────┐       ┌────▼────┐
   │ Worker 1│        │ Worker 2│  ...  │ Worker N │  (2×CPU+1)
   │uvicorn  │        │uvicorn  │       │uvicorn  │
   │(uvloop) │        │(uvloop) │       │(uvloop) │
   └────┬────┘        └────┬────┘       └────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐        ┌────▼────┐       ┌────▼────┐
   │   DB    │        │  Redis  │       │  Arq    │
   │(pg 15)  │        │(cache+  │       │ Worker  │
   │         │        │ queue)  │       │(bg jobs)│
   └─────────┘        └─────────┘       └─────────┘
```

### Request Flow

```
HTTP Request
    ↓
FastAPI (rate_limit middleware)     ← NFR 1.3: back-pressure
    ↓
Controller (request validation)     ← Pydantic v2
    ↓
Service (business logic)            ← async/await throughout
    ↓
Repository (DB access)             ← asyncpg, eager loading
    ↓
PostgreSQL 15
```

---

## 3. Domain Model

### 3.1 Entity Summary

| Entity | Description | Key Fields |
|---|---|---|
| **Customer** | System user (Customer, OrderStaff, Accountant roles) | id, code, name, email, address, banking, role |
| **Order** | Customer purchase with line items | id, code, customer, status, subtotal, tax, total, currency |
| **LineItem** | Product + quantity in an order | id, order, product_id, quantity, unit_price, tax_rate, line_total |
| **Product** | Sellable catalog item | id, sku, name, description, base_price, currency, stock_qty, is_active |
| **Invoice** | Billing document for an order | id, code, order, customer, status, amounts, issue/due dates |
| **Payment** | Money movement record | id, invoice, amount, status, method, gateway_ref |
| **AuditLog** | Immutable action trail | id, entity_type, entity_id, action, actor, payload, ip, timestamp |

### 3.2 Order Status Lifecycle

```
pending → accepted → invoiced → paid → shipped → delivered → closed
    │                                            ↑
    └───────────────── cancelled ◄───────────────┘
```

### 3.3 Invoice Status Lifecycle

```
draft → issued → paid
            ↑
         overdue (auto-set by scheduler)
```

### 3.4 Payment Status Lifecycle

```
pending → authorized → captured → refunded
                            ↑
                        failed
```

---

## 4. Installation & Setup

### 4.1 Prerequisites

- Python 3.12+
- Docker & Docker Compose (for PostgreSQL, Redis, and full-stack deployment)
- `psql` (PostgreSQL 15 client) for direct DB access
- `curl` or `httpie` for API testing

### 4.2 Install Python Dependencies

```bash
# Using uv (recommended — fast, reproducible)
pip install uv
cd oms_backend
uv sync

# Or using pip
pip install -e .
```

### 4.3 Infrastructure via Docker Compose

```bash
docker compose up -d postgres redis
```

Wait for health checks:
```bash
docker compose ps
# Both postgres and redis should show (healthy)
```

### 4.4 Initialize the Database

```bash
psql -h localhost -U postgres -d oms_db -f db/schema.sql
```

Expected output: `CREATE TABLE` / `CREATE INDEX` messages with no errors.

### 4.5 Configuration

Edit `config.yaml` to override defaults:

```yaml
database:
  host: "localhost"      # PostgreSQL host
  port: 5432
  username: "postgres"
  password: "postgres123"
  name: "oms_db"
  min_pool_size: 20
  max_pool_size: 100

redis:
  host: "localhost"
  port: 6379
  db: 0
  password: ""

app:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  debug: false
  log_level: "info"
  cors_origins:
    - "http://localhost:3000"

rate_limiting:
  enabled: true
  per_customer_rpm: 100    # requests per minute per customer
  global_rpm: 10000       # global requests per minute
  burst: 200

cache:
  product_ttl_seconds: 300
  order_ttl_seconds: 60

queue:
  redis_url: "redis://localhost:6379/0"
  max_jobs: 1000
  job_timeout_seconds: 60
  retry_attempts: 3
  retry_delay_seconds: 5

payment_gateway:
  base_url: "https://gateway.example.com"
  api_key: "your-api-key"
  timeout_seconds: 30
  circuit_breaker_threshold: 5
  circuit_breaker_timeout_seconds: 30
```

---

## 5. Running the Application

### 5.1 Development Mode (Uvicorn with auto-reload)

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8000 --reload --loop uvloop
```

### 5.2 Production Simulation (Gunicorn)

```bash
uv run gunicorn -c infra/gunicorn.conf.py server:app
```

Worker count is auto-calculated as `2 × CPU_cores + 1` (e.g., 9 workers on a 4-core machine).

### 5.3 Full Stack via Docker Compose

```bash
docker compose up --build
```

All services start: `postgres`, `redis`, `oms-backend`, `oms-worker`.

### 5.4 Background Worker (Arq)

```bash
uv run python -m infra.worker
```

### 5.5 Verify the API is Running

```bash
# Health check
curl http://localhost:8000/health
# {"status":"ok"}

# Readiness check
curl http://localhost:8000/ready
# {"status":"ready"}

# OpenAPI docs
open http://localhost:8000/docs
```

---

## 6. API Reference

All endpoints are versioned under `/api/v1`. Full OpenAPI spec at `/openapi.json`.

### 6.1 Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe (checks DB) |

### 6.2 Customers

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/customers` | Create customer |
| GET | `/api/v1/customers/{id}` | Get customer by ID |
| GET | `/api/v1/customers/code/{code}` | Get customer by code |
| GET | `/api/v1/customers` | List customers (paginated) |
| PATCH | `/api/v1/customers/{id}` | Update customer |

### 6.3 Products

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/products` | Create product |
| GET | `/api/v1/products/{id}` | Get product by ID |
| GET | `/api/v1/products/sku/{sku}` | Get product by SKU |
| GET | `/api/v1/products/search?q={query}` | Search products (GIN index) |
| GET | `/api/v1/products` | List products (paginated) |
| PATCH | `/api/v1/products/{id}` | Update product |

### 6.4 Orders

| Method | Path | Description | Workflow Step |
|---|---|---|---|
| POST | `/api/v1/orders` | Create order | 1. Customer places order |
| GET | `/api/v1/orders/{id}` | Get order with line items | — |
| GET | `/api/v1/orders/code/{code}` | Get order by code | — |
| GET | `/api/v1/orders` | List orders (filterable) | — |
| POST | `/api/v1/orders/{id}/accept` | Accept order | 2. Staff reviews & accepts |
| POST | `/api/v1/orders/{id}/update` | Update order (line items, notes) | — |
| POST | `/api/v1/orders/{id}/ship` | Ship order | 6. Staff ships paid order |
| POST | `/api/v1/orders/{id}/deliver` | Mark delivered | — |
| POST | `/api/v1/orders/{id}/close` | Close order | 7. Staff closes completed order |
| POST | `/api/v1/orders/{id}/cancel` | Cancel order | — |

### 6.5 Invoices

| Method | Path | Description | Workflow Step |
|---|---|---|---|
| POST | `/api/v1/invoices` | Create invoice from order | 3. Accountant creates invoice |
| GET | `/api/v1/invoices/{id}` | Get invoice | — |
| GET | `/api/v1/invoices/code/{code}` | Get invoice by code | — |
| GET | `/api/v1/invoices` | List invoices (filterable) | — |
| POST | `/api/v1/invoices/{id}/issue` | Issue invoice | — |
| POST | `/api/v1/invoices/{id}/pay` | Mark invoice paid | 5. Accountant verifies payment |

### 6.6 Payments

| Method | Path | Description | Workflow Step |
|---|---|---|---|
| POST | `/api/v1/payments` | Process payment (authorize + capture) | 4. Customer pays invoice |
| GET | `/api/v1/payments/{id}` | Get payment | — |
| GET | `/api/v1/payments/invoice/{invoice_id}` | Get payments for invoice | — |
| POST | `/api/v1/payments/webhook` | Payment gateway webhook | — |

### 6.7 Request Headers

| Header | Description |
|---|---|
| `X-Actor-ID` | UUID of the user performing the action (for audit trail) |
| `X-Forwarded-For` | Client IP for rate limiting and audit |
| `customer_id` | Query param for per-customer rate limiting |

### 6.8 Response Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (validation error) |
| 404 | Not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service unavailable (circuit breaker open) |

---

## 7. Workflow Walkthrough

### Complete Order-to-Closure Workflow

#### Step 1 — Customer Places Order

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-UUID-HERE",
    "items": [
      {"product_id": "PROD-UUID-HERE", "quantity": 2, "tax_rate": "0.08"}
    ],
    "shipping_address": {
      "line1": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "US"
    },
    "currency": "USD",
    "notes": "Please handle with care"
  }'
```

Response: `OrderWithItems` with status `pending`, total computed including tax.

#### Step 2 — Order Staff Accepts Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/{order_id}/accept \
  -H "X-Actor-ID: {staff_uuid}"
```

Order status changes: `pending` → `accepted`.

#### Step 3 — Accountant Creates Invoice

```bash
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -H "X-Actor-ID: {accountant_uuid}" \
  -d '{
    "order_id": "{order_id}",
    "issue_date": "2025-07-12",
    "due_date": "2025-07-26",
    "notes": "Net-14 payment terms"
  }'
```

Order status changes: `accepted` → `invoiced`.

#### Step 4 — Customer Pays Invoice

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": "{invoice_id}",
    "amount": "500.00",
    "currency": "USD",
    "method": "credit_card",
    "gateway_ref": "gw_txn_12345"
  }'
```

Payment status: `pending` → `authorized` → `captured`. Invoice status: `issued` → `paid`.

#### Step 5 — Accountant Verifies Payment

```bash
curl -X POST http://localhost:8000/api/v1/invoices/{invoice_id}/pay \
  -H "X-Actor-ID: {accountant_uuid}"
```

Confirms payment; no status change needed (already set by Step 4).

#### Step 6 — Order Staff Ships Paid Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/{order_id}/ship \
  -H "X-Actor-ID: {staff_uuid}" \
  -H "Content-Type: application/json" \
  -d '{"tracking_number": "1Z999AA10123456784", "carrier": "UPS"}'
```

Order status changes: `invoiced` → `shipped`.

#### Step 7 — Order Staff Closes Completed Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/{order_id}/close \
  -H "X-Actor-ID: {staff_uuid}"
```

Order status changes: `shipped` → `closed`.

---

## 8. Configuration Reference

### 8.1 Environment Variables

All settings in `config.yaml` can be overridden via environment variables using the `OMS_` prefix:

```bash
export OMS_DATABASE__HOST=prod-db.example.com
export OMS_DATABASE__PASSWORD=secure_password
export OMS_REDIS__HOST=prod-redis.example.com
export OMS_APP__WORKERS=16
export OMS_RATE_LIMITING__PER_CUSTOMER_RPM=200
```

### 8.2 Key Tunables

| Parameter | Default | Description |
|---|---|---|
| `database.min_pool_size` | 20 | Always-warm asyncpg connections per worker |
| `database.max_pool_size` | 100 | Max connections per worker (total: worker × 100) |
| `app.workers` | 4 (override by gunicorn) | Gunicorn worker count |
| `rate_limiting.per_customer_rpm` | 100 | Per-customer rate limit |
| `rate_limiting.global_rpm` | 10000 | Global rate limit |
| `cache.product_ttl_seconds` | 300 | Product catalog cache TTL |
| `payment_gateway.circuit_breaker_threshold` | 5 | Failures before circuit opens |
| `payment_gateway.circuit_breaker_timeout_seconds` | 30 | Recovery wait time |

---

## 9. NFR Verification

### NFR 1.1 — Response Time

**Verify async I/O (no blocking DB calls):**
```bash
grep -r "asyncpg\|databases" oms_backend/db/connection.py
```

**Verify connection pooling:**
```bash
curl http://localhost:8000/ready
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='oms_db'"
# Should show multiple idle connections warming up
```

**Verify GIN index on product search:**
```sql
psql -d oms_db -c "\d products"
-- Should show: idx_products_name_gin USING gin(to_tsvector(...))
```

**Load test with locust:**
```bash
cd oms_backend/tests
locust --host=http://localhost:8000 --users=500 --spawn-rate=50 \
  --run-time=60s --headless
# Verify p99 < 200ms for /api/v1/products/search and /api/v1/orders
```

### NFR 1.2 — Concurrency & Resource Utilization

**Verify multiple gunicorn workers:**
```bash
uv run gunicorn -c infra/gunicorn.conf.py server:app &
ps aux | grep "uvicorn.workers.UvicornWorker" | grep -v grep | wc -l
# Expected: 2 * CPU_cores + 1
```

**Verify uvloop is active:**
```python
uv run python -c "import uvloop; print(uvloop.__version__)"
```

### NFR 1.3 — Queue Management

**Verify rate limiting:**
```bash
for i in {1..110}; do
  curl -s http://localhost:8000/api/v1/products > /dev/null
done
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/products
# Expected: 429
```

**Verify circuit breaker:**
```bash
# In tests/test_payment.py, mock gateway to fail 6 times consecutively
# 6th request should return 503; 7th after 30s should succeed
```

**Verify graceful shutdown:**
```bash
uv run gunicorn -c infra/gunicorn.conf.py server:app &
PID=$!
kill -TERM $PID
# No 502s; verify graceful completion in logs
```

---

## 10. Project Structure

```
oms_backend/
├── api/
│   └── v1/
│       ├── __init__.py          # Aggregated API router (/api/v1)
│       ├── customer.py           # Customer REST endpoints
│       ├── product.py           # Product REST endpoints
│       ├── order.py              # Order REST endpoints
│       ├── invoice.py            # Invoice REST endpoints
│       └── payment.py            # Payment REST endpoints
├── core/
│   ├── config.py                 # YAML config loader + Pydantic models
│   ├── cache.py                  # In-memory LRU cache (product catalog)
│   └── rate_limiter.py           # Redis sliding-window rate limiter
├── db/
│   ├── connection.py              # Asyncpg connection pool, session factory
│   └── schema.sql                # Complete PostgreSQL DDL
├── docs/
│   ├── ADR.md                    # Architecture Decision Records
│   ├── NFR_TRACEABILITY.md       # NFR → mechanism mapping
│   ├── NFR_VERIFICATION.md      # Reproducible NFR verification steps
│   ├── LOCAL_DEPLOYMENT.md       # Step-by-step local deployment
│   └── OPENAPI_SPEC.md           # Full OpenAPI 3.0 specification
├── infra/
│   ├── gunicorn.conf.py           # Production gunicorn config
│   └── worker.py                  # Arq background worker (audit, email, etc.)
├── models/
│   └── orm_models.py              # SQLAlchemy async ORM models
├── repositories/
│   ├── base.py                    # Generic CRUD repository (async)
│   └── entities.py                # Per-entity repositories
├── schemas/
│   └── domain.py                  # Pydantic v2 domain models (shared)
├── services/
│   ├── customer.py                # Customer business logic
│   ├── product.py                 # Product business logic
│   ├── order.py                   # Order lifecycle orchestration
│   ├── invoice.py                 # Invoice lifecycle orchestration
│   ├── payment.py                 # Payment processing + circuit breaker
│   └── utils.py                    # Audit logging, billing address builder
├── tests/
│   ├── conftest.py                # pytest fixtures (DB, client)
│   ├── test_order.py              # Order service + endpoint tests
│   └── test_invoice.py            # Invoice service + endpoint tests
├── config.yaml                    # Environment-agnostic configuration
├── docker-compose.yml             # Full stack: postgres, redis, backend, worker
├── Dockerfile                     # Production container image
├── pyproject.toml                 # Python dependencies (uv/pip)
├── server.py                      # FastAPI app factory + lifespan (startup/shutdown)
└── main.py                        # CLI entry point
```

### Key Design Patterns

| Pattern | Location | Purpose |
|---|---|---|
| **Repository** | `repositories/base.py` | Async CRUD with session management |
| **Service Layer** | `services/*.py` | Business logic, transactions, orchestration |
| **Controller** | `api/v1/*.py` | HTTP handling, validation, response mapping |
| **Circuit Breaker** | `services/payment.py` | Fail-fast on external gateway failures |
| **Rate Limiter** | `core/rate_limiter.py` | Redis sliding-window counters |
| **Shared Domain Models** | `schemas/domain.py` | Pydantic v2 models used across all layers |

---

*Last updated: 2025-07-12*
