# Order Management System (OMS) — Backend

A production-grade, backend-only e-commerce Order Management System built with **FastAPI**, **SQLAlchemy**, and **SQLite**.

---

## Table of Contents
1. [NFR Traceability Matrix](#1-nfr-traceability-matrix)
2. [Architectural Decision Records (ADRs)](#2-architectural-decision-records-adrs)
3. [Data Architecture](#3-data-architecture)
4. [Domain Model](#4-domain-model)
5. [Architecture](#5-architecture)
6. [API Endpoints](#6-api-endpoints)
7. [Local Deployment Guide](#7-local-deployment-guide)
8. [Verification Steps](#8-verification-steps)
9. [Project Structure](#9-project-structure)

---

## 1. NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|------------------|---------------------|
| **1.1 Response Time** | SQLAlchemy eager-loading (`joinedload`) on all order/payment/invoice queries to avoid N+1 | `order_service.py`, `payment_service.py`, `invoice_service.py` | `time curl` on product search, cart, checkout under `wrk -t12 -c400` load; observe <500ms p95 |
| **1.1 Response Time** | Connection pooling (`pool_size=20`, `max_overflow=10`) reuses DB connections | `database.py` | Monitor `SELECT 1` query time under concurrent load; pool should not exhaust |
| **1.1 Response Time** | Request-timing middleware logs slow requests (>500ms) | `main.py` (`RequestTimingMiddleware`) | Check logs for "SLOW REQUEST" entries during load test |
| **1.2 Concurrency & Resource** | Uvicorn with multiple workers (4 workers by default) | `Dockerfile`, `run.py` | `htop` during `wrk -t12 -c400`; CPU <80%, RAM <512MB per worker |
| **1.2 Concurrency & Resource** | SQLAlchemy `pool_pre_ping=True` detects stale connections | `database.py` | Force DB restart during load test; connections auto-recover without crash |
| **1.2 Concurrency & Resource** | Configurable `max_workers` and pool sizes via env vars | `config.py` | Change `OMS_DB_POOL_SIZE=50` and observe connection count in DB |
| **1.3 Queue Management** | In-memory sliding-window rate limiter (100 req/min per IP) | `middleware/rate_limit.py` | Send >100 requests/min from same IP → observe HTTP 429 responses |
| **1.3 Queue Management** | Stale entry cleanup every 5 minutes prevents memory leak | `middleware/rate_limit.py` (`_cleanup_stale_entries`) | Monitor memory with `psutil`; no unbounded growth after hours of traffic |
| **1.3 Queue Management** | Global exception handler returns 500 instead of crashing | `main.py` (`global_exception_handler`) | Send malformed request → observe structured 500 response, not crash |

---

## 2. Architectural Decision Records (ADRs)

### ADR-1: FastAPI over Spring Boot

- **Decision:** Use FastAPI (Python) instead of Spring Boot (Java)
- **Context:** NFR 1.1 (Response Time) — Python async I/O minimizes latency; NFR 1.2 (Concurrency) — ASGI workers handle high concurrency
- **Alternatives considered:**
  - *Spring Boot* — rejected due to heavier resource footprint (JVM overhead) and slower cold-start
  - *Flask* — rejected due to lack of native async support and built-in OpenAPI generation
- **Consequences:** Python GIL limits CPU-bound parallelism, but I/O-bound API workloads are well-served by async workers. FastAPI's auto-generated OpenAPI docs satisfy the OpenAPI requirement.

### ADR-2: SQLite for local dev / PostgreSQL-ready

- **Decision:** Use SQLite for zero-config local deployment; schema is portable to PostgreSQL
- **Context:** NFR 1.2 — SQLite handles concurrent reads well; connection pooling mitigates write contention
- **Alternatives considered:**
  - *PostgreSQL* — rejected for local dev due to setup overhead (requires separate service)
  - *In-memory SQLite* — rejected because data must persist across restarts
- **Consequences:** For production, swap `OMS_DATABASE_URL` to a PostgreSQL DSN. SQLAlchemy abstraction makes this a one-line change.

### ADR-3: In-memory sliding-window rate limiter

- **Decision:** Simple in-memory sliding-window counter per IP using a deque of timestamps
- **Context:** NFR 1.3 (Queue Management) — prevents crash under sudden spikes
- **Alternatives considered:**
  - *Redis-based rate limiter* — rejected to avoid external dependency for local deployment
  - *Nginx rate limiting* — rejected because it adds infrastructure complexity and is not part of the application
- **Consequences:** Rate limit resets on server restart; not distributed — fine for single-node deployment. Stale entry cleanup prevents memory leaks.

### ADR-4: Workflow orchestrator pattern

- **Decision:** Dedicated `WorkflowService` orchestrates multi-step transitions with transactional atomicity
- **Context:** The 7-step order lifecycle requires atomic multi-step operations (e.g., create invoice + issue + update order status in one transaction)
- **Alternatives considered:**
  - *Saga pattern* — rejected as over-engineering for a single-service deployment
  - *Direct service calls from controllers* — rejected because it would duplicate transaction logic across endpoints
- **Consequences:** All workflow methods use `commit=False` + explicit `db.commit()` for atomicity. If any step fails, all changes roll back.

### ADR-5: UUID primary keys

- **Decision:** Use UUID strings for all primary keys instead of auto-increment integers
- **Context:** Distributed-friendly IDs that can be generated client-side; no sequential guessing
- **Alternatives considered:**
  - *Auto-increment integers* — rejected because they leak information about record count and cause conflicts in distributed scenarios
  - *ULID* — rejected because UUID is more widely supported and simpler
- **Consequences:** Slightly larger index size; no performance impact at this scale.

---

## 3. Data Architecture

### Entity-Relationship Diagram

```
Customer 1──N Order 1──N OrderItem
                 │
                 ├──N Payment
                 └──N Invoice
```

### Schema Narrative

The system uses six tables managed by SQLAlchemy ORM:

- **customers** — Stores customer profile data including banking details and role. The `role` field supports the three roles (customer, order_staff, accountant) though authentication is not implemented.

- **products** — Product catalog with name, description, base price, and currency. Supports full-text search via `ILIKE` queries.

- **orders** — The central entity tracking the order lifecycle. Status is an enum with 7 states: `PENDING → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED → CLOSED`. The `invoice_ref` field links to the generated invoice.

- **order_items** — Line items belonging to an order, each referencing a product with quantity and unit price. Total amount is computed at order creation time.

- **payments** — Payment records linked to orders. Supports multiple payment methods (credit_card, debit_card, bank_transfer, paypal, cash). Status tracks the payment lifecycle: `PENDING → PAID → VERIFIED → FAILED/REFUNDED`.

- **invoices** — Invoices linked to orders with billing info, amounts, issue/due dates. Status: `DRAFT → ISSUED → PAID → OVERDUE → CANCELLED`.

### Key Design Decisions

- **UUID primary keys** — All tables use UUID v4 strings for distributed-friendly, non-sequential IDs.
- **Timestamps** — Every table has `created_at` and `updated_at` with UTC timezone.
- **Cascading deletes** — Deleting a customer cascades to orders; deleting an order cascades to items, payments, and invoices.
- **Eager loading** — All service `get_by_id` and `list_*` methods use `joinedload` to avoid N+1 queries (NFR 1.1).

---

## 4. Domain Model

### Customer
| Field | Type | Description |
|-------|------|-------------|
| id | UUID string | Primary key |
| name | string(255) | Customer name |
| address | text | Physical address |
| phone | string(50) | Contact phone |
| banking_details | text | Bank account info |
| role | string(50) | Role: customer, order_staff, accountant |
| created_at | datetime | UTC timestamp |
| updated_at | datetime | UTC timestamp |

### Order
| Field | Type | Description |
|-------|------|-------------|
| id | UUID string | Primary key |
| customer_id | UUID string | FK to customers |
| status | enum | PENDING, ACCEPTED, INVOICED, PAID, VERIFIED, SHIPPED, CLOSED |
| total_amount | float | Computed sum of line items |
| currency | string(3) | ISO currency code |
| invoice_ref | UUID string | FK to invoice (set when invoiced) |
| created_at | datetime | UTC timestamp |
| updated_at | datetime | UTC timestamp |

### Product
| Field | Type | Description |
|-------|------|-------------|
| id | UUID string | Primary key |
| name | string(255) | Product name |
| description | text | Product description |
| base_price | float | Unit price |
| currency | string(3) | ISO currency code |
| created_at | datetime | UTC timestamp |
| updated_at | datetime | UTC timestamp |

### Payment
| Field | Type | Description |
|-------|------|-------------|
| id | UUID string | Primary key |
| order_id | UUID string | FK to orders |
| amount | float | Payment amount |
| currency | string(3) | ISO currency code |
| method | enum | CREDIT_CARD, DEBIT_CARD, BANK_TRANSFER, PAYPAL, CASH |
| status | enum | PENDING, PAID, VERIFIED, FAILED, REFUNDED |
| paid_at | datetime | When payment was made |
| verified_at | datetime | When payment was verified |
| created_at | datetime | UTC timestamp |
| updated_at | datetime | UTC timestamp |

### Invoice
| Field | Type | Description |
|-------|------|-------------|
| id | UUID string | Primary key |
| order_id | UUID string | FK to orders |
| billing_info | text | Billing address/info |
| amount | float | Invoice amount |
| currency | string(3) | ISO currency code |
| status | enum | DRAFT, ISSUED, PAID, OVERDUE, CANCELLED |
| issue_date | datetime | When invoice was issued |
| due_date | datetime | Payment due date (30 days after issue) |
| created_at | datetime | UTC timestamp |
| updated_at | datetime | UTC timestamp |

---

## 5. Architecture

### Roles
- **Customer** — places orders, pays invoices
- **Order Staff** — reviews/accepts orders, ships, closes
- **Accountant** — creates invoices, verifies payments

### Order Lifecycle
```
PENDING → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED → CLOSED
```

### Workflow Steps
1. Customer places order → `POST /api/v1/orders`
2. Order Staff reviews & accepts → `POST /api/v1/workflow/orders/{id}/accept`
3. Accountant creates invoice → `POST /api/v1/workflow/orders/{id}/invoice`
4. Customer pays invoice → `POST /api/v1/workflow/invoices/{id}/pay`
5. Accountant verifies payment → `POST /api/v1/workflow/payments/{id}/verify`
6. Order Staff ships paid order → `POST /api/v1/workflow/orders/{id}/ship`
7. Order Staff closes completed order → `POST /api/v1/workflow/orders/{id}/close`

### Transactional Atomicity
All workflow methods use `commit=False` + explicit `db.commit()` to guarantee atomicity. If any step in a multi-step operation fails, all changes are rolled back. This ensures consistency across the order lifecycle.

---

## 6. API Endpoints

### Customers
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/customers` | Create customer |
| GET | `/api/v1/customers` | List customers |
| GET | `/api/v1/customers/{id}` | Get customer |
| PATCH | `/api/v1/customers/{id}` | Update customer |
| DELETE | `/api/v1/customers/{id}` | Delete customer |

### Products
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/products` | Create product |
| GET | `/api/v1/products` | List/search products |
| GET | `/api/v1/products/{id}` | Get product |
| PATCH | `/api/v1/products/{id}` | Update product |
| DELETE | `/api/v1/products/{id}` | Delete product |

### Orders
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/orders` | Place order |
| GET | `/api/v1/orders` | List orders (filter by `customer_id`) |
| GET | `/api/v1/orders/{id}` | Get order |
| PATCH | `/api/v1/orders/{id}/status` | Update order status |
| DELETE | `/api/v1/orders/{id}` | Delete order |

### Payments
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/payments` | Create payment |
| GET | `/api/v1/payments` | List payments (filter by `order_id`) |
| GET | `/api/v1/payments/{id}` | Get payment |
| POST | `/api/v1/payments/{id}/pay` | Mark payment as paid |
| POST | `/api/v1/payments/{id}/verify` | Verify payment |
| DELETE | `/api/v1/payments/{id}` | Delete payment |

### Invoices
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/invoices` | Create invoice |
| GET | `/api/v1/invoices` | List invoices (filter by `order_id`) |
| GET | `/api/v1/invoices/{id}` | Get invoice |
| POST | `/api/v1/invoices/{id}/issue` | Issue invoice |
| PATCH | `/api/v1/invoices/{id}/status` | Update invoice status |
| DELETE | `/api/v1/invoices/{id}` | Delete invoice |

### Workflow (orchestrated lifecycle)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/workflow/orders/{id}/accept` | Staff accepts order |
| POST | `/api/v1/workflow/orders/{id}/invoice` | Accountant creates invoice |
| POST | `/api/v1/workflow/invoices/{id}/pay` | Customer pays invoice |
| POST | `/api/v1/workflow/payments/{id}/verify` | Accountant verifies payment |
| POST | `/api/v1/workflow/orders/{id}/ship` | Staff ships order |
| POST | `/api/v1/workflow/orders/{id}/close` | Staff closes order |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |
| GET | `/openapi.yaml` | OpenAPI spec as JSON |

---

## 7. Local Deployment Guide

### Prerequisites
- Python 3.12+
- `uv` (recommended) or `pip`

### Option 1: Direct (uv)

```bash
cd oms
uv sync
uv run uvicorn app.main:app --reload
```

### Option 2: Direct (pip)

```bash
cd oms
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Docker

```bash
cd oms
docker compose up --build
```

### Verify

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"1.0.0"}
```

OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 8. Verification Steps

### NFR 1.1 — Response Time

```bash
# Measure latency for core journeys
time curl -s http://localhost:8000/api/v1/products?query=laptop

# Place an order
time curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"...","line_items":[{"product_id":"...","quantity":1,"unit_price":29.99}]}'

# Checkout workflow
time curl -X POST http://localhost:8000/api/v1/workflow/orders/{id}/accept

# Load test with wrk
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/products
# Expected: p95 latency < 500ms, no errors
```

### NFR 1.2 — Concurrency & Resource Utilization

```bash
# Install wrk: https://github.com/wg/wrk
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/products

# In another terminal, monitor resources
htop
# Expected: CPU < 80%, RAM < 512MB per worker on 98GB RAM class machine

# Check connection pool usage
# SQLite doesn't expose pool stats directly, but you can verify by
# running concurrent requests and checking no "too many connections" errors
```

### NFR 1.3 — Queue Management

```bash
# Rapid-fire requests from same IP
for i in $(seq 1 120); do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
done
# After ~100 requests you should see 429 responses

# Verify rate limit resets after 60 seconds
sleep 60
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
# Should return 200
```

### Full Workflow Integration Test

```bash
# Run the automated integration test
cd oms
python test_workflow.py
# Expected output: "=== ALL WORKFLOW STEPS PASSED ==="
```

### Unit Tests

```bash
cd oms
pytest tests/ -v
# Expected: 23 passed
```

---

## 9. Project Structure

```
oms/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, middleware, routers
│   ├── config.py            # Pydantic Settings with env vars
│   ├── database.py          # Engine, session, Base with connection pooling
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── customer.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── invoice.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── customer.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── invoice.py
│   ├── services/            # Business logic
│   │   ├── customer_service.py
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── invoice_service.py
│   │   └── workflow_service.py
│   ├── routers/             # FastAPI routers
│   │   ├── customer_router.py
│   │   ├── product_router.py
│   │   ├── order_router.py
│   │   ├── payment_router.py
│   │   ├── invoice_router.py
│   │   └── workflow_router.py
│   └── middleware/          # Cross-cutting concerns
│       └── rate_limit.py
├── tests/
│   ├── __init__.py
│   └── test_services.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── run.py                   # Dev launcher
├── test_workflow.py         # Integration test
└── README.md
```
