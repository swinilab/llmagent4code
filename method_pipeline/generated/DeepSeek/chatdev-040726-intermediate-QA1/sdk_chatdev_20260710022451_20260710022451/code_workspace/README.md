# Order Management System (OMS) — Backend

Production-grade, backend-only e-commerce Order Management System built with **Python / FastAPI / PostgreSQL / Redis / RabbitMQ**.

---

## Table of Contents

1. [NFR Traceability Matrix](#1-nfr-traceability-matrix)
2. [Architectural Decision Records](#2-architectural-decision-records)
3. [Data Architecture](#3-data-architecture)
4. [Domain Model](#4-domain-model)
5. [API Reference](#5-api-reference)
6. [Local Deployment Guide](#6-local-deployment-guide)
7. [Load-Test Plan](#7-load-test-plan)
8. [Instrumentation](#8-instrumentation)

---

## 1. NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Quantitative Verification |
|-----|------------------------|------------------|--------------------------|
| **NFR 1.1** — Checkout p95 ≤ 300 ms | Async I/O (FastAPI/uvicorn/uvloop), DB connection pooling (asyncpg, pool_size=20), Redis product cache, token-bucket rate limiter | `app/services/order_service.py`, `app/services/payment_service.py`, `app/infrastructure/database.py`, `app/infrastructure/cache.py` | Locust: `POST /api/v1/orders` at 2 000 concurrent users → p95 < 300 ms |
| **NFR 1.1** — Search p95 ≤ 150 ms | Redis product cache (TTL 60 s), async DB queries with pagination | `app/services/product_service.py`, `app/infrastructure/cache.py` | Locust: `GET /api/v1/products` at 2 000 concurrent users → p95 < 150 ms |
| **NFR 1.2** — 5 000 concurrent sessions, avg queueing < 50 ms | Bounded DB connection pool (20+10 overflow), async event loop (uvloop), 4 workers (1 per core), Redis cache offloads DB reads | `app/infrastructure/database.py` (pool_size=20, max_overflow=10), `app/config.py` (workers=4) | `/metrics` endpoint: request queueing time p95 < 50 ms; `docker stats`: CPU < 80%, memory < 4 GB |
| **NFR 1.3** — 3x spike absorption | Token-bucket rate limiter (200 burst, 50/s refill), RabbitMQ task queue for deferrable work (invoice gen, notifications) | `app/infrastructure/rate_limiter.py`, `app/infrastructure/queue.py`, `app/middleware/rate_limiter_middleware.py`, `app/worker.py` | Locust spike test (0→6 000 users in 60 s): 0% crash rate, 429 responses for excess, no unbounded memory growth |

### Connection Pool Sizing Rationale (NFR 1.2)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| `pool_size` | 20 | For 4 CPU cores: `pool_size = 2 * cores + effective_spindles` ≈ 2*4 + 12 = 20. Each connection ~10 MB → 200 MB total. |
| `max_overflow` | 10 | Allows burst of 10 extra connections (max 30 total) for traffic spikes. |
| `pool_timeout` | 30 s | Clients wait up to 30 s for a connection before error. |
| Workers | 4 | One per CPU core; each runs an async event loop (uvloop) multiplexing many requests. |
| Async driver | asyncpg | Non-blocking I/O; a single worker handles hundreds of concurrent DB operations without thread-per-connection overhead. |

### Rate Limiter Sizing Rationale (NFR 1.3)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| `max_tokens` | 200 | Allows burst of 200 requests before throttling. At 2 000 users with think time ~2 s, peak RPS ≈ 1 000. 200 tokens provides headroom. |
| `refill_rate` | 50/s | Steady-state throughput cap. At 50 tokens/s, the system handles 3 000 requests/min, matching the target sustained load. |
| `refill_interval` | 0.1 s | Smooth refill prevents token starvation between ticks. |

---

## 2. Architectural Decision Records

### ADR-001: Language & Framework

| Field | Value |
|-------|-------|
| **Decision** | Python 3.12 + FastAPI |
| **Context** | NFR 1.1 (latency), NFR 1.2 (concurrency). Need async I/O for high concurrency on a single node. |
| **Alternatives** | **Go + Gin**: faster raw throughput but slower development velocity; smaller ecosystem for ORM/queue. **Java + Spring Boot**: heavier memory footprint (JVM overhead), longer startup, more boilerplate. |
| **Consequences** | Python's GIL is avoided via async/await; FastAPI's Starlette/uvicorn provides competitive async performance (~20k RPS on 4 cores). Accepts ~15% throughput penalty vs Go in exchange for faster iteration. |

### ADR-002: Database

| Field | Value |
|-------|-------|
| **Decision** | PostgreSQL 16 + asyncpg + SQLAlchemy 2.0 (async) |
| **Context** | ACID compliance for order management, complex queries, optimistic locking. |
| **Alternatives** | **MySQL 8**: similar ACID but weaker JSON support and less mature async driver. **SQLite**: not suitable for concurrent writes. |
| **Consequences** | PostgreSQL provides serializable isolation for order integrity. asyncpg is the fastest async PG driver for Python. SQLAlchemy 2.0's async ORM adds ~5% overhead vs raw SQL but provides type safety and migration tooling. |

### ADR-003: Cache

| Field | Value |
|-------|-------|
| **Decision** | Redis 7 (in-memory cache for product search/browse) |
| **Context** | NFR 1.1 (search p95 ≤ 150 ms). Product data is read-heavy, rarely changes. |
| **Alternatives** | **In-process cache (dict/cachetools)**: faster but not shared across workers; cache invalidation complex. **Memcached**: simpler but lacks data structures and TTL flexibility. |
| **Consequences** | Redis adds a network hop (~1 ms) but provides shared cache across 4 workers, TTL-based invalidation, and can be used for distributed rate limiting in future. |

### ADR-004: Message Queue

| Field | Value |
|-------|-------|
| **Decision** | RabbitMQ (via aio-pika) for deferrable work |
| **Context** | NFR 1.3 (spike absorption). Invoice generation and notifications are not on the critical path. |
| **Alternatives** | **Kafka**: higher throughput but heavier operational overhead; overkill for single-node. **Redis Streams**: simpler but lacks DLQ, dead-letter routing, and persistent acknowledgments. |
| **Consequences** | RabbitMQ provides durable queues, message acknowledgments, and dead-letter exchanges. Adds ~50 ms latency for async work but keeps request threads free. |

### ADR-005: Rate Limiter

| Field | Value |
|-------|-------|
| **Decision** | In-memory token bucket (local to each worker process) |
| **Context** | NFR 1.3 (3x spike). Single-node deployment; no need for distributed coordination. |
| **Alternatives** | **Redis-backed token bucket**: needed for multi-instance but adds network latency. **Fixed-window counter**: simpler but allows double-burst at window boundaries. |
| **Consequences** | In-memory is fastest (~0.01 ms check). On a single node with 4 workers, each has its own bucket → effective capacity is 4x. Accepts slight unevenness across workers. |

---

## 3. Data Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   FastAPI    │────▶│  Order Service   │────▶│  PostgreSQL  │
│  (4 workers) │     │  Product Service │     │  (asyncpg)   │
│  uvloop      │     │  Payment Service │     │  pool=20+10  │
└──────┬───────┘     │  Invoice Service │     └──────────────┘
       │             └────────┬─────────┘
       │                      │
       │              ┌───────▼────────┐
       │              │    Redis 7      │
       │              │  (product cache)│
       │              └───────┬────────┘
       │                      │
       │              ┌───────▼────────┐
       │              │   RabbitMQ     │
       │              │  (task queue)   │
       │              └───────┬────────┘
       │                      │
       │              ┌───────▼────────┐
       │              │  Worker (async)│
       │              │ invoice gen    │
       │              │ notifications  │
       │              └────────────────┘
```

### Entity-Relationship Diagram

```
customers ──1:N── orders ──1:N── order_line_items
                      │
                      ├──1:N── payments
                      │
                      └──1:N── invoices

products ──1:N── order_line_items
```

### Schema (PostgreSQL)

See `alembic/versions/001_initial_schema.py` for the full DDL.

Key design decisions:
- **Optimistic locking** via `version` column on `orders` — prevents lost updates during concurrent status transitions.
- **Enums** for status fields — enforced at DB level to prevent invalid states.
- **Decimal(12,2)** for monetary values — avoids floating-point rounding errors.
- **Timestamps with timezone** — all times stored in UTC.

---

## 4. Domain Model

### Order State Machine

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

- **CANCELLED** is a terminal state reachable from CREATED, ACCEPTED, INVOICED, or PAID.
- Transitions are enforced by `OrderStatus.allowed_transitions()` in the domain layer.
- Illegal transitions raise `InvalidOrderStateTransition`.

### Hot Paths vs Back-Office

| Step | Role | Path Type | Latency Budget |
|------|------|-----------|----------------|
| 1. Customer places order | Customer | **Hot** (checkout) | p95 ≤ 300 ms |
| 2. Order Staff reviews & accepts | Order Staff | Back-office | Relaxed |
| 3. Accountant creates invoice | Accountant | Back-office | Relaxed |
| 4. Customer pays invoice | Customer | **Hot** (checkout) | p95 ≤ 300 ms |
| 5. Accountant verifies payment | Accountant | Back-office | Relaxed |
| 6. Order Staff ships paid order | Order Staff | Back-office | Relaxed |
| 7. Order Staff closes completed order | Order Staff | Back-office | Relaxed |

---

## 5. API Reference

### Base URL: `http://localhost:8000/api/v1`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/customers` | Create customer | None |
| GET | `/customers/{id}` | Get customer | None |
| GET | `/customers` | List customers | None |
| POST | `/products` | Create product | None |
| GET | `/products/{id}` | Get product (cached) | None |
| GET | `/products` | Search products (cached) | None |
| PUT | `/products/{id}` | Update product | None |
| POST | `/orders` | Place order (rate-limited) | None |
| GET | `/orders/{id}` | Get order with line items | None |
| GET | `/orders` | List orders | None |
| PATCH | `/orders/{id}/status` | Update order status | None |
| POST | `/payments` | Process payment (rate-limited) | None |
| POST | `/payments/verify` | Verify payment | None |
| GET | `/payments/{id}` | Get payment | None |
| GET | `/payments/by-order/{order_id}` | List payments by order | None |
| POST | `/invoices` | Create invoice | None |
| GET | `/invoices/{id}` | Get invoice | None |
| GET | `/invoices/by-order/{order_id}` | List invoices by order | None |
| GET | `/health` | Health check | None |
| GET | `/metrics` | Performance metrics | None |
| GET | `/docs` | Swagger UI | None |
| GET | `/openapi.json` | OpenAPI spec | None |

### Error Responses

| Status | Meaning |
|--------|---------|
| 400 | Domain error (invalid transition, insufficient stock, etc.) |
| 404 | Entity not found |
| 409 | Optimistic lock conflict |
| 429 | Rate limited (Retry-After header included) |

---

## 6. Local Deployment Guide

### Prerequisites

- Docker & Docker Compose (for infrastructure)
- Python 3.12+ (for local development)
- `uv` package manager (recommended)

### Quick Start (Docker Compose)

```bash
# 1. Clone and enter the project
cd oms-backend

# 2. Start all services
docker compose up -d

# 3. Run database migrations
docker compose exec app alembic upgrade head

# 4. Verify health
curl http://localhost:8000/health
# → {"status":"ok","service":"oms"}

# 5. View Swagger docs
open http://localhost:8000/docs
```

### Local Development (without Docker)

```bash
# 1. Start infrastructure
docker compose up -d postgres redis rabbitmq

# 2. Create virtual environment
uv venv
source .venv/bin/activate

# 3. Install dependencies
uv sync

# 4. Run migrations
alembic upgrade head

# 5. Start the app
uvicorn app.main:app --reload --workers 4 --loop uvloop --http httptools

# 6. Start the background worker (in another terminal)
python -m app.worker
```

### Resource Limits

| Service | CPU Limit | Memory Limit | Justification |
|---------|-----------|--------------|---------------|
| app (FastAPI) | 4 cores | 4 GB | Matches target hardware (4 cores, 98 GB RAM). 4 workers × 1 GB each. |
| worker | 2 cores | 2 GB | Background tasks need less CPU. |
| postgres | 2 cores | 2 GB | Shared_buffers = 25% of RAM = 512 MB. |
| redis | 1 core | 1 GB | In-memory dataset < 500 MB. |
| rabbitmq | 1 core | 1 GB | Message persistence to disk. |

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

# Place an order
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":1,"line_items":[{"product_id":1,"quantity":2}]}'
```

---

## 7. Load-Test Plan

See [load_test/plan.md](load_test/plan.md) for the complete plan.

### Quick Run

```bash
# Baseline (200 users)
locust -f load_test/locustfile.py --scenario baseline --host http://localhost:8000 --headless --csv=results/baseline

# Sustained (2 000 users)
locust -f load_test/locustfile.py --scenario sustained --host http://localhost:8000 --headless --csv=results/sustained

# Spike (6 000 users in 60 s)
locust -f load_test/locustfile.py --scenario spike --host http://localhost:8000 --headless --csv=results/spike
```

### Pass/Fail Criteria

| Metric | Threshold |
|--------|-----------|
| Checkout p95 latency | ≤ 300 ms |
| Search p95 latency | ≤ 150 ms |
| Error rate (non-429) | < 1% |
| CPU usage | < 80% |
| Memory usage | < 4 GB |
| Request queueing p95 | < 50 ms |

---

## 8. Instrumentation

### Metrics Endpoint

`GET /metrics` returns:

```json
{
  "request_count": {"/api/v1/orders": 1500, "/api/v1/products": 4500},
  "status_count": {"200": 5800, "201": 200, "429": 50},
  "latency": {
    "/api/v1/orders": {"p50_ms": 45, "p95_ms": 210, "p99_ms": 380, "count": 1500},
    "/api/v1/products": {"p50_ms": 12, "p95_ms": 85, "p99_ms": 160, "count": 4500}
  },
  "rate_limiter": {"available_tokens": 150, "max_tokens": 200}
}
```

### Structured Logging

All logs are JSON-formatted with correlation IDs:

```json
{"asctime": "2025-01-01T12:00:00+0000", "name": "app.services.order_service", "levelname": "INFO", "message": "Order created", "correlation_id": "abc-123-def"}
```

### Health Check

`GET /health` returns `{"status": "ok", "service": "oms"}` for load balancer probing.

---

## Project Structure

```
oms-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration (env-based)
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── enums.py         # Status enums with state machine
│   │   └── exceptions.py    # Domain exceptions
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database.py      # Async DB engine + session factory
│   │   ├── cache.py         # Redis cache helpers
│   │   ├── queue.py         # RabbitMQ publisher
│   │   ├── rate_limiter.py  # Token-bucket rate limiter
│   │   └── logging.py       # Structured JSON logging
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py          # Generic CRUD repository
│   │   ├── customer.py
│   │   ├── product.py       # With search support
│   │   ├── order.py         # With line-item eager loading
│   │   ├── payment.py
│   │   └── invoice.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── order_service.py     # Order lifecycle + state machine
│   │   ├── product_service.py  # Cached search/browse
│   │   ├── payment_service.py  # Payment processing
│   │   ├── invoice_service.py  # Invoice creation
│   │   └── customer_service.py # Customer CRUD
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── customer_controller.py
│   │   ├── product_controller.py
│   │   ├── order_controller.py
│   │   ├── payment_controller.py
│   │   └── invoice_controller.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── correlation_id.py
│   │   ├── rate_limiter_middleware.py
│   │   └── metrics.py
│   └── worker.py            # Background task consumer
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
├── alembic.ini
├── load_test/
│   ├── locustfile.py
│   └── plan.md
├── tests/
├── Dockerfile
├── docker-compose.yml
├── .env
├── pyproject.toml
└── README.md
```
