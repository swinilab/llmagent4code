# Order Management System (OMS) — Backend

Production-grade e-commerce Order Management System backend built with Python, FastAPI, SQLAlchemy, and async infrastructure.

---

## Table of Contents

1. [NFR Traceability Matrix](#1-nfr-traceability-matrix)
2. [Architectural Decision Records (ADRs)](#2-architectural-decision-records-adrs)
3. [Data Architecture](#3-data-architecture)
4. [Domain Model](#4-domain-model)
5. [API Reference](#5-api-reference)
6. [Local Deployment Guide](#6-local-deployment-guide)
7. [Docker Deployment](#7-docker-deployment)
8. [Verification Steps](#8-verification-steps)

---

## 1. NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|------------------|-------------------|
| **NFR 1.1** Response Time | Async I/O with SQLAlchemy async session + FastAPI async handlers; connection pooling via `async_sessionmaker`; eager-loading of relationships to avoid N+1 queries; SQLite WAL mode for concurrent reads | `app/database.py`, `app/main.py` (all controllers), `app/repositories/order_repo.py` | Run `ab -n 100 -c 10 http://localhost:8000/api/v1/products` and observe avg latency < 200ms |
| **NFR 1.2** Concurrency & Resource Utilization | `asyncio` worker pool in QueueManager; non-blocking DB queries; configurable worker count; priority-based task queuing | `app/infrastructure/queue_manager.py` | Monitor CPU usage under load (`htop`); verify workers scale with `OMS_QUEUE_WORKER_COUNT` |
| **NFR 1.3** Queue Management | Bounded `asyncio.PriorityQueue` with `maxsize`; priority-based task scheduling (CRITICAL > HIGH > NORMAL > LOW); non-essential tasks dropped when full; essential tasks block | `app/infrastructure/queue_manager.py` | POST 2000 rapid orders; check `/health/queue` for `dropped_count` > 0 |
| **NFR 2.1** Graceful Degradation | `GracefulDegradationManager` monitors RSS memory & CPU loadavg (cross-platform: Linux /proc, macOS ps, psutil fallback); disables product search, order history, invoice listing under load | `app/infrastructure/graceful_degradation.py`, `app/controllers/product_controller.py` | Simulate high memory (set low threshold); call `GET /api/v1/products?q=test` → 503 |
| **NFR 2.2** Fault Detection & Recovery | `CircuitBreaker` with configurable failure threshold and recovery timeout; auto-transitions CLOSED → OPEN → HALF_OPEN; tracks metrics (total calls, successes, failures, state transitions) | `app/infrastructure/circuit_breaker.py` | Mock a failing external call; observe circuit trip after N failures; verify auto-recovery after timeout |
| **NFR 2.3** State Preservation | `StateManager` scans for non-terminal orders on startup; persistent heartbeat table in DB for crash detection across restarts; SQLite WAL mode for crash-safe writes; graceful shutdown writes final heartbeat | `app/infrastructure/state_manager.py`, `app/database.py` | Kill process mid-transaction; restart; check logs for "State recovery: found X orders pending processing" |

---

## 2. Architectural Decision Records (ADRs)

### ADR-001: Async Python with FastAPI

| Field | Value |
|-------|-------|
| **Decision** | Use FastAPI with async SQLAlchemy 2.0 |
| **Context** | NFR 1.1 (Response Time), NFR 1.2 (Concurrency) — need high throughput with minimal latency |
| **Alternatives** | 1. Django + DRF: heavier, synchronous by default, lower throughput under async workloads. 2. Flask + gevent: less structured, no built-in OpenAPI, manual async management. |
| **Consequences** | + Native async/await, automatic OpenAPI docs, Pydantic validation. − Requires async-aware DB drivers (aiosqlite). |

### ADR-002: SQLite with WAL Mode for Local Development

| Field | Value |
|-------|-------|
| **Decision** | Use SQLite (via aiosqlite) with WAL journal mode as the primary database |
| **Context** | NFR 2.3 (State Preservation) — need crash-safe writes; local deploy simplicity |
| **Alternatives** | 1. PostgreSQL: more production-ready but adds deployment complexity. 2. In-memory store: loses state on crash, violates NFR 2.3. |
| **Consequences** | + Zero-config, portable, WAL mode provides crash recovery and concurrent read access. − Not suitable for multi-writer horizontal scaling; can be swapped to PostgreSQL via connection string. |

### ADR-003: Bounded Async Priority Queue with Backpressure

| Field | Value |
|-------|-------|
| **Decision** | Use `asyncio.PriorityQueue` with configurable `maxsize`, worker pool, and priority levels (CRITICAL > HIGH > NORMAL > LOW) |
| **Context** | NFR 1.3 (Queue Management), NFR 2.1 (Graceful Degradation) — spikes must not crash the system |
| **Alternatives** | 1. Redis Queue/RQ: adds external dependency, more operational overhead. 2. Thread pool with `queue.Queue`: blocking, doesn't integrate with async event loop. |
| **Consequences** | + In-process, no external deps, priority-based scheduling, non-essential tasks dropped under pressure. − Queue lost on process crash (mitigated by StateManager + DB persistence). |

### ADR-004: Circuit Breaker Pattern for External Calls

| Field | Value |
|-------|-------|
| **Decision** | Implement a local circuit breaker with CLOSED/OPEN/HALF_OPEN states and metrics tracking |
| **Context** | NFR 2.2 (Fault Detection and Recovery) — prevent cascading failures |
| **Alternatives** | 1. Retry-only: can amplify load on failing services. 2. Bulkhead pattern: more complex, requires thread/process isolation. |
| **Consequences** | + Protects downstream services, auto-recovers, tracks metrics. − Adds latency on state transitions; state is in-memory (lost on restart). |

### ADR-005: Layered Architecture (Controller → Service → Repository)

| Field | Value |
|-------|-------|
| **Decision** | Strict three-layer separation: Controller (HTTP), Service (business logic), Repository (data access) |
| **Context** | All NFRs — maintainability, testability, separation of concerns |
| **Alternatives** | 1. Fat controllers: business logic in HTTP handlers → untestable, hard to maintain. 2. Active Record pattern: couples data access with business logic. |
| **Consequences** | + Clear boundaries, testable in isolation, easy to swap implementations. − More files/boilerplate. |

### ADR-006: Request ID Middleware for Distributed Tracing

| Field | Value |
|-------|-------|
| **Decision** | Add a middleware that attaches a unique X-Request-ID to every request/response |
| **Context** | NFR 2.2 (Fault Detection) — need to correlate log entries across components |
| **Alternatives** | 1. No tracing: makes debugging distributed failures harder. 2. OpenTelemetry: more powerful but adds significant complexity. |
| **Consequences** | + Simple, zero-dependency tracing. − IDs are not propagated to external services. |

---

## 3. Data Architecture

### Entity-Relationship Overview

```
┌──────────┐       ┌──────────┐       ┌───────────┐
│ Customer │1───N→│  Order   │1───1→│  Invoice  │
└──────────┘       └──────────┘       └───────────┘
                        │ 1                   │
                        │                     │
                        │ N                   │
                   ┌──────────┐          ┌──────────┐
                   │OrderItem │          │ Payment  │
                   └──────────┘          └──────────┘
                        │ N
                        │ 1
                   ┌──────────┐
                   │ Product  │
                   └──────────┘
```

### Schema (SQLAlchemy ORM)

All tables use UUID hex strings (32 chars) as primary keys. Timestamps are UTC with timezone.

**`customers`**
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(32) PK | UUID hex |
| name | VARCHAR(255) | |
| address | TEXT | |
| phone | VARCHAR(50) | |
| banking_details | TEXT | |
| role | ENUM(UserRole) | CUSTOMER, ORDER_STAFF, ACCOUNTANT |
| created_at | DATETIME(TZ) | |
| updated_at | DATETIME(TZ) | |

**`products`**
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(32) PK | UUID hex |
| name | VARCHAR(255) | |
| description | TEXT | |
| base_price | FLOAT | |
| currency | VARCHAR(3) | ISO 4217 |
| stock_quantity | INTEGER | |
| created_at | DATETIME(TZ) | |

**`orders`**
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(32) PK | UUID hex |
| customer_id | VARCHAR(32) FK→customers | |
| status | ENUM(OrderStatus) | Full lifecycle |
| total_amount | FLOAT | |
| currency | VARCHAR(3) | |
| created_at | DATETIME(TZ) | |
| updated_at | DATETIME(TZ) | |

**`order_items`**
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(32) PK | UUID hex |
| order_id | VARCHAR(32) FK→orders | |
| product_id | VARCHAR(32) FK→products | |
| quantity | INTEGER | |
| unit_price | FLOAT | |
| total_price | FLOAT | |

**`payments`**
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(32) PK | UUID hex |
| order_id | VARCHAR(32) FK→orders | unique |
| amount | FLOAT | |
| currency | VARCHAR(3) | |
| method | ENUM(PaymentMethod) | |
| status | ENUM(PaymentStatus) | |
| transaction_id | VARCHAR(64) | nullable |
| timestamp | DATETIME(TZ) | |

**`invoices`**
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(32) PK | UUID hex |
| order_id | VARCHAR(32) FK→orders | unique |
| customer_id | VARCHAR(32) FK→customers | |
| billing_info | TEXT | |
| total_amount | FLOAT | |
| currency | VARCHAR(3) | |
| issue_date | DATETIME(TZ) | |
| due_date | DATETIME(TZ) | |
| status | ENUM(InvoiceStatus) | |
| paid_at | DATETIME(TZ) | nullable |
| created_at | DATETIME(TZ) | |

**`heartbeats`** (state preservation)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| instance_id | VARCHAR(64) | instance identifier |
| last_heartbeat | DATETIME(TZ) | timestamp |
| status | VARCHAR(32) | running/shutdown |

### Order Status Lifecycle

```
PENDING → REVIEWED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED
    ↑         ↑          ↑           ↑
    └─────────┴──────────┴───────────┘
                    ↓
               CANCELLED
```

---

## 4. Domain Model

### Enums

| Enum | Values |
|------|--------|
| `OrderStatus` | PENDING, REVIEWED, ACCEPTED, INVOICED, PAID, SHIPPED, CLOSED, CANCELLED |
| `PaymentStatus` | PENDING, COMPLETED, FAILED, REFUNDED |
| `PaymentMethod` | CREDIT_CARD, DEBIT_CARD, BANK_TRANSFER, DIGITAL_WALLET |
| `InvoiceStatus` | DRAFT, ISSUED, PAID, OVERDUE, CANCELLED |
| `UserRole` | CUSTOMER, ORDER_STAFF, ACCOUNTANT |

### User Workflow (7 Steps)

1. **Customer** → `POST /api/v1/orders` — Place order (status: PENDING)
2. **Order Staff** → `PUT /api/v1/orders/{id}/review` → Review (status: REVIEWED)
3. **Order Staff** → `PUT /api/v1/orders/{id}/accept` → Accept (status: ACCEPTED)
4. **Accountant** → `POST /api/v1/invoices` — Create invoice (status: INVOICED)
5. **Customer** → `POST /api/v1/payments` — Pay invoice (status: PAID)
6. **Accountant** → `PUT /api/v1/payments/{id}/verify` — Verify payment
7. **Order Staff** → `PUT /api/v1/orders/{id}/ship` — Ship (status: SHIPPED)
8. **Order Staff** → `PUT /api/v1/orders/{id}/close` — Close (status: CLOSED)

Additional: **Order Staff** → `PUT /api/v1/orders/{id}/cancel` — Cancel before shipping

---

## 5. API Reference

Full OpenAPI 3.1 spec available at `/docs` (Swagger UI) or `/redoc` (ReDoc) when the server is running.

### Endpoints Summary

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/v1/customers` | Any | Create customer |
| GET | `/api/v1/customers` | Any | List customers |
| GET | `/api/v1/customers/{id}` | Any | Get customer |
| POST | `/api/v1/products` | Any | Create product |
| GET | `/api/v1/products` | Any | Search products |
| GET | `/api/v1/products/{id}` | Any | Get product |
| POST | `/api/v1/orders` | Customer | Place order |
| GET | `/api/v1/orders` | Any | List orders |
| GET | `/api/v1/orders/{id}` | Any | Get order |
| PUT | `/api/v1/orders/{id}/review` | Staff | Review order |
| PUT | `/api/v1/orders/{id}/accept` | Staff | Accept order |
| PUT | `/api/v1/orders/{id}/cancel` | Staff | Cancel order (before shipping) |
| PUT | `/api/v1/orders/{id}/ship` | Staff | Ship order |
| PUT | `/api/v1/orders/{id}/close` | Staff | Close order |
| POST | `/api/v1/invoices` | Accountant | Create invoice |
| GET | `/api/v1/invoices` | Any | List invoices |
| GET | `/api/v1/invoices/{id}` | Any | Get invoice |
| POST | `/api/v1/payments` | Customer | Process payment |
| GET | `/api/v1/payments` | Any | List payments |
| GET | `/api/v1/payments/{id}` | Any | Get payment |
| PUT | `/api/v1/payments/{id}/verify` | Accountant | Verify payment |
| GET | `/health/live` | Any | Liveness probe |
| GET | `/health/ready` | Any | Readiness probe |
| GET | `/health/degradation` | Any | Degradation status |
| GET | `/health/queue` | Any | Queue metrics |
| GET | `/health/state` | Any | State info |

---

## 6. Local Deployment Guide

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)

### Quick Start

```bash
# 1. Clone the repository
cd oms-backend

# 2. Create virtual environment and install dependencies
uv sync

# 3. Run the application
uv run python -m app.main
```

The server starts at `http://localhost:8000`.

### Configuration

All configuration is via environment variables with the `OMS_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_DATABASE_URL` | `sqlite+aiosqlite:///./oms.db` | Database connection string |
| `OMS_DATABASE_POOL_SIZE` | `10` | Connection pool size |
| `OMS_DATABASE_MAX_OVERFLOW` | `20` | Max overflow connections |
| `OMS_HOST` | `0.0.0.0` | Server bind address |
| `OMS_PORT` | `8000` | Server port |
| `OMS_RELOAD` | `False` | Auto-reload on code changes |
| `OMS_REQUEST_TIMEOUT_SECONDS` | `30` | Request timeout |
| `OMS_QUEUE_MAX_SIZE` | `1000` | Max async queue size |
| `OMS_QUEUE_WORKER_COUNT` | `4` | Number of queue workers |
| `OMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `OMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `30.0` | Seconds before half-open retry |
| `OMS_DEGRADATION_MEMORY_THRESHOLD_MB` | `512` | Memory threshold for degradation |
| `OMS_DEGRADATION_CPU_THRESHOLD_PERCENT` | `90.0` | CPU threshold for degradation |

### Using a `.env` file

```bash
echo "OMS_DATABASE_URL=sqlite+aiosqlite:///./oms.db" > .env
echo "OMS_PORT=8000" >> .env
uv run python -m app.main
```

---

## 7. Docker Deployment

### Build and Run

```bash
# Build the image
docker compose build

# Start the service
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Verify

```bash
curl http://localhost:8000/health/live
# {"status":"alive","uptime_seconds":12.34}
```

---

## 8. Verification Steps

### NFR 1.1 — Response Time

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Run load test
ab -n 200 -c 20 http://localhost:8000/api/v1/products

# Expected: avg latency < 200ms, no failed requests
```

### NFR 1.2 — Concurrency

```bash
# Send concurrent requests
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8000/api/v1/orders \
    -H "Content-Type: application/json" \
    -d '{"customer_id":"<id>","items":[{"product_id":"<id>","quantity":1}]}' &
done
wait

# Check /health/queue for processed_count
curl http://localhost:8000/health/queue
```

### NFR 1.3 — Queue Management

```bash
# Set small queue size
export OMS_QUEUE_MAX_SIZE=10

# Rapidly enqueue many tasks
for i in $(seq 1 100); do
  curl -s -X POST http://localhost:8000/api/v1/orders \
    -H "Content-Type: application/json" \
    -d '{"customer_id":"<id>","items":[{"product_id":"<id>","quantity":1}]}' &
done

# Verify dropped_count > 0
curl http://localhost:8000/health/queue
```

### NFR 2.1 — Graceful Degradation

```bash
# Set a very low memory threshold
export OMS_DEGRADATION_MEMORY_THRESHOLD_MB=1

# Restart server, then try product search
curl http://localhost:8000/api/v1/products?q=test
# Expected: 503 Service Unavailable with degradation message

# Check degradation status
curl http://localhost:8000/health/degradation
# {"degraded":true,"product_search_disabled":true,...}
```

### NFR 2.2 — Fault Detection & Recovery

```bash
# The circuit breaker is used for external service calls.
# To test, you can observe the circuit breaker state programmatically.
# Check the logs for circuit breaker state transitions.
# Simulate by calling a service that raises exceptions repeatedly.
```

### NFR 2.3 — State Preservation

```bash
# 1. Create an order (POST /api/v1/orders)
# 2. Review it (PUT /api/v1/orders/{id}/review)
# 3. Kill the server process (Ctrl+C or kill -9)
# 4. Restart the server
# 5. Check logs for:
#    "State recovery: found 1 orders pending processing"
# 6. The order should still be in REVIEWED status
curl http://localhost:8000/api/v1/orders/<id>
```

### Full Workflow Test

```bash
# 1. Create a customer
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","address":"123 Main St","phone":"555-0100","banking_details":"ACC-12345"}')
CUSTOMER_ID=$(echo $CUSTOMER | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Create a product
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Widget","base_price":19.99,"stock_quantity":100}')
PRODUCT_ID=$(echo $PRODUCT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Place order (Customer)
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":2}]}")
ORDER_ID=$(echo $ORDER | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order: $ORDER_ID"

# 4. Review order (Staff)
curl -s -X PUT "http://localhost:8000/api/v1/orders/$ORDER_ID/review"

# 5. Accept order (Staff)
curl -s -X PUT "http://localhost:8000/api/v1/orders/$ORDER_ID/accept"

# 6. Create invoice (Accountant)
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"billing_info\":\"Invoice for Alice\"}")
INVOICE_ID=$(echo $INVOICE | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 7. Pay invoice (Customer)
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"amount\":39.98,\"method\":\"CREDIT_CARD\"}")
PAYMENT_ID=$(echo $PAYMENT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 8. Verify payment (Accountant)
curl -s -X PUT "http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify"

# 9. Ship order (Staff)
curl -s -X PUT "http://localhost:8000/api/v1/orders/$ORDER_ID/ship"

# 10. Close order (Staff)
curl -s -X PUT "http://localhost:8000/api/v1/orders/$ORDER_ID/close"

# 11. Verify final state
curl -s "http://localhost:8000/api/v1/orders/$ORDER_ID" | python3 -m json.tool
```

### Run Automated Tests

```bash
# Run the full workflow integration test
uv run python test_workflow.py

# Run the HTTP-based integration test (requires server running)
uv run python test_integration.py
```
