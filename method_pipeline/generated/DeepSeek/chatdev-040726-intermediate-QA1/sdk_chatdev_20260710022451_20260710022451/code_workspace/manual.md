# Order Management System (OMS) — User Manual

> **Version:** 1.0.0  
> **Tech Stack:** Python 3.12 / FastAPI / PostgreSQL 16 / Redis 7 / RabbitMQ  
> **Target Hardware:** Single node, 4+ CPU cores, up to 98 GB RAM

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [Quick Start Guide](#3-quick-start-guide)
4. [API Reference](#4-api-reference)
5. [User Roles & Workflows](#5-user-roles--workflows)
6. [Order Lifecycle & State Machine](#6-order-lifecycle--state-machine)
7. [Performance & Rate Limiting](#7-performance--rate-limiting)
8. [Caching Strategy](#8-caching-strategy)
9. [Background Workers & Queueing](#9-background-workers--queueing)
10. [Monitoring & Instrumentation](#10-monitoring--instrumentation)
11. [Load Testing](#11-load-testing)
12. [Configuration Reference](#12-configuration-reference)
13. [Project Structure](#13-project-structure)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. System Overview

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that handles the complete order workflow:

```
Customer Ordering → Payment Processing → Invoicing → Shipping → Closure
```

It serves **three roles**:
- **Customer** — browses products, places orders, pays invoices
- **Order Staff** — reviews/accepts orders, ships paid orders, closes completed orders
- **Accountant** — creates invoices, verifies payments

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language & Framework | **Python 3.12 + FastAPI** | Async I/O for high concurrency; fast development velocity |
| Database | **PostgreSQL 16 + asyncpg** | ACID compliance, optimistic locking, mature async driver |
| Cache | **Redis 7** | Shared across workers, TTL-based invalidation, sub-ms reads |
| Message Queue | **RabbitMQ** | Durable queues, DLQ support, persistent acknowledgments |
| Rate Limiter | **In-memory token bucket** | ~0.01 ms check latency, no network hop on single-node |

---

## 2. Architecture at a Glance

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│   FastAPI App     │────▶│  Service Layer   │────▶│  PostgreSQL  │
│  (4 async workers)│     │  (business logic) │     │  (asyncpg)   │
│  uvloop + httptools│     └────────┬─────────┘     │  pool=20+10  │
└──────┬───────────┘              │                 └──────────────┘
       │                          │
       │                  ┌───────▼────────┐
       │                  │    Redis 7      │
       │                  │  (product cache)│
       │                  └───────┬────────┘
       │                          │
       │                  ┌───────▼────────┐
       │                  │   RabbitMQ     │
       │                  │  (task queue)   │
       │                  └───────┬────────┘
       │                          │
       │                  ┌───────▼────────┐
       │                  │  Worker (async)│
       │                  │ invoice gen    │
       │                  │ notifications  │
       │                  └────────────────┘
```

### Connection Pool Sizing

| Parameter | Value | Justification |
|-----------|-------|---------------|
| `pool_size` | 20 | `2 × cores + effective_spindles` = 2×4 + 12 = 20 |
| `max_overflow` | 10 | Allows burst of 10 extra connections (max 30 total) |
| `pool_timeout` | 30 s | Clients wait up to 30 s for a connection before error |
| Workers | 4 | One per CPU core; each runs an async event loop |

### Rate Limiter Sizing

| Parameter | Value | Justification |
|-----------|-------|---------------|
| `max_tokens` | 200 | Allows burst of 200 requests before throttling |
| `refill_rate` | 50/s | Steady-state throughput cap (~3 000 requests/min) |
| `refill_interval` | 0.1 s | Smooth refill prevents token starvation |

---

## 3. Quick Start Guide

### Prerequisites

- **Docker & Docker Compose** (recommended for full stack)
- **Python 3.12+** (for local development without Docker)
- **uv** package manager (recommended, but pip works too)

### Option A: Full Stack with Docker Compose (Recommended)

```bash
# 1. Clone the project
cd oms-backend

# 2. Start all services (PostgreSQL, Redis, RabbitMQ, App, Worker)
docker compose up -d

# 3. Run database migrations
docker compose exec app alembic upgrade head

# 4. Verify health
curl http://localhost:8000/health
# → {"status":"ok","service":"oms"}

# 5. Open Swagger UI
open http://localhost:8000/docs
```

### Option B: Local Development

```bash
# 1. Start infrastructure only
docker compose up -d postgres redis rabbitmq

# 2. Create virtual environment
uv venv
source .venv/bin/activate

# 3. Install dependencies
uv sync

# 4. Run migrations
alembic upgrade head

# 5. Start the app (Terminal 1)
uvicorn app.main:app --reload --workers 4 --loop uvloop --http httptools

# 6. Start the background worker (Terminal 2)
python -m app.worker
```

### Seeding Test Data

```bash
# Create a customer
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","address":"123 Main St","phone":"+1-555-1234","banking_details":"ACC-001","role":"CUSTOMER"}'

# Create products
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Widget A","base_price":29.99,"currency":"USD","stock_available":100}'

curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Widget B","base_price":49.99,"currency":"USD","stock_available":50}'
```

### Running the Full Order Workflow

```bash
# Step 1: Customer places order (CREATED)
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":1,"line_items":[{"product_id":1,"quantity":2}]}'
# → {"id":1, "status":"CREATED", "version":1, ...}

# Step 2: Order Staff accepts (ACCEPTED)
curl -X PATCH http://localhost:8000/api/v1/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"new_status":"ACCEPTED","version":1}'
# → {"id":1, "status":"ACCEPTED", "version":2, ...}

# Step 3: Accountant creates invoice (INVOICED)
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{"order_id":1,"billing_name":"Alice","billing_address":"123 Main St","version":2}'
# → {"id":1, "status":"ISSUED", ...}  (order now INVOICED, version=3)

# Step 4: Customer pays invoice (payment PENDING, order stays INVOICED)
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{"order_id":1,"amount":59.98,"currency":"USD","method":"CREDIT_CARD","version":3}'
# → {"id":1, "status":"PENDING", ...}

# Step 5: Accountant verifies payment (PAID)
curl -X POST http://localhost:8000/api/v1/payments/verify \
  -H "Content-Type: application/json" \
  -d '{"payment_id":1,"status":"COMPLETED","order_version":3}'
# → {"id":1, "status":"COMPLETED", ...}  (order now PAID, version=4)

# Step 6: Order Staff ships (SHIPPED)
curl -X PATCH http://localhost:8000/api/v1/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"new_status":"SHIPPED","version":4}'
# → {"id":1, "status":"SHIPPED", "version":5, ...}

# Step 7: Order Staff closes (CLOSED)
curl -X PATCH http://localhost:8000/api/v1/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"new_status":"CLOSED","version":5}'
# → {"id":1, "status":"CLOSED", "version":6, ...}
```

---

## 4. API Reference

**Base URL:** `http://localhost:8000/api/v1`

### Customer Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/customers` | Create a new customer |
| `GET` | `/customers/{id}` | Get customer by ID |
| `GET` | `/customers` | List all customers (paginated) |

**Create Customer:**
```json
{
  "name": "Alice",
  "address": "123 Main St",
  "phone": "+1-555-1234",
  "banking_details": "ACC-001",
  "role": "CUSTOMER"
}
```

### Product Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/products` | Create a new product |
| `GET` | `/products/{id}` | Get product by ID (cached) |
| `GET` | `/products` | Search/browse products (cached) |
| `PUT` | `/products/{id}` | Update product (invalidates cache) |

**Search Parameters:**
- `q` — Full-text search query
- `min_price` / `max_price` — Price range filter
- `in_stock_only` — Boolean, filter to in-stock only
- `page` / `page_size` — Pagination (default: page=1, page_size=20)

### Order Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/orders` | Place a new order **(rate-limited, hot path)** |
| `GET` | `/orders/{id}` | Get order with line items |
| `GET` | `/orders` | List orders (filter by `customer_id`) |
| `PATCH` | `/orders/{id}/status` | Transition order status |

**Place Order (checkout):**
```json
{
  "customer_id": 1,
  "line_items": [
    {"product_id": 1, "quantity": 2}
  ]
}
```

**Update Status:**
```json
{
  "new_status": "ACCEPTED",
  "version": 1
}
```

### Payment Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/payments` | Process a payment **(rate-limited, hot path)** |
| `POST` | `/payments/verify` | Accountant verifies a payment |
| `GET` | `/payments/{id}` | Get payment by ID |
| `GET` | `/payments/by-order/{order_id}` | List payments for an order |

**Process Payment:**
```json
{
  "order_id": 1,
  "amount": 59.98,
  "currency": "USD",
  "method": "CREDIT_CARD",
  "version": 3
}
```

**Verify Payment:**
```json
{
  "payment_id": 1,
  "status": "COMPLETED",
  "order_version": 3
}
```

### Invoice Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/invoices` | Create invoice for accepted order |
| `GET` | `/invoices/{id}` | Get invoice by ID |
| `GET` | `/invoices/by-order/{order_id}` | List invoices for an order |

**Create Invoice:**
```json
{
  "order_id": 1,
  "billing_name": "Alice",
  "billing_address": "123 Main St",
  "version": 2
}
```

### System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (`{"status":"ok","service":"oms"}`) |
| `GET` | `/metrics` | Performance metrics snapshot |
| `GET` | `/docs` | Swagger UI documentation |
| `GET` | `/openapi.json` | OpenAPI 3.0 specification |

### Error Responses

| Status | Meaning | Example |
|--------|---------|--------|
| **400** | Domain rule violation | Invalid state transition, insufficient stock |
| **404** | Entity not found | Customer, product, or order doesn't exist |
| **409** | Optimistic lock conflict | Concurrent modification detected; retry |
| **429** | Rate limited | Too many requests; includes `Retry-After` header |

**429 Response Example:**
```json
{
  "detail": "Too many requests. Please retry after the rate limit window.",
  "retry_after_seconds": 1
}
```
Headers: `Retry-After: 1`, `X-RateLimit-Limit: 200`

---

## 5. User Roles & Workflows

### Role: Customer

The customer interacts with the system through the **checkout journey** (hot path — strict latency requirements):

1. **Browse products** — `GET /api/v1/products` (cached, p95 ≤ 150 ms)
2. **View product details** — `GET /api/v1/products/{id}` (cached)
3. **Place order** — `POST /api/v1/orders` (rate-limited, p95 ≤ 300 ms)
4. **Pay invoice** — `POST /api/v1/payments` (rate-limited, p95 ≤ 300 ms)

### Role: Order Staff

Order Staff handles back-office operations (relaxed latency budgets):

1. **Review & accept orders** — `PATCH /api/v1/orders/{id}/status` → `ACCEPTED`
2. **Ship paid orders** — `PATCH /api/v1/orders/{id}/status` → `SHIPPED`
3. **Close completed orders** — `PATCH /api/v1/orders/{id}/status` → `CLOSED`

### Role: Accountant

Accountant handles financial operations (back-office, relaxed latency):

1. **Create invoice** — `POST /api/v1/invoices` (transitions order to `INVOICED`)
2. **Verify payment** — `POST /api/v1/payments/verify` (transitions order to `PAID`)

---

## 6. Order Lifecycle & State Machine

The order status follows a strict state machine enforced at the **domain layer** (not just controller-level checks). Illegal transitions are rejected with a clear error.

```
                    ┌──────────┐
                    │ CREATED  │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
              ┌────▶│ ACCEPTED │◀────┐
              │     └────┬─────┘     │
              │          │          │
              │     ┌────▼─────┐     │
              │     │ INVOICED │     │
              │     └────┬─────┘     │
              │          │          │
              │     ┌────▼─────┐     │
              │     │  PAID    │     │
              │     └────┬─────┘     │
              │          │          │
              │     ┌────▼─────┐     │
              │     │ SHIPPED  │     │
              │     └────┬─────┘     │
              │          │          │
              │     ┌────▼─────┐     │
              │     │  CLOSED  │     │
              │     └──────────┘     │
              │                      │
              │     ┌──────────┐      │
              └─────│CANCELLED│◀─────┘
                    └──────────┘
```

### Allowed Transitions

| Current State | Allowed Next States |
|---------------|---------------------|
| `CREATED` | `ACCEPTED`, `CANCELLED` |
| `ACCEPTED` | `INVOICED`, `CANCELLED` |
| `INVOICED` | `PAID`, `CANCELLED` |
| `PAID` | `SHIPPED`, `CANCELLED` |
| `SHIPPED` | `CLOSED` |
| `CLOSED` | *(terminal — no transitions)* |
| `CANCELLED` | *(terminal — no transitions)* |

### Optimistic Locking

Every order has a `version` field that increments on each status change. When updating an order's status, you must provide the current `version` number. If another operation has modified the order concurrently, the system returns a **409 Conflict** error.

**Example of a conflict:**
```bash
# User A tries to accept order (version=1)
curl -X PATCH ... -d '{"new_status":"ACCEPTED","version":1}'
# → 200 OK (version becomes 2)

# User B tries to cancel the same order (version=1 — stale!)
curl -X PATCH ... -d '{"new_status":"CANCELLED","version":1}'
# → 400 {"detail": "Concurrent modification detected; retry the operation."}
```

---

## 7. Performance & Rate Limiting

### Rate Limiter (Token Bucket)

The system uses an **in-memory token-bucket rate limiter** to protect the checkout hot-path endpoints from traffic spikes.

**Guarded endpoints:**
- `POST /api/v1/orders` — Place order
- `POST /api/v1/payments` — Process payment

**How it works:**
1. The bucket starts with 200 tokens (max burst capacity).
2. Tokens are refilled at 50 tokens/second (smoothly, every 0.1 s).
3. Each request to a guarded endpoint consumes 1 token.
4. If the bucket is empty, the request is rejected with **HTTP 429** and a `Retry-After: 1` header.
5. Read operations (GET), back-office transitions (PATCH), and system endpoints (health, metrics, docs) are **not rate-limited**.

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Checkout p95 latency | ≤ 300 ms | Locust at 2 000 concurrent users |
| Search/browse p95 latency | ≤ 150 ms | Locust at 2 000 concurrent users |
| Request queueing time (p95) | < 50 ms | `/metrics` endpoint |
| Error rate (non-429) | < 1% | Locust stats |
| CPU usage | < 80% | `docker stats` |
| Memory usage | < 4 GB | `docker stats` |

### Backpressure & Spike Absorption

When traffic exceeds capacity:
1. The **rate limiter** rejects excess checkout requests with 429.
2. **Deferrable work** (invoice generation, notifications) is pushed to **RabbitMQ** queues and processed asynchronously by the background worker.
3. The **bounded DB connection pool** (max 30 connections) prevents database overload.

---

## 8. Caching Strategy

### What Gets Cached

| Data | Cache Store | TTL | Invalidation |
|------|-------------|-----|--------------|
| Individual products | Redis | 60 seconds | On product update (`PUT /api/v1/products/{id}`) |
| Search results | Redis | 30 seconds | TTL expiry (eventual consistency) |

### Cache Flow

```
GET /api/v1/products/{id}
  │
  ├── Check Redis cache
  │     ├── HIT  → Return cached product (fast path)
  │     └── MISS → Query PostgreSQL, write to Redis, return
  │
PUT /api/v1/products/{id}
  │
  ├── Update PostgreSQL
  ├── Invalidate Redis cache for this product
  └── Re-write updated product to Redis
```

### Why Redis?

- **Shared across workers** — All 4 FastAPI workers share the same Redis instance, so a cache write by one worker is immediately visible to all others.
- **TTL-based invalidation** — No complex cache-coherency protocol needed; stale data is automatically evicted.
- **Sub-millisecond reads** — Redis operates entirely in memory, delivering consistent <1 ms read latency.

---

## 9. Background Workers & Queueing

### Architecture

RabbitMQ decouples **spike-prone work** from the request thread:

```
Request Thread (FastAPI)          Background Worker
┌──────────────────────┐          ┌──────────────────────┐
│ POST /api/v1/orders │─────────▶│ oms.notifications    │
│ (returns 201 fast)  │  publish │ (email/SMS/webhook)  │
└──────────────────────┘          └──────────────────────┘

┌──────────────────────┐          ┌──────────────────────┐
│ POST /api/v1/invoices│─────────▶│ oms.invoice.generation│
│ (returns 201 fast)   │  publish │ (PDF generation)      │
└──────────────────────┘          └──────────────────────┘
```

### What Gets Queued

| Event | Queue | Handler |
|-------|-------|---------|
| Order created | `oms.notifications` | Sends notification |
| Order status changed | `oms.notifications` | Sends notification |
| Payment initiated | `oms.notifications` | Sends notification |
| Payment verified | `oms.notifications` | Sends notification |
| Invoice created | `oms.notifications` | Sends notification |
| Invoice generation | `oms.invoice.generation` | Generates invoice PDF |

### Running the Worker

```bash
# Start the background worker (separate process)
python -m app.worker

# Or via Docker Compose (already configured)
docker compose up -d worker
```

The worker consumes messages from both queues concurrently using `asyncio.gather`. Each queue has a prefetch count of 10, meaning the worker processes up to 10 messages at a time per queue.

---

## 10. Monitoring & Instrumentation

### Metrics Endpoint

`GET /metrics` returns a real-time snapshot of system performance:

```json
{
  "request_count": {
    "/api/v1/orders": 1500,
    "/api/v1/products": 4500,
    "/api/v1/payments": 800
  },
  "status_count": {
    "200": 5800,
    "201": 200,
    "400": 15,
    "429": 50
  },
  "latency": {
    "/api/v1/orders": {
      "p50_ms": 45,
      "p95_ms": 210,
      "p99_ms": 380,
      "count": 1500
    },
    "/api/v1/products": {
      "p50_ms": 12,
      "p95_ms": 85,
      "p99_ms": 160,
      "count": 4500
    }
  },
  "rate_limiter": {
    "available_tokens": 150,
    "max_tokens": 200
  }
}
```

### Health Check

`GET /health` — Returns `{"status": "ok", "service": "oms"}` for load balancer probing.

### Structured Logging

All logs are JSON-formatted with correlation IDs for end-to-end tracing:

```json
{
  "asctime": "2025-01-01T12:00:00+0000",
  "name": "app.services.order_service",
  "levelname": "INFO",
  "message": "Order created",
  "correlation_id": "abc-123-def"
}
```

Every request receives a correlation ID (either from the `X-Correlation-ID` header or auto-generated). This ID is propagated through all log messages and returned in the response headers, enabling you to trace a request across all services.

### Docker Stats

Monitor resource usage in real-time:

```bash
docker stats
```

Expected resource usage under load:
- **app container:** CPU < 80%, Memory < 4 GB
- **postgres container:** CPU < 50%, Memory < 2 GB
- **redis container:** CPU < 20%, Memory < 1 GB
- **rabbitmq container:** CPU < 20%, Memory < 1 GB

---

## 11. Load Testing

### Test Scenarios

The project includes a Locust-based load test suite in `load_test/`.

| Scenario | Users | Spawn Rate | Duration | Purpose |
|----------|-------|------------|----------|---------|
| **Baseline** | 200 | 10 users/s | 5 min | Verify basic functionality |
| **Sustained** | 2 000 | 50 users/s | 10 min | Verify NFR 1.1 & 1.2 |
| **Spike** | 0→6 000 | 100 users/s | 5 min | Verify NFR 1.3 (3x spike) |

### Running Load Tests

```bash
# 1. Ensure the stack is running
docker compose up -d

# 2. Run migrations
docker compose exec app alembic upgrade head

# 3. Baseline test
locust -f load_test/locustfile.py --scenario baseline \
  --host http://localhost:8000 --headless --csv=results/baseline

# 4. Sustained load test
locust -f load_test/locustfile.py --scenario sustained \
  --host http://localhost:8000 --headless --csv=results/sustained

# 5. Spike test
locust -f load_test/locustfile.py --scenario spike \
  --host http://localhost:8000 --headless --csv=results/spike
```

### Pass/Fail Criteria

| Metric | Threshold | Source |
|--------|-----------|--------|
| Checkout p95 latency | ≤ 300 ms | Locust stats |
| Search p95 latency | ≤ 150 ms | Locust stats |
| Throughput (sustained) | ≥ 500 RPS | Locust stats |
| Error rate (non-429) | < 1% | Locust stats |
| CPU usage | < 80% | `docker stats` |
| Memory usage | < 4 GB | `docker stats` |
| Request queueing p95 | < 50 ms | `/metrics` endpoint |
| Rate limiter tokens | > 0 at steady state | `/metrics` endpoint |

### What the Load Test Simulates

The Locust test (`load_test/locustfile.py`) simulates realistic user behavior:

- **Browse products** (3× weight) — Search and view product listings
- **Get product** (2× weight) — View individual product details
- **Place order** (1× weight) — Create a new order (checkout)
- **Process workflow** (1× weight) — Full order lifecycle (accept → invoice → pay → verify → ship → close)

Think time is randomized between 0.5 and 3.0 seconds to simulate realistic user pacing.

---

## 12. Configuration Reference

All configuration is loaded from environment variables with the `OMS_` prefix. See `app/config.py` for defaults.

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_HOST` | `0.0.0.0` | Bind address |
| `OMS_PORT` | `8000` | HTTP port |
| `OMS_WORKERS` | `4` | Number of uvicorn workers |
| `OMS_LOG_LEVEL` | `INFO` | Logging level |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_DB_URL` | `postgresql+asyncpg://oms:oms@localhost:5432/oms` | PostgreSQL connection string |
| `OMS_DB_POOL_SIZE` | `20` | Connection pool size |
| `OMS_DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `OMS_DB_POOL_TIMEOUT` | `30` | Connection wait timeout (seconds) |

### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `OMS_REDIS_PRODUCT_CACHE_TTL` | `60` | Product cache TTL (seconds) |

### RabbitMQ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection string |
| `OMS_INVOICE_QUEUE_NAME` | `oms.invoice.generation` | Invoice generation queue |
| `OMS_NOTIFICATION_QUEUE_NAME` | `oms.notifications` | Notifications queue |

### Rate Limiter Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_RATE_LIMIT_TOKENS` | `200` | Max burst capacity |
| `OMS_RATE_LIMIT_REFILL_RATE` | `50.0` | Tokens per second refill |
| `OMS_RATE_LIMIT_REFILL_INTERVAL` | `0.1` | Refill tick interval (seconds) |

### .env File

You can also use a `.env` file in the project root:

```env
OMS_DB_URL=postgresql+asyncpg://oms:oms@localhost:5432/oms
OMS_REDIS_URL=redis://localhost:6379/0
OMS_RABBITMQ_URL=amqp://guest:guest@localhost:5672/
OMS_LOG_LEVEL=INFO
```

---

## 13. Project Structure

```
oms-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Configuration (env-based)
│   ├── worker.py                 # Background task consumer
│   │
│   ├── domain/                   # Domain layer
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   ├── enums.py              # Status enums with state machine
│   │   └── exceptions.py         # Domain exceptions
│   │
│   ├── infrastructure/           # Infrastructure layer
│   │   ├── database.py           # Async DB engine + session factory
│   │   ├── cache.py              # Redis cache helpers
│   │   ├── queue.py              # RabbitMQ publisher
│   │   ├── rate_limiter.py       # Token-bucket rate limiter
│   │   └── logging.py            # Structured JSON logging
│   │
│   ├── repositories/             # Data access layer
│   │   ├── base.py               # Generic CRUD repository
│   │   ├── customer.py
│   │   ├── product.py            # With search support
│   │   ├── order.py              # With line-item eager loading
│   │   ├── payment.py
│   │   └── invoice.py
│   │
│   ├── services/                 # Business logic layer
│   │   ├── order_service.py      # Order lifecycle + state machine
│   │   ├── product_service.py    # Cached search/browse
│   │   ├── payment_service.py    # Payment processing
│   │   ├── invoice_service.py   # Invoice creation
│   │   └── customer_service.py  # Customer CRUD
│   │
│   ├── controllers/              # REST API layer
│   │   ├── customer_controller.py
│   │   ├── product_controller.py
│   │   ├── order_controller.py
│   │   ├── payment_controller.py
│   │   └── invoice_controller.py
│   │
│   └── middleware/               # ASGI middleware
│       ├── correlation_id.py     # Request tracing
│       ├── rate_limiter_middleware.py  # Admission control
│       └── metrics.py            # Performance metrics
│
├── alembic/                      # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
│
├── load_test/                    # Load testing
│   ├── locustfile.py             # Locust test scenarios
│   └── plan.md                   # Test plan documentation
│
├── tests/                        # Unit tests
│   ├── test_domain.py
│   └── test_rate_limiter.py
│
├── Dockerfile                    # Production container image
├── docker-compose.yml            # Local development stack
├── pyproject.toml                # Python project configuration
├── .env                          # Environment variables
└── README.md                     # Project documentation
```

---

## 14. Troubleshooting

### Common Issues

#### "Cannot connect to PostgreSQL"

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Verify connection string in .env
echo $OMS_DB_URL
```

#### "RabbitMQ not available" Warning on Startup

The app starts gracefully even if RabbitMQ is unavailable. Queues will be declared when the connection is established. If you see this warning:

```bash
# Check if RabbitMQ is running
docker compose ps rabbitmq

# Restart if needed
docker compose restart rabbitmq
```

#### Rate Limiter Rejecting All Requests

If you're getting 429 responses during development:

```bash
# Check current rate limiter state
curl http://localhost:8000/metrics | jq .rate_limiter

# The bucket refills at 50 tokens/second. Wait a few seconds and retry.
```

#### Optimistic Lock Conflicts

If you get a 409 Conflict error:

```bash
# Re-fetch the order to get the latest version
curl http://localhost:8000/api/v1/orders/1

# Retry the operation with the updated version number
curl -X PATCH http://localhost:8000/api/v1/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"new_status":"ACCEPTED","version":2}'  # Use the latest version
```

#### "Insufficient stock" Error

```bash
# Check current stock levels
curl http://localhost:8000/api/v1/products/1

# Create more stock or reduce the order quantity
curl -X PUT http://localhost:8000/api/v1/products/1 \
  -H "Content-Type: application/json" \
  -d '{"description":"Widget A","base_price":29.99,"currency":"USD","stock_available":500}'
```

#### Database Migration Fails

```bash
# Check migration history
docker compose exec app alembic history

# Downgrade and re-apply
docker compose exec app alembic downgrade -1
docker compose exec app alembic upgrade head

# If still failing, check the migration file
cat alembic/versions/001_initial_schema.py
```

### Getting Help

- **Swagger UI:** `http://localhost:8000/docs` — Interactive API documentation
- **Metrics:** `http://localhost:8000/metrics` — Real-time performance data
- **Health:** `http://localhost:8000/health` — Service health check
- **RabbitMQ Management:** `http://localhost:15672` (guest/guest) — Queue monitoring

---

*© ChatDev — Order Management System v1.0.0*
