# Order Management System (OMS)

Production-grade, backend-only e-commerce Order Management System.

## Architecture Overview

### Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Language** | Python 3.12 | Async-native, excellent ecosystem, rapid development |
| **Framework** | FastAPI | Async-first, automatic OpenAPI, built-in validation via Pydantic, high throughput |
| **Database** | PostgreSQL 16 | ACID compliance, row-level locking, JSON support, mature async driver (asyncpg) |
| **Cache** | Redis 7 | In-memory key-value store, sub-millisecond reads, TTL support, also used for rate limiting and task queue |
| **Task Queue** | RQ (Redis Queue) | Lightweight, Redis-backed, no external broker dependency, good for single-node deployment |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, well-tested, async support, connection pooling, migration support via Alembic |
| **Async I/O** | uvloop + httptools | High-performance event loop and HTTP parser for Python asyncio |

### Why Python + FastAPI?

- **Async-native**: FastAPI is built on Starlette/asyncio, providing non-blocking I/O for the checkout path (NFR 1.1, 1.2).
- **Automatic OpenAPI**: Built-in OpenAPI spec generation satisfies the "OpenAPI-friendly, versioned paths" requirement.
- **Pydantic validation**: Request/response validation with zero boilerplate.
- **Connection pooling**: SQLAlchemy's async engine provides bounded, sized connection pools (HikariCP-style).
- **Performance**: With uvloop and httptools, FastAPI achieves throughput comparable to Go/Node.js for I/O-bound workloads.

---

## NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Quantitative Verification Method |
|-----|----------------------|------------------|--------------------------------|
| **NFR 1.1** Response Time (checkout p95 ≤ 300ms, search p95 ≤ 150ms) | Async I/O (uvloop), Redis cache for product search, bounded DB connection pool, rate limiting to prevent overload | `oms/main.py` (uvloop config), `oms/infrastructure/cache.py`, `oms/infrastructure/database.py` (pool_size=20), `oms/api/routes.py` (check_rate_limit) | **Tool:** Locust with 2000 concurrent users. **Metric:** p95 latency for `/api/v1/orders` POST (checkout) and `/api/v1/products` GET (search). **Pass:** checkout p95 < 300ms, search p95 < 150ms |
| **NFR 1.2** Concurrency & Resource Utilization (5000 concurrent sessions, avg queueing < 50ms) | Bounded DB connection pool (20 + 10 overflow), async event loop, Redis cache for hot reads, 4 worker processes | `oms/config.py` (pool_size=20, max_overflow=10, workers=4), `oms/infrastructure/database.py` (QueuePool), `oms/infrastructure/cache.py` | **Tool:** Locust with 5000 concurrent users. **Metric:** Average request queueing time, CPU/memory utilization. **Pass:** avg queueing < 50ms, CPU < 80%, memory < 32GB |
| **NFR 1.3** Queue Management (3x spike absorption) | Token-bucket rate limiter at admission layer, RQ task queue for deferrable work (invoice generation, notifications), HTTP 429 with Retry-After | `oms/infrastructure/rate_limiter.py` (capacity=100, refill=20/s), `oms/infrastructure/task_queue.py`, `oms/api/routes.py` (429 response) | **Tool:** Locust spike test (ramp 500→6000 users in 60s). **Metric:** Error rate, memory growth, queue depth. **Pass:** No crashes, no unbounded memory, error rate < 1% (excluding 429), no silent request loss |
- **4 worker processes** (uvicorn workers): Matches a typical 4-core CPU. Each worker runs an async event loop, handling many concurrent connections via asyncio.
- **Database connection pool: 20 + 10 overflow**: With 4 workers, each worker gets ~5-8 connections. PostgreSQL handles 20-30 concurrent connections efficiently. The overflow of 10 handles traffic spikes.
- **Redis connection pool: 10**: Redis is single-threaded; 10 connections are sufficient for cache reads, rate limiting, and task queue operations.
- **Rate limiter: 100 tokens, refill 20/sec**: Allows 20 requests/second sustained, with burst capacity of 100. This prevents the database from being overwhelmed during spikes.

## Architectural Decision Records (ADRs)

### ADR-001: Use FastAPI (Python) as the Web Framework

- **Decision**: FastAPI with Python 3.12
- **Context**: NFR 1.1 (response time), NFR 1.2 (concurrency)
- **Alternatives considered**:
  - *Go with Gin*: Higher raw throughput, but longer development time, less ecosystem for async ORM
  - *Node.js with Express*: Good async I/O, but callback complexity, weaker type safety
  - *Java with Spring Boot*: Excellent for enterprise, but heavy JVM overhead, slower startup, more boilerplate
- **Consequences**: Slightly lower raw throughput than Go, but significantly faster development, excellent async support, and automatic OpenAPI generation

### ADR-002: Use PostgreSQL with SQLAlchemy Async

- **Alternatives considered**:
  - *MongoDB*: No native transactions across collections, weaker consistency guarantees
  - *SQLite*: No concurrent write support, unsuitable for production
- **Consequences**: Requires running PostgreSQL, but provides strong consistency, row-level locking, and optimistic locking support

### ADR-003: Use Redis for Cache, Rate Limiting, and Task Queue

- **Decision**: Single Redis instance for cache + rate limiter + task queue
- **Context**: NFR 1.1 (cache for product search), NFR 1.3 (rate limiting, task queue)
- **Rate limiter: 500 tokens, refill 200/sec**: Allows 200 requests/second sustained, with burst capacity of 500. This prevents the database from being overwhelmed during spikes.
  - *Memcached*: Cache only, no rate limiting or queue support
  - *RabbitMQ*: Better message broker, but adds operational complexity for single-node deployment
  - *In-memory cache*: No shared state across workers, cache invalidation complexity
- **Consequences**: Single point of failure for cache, but acceptable for single-node deployment. Redis persistence ensures data safety.

### ADR-004: Token-Bucket Rate Limiter at Admission Layer

- **Decision**: In-process token-bucket rate limiter (asyncio-based)
- **Context**: NFR 1.3 (spike absorption, backpressure)
- **Alternatives considered**:
  - *Redis-based rate limiter*: Shared across instances, but adds network latency
  - *Fixed-window counter*: Simpler but allows burst traffic at window boundaries
  - *Leaky bucket*: More complex, harder to tune
- **Consequences**: In-process limiter is faster but not shared across workers. Each worker has its own bucket, so total capacity scales with workers.

### ADR-005: RQ for Deferrable Work

- **Decision**: RQ (Redis Queue) for async task processing
- **Context**: NFR 1.3 (decouple spike-prone work from request threads)
- **Alternatives considered**:
  - *Celery*: More features, but heavier, requires separate broker (RabbitMQ/Redis)
  - *Kafka*: Overkill for single-node deployment, high operational complexity
  - *ThreadPoolExecutor*: No persistence, tasks lost on crash
- **Consequences**: RQ is simple and Redis-backed. Tasks are persisted in Redis. Worker processes can be scaled independently.

---

## Data Architecture

### Entity-Relationship Diagram (Textual)

```
Customer 1───* Order 1───* OrderLineItem
                 1
                 │
                 ├─── 0..1 Payment
                 │
                 └─── 0..1 Invoice
```

### Schema

See `oms/infrastructure/orm_models.py` for the complete SQLAlchemy ORM schema.

Key design decisions:
- **Optimistic locking**: `Order.version` field incremented on each update. Concurrent modifications are detected and rejected with `409 Conflict`.
- **State machine**: `OrderStatus` enum with explicit transition matrix enforced at the domain layer (not just controller).
- **Soft deletes**: Not implemented; orders reach terminal states (CLOSED, CANCELLED) and remain in the database.
- **Indexes**: Product description has a B-tree index for ILIKE searches.

---

## API Endpoints

All endpoints are versioned under `/api/v1/`.

### Customer Endpoints
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers` - List customers
- `GET /api/v1/customers/{id}` - Get customer

### Product Endpoints (Cached)
- `POST /api/v1/products` - Create product
- `GET /api/v1/products?q=&limit=&offset=` - Search products (cached, latency-sensitive)
- `GET /api/v1/products/{id}` - Get product (cached)

### Order Endpoints
- `POST /api/v1/orders` - Place order (rate-limited, checkout path)
- `GET /api/v1/orders` - List orders
- `GET /api/v1/orders/{id}` - Get order
- `GET /api/v1/customers/{id}/orders` - List customer orders
- `POST /api/v1/orders/{id}/transition` - Transition order status

### Workflow Endpoints
- `POST /api/v1/orders/{id}/accept` - Accept order (Staff)
- `POST /api/v1/orders/{id}/invoice` - Create invoice (Accountant)
- `POST /api/v1/orders/{id}/pay` - Pay invoice (Customer, rate-limited)
- `POST /api/v1/orders/{id}/verify-payment` - Verify payment (Accountant)
- `POST /api/v1/orders/{id}/ship` - Ship order (Staff)
- `POST /api/v1/orders/{id}/close` - Close order (Staff)
- `POST /api/v1/orders/{id}/cancel` - Cancel order

### Monitoring
- `GET /api/v1/health` - Health check
- `GET /api/v1/metrics` - Runtime metrics

### OpenAPI Spec
Available at `/docs` (Swagger UI) or `/api/v1/openapi.json`.

---

## Local Deployment Guide

### Prerequisites
- Docker and Docker Compose (recommended)
- OR Python 3.12+, PostgreSQL 16+, Redis 7+

### Option 1: Docker Compose (Recommended)

```bash
# Clone and start all services
docker-compose up --build

# The API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Option 2: Manual Setup

```bash
# 1. Start PostgreSQL and Redis
# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg redis rq pydantic pydantic-settings python-json-logger httptools

# 4. Set environment variables
export DATABASE_URL="postgresql+asyncpg://oms:oms@localhost:5432/oms"
export REDIS_URL="redis://localhost:6379/0"

# 5. Run the API
python -m uvicorn oms.main:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop --http httptools

# 6. Run the RQ worker (in a separate terminal)
rq worker --url redis://localhost:6379/0 oms_tasks
```

### Resource Limits (Docker Compose)

| Service | CPU Limit | Memory Limit | Justification |
|---------|-----------|-------------|---------------|
| API | 4 cores | 4GB | Handles 5000 concurrent sessions with async I/O |
| PostgreSQL | 2 cores | 4GB | Connection pool of 20-30 connections |
| Redis | 1 core | 1GB | Cache + rate limiter + task queue |
| Worker | 2 cores | 2GB | Processes deferrable tasks |

Total: ~9 CPU cores, ~11GB RAM (well within the 98GB target).

---

## Load Test Plan

### Tool: Locust

### Test Scenarios

#### 1. Baseline Load
- **Users**: 500 concurrent
- **Spawn rate**: 10 users/second
- **Duration**: 5 minutes
- **Expected**: All NFRs met comfortably

#### 2. Sustained Load (Target Concurrency)
- **Users**: 2000 concurrent (NFR 1.1 target)
- **Spawn rate**: 20 users/second
- **Duration**: 10 minutes
- **Expected**: Checkout p95 < 300ms, search p95 < 150ms

#### 3. Spike Scenario (3x Baseline)
- **Users**: Ramp from 500 to 6000 in 60 seconds
- **Spawn rate**: ~92 users/second
- **Duration**: 2 minutes sustained at peak
- **Expected**: No crashes, no unbounded memory, 429 responses for excess traffic

### Metrics to Capture

| Metric | Tool | Pass/Fail Threshold |
|--------|------|---------------------|
| p50 latency | Locust stats | < 100ms (checkout), < 50ms (search) |
| p95 latency | Locust stats | < 300ms (checkout), < 150ms (search) |
| p99 latency | Locust stats | < 500ms (checkout), < 300ms (search) |
| Throughput (RPS) | Locust stats | > 500 RPS sustained |
| Error rate | Locust stats | < 1% (excluding 429) |
| CPU utilization | `docker stats` / `top` | < 80% |
| Memory utilization | `docker stats` / `free` | < 32GB |
| Queue depth | Redis `LLEN oms_tasks` | < 1000 at steady state |

### Running Load Tests

```bash
# Start Locust web interface
locust -f oms/load_test/locustfile.py --host=http://localhost:8000

# Headless mode (sustained load test)
locust -f oms/load_test/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 2000 \
  --spawn-rate 20 \
  --run-time 10m \
  --csv=results/sustained

# Headless mode (spike test)
locust -f oms/load_test/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 6000 \
  --spawn-rate 100 \
  --run-time 3m \
  --csv=results/spike
```

### Instrumentation

The system exposes:
- **`/api/v1/metrics`**: Rate limiter state (available tokens, capacity)
- **`/api/v1/health`**: Service health
- **Structured JSON logs**: All requests logged with correlation IDs, timing, and status codes
- **Locust integration**: Custom event hooks capture p50/p95/p99, throughput, error rate

---

## Cache Invalidation Policy

| Cache Key Pattern | TTL | Invalidation Trigger |
|------------------|-----|---------------------|
| `product:{id}` | 60 seconds | Product update/delete |
| `product_search:{query}:{limit}:{offset}` | 60 seconds | Any product mutation (broad invalidation via `delete_pattern("product_search:*")`) |

### Why TTL-based invalidation?
- Simple, no need for complex cache coherence protocols
- 60-second TTL is acceptable for product catalog data
- On mutation, we proactively invalidate the specific product and all search caches
- Stale data is bounded to 60 seconds maximum

---

## Order State Machine

```
                    ┌─────────┐
                    │ CREATED │
                    └────┬────┘
                    ┌────┴────┐
                    │         │
               ┌────▼──┐  ┌──▼───────┐
               │ACCEPTED│  │CANCELLED │ (terminal)
               └────┬──┘  └──────────┘
                    │
               ┌────▼──┐
               │INVOICED│
               └────┬──┘
                    │
               ┌────▼──┐
               │  PAID │
               └────┬──┘
                    │
               ┌────▼───┐
               │ SHIPPED │
               └────┬───┘
                    │
               ┌────▼──┐
               │ CLOSED │ (terminal)
               └───────┘
```

Cancellation is allowed from CREATED, ACCEPTED, INVOICED, and PAID states.
Once SHIPPED or CLOSED, cancellation is not permitted.

---

## Project Structure

```
oms/
├── __init__.py
├── main.py                    # Application entry point
├── config.py                  # Configuration (pydantic-settings)
├── domain/
│   ├── __init__.py
│   ├── enums.py               # OrderStatus, PaymentStatus, etc.
│   ├── errors.py              # Domain errors
│   └── models.py              # Domain models (dataclasses)
├── infrastructure/
│   ├── __init__.py
│   ├── database.py            # Async SQLAlchemy engine + session
│   ├── cache.py               # Redis cache
│   ├── rate_limiter.py        # Token-bucket rate limiter
│   ├── task_queue.py          # RQ task queue
│   ├── logging.py             # Structured JSON logging
│   └── orm_models.py          # SQLAlchemy ORM models
├── application/
│   ├── __init__.py
│   ├── services.py            # Business logic services
│   ├── workflows.py           # Workflow orchestration
│   └── tasks.py               # Background tasks
├── adapters/
│   ├── __init__.py
│   └── repositories.py        # Data access repositories
├── api/
│   ├── __init__.py
│   ├── routes.py              # FastAPI route handlers
│   └── schemas.py             # Pydantic request/response schemas
├── tests/
│   ├── __init__.py
│   ├── test_domain.py         # Domain layer tests
│   └── test_services.py       # Service layer tests
└── load_test/
    └── locustfile.py          # Locust load test scenarios
```

---

## Deliverables Checklist

- [x] NFR Traceability Matrix with quantitative thresholds
- [x] ADRs for major decisions (5 ADRs)
- [x] Data architecture narrative + complete schema
- [x] Shared domain models (dataclasses + enums)
- [x] Complete backend code: entities, repositories, services, controllers, config, OpenAPI spec
- [x] IaC config (Dockerfile, docker-compose.yml) with resource limits
- [x] Local deployment guide
- [x] Load-test plan and instrumentation
