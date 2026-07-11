# Order Management System (OMS) — User Manual

**Version:** 1.0.0  
**Product Owner:** ChatDev — Chief Product Officer  
**Tech Stack:** Python 3.12 / FastAPI / PostgreSQL 16 / Redis 7 / RQ  

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Main Functions & Features](#2-main-functions--features)
3. [Architecture at a Glance](#3-architecture-at-a-glance)
4. [Installation & Environment Setup](#4-installation--environment-setup)
5. [Running the System](#5-running-the-system)
6. [API Reference](#6-api-reference)
7. [User Workflows](#7-user-workflows)
8. [Load Testing & Performance Verification](#8-load-testing--performance-verification)
9. [Monitoring & Observability](#9-monitoring--observability)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. System Overview

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that manages the complete order lifecycle:

1. **Customer** places an order
2. **Order Staff** reviews and accepts the order
3. **Accountant** creates an invoice for the accepted order
4. **Customer** pays the invoice
5. **Accountant** verifies the payment
6. **Order Staff** ships the paid order
7. **Order Staff** closes the completed order

The system is designed to handle **2,000 concurrent users** with **p95 latency ≤ 300ms** on the checkout path and **p95 latency ≤ 150ms** on product search, while absorbing **3x traffic spikes** without crashes or data loss.

### Three User Roles

| Role | Description | Key Actions |
|------|-------------|-------------|
| **Customer** | End-user who browses products and places orders | Browse products, place orders, pay invoices |
| **Order Staff** | Back-office operator managing order fulfillment | Accept orders, ship orders, close orders |
| **Accountant** | Back-office operator managing financials | Create invoices, verify payments |

---

## 2. Main Functions & Features

### 2.1 Product Catalog (Cached, Latency-Sensitive)
- Browse and search products by description
- Results are cached in Redis for sub-50ms reads
- Cache TTL: 60 seconds; invalidated on product mutations

### 2.2 Order Management
- Place orders with multiple line items
- Full state machine with enforced transitions (domain-layer validation)
- Optimistic locking via version field (prevents concurrent overwrites)
- Rate-limited checkout endpoints to prevent overload

### 2.3 Payment Processing
- Create payment records for orders
- Verify payments (Accountant action)
- Idempotent verification — re-verifying an already-completed payment is safe

### 2.4 Invoice Management
- Generate invoices for accepted orders
- Automatic 30-day due date
- Async notification task enqueued on invoice creation

### 2.5 Admission Control & Backpressure
- **Token-bucket rate limiter** on POST endpoints (checkout, payment)
- Capacity: 500 tokens burst, refill 200 tokens/second
- HTTP 429 + `Retry-After: 1` header when capacity exceeded

### 2.6 Deferrable Task Queue
- Invoice notifications are decoupled from request threads via RQ (Redis Queue)
- RQ worker runs in a separate container/process
- All synchronous RQ calls are offloaded to a thread pool to avoid blocking the async event loop

### 2.7 Observability
- Structured JSON logging with correlation IDs
- Health check endpoint (`/api/v1/health`)
- Metrics endpoint (`/api/v1/metrics`) exposing rate limiter state
- Automatic OpenAPI docs at `/docs`

---

## 3. Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     Client / Load Tester                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI (4 workers)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │ Worker 4 │     │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘     │
│        │              │              │              │         │
│  ┌─────┴──────────────┴──────────────┴──────────────┴─────┐  │
│  │              Token-Bucket Rate Limiter                   │  │
│  └──────────────────────────┬──────────────────────────────┘  │
└──────────────────────────────┼────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
│  PostgreSQL  │      │    Redis     │      │   RQ Worker(s)   │
│  (Pool: 20+10)│      │  (Cache +    │      │  (Deferrable     │
│              │      │   Rate Limiter│      │   Tasks)         │
│              │      │   + Queue)   │      │                  │
└──────────────┘      └──────────────┘      └──────────────────┘
```

### Technology Justification

| Component | Choice | Why |
|-----------|--------|-----|
| **Language** | Python 3.12 | Async-native, excellent ecosystem, rapid development |
| **Framework** | FastAPI | Async-first, automatic OpenAPI, Pydantic validation, high throughput |
| **Database** | PostgreSQL 16 | ACID compliance, row-level locking, optimistic locking support |
| **Cache** | Redis 7 | Sub-millisecond reads, TTL support, also used for rate limiting + task queue |
| **Task Queue** | RQ (Redis Queue) | Lightweight, Redis-backed, no external broker dependency |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, async support, connection pooling |
| **Async I/O** | uvloop + httptools | High-performance event loop and HTTP parser |

---

## 4. Installation & Environment Setup

### 4.1 Prerequisites

- **Docker** and **Docker Compose** (recommended)
- OR **Python 3.12+**, **PostgreSQL 16+**, **Redis 7+** (manual setup)

### 4.2 Quick Start with Docker Compose (Recommended)

```bash
# 1. Clone the repository
cd oms

# 2. Start all services
docker-compose up --build

# 3. Verify the system is running
curl http://localhost:8000/api/v1/health
# Expected: {"status":"healthy","service":"oms"}
```

### 4.3 Manual Setup (Without Docker)

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -e .

# 3. Start PostgreSQL and Redis (using your preferred method)
#    Ensure they are running on localhost:5432 and localhost:6379

# 4. Set environment variables
export DATABASE_URL="postgresql+asyncpg://oms:oms@localhost:5432/oms"
export REDIS_URL="redis://localhost:6379/0"
export LOG_LEVEL="INFO"

# 5. Run the API server
python -m uvicorn oms.main:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop --http httptools

# 6. In a separate terminal, start the RQ worker
rq worker --url redis://localhost:6379/0 oms_tasks
```

### 4.4 Resource Limits (Docker Compose)

| Service | CPU Limit | Memory Limit | Rationale |
|---------|-----------|-------------|-----------|
| **API** | 4 cores | 4 GB | Handles 5,000 concurrent sessions with async I/O |
| **PostgreSQL** | 2 cores | 4 GB | Connection pool of 20-30 connections |
| **Redis** | 1 core | 1 GB | Cache + rate limiter + task queue |
| **Worker** | 2 cores | 2 GB | Processes deferrable tasks |

**Total:** ~9 CPU cores, ~11 GB RAM (well within the 98 GB target hardware).

---

## 5. Running the System

### 5.1 Starting the System

```bash
# Docker Compose (all services)
docker-compose up -d

# Check logs
docker-compose logs -f api
```

### 5.2 Seeding Test Data

Before running load tests or exploring the API, seed the database with test data:

```bash
# Via API (after system is running)
curl -X POST http://localhost:8000/api/v1/seed

# Or via CLI
python -m oms.load_test.seed_data
```

This creates 1,000 customers and 100 products for testing.

### 5.3 Accessing the API

| Resource | URL |
|----------|-----|
| **API Base** | `http://localhost:8000/api/v1` |
| **Swagger UI** | `http://localhost:8000/docs` |
| **ReDoc** | `http://localhost:8000/redoc` |
| **OpenAPI JSON** | `http://localhost:8000/api/v1/openapi.json` |
| **Health Check** | `http://localhost:8000/api/v1/health` |
| **Metrics** | `http://localhost:8000/api/v1/metrics` |

### 5.4 Running Tests

```bash
# Run domain layer tests
pytest oms/tests/test_domain.py -v

# Run service layer tests
pytest oms/tests/test_services.py -v

# Run all tests
pytest oms/tests/ -v
```

---

## 6. API Reference

All endpoints are versioned under `/api/v1/`.

### 6.1 Customer Endpoints

#### `POST /api/v1/customers` — Create Customer
```json
// Request
{
  "name": "Alice Johnson",
  "address": "123 Main St, Springfield",
  "phone": "555-1234",
  "banking_details": "ACC-123456",
  "role": "CUSTOMER"
}

// Response (201 Created)
{
  "id": "a1b2c3d4-...",
  "name": "Alice Johnson",
  "address": "123 Main St, Springfield",
  "phone": "555-1234",
  "banking_details": "ACC-123456",
  "role": "CUSTOMER",
  "created_at": "2025-07-11T12:00:00Z",
  "updated_at": "2025-07-11T12:00:00Z"
}
```

#### `GET /api/v1/customers` — List Customers
#### `GET /api/v1/customers/{id}` — Get Customer by ID

### 6.2 Product Endpoints (Cached)

#### `POST /api/v1/products` — Create Product
```json
// Request
{
  "description": "Premium Widget",
  "base_price": 29.99,
  "currency": "USD",
  "stock_available": true
}
```

#### `GET /api/v1/products?q=widget&limit=20&offset=0` — Search Products
- **Cached** in Redis for 60 seconds
- **Latency-sensitive** (NFR 1.1 target: p95 ≤ 150ms)
- `q`: search query (ILIKE match on description)
- `limit`: max results (default 50)
- `offset`: pagination offset (default 0)

#### `GET /api/v1/products/{id}` — Get Product by ID (cached)

### 6.3 Order Endpoints

#### `POST /api/v1/orders` — Place Order (Rate-Limited)
- **Critical checkout path** (NFR 1.1 target: p95 ≤ 300ms)
- **Rate-limited** by token-bucket (500 burst, 200/s refill)
- Returns **429 Too Many Requests** with `Retry-After: 1` when overloaded

```json
// Request
{
  "customer_id": "a1b2c3d4-...",
  "line_items": [
    {
      "product_id": "p1-...",
      "product_description": "Premium Widget",
      "quantity": 2,
      "unit_price": 29.99,
      "currency": "USD"
    }
  ]
}

// Response (201 Created)
{
  "id": "o1-...",
  "customer_id": "a1b2c3d4-...",
  "line_items": [...],
  "status": "CREATED",
  "total_amount": 59.98,
  "currency": "USD",
  "invoice_ref": null,
  "version": 1,
  "created_at": "2025-07-11T12:00:00Z",
  "updated_at": "2025-07-11T12:00:00Z"
}
```

#### `GET /api/v1/orders` — List All Orders
#### `GET /api/v1/orders/{id}` — Get Order by ID
#### `GET /api/v1/customers/{id}/orders` — List Customer Orders

#### `POST /api/v1/orders/{id}/transition` — Generic Status Transition
```json
// Request
{
  "target_status": "ACCEPTED",
  "expected_version": 1
}
```

### 6.4 Workflow Endpoints

| Step | Endpoint | Role | Description |
|------|----------|------|-------------|
| 2 | `POST /orders/{id}/accept` | Staff | Accept order (CREATED → ACCEPTED) |
| 3 | `POST /orders/{id}/invoice` | Accountant | Create invoice (ACCEPTED → INVOICED) |
| 4 | `POST /orders/{id}/pay` | Customer | Pay invoice (rate-limited) |
| 5 | `POST /orders/{id}/verify-payment` | Accountant | Verify payment (INVOICED → PAID) |
| 6 | `POST /orders/{id}/ship` | Staff | Ship order (PAID → SHIPPED) |
| 7 | `POST /orders/{id}/close` | Staff | Close order (SHIPPED → CLOSED) |
| — | `POST /orders/{id}/cancel` | Any | Cancel order (any pre-SHIPPED state → CANCELLED) |

### 6.5 Payment & Invoice Endpoints

#### `GET /api/v1/payments/{id}` — Get Payment
#### `GET /api/v1/invoices/{id}` — Get Invoice

### 6.6 Monitoring Endpoints

#### `GET /api/v1/health`
```json
{"status": "healthy", "service": "oms"}
```

#### `GET /api/v1/metrics`
```json
{
  "rate_limiter": {
    "capacity": 500,
    "available_tokens": 423.5
  },
  "version": "1.0.0"
}
```

---

## 7. User Workflows

### 7.1 Complete Order Lifecycle

```
Step 1: Customer places order
  POST /api/v1/orders
  Status: CREATED

Step 2: Order Staff accepts
  POST /api/v1/orders/{id}/accept
  Status: ACCEPTED

Step 3: Accountant creates invoice
  POST /api/v1/orders/{id}/invoice
  Status: INVOICED
  (Async notification enqueued)

Step 4: Customer pays
  POST /api/v1/orders/{id}/pay
  Status: INVOICED (payment created)

Step 5: Accountant verifies payment
  POST /api/v1/orders/{id}/verify-payment
  Status: PAID

Step 6: Order Staff ships
  POST /api/v1/orders/{id}/ship
  Status: SHIPPED

Step 7: Order Staff closes
  POST /api/v1/orders/{id}/close
  Status: CLOSED
```

### 7.2 State Machine Diagram

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

**Cancellation** is allowed from CREATED, ACCEPTED, INVOICED, and PAID states.  
Once SHIPPED or CLOSED, cancellation is rejected with HTTP 409.

### 7.3 Error Responses

| HTTP Status | Code | Meaning |
|-------------|------|---------|
| **400** | `BUSINESS_RULE_VIOLATION` | Invalid operation (e.g., paying an already-paid order) |
| **404** | `ENTITY_NOT_FOUND` | Entity (customer, order, product) not found |
| **409** | `INVALID_STATE_TRANSITION` | Illegal state transition (e.g., CREATED → SHIPPED) |
| **409** | `CONCURRENCY_CONFLICT` | Optimistic lock version mismatch (retry with fresh version) |
| **429** | — | Rate limit exceeded (retry after 1 second) |

---

## 8. Load Testing & Performance Verification

### 8.1 Tool: Locust

The system includes a comprehensive Locust load test suite at `oms/load_test/locustfile.py`.

### 8.2 Test Scenarios

#### Scenario 1: Baseline Load
```bash
locust -f oms/load_test/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 500 \
  --spawn-rate 10 \
  --run-time 5m \
  --csv=results/baseline
```

#### Scenario 2: Sustained Load (NFR 1.1 Target)
```bash
locust -f oms/load_test/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 2000 \
  --spawn-rate 20 \
  --run-time 10m \
  --csv=results/sustained
```

#### Scenario 3: Spike Test (NFR 1.3 — 3x Baseline)
```bash
locust -f oms/load_test/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 6000 \
  --spawn-rate 100 \
  --run-time 3m \
  --csv=results/spike
```

### 8.3 Pass/Fail Thresholds

| Metric | Tool | Pass Threshold | Fail Threshold |
|--------|------|----------------|----------------|
| **Checkout p95 latency** | Locust | ≤ 300ms | > 300ms |
| **Search p95 latency** | Locust | ≤ 150ms | > 150ms |
| **Checkout p50 latency** | Locust | ≤ 100ms | > 100ms |
| **Search p50 latency** | Locust | ≤ 50ms | > 50ms |
| **Checkout p99 latency** | Locust | ≤ 500ms | > 500ms |
| **Search p99 latency** | Locust | ≤ 300ms | > 300ms |
| **Throughput** | Locust | > 500 RPS | ≤ 500 RPS |
| **Error rate (excl. 429)** | Locust | < 1% | ≥ 1% |
| **CPU utilization** | `docker stats` | < 80% | ≥ 80% |
| **Memory utilization** | `docker stats` | < 32 GB | ≥ 32 GB |
| **Queue depth** | `redis-cli LLEN oms_tasks` | < 1000 | ≥ 1000 |

### 8.4 Metrics to Capture During Load Tests

1. **Latency percentiles** (p50, p95, p99) — from Locust stats
2. **Throughput** (requests per second) — from Locust stats
3. **Error rate** — from Locust stats (excluding 429 responses)
4. **CPU utilization** — `docker stats oms-api`
5. **Memory utilization** — `docker stats oms-api`
6. **Queue depth** — `docker exec oms-redis redis-cli LLEN oms_tasks`
7. **Rate limiter state** — `curl http://localhost:8000/api/v1/metrics`

### 8.5 Seeding Data for Load Tests

The Locust master process automatically seeds data. To seed manually:

```bash
# Seed 1000 customers and 100 products
python -m oms.load_test.seed_data
```

---

## 9. Monitoring & Observability

### 9.1 Structured JSON Logging

All logs are output as JSON with correlation IDs for request tracing:

```json
{
  "asctime": "2025-07-11T12:00:00+0000",
  "name": "oms",
  "levelname": "INFO",
  "message": "Order placed",
  "correlation_id": "abc-123-def",
  "order_id": "o1-...",
  "customer_id": "c1-..."
}
```

### 9.2 Correlation IDs

Every request receives a correlation ID (from `X-Correlation-ID` header or auto-generated). This ID is:
- Set on the request via middleware
- Propagated through async boundaries via `contextvars`
- Included in all log entries
- Returned in the response header `X-Correlation-ID`

### 9.3 Health Check

```bash
curl http://localhost:8000/api/v1/health
# {"status":"healthy","service":"oms"}
```

### 9.4 Metrics Endpoint

```bash
curl http://localhost:8000/api/v1/metrics
# {
#   "rate_limiter": {
#     "capacity": 500,
#     "available_tokens": 423.5
#   },
#   "version": "1.0.0"
# }
```

### 9.5 Docker Monitoring

```bash
# View real-time resource usage
docker stats

# View API logs
docker-compose logs -f api

# View worker logs
docker-compose logs -f worker

# Check Redis queue depth
docker exec oms-redis redis-cli LLEN oms_tasks
```

---

## 10. Troubleshooting

### 10.1 Common Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| `Connection refused` on startup | PostgreSQL/Redis not ready | Wait for health checks; check `docker-compose logs` |
| `429 Too Many Requests` | Rate limit exceeded | Wait 1 second and retry; reduce request rate |
| `409 Conflict` (version mismatch) | Concurrent modification | Re-fetch the order to get the latest version, then retry |
| `409 Conflict` (invalid transition) | Illegal state change | Check the current order status; follow the valid state machine |
| Slow product search | Cache miss / no Redis | Ensure Redis is running; check `REDIS_URL` |
| Tasks not executing | RQ worker not running | Start worker: `rq worker --url redis://localhost:6379/0 oms_tasks` |

### 10.2 Checking Service Status

```bash
# Check all containers
docker-compose ps

# Check API health
curl http://localhost:8000/api/v1/health

# Check Redis connectivity
docker exec oms-redis redis-cli ping
# Expected: PONG

# Check PostgreSQL connectivity
docker exec oms-postgres pg_isready -U oms
# Expected: /var/run/postgresql:5432 - accepting connections
```

### 10.3 Resetting the Database

```bash
# Stop all services
docker-compose down

# Remove the PostgreSQL volume
docker volume rm oms_postgres_data

# Restart
docker-compose up -d

# Re-seed data
curl -X POST http://localhost:8000/api/v1/seed
```

### 10.4 Performance Tuning

If the system does not meet NFR targets:

1. **Increase rate limiter capacity** in `oms/config.py`:
   - `rate_limit_tokens`: Increase burst capacity
   - `rate_limit_refill_rate`: Increase sustained throughput

2. **Adjust database pool size** in `oms/config.py`:
   - `database_pool_size`: Increase for more concurrent DB connections
   - `database_max_overflow`: Increase for spike tolerance

3. **Scale workers** in `docker-compose.yml`:
   - Increase API `cpus` limit
   - Increase `WORKERS` environment variable

4. **Tune cache TTL** in `oms/config.py`:
   - `product_cache_ttl`: Increase for fewer cache misses (trade-off: stale data)

---

## Appendix: Project Structure

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
│   ├── context.py             # Context variables (correlation ID)
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
    ├── __init__.py
    ├── locustfile.py          # Locust load test scenarios
    └── seed_data.py           # Test data seeder
```

---

*This manual was prepared by the ChatDev Chief Product Officer. For questions or feature requests, please contact the ChatDev team.*
