# Order Management System (OMS) — Backend

Production-grade e-commerce Order Management System backend serving three roles:
**Customer**, **Order Staff**, and **Accountant**.

---

## Table of Contents

1. [NFR Traceability Matrix](#1-nfr-traceability-matrix)
2. [Architectural Decision Records](#2-architectural-decision-records)
3. [Data Architecture & Schema](#3-data-architecture--schema)
4. [Domain Model & State Machine](#4-domain-model--state-machine)
5. [API Reference](#5-api-reference)
6. [Infrastructure & Deployment](#6-infrastructure--deployment)
7. [Load Test Plan](#7-load-test-plan)
8. [Local Deployment Guide](#8-local-deployment-guide)

---

## 1. NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Quantitative Verification |
|-----|------------------------|------------------|--------------------------|
| **NFR 1.1** Response Time (checkout p95 ≤ 300ms, p99 ≤ 600ms; browse p95 ≤ 150ms) | Async I/O (FastAPI + asyncpg + aioredis + aio-pika); cache-aside (Redis) for product browse; sized connection pools | `app/main.py` (uvicorn async workers), `app/infrastructure/cache.py`, `app/infrastructure/database.py` | **Tool:** Locust with 2,000 concurrent VUs, 1-5s think time, 10-min steady state. **Threshold:** p95 checkout < 300ms, p99 checkout < 600ms, p95 browse < 150ms. **Artifact:** Locust HTML report + Prometheus `http_request_duration_seconds` histogram. |
| **NFR 1.2** Concurrency & Resource Utilization (5,000 concurrent sessions, queueing < 50ms, CPU 60-85%) | Worker pool sized via `workers = cores × (1 + wait_time/compute_time)` = 8 × (1 + 20) = 168 → 8 workers × 4096 concurrency; DB pool sized via Little's Law: `pool = λ × W` = 2000 × 0.02 = 40 connections; Redis LRU eviction | `app/config.py` (pool sizes), `app/infrastructure/database.py` (asyncpg pool), `app/infrastructure/cache.py` (Redis allkeys-lru) | **Tool:** Locust sustained 5,000 sessions ≥10 min + Prometheus. **Threshold:** CPU 60-85%, queueing < 50ms, error rate < 1%. **Artifact:** `GET /metrics` → `rate_limiter_tokens_available`, `db_connection_pool_size`. |
| **NFR 1.3** Queue Management (3x spike, no crashes, no OOM, no silent loss) | Token bucket rate limiter (capacity=2000, refill=500/s); bounded RabbitMQ queue (max 10,000, reject-publish); circuit breaker (50% failure rate, 30s open, 3 half-open trials); idempotency (Redis TTL 24h) | `app/infrastructure/rate_limiter.py`, `app/infrastructure/messaging.py`, `app/infrastructure/circuit_breaker.py`, `app/infrastructure/idempotency.py` | **Tool:** Locust spike scenario (3x ramp over 60s, held 5 min). **Threshold:** No crashes, no OOM, error rate < 5% during spike (rate-limited 429s are acceptable), circuit breaker transitions logged. **Artifact:** `GET /metrics` → `circuit_breaker_state`, `queue_depth`. |

### Sizing Formulas & Derivation

**Worker Pool (NFR 1.2):**
```
workers = cores × (1 + wait_time / compute_time)
cores = 16 (assumed)
wait_time = 40ms (avg DB query + cache + messaging I/O)
compute_time = 2ms (avg CPU-bound processing per request)
ratio = 40 / 2 = 20
workers = 16 × (1 + 20) = 336 theoretical async connections per process
```
We run 8 uvicorn workers, each with `--limit-concurrency 4096`:
- Total theoretical capacity: 8 × 4096 = 32,768 concurrent connections
- Actual sustained: 5,000 concurrent sessions (well within capacity)

**DB Connection Pool (NFR 1.2):**
```
Using Little's Law: L = λ × W
λ = 2,000 req/s (target throughput)
W = 20ms (avg DB query time)
L = 2,000 × 0.02 = 40 connections
```
- `pool_size = 40` (matches Little's Law)
- `max_overflow = 10` (burst capacity for spikes)
- Max total: 50 connections

**Rate Limiter (NFR 1.3):**
```
Capacity = 2,000 tokens (burst = 2,000 concurrent checkout requests)
Refill rate = 500 tokens/s (sustained = 500 checkout ops/s)
```
At 3x baseline spike (6,000 req/s), the limiter allows 500/s sustained,
rejecting excess with HTTP 429 + Retry-After header.

**Memory Ceiling (NFR 1.3):**
- App: 32 GB (8 workers × 4 GB)
- RabbitMQ queue: max 10,000 messages × ~400 KB = 4 GB
- Redis: 2 GB (allkeys-lru eviction)
- Total: 38 GB (within 98 GB target, leaving 60 GB headroom)

---

## 2. Architectural Decision Records

### ADR-001: Language & Framework

| Field | Value |
|-------|-------|
| **Decision** | Python with FastAPI |
| **Context** | NFR 1.1 (response time), NFR 1.2 (concurrency) |
| **Alternatives** | **Go (Gin):** ~2x raw throughput but slower development velocity, smaller ecosystem for async patterns. **Node.js (Express):** Good async I/O but single-threaded limits CPU-bound work; callback-heavy patterns. **Java (Spring WebFlux):** Excellent throughput but heavy JVM overhead (2-4 GB base), slower startup, more boilerplate. |
| **Consequences** | Python adds ~5-10ms overhead vs Go/Java for CPU-bound work, but async I/O (FastAPI + asyncpg) keeps total checkout latency under 300ms. Development speed is ~3x faster. Memory per worker: ~500 MB vs ~2 GB for Java. |

### ADR-002: Database

| Field | Value |
|-------|-------|
| **Decision** | PostgreSQL with asyncpg driver |
| **Context** | NFR 1.1 (response time), NFR 1.2 (concurrency) |
| **Alternatives** | **MySQL:** Similar performance but weaker JSON support, no native UUID type. **MongoDB:** Better write throughput but lacks ACID transactions needed for order lifecycle; eventual consistency risks for payment flow. |
| **Consequences** | PostgreSQL adds ~2ms latency vs in-memory stores but provides strong consistency guarantees essential for financial transactions. asyncpg is the fastest PostgreSQL driver for Python (~2x faster than psycopg2 async). |

### ADR-003: Cache

| Field | Value |
|-------|-------|
| **Decision** | Redis with allkeys-lru eviction |
| **Context** | NFR 1.1 (browse p95 ≤ 150ms), NFR 1.2 (hot read path) |
| **Alternatives** | **Memcached:** Simpler, lower memory overhead but no data structures, no TTL-based eviction control. **Local LRU cache (cachetools):** Zero network latency but no cross-worker sharing; each worker would have a separate cache, reducing hit rate. |
| **Consequences** | Redis adds ~1ms network latency per cache operation but enables shared cache across all 8 workers. allkeys-lru eviction ensures hot products stay cached under memory pressure. Max staleness: TTL (60s) + clock skew (~2s) = ~62s. |

### ADR-004: Message Queue

| Field | Value |
|-------|-------|
| **Decision** | RabbitMQ with bounded queue (max 10,000) |
| **Context** | NFR 1.3 (spike absorption, no OOM) |
| **Alternatives** | **Kafka:** Higher throughput (millions msg/s) but heavier operational overhead (ZooKeeper/KRaft), higher latency (~10ms vs ~1ms). Overkill for OMS scale. **Redis Streams:** Simpler deployment but no native dead-lettering, no delivery guarantees matching RabbitMQ. |
| **Consequences** | RabbitMQ adds ~2ms per publish but provides reliable delivery, dead-letter queues, and consumer acknowledgments. Max 10,000 messages × 400 KB = 4 GB memory bound. |

### ADR-005: Rate Limiter

| Field | Value |
|-------|-------|
| **Decision** | In-process token bucket |
| **Context** | NFR 1.3 (admission control) |
| **Alternatives** | **Redis-backed token bucket:** Shared state across workers but adds ~1ms latency per check and Redis load. **Nginx rate limiting:** Offloads to reverse proxy but less flexible (no application-level awareness). |
| **Consequences** | In-process limiter has zero network overhead but is per-worker. With 8 workers, effective capacity = 8 × 2000 = 16,000 tokens burst. This is acceptable since we target 5,000 concurrent sessions. |

### ADR-006: Circuit Breaker

| Field | Value |
|-------|-------|
| **Decision** | In-process sliding-window circuit breaker (Resilience4j-style) |
| **Context** | NFR 1.3 (downstream dependency resilience) |
| **Alternatives** | **Hystrix (Netflix):** Java-only. **Polly (.NET):** C#-only. **pybreaker:** Python library but no async support. |
| **Consequences** | Custom implementation adds ~100 lines of code but gives full control over failure rate calculation (sliding window of last 100 calls). Open duration: 30s. Half-open trials: 3. |

---

## 3. Data Architecture & Schema

### Entity-Relationship Diagram (Text)

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│ Customer │1───many│  Order   │1───many│ Payment  │
└──────────┘       └──────────┘       └──────────┘
                        │
                        │1
                        │
                   ┌────┴──────┐
                   │  Invoice  │
                   └───────────┘
```

### Database Schema (PostgreSQL)

See `app/repositories/orm_models.py` for complete SQLAlchemy definitions.

**Tables:**
- `customers` — id (UUID PK), name, address, phone, banking_details, order_history (JSON), role (enum), created_at, updated_at
- `products` — id (UUID PK), name, description, base_price (DECIMAL 12,2), currency (enum), stock_available (INT), last_modified, created_at
- `orders` — id (UUID PK), customer_id (FK), line_items (JSON), subtotal, tax_amount, total_amount, status (enum), invoice_ref (UUID nullable), version (INT, optimistic lock), timestamps for each transition
- `payments` — id (UUID PK), order_id (FK), amount, currency, status (enum), method (enum), idempotency_key (UNIQUE), timestamp
- `invoices` — id (UUID PK), order_id (FK), customer_name, customer_address, billing_info, subtotal, tax_amount, total_amount, status (enum), issue_date, due_date

### Order State-Transition Table

| From State | Event | To State | Guard Condition |
|------------|-------|----------|-----------------|
| CREATED | accept | ACCEPTED | None |
| ACCEPTED | invoice | INVOICED | None |
| INVOICED | pay | PAID | None |
| PAID | ship | SHIPPED | None |
| SHIPPED | close | CLOSED | None |
| CREATED | cancel | CANCELLED | None |
| ACCEPTED | cancel | CANCELLED | None |
| INVOICED | cancel | CANCELLED | None |
| PAID | cancel | CANCELLED | None |

Enforced in `app/domain/state_machine.py` — illegal transitions raise `IllegalTransitionError` before any persistence write.

---

## 4. Domain Model & State Machine

### Domain Models

See `app/domain/models.py` for complete Pydantic definitions:
- `Customer`, `Product`, `LineItem`, `Order`, `Payment`, `Invoice`

### State Machine

See `app/domain/state_machine.py`:
- `ORDER_TRANSITIONS` — list of all valid transitions
- `validate_transition(current, event)` — validates and returns target state
- `IllegalTransitionError` — raised for invalid transitions

---

## 5. API Reference

### Versioned Endpoints (v1)

| Method | Path | Description | Latency Budget | Auth |
|--------|------|-------------|----------------|------|
| POST | `/api/v1/orders/place` | Place order (checkout) | p95 ≤ 300ms | None |
| POST | `/api/v1/orders/accept` | Accept order (staff) | p95 ≤ 1s | None |
| POST | `/api/v1/orders/invoice` | Create invoice (accountant) | p95 ≤ 1s | None |
| POST | `/api/v1/orders/pay` | Submit payment (customer) | p95 ≤ 300ms | None |
| POST | `/api/v1/orders/verify` | Verify payment (accountant) | p95 ≤ 1s | None |
| POST | `/api/v1/orders/ship` | Ship order (staff) | p95 ≤ 1s | None |
| POST | `/api/v1/orders/close` | Close order (staff) | p95 ≤ 1s | None |
| POST | `/api/v1/orders/cancel` | Cancel order | p95 ≤ 1s | None |
| GET | `/api/v1/orders/{id}` | Get order | p95 ≤ 150ms | None |
| GET | `/api/v1/orders/` | List orders | p95 ≤ 150ms | None |
| GET | `/api/v1/products/search` | Search products (cached) | p95 ≤ 150ms | None |
| GET | `/api/v1/products/{id}` | Get product (cached) | p95 ≤ 150ms | None |
| GET | `/api/v1/products/` | List products | p95 ≤ 150ms | None |
| PATCH | `/api/v1/products/{id}` | Update product (invalidates cache) | p95 ≤ 1s | None |
| GET | `/metrics` | Prometheus metrics | N/A | None |
| GET | `/health` | Health check | N/A | None |
| GET | `/docs` | OpenAPI Swagger UI | N/A | None |
| GET | `/redoc` | OpenAPI ReDoc | N/A | None |

### Rate Limiting

Checkout endpoints (`/orders/place`, `/orders/pay`) are rate-limited:
- **429 Too Many Requests** with `Retry-After` header when limit exceeded
- Token bucket: capacity 2,000, refill 500/s

### Idempotency

Payment submission (`/orders/pay`) requires `idempotency_key` in the request body.
Duplicate keys return the original response without reprocessing (24h TTL).

---

## 6. Infrastructure & Deployment

### Resource Limits (Docker Compose)

| Service | CPU Cores | Memory | Derivation |
|---------|-----------|--------|------------|
| App (8 workers) | 16 | 32 GB | 8 workers × 4 GB/worker |
| PostgreSQL | 4 | 8 GB | 40 connections × 200 MB |
| Redis | 2 | 2 GB | 500k entries × 4 KB |
| RabbitMQ | 2 | 4 GB | 10k messages × 400 KB |
| **Total** | **24** | **46 GB** | Leaves 52 GB for OS + headroom |

### Pool Sizing (from config.py)

```python
# DB pool: Little's Law L = λ × W = 2000 × 0.02 = 40
db_pool_size = 40
db_max_overflow = 10  # burst

# Redis pool
redis_pool_size = 20

# RabbitMQ channel pool
rabbitmq_channel_pool_size = 10

# Rate limiter
rate_limit_capacity = 2000    # burst
rate_limit_refill_per_second = 500.0  # sustained
```

---

## 7. Load Test Plan

### Tool: Locust

### Scenario 1: Baseline Steady Load
- **Users:** 2,000 concurrent
- **Think time:** 1-5s (uniform distribution)
- **Duration:** 10 minutes steady state
- **User mix:** 70% CheckoutUser, 30% BackOfficeUser
- **Pass criteria:**
  - Checkout p95 < 300ms, p99 < 600ms
  - Browse p95 < 150ms
  - Error rate < 1%
  - CPU 60-85%

### Scenario 2: Sustained Load
- **Users:** 5,000 concurrent sessions
- **Think time:** 1-5s
- **Duration:** ≥10 minutes
- **Pass criteria:**
  - Average request queueing time < 50ms
  - CPU 60-85%
  - Error rate < 1%
  - No connection pool exhaustion

### Scenario 3: Spike (3x Baseline)
- **Ramp:** 0 → 6,000 users over 60 seconds (linear)
- **Hold:** 5 minutes at peak
- **Pass criteria:**
  - No process crashes
  - No unbounded memory growth (monitor via `docker stats`)
  - No silent request loss (429s are acceptable, logged)
  - Circuit breaker transitions logged (if any)
  - Error rate (excluding 429) < 1%

### Running Load Tests

```bash
# Start Locust web UI
cd load_tests
locust -f locustfile.py --host=http://localhost:8000 --web-host=0.0.0.0 --web-port=8089

# Headless mode (Scenario 1)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 2000 --spawn-rate 100 --run-time 10m \
  --headless --html report_baseline.html --csv baseline

# Headless mode (Scenario 2)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 5000 --spawn-rate 100 --run-time 10m \
  --headless --html report_sustained.html --csv sustained

# Headless mode (Scenario 3 - spike)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 6000 --spawn-rate 100 --run-time 6m \
  --headless --html report_spike.html --csv spike
```

### Metrics Dashboard (Prometheus Query Examples)

```promql
# p95 latency for checkout (last 5 minutes)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{endpoint=~"/api/v1/orders/(place|pay)"}[5m])) by (le))

# p99 latency for checkout
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{endpoint=~"/api/v1/orders/(place|pay)"}[5m])) by (le))

# p95 latency for browse
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{endpoint=~"/api/v1/products"}[5m])) by (le))

# Throughput (req/s)
sum(rate(http_requests_total[1m]))

# Error rate (%)
sum(rate(http_errors_total[1m])) / sum(rate(http_requests_total[1m])) * 100

# Rate limiter tokens available
rate_limiter_tokens_available

# Circuit breaker state
circuit_breaker_state

# Queue depth
queue_depth
```

---

## 8. Local Deployment Guide

### Prerequisites

- Docker & Docker Compose (for containerized deployment)
- OR Python 3.12+ with uv (for local development)

### Option A: Docker Compose (Recommended)

```bash
# Clone and navigate
cd oms

# Start all services
docker compose up --build -d

# Check logs
docker compose logs -f app

# Access API
curl http://localhost:8000/health

# OpenAPI docs
open http://localhost:8000/docs

# Metrics
curl http://localhost:9090/metrics

# Stop
docker compose down
```

### Option B: Local Development

```bash
# Prerequisites: PostgreSQL, Redis, RabbitMQ running locally

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync

# Set environment variables (adjust for local services)
export OMS_DB_URL="postgresql+asyncpg://oms:oms@localhost:5432/oms"
export OMS_REDIS_URL="redis://localhost:6379/0"
export OMS_RABBITMQ_URL="amqp://guest:guest@localhost:5672/"

# Run database migrations (creates tables)
python -c "import asyncio; from app.infrastructure.database import init_db; asyncio.run(init_db())"

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 8 --limit-concurrency 4096
```

### Verification

```bash
# Health check
curl http://localhost:8000/health
# → {"status":"healthy","service":"oms-backend"}

# Place an order
curl -X POST http://localhost:8000/api/v1/orders/place \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"00000000-0000-0000-0000-000000000001","line_items":[{"product_id":"00000000-0000-0000-0000-000000000001","quantity":2}]}'

# Get metrics
curl http://localhost:8000/metrics
```

---

## File Structure

```
oms/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings with pool-sizing formulas
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── enums.py               # Status enums
│   │   ├── models.py              # Pydantic domain models
│   │   └── state_machine.py       # Order state machine
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database.py            # Asyncpg connection pool
│   │   ├── cache.py               # Redis cache-aside layer
│   │   ├── messaging.py           # RabbitMQ producer/consumer
│   │   ├── rate_limiter.py        # Token bucket rate limiter
│   │   ├── circuit_breaker.py     # Sliding-window circuit breaker
│   │   └── idempotency.py         # Idempotency key store
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                # Generic CRUD repository
│   │   ├── orm_models.py          # SQLAlchemy ORM models
│   │   ├── customer_repo.py
│   │   ├── order_repo.py          # With optimistic-lock update
│   │   ├── product_repo.py        # With cache-aside methods
│   │   ├── payment_repo.py        # With idempotency key lookup
│   │   └── invoice_repo.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── order_service.py       # Order lifecycle orchestration
│   │   └── product_service.py     # Product browse/search
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py        # FastAPI DI
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── order_controller.py    # Order REST endpoints
│   │       ├── product_controller.py  # Product REST endpoints
│   │       └── metrics_controller.py  # Prometheus metrics
│   └── middleware/
│       ├── __init__.py
│       ├── correlation_id.py      # Correlation ID middleware
│       └── logging_middleware.py  # Structured logging setup
├── load_tests/
│   └── locustfile.py              # Locust load test scenarios
├── tests/
│   └── __init__.py
├── docker-compose.yml             # Multi-service deployment
├── Dockerfile                      # App container image
├── pyproject.toml
└── README.md
```
