# Order Management System (OMS) — User Manual

**Version:** 1.0.0  
**Product:** Production-grade e-commerce Order Management System Backend  
**Roles Served:** Customer, Order Staff, Accountant  
**Tech Stack:** Python 3.12+ / FastAPI / PostgreSQL / Redis / RabbitMQ

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Main Functions](#2-main-functions)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Installation & Environment Setup](#4-installation--environment-setup)
5. [Running the System](#5-running-the-system)
6. [API Usage Guide](#6-api-usage-guide)
7. [Complete Order Lifecycle Walkthrough](#7-complete-order-lifecycle-walkthrough)
8. [Running Tests](#8-running-tests)
9. [Load Testing](#9-load-testing)
10. [Monitoring & Metrics](#10-monitoring--metrics)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade backend that serves the complete e-commerce order workflow:

1. **Customer** places an order
2. **Order Staff** reviews & accepts the order
3. **Accountant** creates an invoice for the accepted order
4. **Customer** pays the invoice
5. **Accountant** verifies the payment
6. **Order Staff** ships the paid order
7. **Order Staff** closes the completed order

The system is designed to meet strict performance targets:
- **Checkout path** (order placement, payment submission): p95 ≤ 300ms, p99 ≤ 600ms
- **Product browse/search**: p95 ≤ 150ms
- **Back-office operations** (accept, invoice, verify, ship, close): p95 ≤ 1s
- **Sustains** 5,000 concurrent sessions with CPU utilization between 60–85%
- **Absorbs** 3x traffic spikes without crashes or memory leaks

---

## 2. Main Functions

### 2.1 Order Lifecycle Management

| Function | Endpoint | Role | Description |
|----------|----------|------|-------------|
| Place Order | `POST /api/v1/orders/place` | Customer | Create a new order with line items (rate-limited) |
| Accept Order | `POST /api/v1/orders/accept` | Order Staff | Review and accept a pending order |
| Create Invoice | `POST /api/v1/orders/invoice` | Accountant | Generate invoice for accepted order |
| Submit Payment | `POST /api/v1/orders/pay` | Customer | Pay invoice (rate-limited, idempotent) |
| Verify Payment | `POST /api/v1/orders/verify` | Accountant | Confirm payment reconciliation |
| Ship Order | `POST /api/v1/orders/ship` | Order Staff | Mark order as shipped |
| Close Order | `POST /api/v1/orders/close` | Order Staff | Close completed order |
| Cancel Order | `POST /api/v1/orders/cancel` | Any | Cancel order (pre-SHIPPED only) |
| Get Order | `GET /api/v1/orders/{id}` | Any | Retrieve order details |
| List Orders | `GET /api/v1/orders/` | Any | List all orders with pagination |

### 2.2 Product Catalog

| Function | Endpoint | Description |
|----------|----------|-------------|
| Search Products | `GET /api/v1/products/search?q=...` | Search by name (cached) |
| Get Product | `GET /api/v1/products/{id}` | Get product detail (cached) |
| List Products | `GET /api/v1/products/` | List all products |
| Update Product | `PATCH /api/v1/products/{id}` | Update price/stock (invalidates cache) |

### 2.3 System Functions

| Function | Endpoint | Description |
|----------|----------|-------------|
| Health Check | `GET /health` | Service health status |
| Metrics | `GET /metrics` | Prometheus metrics in exposition format |
| API Docs | `GET /docs` | Swagger UI interactive documentation |
| API Docs | `GET /redoc` | ReDoc alternative documentation |

### 2.4 Order State Machine

The order status follows a strict state machine enforced at the domain layer:

```
CREATED ──accept──→ ACCEPTED ──invoice──→ INVOICED ──pay──→ PAID ──ship──→ SHIPPED ──close──→ CLOSED
    │                  │                  │              │
    └──cancel──→ CANCELLED (terminal) ←──┘              │
                                                         └──cancel──→ CANCELLED (terminal)
```

**Illegal transitions** (e.g., skipping from CREATED to PAID, or cancelling after SHIPPED) are rejected with an `IllegalTransitionError` **before** any database write occurs.

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │  Order   │  │ Product  │  │ Metrics  │  │   Middleware      │  │
│  │Controller│  │Controller│  │Controller│  │ • Correlation ID  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │ • Structured Logs │  │
│       │              │              │        └───────────────────┘  │
│  ┌────┴──────────────┴──────────────┴────┐                          │
│  │          Service Layer                │                          │
│  │  OrderService  │  ProductService      │                          │
│  └────┬───────────┴───────────┬──────────┘                          │
│       │                       │                                      │
│  ┌────┴───────────────────────┴──────┐                               │
│  │       Infrastructure Layer       │                               │
│  │ ┌────────┐ ┌────────┐ ┌───────┐  │                               │
│  │ │Database│ │ Cache  │ │Message│  │                               │
│  │ │(asyncpg│ │(Redis) │ │ (RMQ) │  │                               │
│  │ └───┬────┘ └───┬────┘ └───┬───┘  │                               │
│  │ ┌───┴────┐ ┌───┴────┐ ┌──┴────┐ │                               │
│  │ │Rate    │ │Circuit │ │Idempo-│ │                               │
│  │ │Limiter │ │Breaker │ │tency  │ │                               │
│  │ └────────┘ └────────┘ └───────┘ │                               │
│  └─────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
   ┌──────────┐   ┌────────┐   ┌──────────┐
   │PostgreSQL│   │ Redis  │   │ RabbitMQ │
   │  (data)  │   │(cache) │   │ (queue)  │
   └──────────┘   └────────┘   └──────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Language** | Python 3.12+ | Fast development velocity, rich async ecosystem |
| **Web Framework** | FastAPI | Async I/O, automatic OpenAPI docs, Pydantic validation |
| **Database** | PostgreSQL + asyncpg | ACID transactions for financial data, strong consistency |
| **Cache** | Redis (allkeys-lru) | Shared cache across workers, 60s TTL, max staleness ~62s |
| **Message Queue** | RabbitMQ (bounded) | Reliable delivery, dead-lettering, max 10,000 messages |
| **Rate Limiter** | In-process token bucket | Zero network overhead, capacity=2000, refill=500/s |
| **Circuit Breaker** | In-process sliding window | 50% failure threshold, 30s open, 3 half-open trials |

### Resource Sizing

| Service | CPU | Memory | Derivation |
|---------|-----|--------|------------|
| App (8 workers) | 16 cores | 32 GB | 8 workers × 4 GB/worker |
| PostgreSQL | 4 cores | 8 GB | 40 connections × 200 MB |
| Redis | 2 cores | 2 GB | ~500k entries × 4 KB |
| RabbitMQ | 2 cores | 4 GB | 10k messages × 400 KB |
| **Total** | **24 cores** | **46 GB** | Leaves 52 GB for OS + headroom |

**Pool Sizing Formulas:**
- **DB Connection Pool:** `L = λ × W = 2000 × 0.02 = 40 connections` (Little's Law)
- **Worker Pool:** `workers = cores × (1 + wait_time/compute_time) = 16 × (1 + 20) = 336` theoretical per process
- **Rate Limiter:** Capacity = 2000 (burst), Refill = 500/s (sustained)

---

## 4. Installation & Environment Setup

### 4.1 Prerequisites

- **Docker & Docker Compose** (recommended for full deployment)
- **OR** Python 3.12+ with `uv` (for local development)
- **OR** Python 3.12+ with `pip` (alternative)

### 4.2 Option A: Docker Compose (Recommended)

This is the simplest way to run the full system with all dependencies.

```bash
# Navigate to the OMS directory
cd oms

# Start all services (PostgreSQL, Redis, RabbitMQ, App)
docker compose up --build -d

# Verify all services are running
docker compose ps

# Check logs
docker compose logs -f app
```

### 4.3 Option B: Local Development with uv

```bash
# Navigate to the OMS directory
cd oms

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install all dependencies
uv sync

# Ensure PostgreSQL, Redis, and RabbitMQ are running locally
# (e.g., via Docker for just the infrastructure)
docker run -d --name oms-postgres -e POSTGRES_DB=oms -e POSTGRES_USER=oms -e POSTGRES_PASSWORD=oms -p 5432:5432 postgres:16-alpine
docker run -d --name oms-redis -p 6379:6379 redis:7-alpine redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
docker run -d --name oms-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management-alpine

# Set environment variables (or use defaults)
export OMS_DB_URL="postgresql+asyncpg://oms:oms@localhost:5432/oms"
export OMS_REDIS_URL="redis://localhost:6379/0"
export OMS_RABBITMQ_URL="amqp://guest:guest@localhost:5672/"

# Initialize database tables
python -c "import asyncio; from app.infrastructure.database import init_db; asyncio.run(init_db())"

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 8 --limit-concurrency 4096
```

### 4.4 Option C: Local Development with pip

```bash
cd oms

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg redis aio-pika pydantic pydantic-settings prometheus-client structlog python-json-logger

# Follow the same steps as Option B for infrastructure and running
```

### 4.5 Environment Variables

All configuration is managed via environment variables with the `OMS_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_DB_URL` | `postgresql+asyncpg://oms:oms@localhost:5432/oms` | PostgreSQL connection string |
| `OMS_REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `OMS_RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection string |
| `OMS_UVICORN_WORKERS` | `8` | Number of uvicorn worker processes |
| `OMS_DB_POOL_SIZE` | `40` | Database connection pool size |
| `OMS_RATE_LIMIT_CAPACITY` | `2000` | Token bucket burst capacity |
| `OMS_RATE_LIMIT_REFILL` | `500.0` | Token bucket refill rate (tokens/s) |
| `OMS_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `OMS_PRODUCT_CACHE_TTL` | `60` | Product cache TTL in seconds |

---

## 5. Running the System

### 5.1 Start with Docker Compose

```bash
cd oms
docker compose up --build -d
```

The system starts four containers:
- **app** — FastAPI application on port 8000 (metrics on 9090)
- **postgres** — PostgreSQL 16 on port 5432
- **redis** — Redis 7 on port 6379
- **rabbitmq** — RabbitMQ 3 on ports 5672 (AMQP) and 15672 (Management UI)

### 5.2 Verify the System is Running

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"oms-backend"}

# OpenAPI documentation
open http://localhost:8000/docs

# Metrics endpoint
curl http://localhost:8000/metrics
```

### 5.3 Stop the System

```bash
docker compose down
```

To also remove volumes (database data):
```bash
docker compose down -v
```

---

## 6. API Usage Guide

### 6.1 Seeding Test Data

Before using the system, you need to create at least one customer and one product. Here's a helper script:

```python
# seed_data.py — Run with: python seed_data.py
import asyncio
import httpx
from uuid import UUID

BASE_URL = "http://localhost:8000"

async def seed():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Create a customer (direct DB insert via API isn't available,
        # so we use the known test UUIDs)
        print("Using pre-seeded test data:")
        print(f"  Customer ID: 00000000-0000-0000-0000-000000000001")
        print(f"  Product ID:  00000000-0000-0000-0000-000000000001")
        
        # Verify health
        resp = await client.get("/health")
        print(f"  Health: {resp.json()}")

asyncio.run(seed())
```

> **Note:** The system uses UUIDs for all entities. For testing, the following fixed UUIDs are used:
> - Customer: `00000000-0000-0000-0000-000000000001`
> - Product: `00000000-0000-0000-0000-000000000001`

### 6.2 API Endpoint Reference

#### Order Endpoints

**Place Order** (checkout-critical, rate-limited)
```bash
curl -X POST http://localhost:8000/api/v1/orders/place \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "00000000-0000-0000-0000-000000000001",
    "line_items": [
      {"product_id": "00000000-0000-0000-0000-000000000001", "quantity": 2}
    ]
  }'
```

**Accept Order** (back-office)
```bash
curl -X POST http://localhost:8000/api/v1/orders/accept \
  -H "Content-Type: application/json" \
  -d '{"order_id": "<ORDER_ID_FROM_PLACE>"}'
```

**Create Invoice** (back-office)
```bash
curl -X POST http://localhost:8000/api/v1/orders/invoice \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<ORDER_ID>",
    "customer_name": "John Doe",
    "customer_address": "123 Main St, City, Country",
    "billing_info": "john@example.com"
  }'
```

**Submit Payment** (checkout-critical, rate-limited, idempotent)
```bash
curl -X POST http://localhost:8000/api/v1/orders/pay \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<ORDER_ID>",
    "amount": "108.00",
    "method": "CREDIT_CARD",
    "idempotency_key": "unique-payment-key-123"
  }'
```

**Verify Payment** (back-office)
```bash
curl -X POST http://localhost:8000/api/v1/orders/verify \
  -H "Content-Type: application/json" \
  -d '{"order_id": "<ORDER_ID>"}'
```

**Ship Order** (back-office)
```bash
curl -X POST http://localhost:8000/api/v1/orders/ship \
  -H "Content-Type: application/json" \
  -d '{"order_id": "<ORDER_ID>"}'
```

**Close Order** (back-office)
```bash
curl -X POST http://localhost:8000/api/v1/orders/close \
  -H "Content-Type: application/json" \
  -d '{"order_id": "<ORDER_ID>"}'
```

**Cancel Order**
```bash
curl -X POST http://localhost:8000/api/v1/orders/cancel \
  -H "Content-Type: application/json" \
  -d '{"order_id": "<ORDER_ID>"}'
```

**Get Order**
```bash
curl http://localhost:8000/api/v1/orders/<ORDER_ID>
```

**List Orders**
```bash
curl "http://localhost:8000/api/v1/orders/?skip=0&limit=10"
```

#### Product Endpoints

**Search Products** (cached)
```bash
curl "http://localhost:8000/api/v1/products/search?q=test&page=1&page_size=20"
```

**Get Product** (cached)
```bash
curl http://localhost:8000/api/v1/products/00000000-0000-0000-0000-000000000001
```

**List Products**
```bash
curl "http://localhost:8000/api/v1/products/?skip=0&limit=100"
```

**Update Product** (invalidates cache)
```bash
curl -X PATCH http://localhost:8000/api/v1/products/00000000-0000-0000-0000-000000000001 \
  -H "Content-Type: application/json" \
  -d '{"base_price": "19.99", "stock_available": 50}'
```

### 6.3 Rate Limiting Behavior

Checkout endpoints (`/orders/place`, `/orders/pay`) are protected by a token bucket rate limiter:

- **Capacity:** 2,000 tokens (burst allowance)
- **Refill rate:** 500 tokens/second (sustained throughput)
- **On rejection:** HTTP `429 Too Many Requests` with `Retry-After` header

```bash
# Example of rate-limited response
curl -v -X POST http://localhost:8000/api/v1/orders/place \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "00000000-0000-0000-0000-000000000001", "line_items": []}'

# Response when rate limited:
# HTTP/1.1 429 Too Many Requests
# Retry-After: 2
# {"detail": "Too many requests. Please retry later."}
```

### 6.4 Idempotency for Payment

Payment submission uses idempotency keys to make retries safe:

- Include a unique `idempotency_key` in every payment request
- If the same key is used again within 24 hours, the original response is returned
- This prevents duplicate charges when clients retry due to network timeouts

```bash
# First request — processes normally
curl -X POST http://localhost:8000/api/v1/orders/pay \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<ORDER_ID>",
    "amount": "108.00",
    "method": "CREDIT_CARD",
    "idempotency_key": "my-unique-key-456"
  }'

# Second request with same key — returns cached response
curl -X POST http://localhost:8000/api/v1/orders/pay \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<ORDER_ID>",
    "amount": "108.00",
    "method": "CREDIT_CARD",
    "idempotency_key": "my-unique-key-456"
  }'
# → Same response as first request, no duplicate charge
```

### 6.5 Circuit Breaker Behavior

The system uses circuit breakers for downstream dependencies (payment gateway, shipping API):

- **CLOSED** (normal): All requests pass through
- **OPEN** (failing): Requests are rejected immediately with HTTP 503
- **HALF_OPEN** (probing): Limited requests allowed to test recovery

When a circuit breaker is OPEN:
```bash
curl -X POST http://localhost:8000/api/v1/orders/pay \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<ORDER_ID>",
    "amount": "108.00",
    "method": "CREDIT_CARD",
    "idempotency_key": "another-key"
  }'

# Response:
# HTTP/1.1 503 Service Unavailable
# Retry-After: 30
# {"detail": "Payment service temporarily unavailable. Please retry later."}
```

---

## 7. Complete Order Lifecycle Walkthrough

This walkthrough demonstrates the full order lifecycle from placement to closure.

### Step 1: Place Order (Customer)

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/place \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "00000000-0000-0000-0000-000000000001",
    "line_items": [
      {"product_id": "00000000-0000-0000-0000-000000000001", "quantity": 2}
    ]
  }' | python -m json.tool
```

**Response:**
```json
{
  "id": "a1b2c3d4-...",
  "customer_id": "00000000-0000-0000-0000-000000000001",
  "line_items": [...],
  "subtotal": "20.00",
  "tax_amount": "1.60",
  "total_amount": "21.60",
  "status": "CREATED",
  "version": 1,
  ...
}
```

Save the `id` as `ORDER_ID` for subsequent steps.

### Step 2: Accept Order (Order Staff)

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/accept \
  -H "Content-Type: application/json" \
  -d '{"order_id": "'$ORDER_ID'"}' | python -m json.tool
```

**Response:** Status changes to `ACCEPTED`.

### Step 3: Create Invoice (Accountant)

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/invoice \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "'$ORDER_ID'",
    "customer_name": "John Doe",
    "customer_address": "123 Main St",
    "billing_info": "john@example.com"
  }' | python -m json.tool
```

**Response:** Invoice created, order status changes to `INVOICED`.

### Step 4: Pay Invoice (Customer)

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/pay \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "'$ORDER_ID'",
    "amount": "21.60",
    "method": "CREDIT_CARD",
    "idempotency_key": "payment-'$ORDER_ID'"
  }' | python -m json.tool
```

**Response:** Payment processed, order status changes to `PAID`.

### Step 5: Verify Payment (Accountant)

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/verify \
  -H "Content-Type: application/json" \
  -d '{"order_id": "'$ORDER_ID'"}' | python -m json.tool
```

**Response:** Payment verified (status remains `PAID`).

### Step 6: Ship Order (Order Staff)

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/ship \
  -H "Content-Type: application/json" \
  -d '{"order_id": "'$ORDER_ID'"}' | python -m json.tool
```

**Response:** Order status changes to `SHIPPED`.

### Step 7: Close Order (Order Staff)

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/close \
  -H "Content-Type: application/json" \
  -d '{"order_id": "'$ORDER_ID'"}' | python -m json.tool
```

**Response:** Order status changes to `CLOSED`. Lifecycle complete!

### Cancellation Example

```bash
# Cancel from CREATED state
curl -s -X POST http://localhost:8000/api/v1/orders/cancel \
  -H "Content-Type: application/json" \
  -d '{"order_id": "'$ORDER_ID'"}' | python -m json.tool
```

**Response:** Order status changes to `CANCELLED`, stock is restored.

---

## 8. Running Tests

### 8.1 Unit Tests

The project includes unit tests for the domain layer (state machine and models).

```bash
# Navigate to the OMS directory
cd oms

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=term-missing -v
```

**Test Coverage:**
- `tests/test_state_machine.py` — Verifies all valid and invalid order state transitions
- `tests/test_lineitem.py` — Verifies LineItem model creation, validation, and auto-calculation

### 8.2 Expected Test Output

```
tests/test_state_machine.py::TestOrderStateMachine::test_forward_flow PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_cancel_from_created PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_cancel_from_accepted PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_cancel_from_invoiced PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_cancel_from_paid PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_cancel_from_shipped_invalid PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_cancel_from_closed_invalid PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_skip_state_invalid PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_invalid_event PASSED
tests/test_state_machine.py::TestOrderStateMachine::test_cancelled_is_terminal PASSED
tests/test_lineitem.py::TestLineItem::test_total_price_auto_calculation PASSED
tests/test_lineitem.py::TestLineItem::test_total_price_explicit PASSED
tests/test_lineitem.py::TestLineItem::test_quantity_must_be_positive PASSED
tests/test_lineitem.py::TestLineItem::test_quantity_one_is_valid PASSED
tests/test_lineitem.py::TestLineItem::test_zero_unit_price PASSED
tests/test_lineitem.py::TestLineItem::test_large_quantity PASSED
tests/test_lineitem.py::TestLineItem::test_decimal_precision PASSED
```

---

## 9. Load Testing

### 9.1 Tool: Locust

The project includes a comprehensive Locust load test plan with three scenarios matching NFR 1.1–1.3.

### 9.2 Prerequisites

```bash
# Install Locust (included in dependencies)
uv sync

# Or install separately
pip install locust
```

### 9.3 Scenario 1: Baseline Steady Load

Simulates 2,000 concurrent users with 1–5s think time for 10 minutes.

```bash
cd oms/load_tests

locust -f locustfile.py --host=http://localhost:8000 \
  --users 2000 --spawn-rate 100 --run-time 10m \
  --headless --html report_baseline.html --csv baseline
```

**Pass Criteria:**
- Checkout (place_order, pay): p95 < 300ms, p99 < 600ms
- Browse/search: p95 < 150ms
- Error rate < 1%
- CPU utilization 60–85%

### 9.4 Scenario 2: Sustained Load

Simulates 5,000 concurrent sessions for ≥10 minutes.

```bash
cd oms/load_tests

locust -f locustfile.py --host=http://localhost:8000 \
  --users 5000 --spawn-rate 100 --run-time 10m \
  --headless --html report_sustained.html --csv sustained
```

**Pass Criteria:**
- Average request queueing time < 50ms
- CPU utilization 60–85%
- Error rate < 1%
- No connection pool exhaustion

### 9.5 Scenario 3: Spike (3x Baseline)

Ramps from 0 to 6,000 users over 60 seconds, held for 5 minutes.

```bash
cd oms/load_tests

locust -f locustfile.py --host=http://localhost:8000 \
  --users 6000 --spawn-rate 100 --run-time 6m \
  --headless --html report_spike.html --csv spike
```

**Pass Criteria:**
- No process crashes
- No unbounded memory growth (monitor via `docker stats`)
- No silent request loss (HTTP 429s are acceptable)
- Circuit breaker transitions logged (if any)
- Error rate (excluding 429) < 1%

### 9.6 Interactive Mode

For real-time monitoring during development:

```bash
cd oms/load_tests

locust -f locustfile.py --host=http://localhost:8000 \
  --web-host=0.0.0.0 --web-port=8089
```

Then open `http://localhost:8089` in your browser to access the Locust web UI.

### 9.7 Understanding Load Test Results

The Locust HTML report includes:

| Metric | Description |
|--------|-------------|
| **Response Time (ms)** | p50, p95, p99 latency per endpoint |
| **Throughput (req/s)** | Requests per second |
| **Error Rate (%)** | Percentage of failed requests |
| **User Count** | Number of active simulated users |
| **Total Requests** | Cumulative request count |

---

## 10. Monitoring & Metrics

### 10.1 Prometheus Metrics Endpoint

The system exposes metrics in the standard Prometheus exposition format at `GET /metrics`:

```bash
curl http://localhost:8000/metrics
```

**Key Metrics:**

| Metric Name | Type | Description |
|-------------|------|-------------|
| `http_request_duration_seconds` | Histogram | Request latency with buckets [5ms, 10ms, 25ms, 50ms, 75ms, 100ms, 150ms, 200ms, 300ms, 500ms, 750ms, 1s, 2s, 5s] |
| `http_requests_total` | Counter | Total requests by method, endpoint, status |
| `http_errors_total` | Counter | Total errors by method, endpoint, status code |
| `rate_limiter_tokens_available` | Gauge | Available tokens in rate limiter |
| `circuit_breaker_state` | Gauge | 0=CLOSED, 1=OPEN, 2=HALF_OPEN (per breaker) |
| `db_connection_pool_size` | Gauge | Database connection pool size |
| `queue_depth` | Gauge | Message queue depth (per queue) |

### 10.2 Prometheus Query Examples

```promql
# p95 latency for checkout endpoints (last 5 minutes)
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket{
    endpoint=~"/api/v1/orders/(place|pay)"
  }[5m])) by (le)
)

# p99 latency for checkout
histogram_quantile(0.99, 
  sum(rate(http_request_duration_seconds_bucket{
    endpoint=~"/api/v1/orders/(place|pay)"
  }[5m])) by (le)
)

# p95 latency for product browse
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket{
    endpoint=~"/api/v1/products"
  }[5m])) by (le)
)

# Throughput (req/s)
sum(rate(http_requests_total[1m]))

# Error rate (%)
sum(rate(http_errors_total[1m])) / sum(rate(http_requests_total[1m])) * 100

# Rate limiter status
rate_limiter_tokens_available

# Circuit breaker states
circuit_breaker_state

# Queue depth
queue_depth{queue_name="oms.deferred.work"}
```

### 10.3 Structured Logging

The system uses structured JSON logging with correlation IDs for request tracing.

**Log format (production):**
```json
{"event": "Order placed", "order_id": "a1b2c3d4-...", "total": "21.60", "timestamp": "2025-07-10T12:34:56Z", "logger": "app.services.order_service", "level": "INFO"}
```

**Log format (development):**
```
2025-07-10T12:34:56Z [info     ] Order placed              order_id=a1b2c3d4-... total=21.60
```

**Correlation IDs** are propagated through:
- Request header: `X-Correlation-ID`
- Response header: `X-Correlation-ID`
- All log entries within a request's scope

### 10.4 Viewing Logs

```bash
# Docker Compose
docker compose logs -f app

# Local development (stdout)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
```

### 10.5 RabbitMQ Management UI

When running with Docker Compose, RabbitMQ's management UI is available:

- **URL:** http://localhost:15672
- **Username:** guest
- **Password:** guest

From here you can monitor:
- Queue depth (`oms.deferred.work`)
- Message rates
- Consumer status
- Connection health

---

## 11. Troubleshooting

### 11.1 Database Connection Issues

**Symptom:** `Connection refused` or `could not connect to server`

**Solution:**
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Verify connection string
echo $OMS_DB_URL
# Should be: postgresql+asyncpg://oms:oms@postgres:5432/oms
```

### 11.2 Redis Connection Issues

**Symptom:** `Error 111 connecting to redis:6379. Connection refused`

**Solution:**
```bash
# Check if Redis is running
docker compose ps redis

# Verify Redis is accepting connections
docker compose exec redis redis-cli ping
# Should return: PONG
```

### 11.3 RabbitMQ Connection Issues

**Symptom:** `Connection refused` or `channel closed`

**Solution:**
```bash
# Check if RabbitMQ is running
docker compose ps rabbitmq

# Check RabbitMQ logs
docker compose logs rabbitmq

# Verify via management UI
open http://localhost:15672
```

### 11.4 Rate Limiter Too Aggressive

**Symptom:** Many HTTP 429 responses during normal operation

**Solution:** Adjust rate limiter settings via environment variables:

```bash
# Increase capacity and refill rate
export OMS_RATE_LIMIT_CAPACITY=5000
export OMS_RATE_LIMIT_REFILL=1000
```

### 11.5 Circuit Breaker Tripping Frequently

**Symptom:** HTTP 503 responses from payment/shipping endpoints

**Solution:** Check the downstream dependency health. The circuit breaker will automatically reset after 30 seconds (configurable via `OMS_CB_OPEN_DURATION_SECONDS`).

### 11.6 Memory Issues

**Symptom:** Container OOM kills or high memory usage

**Solution:**
```bash
# Monitor memory usage
docker stats

# Check if RabbitMQ queue is growing unbounded
# Visit http://localhost:15672 and check queue depth

# Reduce worker count if needed
export OMS_UVICORN_WORKERS=4
```

### 11.7 Slow Response Times

**Symptom:** p95 latency exceeds 300ms for checkout

**Solution:**
1. Check database query performance
2. Verify Redis cache hit rate (via `GET /metrics`)
3. Check if connection pools are exhausted
4. Monitor CPU utilization — should be 60–85% at peak

### 11.8 Common Error Codes

| HTTP Status | Meaning | Common Cause |
|-------------|---------|--------------|
| 201 | Created | Order placed successfully |
| 200 | OK | Operation successful |
| 400 | Bad Request | Invalid input data (e.g., insufficient stock) |
| 404 | Not Found | Order or product ID doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded (checkout endpoints) |
| 503 | Service Unavailable | Circuit breaker open (payment/shipping) |

---

## File Structure Reference

```
oms/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings with pool-sizing formulas
│   ├── domain/
│   │   ├── enums.py               # Status enums (OrderStatus, PaymentStatus, etc.)
│   │   ├── models.py              # Pydantic domain models
│   │   └── state_machine.py       # Order state machine with transition validation
│   ├── infrastructure/
│   │   ├── database.py            # Asyncpg connection pool (sized via Little's Law)
│   │   ├── cache.py               # Redis cache-aside layer (TTL 60s, LRU eviction)
│   │   ├── messaging.py           # RabbitMQ producer/consumer (bounded queue)
│   │   ├── rate_limiter.py        # Token bucket rate limiter (capacity=2000, refill=500/s)
│   │   ├── circuit_breaker.py     # Sliding-window circuit breaker (50% threshold, 30s open)
│   │   └── idempotency.py         # Idempotency key store (Redis, 24h TTL)
│   ├── repositories/
│   │   ├── base.py                # Generic CRUD repository with JSON serialization
│   │   ├── orm_models.py          # SQLAlchemy ORM models (5 tables)
│   │   ├── customer_repo.py
│   │   ├── order_repo.py          # With optimistic-lock version check
│   │   ├── product_repo.py        # With cache-aside and atomic stock operations
│   │   ├── payment_repo.py        # With idempotency key lookup
│   │   └── invoice_repo.py
│   ├── services/
│   │   ├── order_service.py       # Order lifecycle orchestration (7 operations)
│   │   └── product_service.py     # Product browse/search with cache-aside
│   ├── api/
│   │   ├── dependencies.py        # FastAPI DI with UnitOfWork pattern
│   │   └── v1/
│   │       ├── order_controller.py    # 10 REST endpoints for order lifecycle
│   │       ├── product_controller.py  # 4 REST endpoints for product catalog
│   │       └── metrics_controller.py  # Prometheus metrics + middleware
│   └── middleware/
│       ├── correlation_id.py      # X-Correlation-ID header propagation
│       └── logging_middleware.py  # Structured JSON logging (structlog)
├── load_tests/
│   └── locustfile.py              # 3 load test scenarios (baseline, sustained, spike)
├── tests/
│   ├── test_state_machine.py      # 10 tests for order state transitions
│   └── test_lineitem.py           # 7 tests for LineItem model validation
├── docker-compose.yml             # 4 services with resource limits
├── Dockerfile                      # Multi-stage build (uv → runtime)
├── pyproject.toml
├── README.md                      # Full documentation with ADRs and NFR matrix
└── manual.md                      # This file — user manual
```

---

*For questions, feature requests, or bug reports, please contact the ChatDev product team.*
