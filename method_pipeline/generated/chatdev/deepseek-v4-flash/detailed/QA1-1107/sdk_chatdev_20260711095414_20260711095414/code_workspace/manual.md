# Order Management System (OMS) — User Manual

> **Version:** 1.0.0  
> **Product Owner:** Chief Product Officer, ChatDev  
> **Tech Stack:** Python 3.12, FastAPI, PostgreSQL (asyncpg), Redis, RabbitMQ, Prometheus, Locust  
> **Target Hardware:** Single node, 8 CPU cores, 98 GB RAM

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Main Functions & Features](#2-main-functions--features)
3. [Architecture at a Glance](#3-architecture-at-a-glance)
4. [Installation & Environment Setup](#4-installation--environment-setup)
5. [Running the System](#5-running-the-system)
6. [API Reference](#6-api-reference)
7. [User Workflows](#7-user-workflows)
8. [Load Testing](#8-load-testing)
9. [Monitoring & Metrics](#9-monitoring--metrics)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. System Overview

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that serves the complete order lifecycle:

1. **Customer** places an order
2. **Order Staff** reviews and accepts the order
3. **Accountant** creates an invoice for the accepted order
4. **Customer** pays the invoice
5. **Accountant** verifies the payment
6. **Order Staff** ships the paid order
7. **Order Staff** closes the completed order

The system serves three roles: **Customer**, **Order Staff**, and **Accountant**. No authentication is required (as per specification).

### Performance Targets

| Metric | Target | Condition |
|--------|--------|-----------|
| Checkout p95 latency | ≤ 300 ms | 2,000 concurrent users, 1–5s think time |
| Checkout p99 latency | ≤ 600 ms | 2,000 concurrent users, 1–5s think time |
| Product search p95 latency | ≤ 150 ms | 2,000 concurrent users, 1–5s think time |
| Back-office p95 latency | ≤ 1,000 ms | Relaxed (not customer-facing) |
| Concurrent sessions | 5,000 | Average queue time < 50 ms |
| CPU utilization | 60–85% | At peak, with headroom for spikes |
| Spike absorption | 3× baseline | 60s ramp, no crashes/OOM/silent loss |

---

## 2. Main Functions & Features

### 2.1 Order Lifecycle Management

Complete state machine for orders with enforced legal transitions:

| From State | Event | To State | Guard Condition |
|------------|-------|----------|-----------------|
| CREATED | `accept` | ACCEPTED | Order staff reviews and accepts |
| CREATED | `cancel` | CANCELLED | Customer or staff cancels before acceptance |
| ACCEPTED | `invoice` | INVOICED | Accountant creates invoice |
| ACCEPTED | `cancel` | CANCELLED | Cancelled before invoicing |
| INVOICED | `pay` | PAID | Customer pays invoice |
| INVOICED | `cancel` | CANCELLED | Cancelled before payment |
| PAID | `ship` | SHIPPED | Order staff ships paid order |
| PAID | `cancel` | CANCELLED | Cancelled before shipping (refund needed) |
| PAID | `verify` | PAID | Accountant verifies payment (no-op) |
| SHIPPED | `close` | CLOSED | Order staff closes completed order |

Illegal transitions are **rejected before any persistence write** by the domain state machine.

### 2.2 Cache-Aside Layer (Redis)

- **Product cache:** TTL = 60 seconds (max staleness window)
- **Search result cache:** TTL = 30 seconds
- **Invalidation:** Triggered automatically on price/stock updates
- **Eviction policy:** Redis `allkeys-lru` (default)

### 2.3 Rate Limiting (Token Bucket)

- **Capacity:** 5,000 tokens (burst)
- **Refill rate:** 1,000 tokens/second (sustained)
- **Scope:** Checkout-critical endpoints (`POST /api/v1/orders/`, `POST /api/v1/orders/payment`)
- **Rejection behavior:** HTTP 429 with `Retry-After: 1` header

### 2.4 Circuit Breaker (Resilience4j-style)

- **Payment gateway breaker:** Opens after 50 failures, 30s recovery timeout, 3 half-open trial calls
- **Shipping provider breaker:** Same configuration
- **Behavior:** HTTP 503 with `Retry-After: 30` header when open

### 2.5 Deferred Task Queue (RabbitMQ)

- **Queue:** `oms_deferred_tasks` (durable, persistent messages)
- **Consumer concurrency:** 8 (one per core)
- **Deferrable work:** Invoice generation, notification dispatch, shipping label creation
- **Queue depth monitoring:** Sampled every 5 seconds, exposed as Prometheus metric

### 2.6 Idempotency Handling

- **Payment submission:** Idempotency key stored in Redis with 1-hour TTL
- **Duplicate detection:** Checked before any DB writes
- **Safe retries:** Under spike conditions, retries are idempotent

### 2.7 Optimistic Locking

- **Version field:** Every order has a `version` integer (starts at 1)
- **Conflict detection:** Updates check `WHERE version = expected_version`
- **Conflict response:** HTTP 400 with descriptive error

### 2.8 Structured Logging & Correlation IDs

- **Correlation ID:** Every request gets a `X-Request-ID` (UUID), propagated in response headers
- **Log format:** `timestamp | LEVEL | logger | message`
- **Request tracing:** Correlation ID included in all log entries

---

## 3. Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Health   │  │ Order    │  │ Product  │  │ Customer   │  │
│  │ Ctrl     │  │ Ctrl     │  │ Ctrl     │  │ Ctrl       │  │
│  └──────────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│                     │              │               │         │
│  ┌──────────────────┴──────────────┴───────────────┴──────┐ │
│  │                   Service Layer                         │ │
│  │  OrderService  ProductService  PaymentService          │ │
│  │  InvoiceService                                         │ │
│  └──────────────────┬──────────────┬───────────────────────┘ │
│                     │              │                          │
│  ┌──────────────────┴──────────────┴───────────────────────┐ │
│  │              Repository Layer (Cache-Aside)               │ │
│  │  OrderRepo  ProductRepo  PaymentRepo  InvoiceRepo        │ │
│  │  CustomerRepo  BaseRepository                            │ │
│  └──────────────────┬──────────────┬───────────────────────┘ │
│                     │              │                          │
└─────────────────────┼──────────────┼──────────────────────────┘
                      │              │
         ┌────────────┴────┐  ┌─────┴────────────┐
         │   PostgreSQL    │  │      Redis       │
         │   (asyncpg)     │  │  (cache + idem)  │
         └─────────────────┘  └──────────────────┘
                      │
         ┌────────────┴────────────┐
         │       RabbitMQ          │
         │  (deferred task queue)  │
         └─────────────────────────┘
```

### Technology Choices & Justification

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.12 | Async/await native, rich ecosystem, FastAPI for high-throughput HTTP |
| **Web Framework** | FastAPI | Async-native, automatic OpenAPI docs, Pydantic validation, high performance |
| **Database** | PostgreSQL 16 | Mature, ACID-compliant, excellent async driver (asyncpg) |
| **Cache** | Redis 7 | Sub-millisecond reads, TTL support, idempotency key store |
| **Message Broker** | RabbitMQ | Durable queues, persistent messages, management UI |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, async support, connection pooling |
| **Metrics** | Prometheus client | Standard exposition format, histogram support for latency |
| **Load Testing** | Locust | Python-based, distributed, real-time metrics |
| **Circuit Breaker** | pybreaker | Lightweight, proven, async-compatible wrapper |

### Resource Allocation

| Component | CPU | Memory | Derivation |
|-----------|-----|--------|------------|
| App container | 4 cores | 4 GB | 50% of 8 cores, 4% of 98 GB |
| PostgreSQL | 2 cores | 2 GB | 25% of 8 cores |
| Redis | 1 core | 1 GB | 12.5% of 8 cores |
| RabbitMQ | 1 core | 1 GB | 12.5% of 8 cores |
| **Total** | **8 cores** | **8 GB** | Well within 98 GB target |

### Pool Sizing Formulas

**DB Connection Pool:**
```
pool_size = cores × 2 = 8 × 2 = 16
max_overflow = 8 (50% headroom for bursts)
```
Derivation: HikariCP-style heuristic. With async I/O, connections spend most time waiting on DB, so `wait_time/compute_time` ratio is high. 16 connections per 8 cores is conservative.

**Worker Pool (Uvicorn workers):**
```
workers = 4 (in container, leaving 4 cores for OS and other services)
```
Derivation: For async workers, `workers = cores` is standard. We use 4 in container to leave headroom.

**Rate Limiter (Token Bucket):**
```
capacity = 5000 (burst)
refill_rate = 1000/s (sustained)
```
Derivation: At 2,000 concurrent users with 1–5s think time, peak throughput ≈ 2,000/1 = 2,000 req/s. Capacity of 5,000 allows 2.5× burst. Refill of 1,000/s sustains normal load with headroom.

**Consumer Pool (RabbitMQ):**
```
concurrency = 8 (one per core)
```
Derivation: One consumer per core for CPU-bound task processing.

---

## 4. Installation & Environment Setup

### 4.1 Prerequisites

- **Docker & Docker Compose** (recommended for containerized deployment)
- **OR** Python 3.12+ with `uv` package manager (for bare-metal deployment)
- At least **8 GB RAM** and **4 CPU cores** recommended

### 4.2 Quick Start (Docker Compose)

```bash
# 1. Clone the repository
cd oms

# 2. Start all services (PostgreSQL, Redis, RabbitMQ, App)
docker compose up --build -d

# 3. Verify all services are healthy
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 4. View the OpenAPI documentation
open http://localhost:8000/docs
```

### 4.3 Bare-Metal Deployment

#### Step 1: Start Dependencies

```bash
# PostgreSQL
docker run -d --name oms-postgres \
  -e POSTGRES_USER=oms \
  -e POSTGRES_PASSWORD=oms \
  -e POSTGRES_DB=oms \
  -p 5432:5432 \
  postgres:16-alpine

# Redis
docker run -d --name oms-redis \
  -p 6379:6379 \
  redis:7-alpine

# RabbitMQ
docker run -d --name oms-rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management-alpine
```

#### Step 2: Install Python Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync project dependencies
uv sync
```

#### Step 3: Configure Environment (Optional)

Create a `.env` file in the project root:

```env
OMS_DB_URL=postgresql+asyncpg://oms:oms@localhost:5432/oms
OMS_REDIS_URL=redis://localhost:6379/0
OMS_RABBITMQ_URL=amqp://guest:guest@localhost:5672/
OMS_HOST=0.0.0.0
OMS_PORT=8000
OMS_WORKERS=4
```

#### Step 4: Run the Application

```bash
uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4.4 Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Metrics endpoint
curl http://localhost:8000/metrics

# OpenAPI docs
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc
```

---

## 5. Running the System

### 5.1 Starting the Application

**Docker Compose (recommended):**
```bash
docker compose up --build -d
```

**Bare-metal:**
```bash
uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5.2 Seed Data

The application automatically seeds the database on first startup with:

- **1 Customer:** John Doe (ID: `00000000-0000-0000-0000-000000000001`)
- **3 Products:**
  - High-performance laptop (16GB RAM) — $1,299.99 — 100 in stock
  - Wireless noise-cancelling headphones — $349.99 — 250 in stock
  - Ergonomic mechanical keyboard — $159.99 — 500 in stock

To manually re-seed (if needed):
```bash
uv run python -m oms.seed
```

### 5.3 Running Tests

```bash
# Run all unit tests
uv run pytest oms/tests/ -v

# Run specific test file
uv run pytest oms/tests/test_state_machine.py -v
```

### 5.4 Shutting Down

**Docker Compose:**
```bash
docker compose down
```

**Bare-metal:** Press `Ctrl+C` in the terminal running uvicorn.

---

## 6. API Reference

### 6.1 Base URL

All API endpoints are served at: `http://localhost:8000`

### 6.2 System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics (text format) |
| GET | `/docs` | Swagger UI (OpenAPI) |
| GET | `/redoc` | ReDoc UI |

### 6.3 Customer Endpoints

#### `POST /api/v1/customers` — Create Customer

**Request Body:**
```json
{
  "name": "Jane Smith",
  "address": "456 Oak Ave, Metropolis, USA",
  "phone": "+1-555-0200",
  "banking_details": "Chase Bank, Account ****5678",
  "role": "CUSTOMER"
}
```

**Response (201):**
```json
{
  "id": "a1b2c3d4-...",
  "name": "Jane Smith",
  "address": "456 Oak Ave, Metropolis, USA",
  "phone": "+1-555-0200",
  "banking_details": "Chase Bank, Account ****5678",
  "role": "CUSTOMER",
  "order_history": []
}
```

#### `GET /api/v1/customers` — List All Customers

**Response (200):** Array of customer objects.

#### `GET /api/v1/customers/{customer_id}` — Get Customer by ID

**Response (200):** Single customer object.  
**Response (404):** Customer not found.

### 6.4 Product Endpoints

#### `GET /api/v1/products/search?q={query}&limit={n}` — Search Products

**Query Parameters:**
- `q` (required): Search term (min 1 character)
- `limit` (optional, default 20, max 100): Max results

**Response (200):**
```json
[
  {
    "id": "00000000-0000-0000-0000-000000000010",
    "description": "High-performance laptop with 16GB RAM",
    "base_price": "1299.99",
    "currency": "USD",
    "stock_available": 100,
    "last_modified": "2025-07-10T12:00:00+00:00"
  }
]
```

**Performance:** p95 ≤ 150 ms (cache-aside via Redis).

#### `GET /api/v1/products/{product_id}` — Get Product by ID

**Response (200):** Single product object (cache-aside).  
**Response (404):** Product not found.

#### `PATCH /api/v1/products/{product_id}/price` — Update Price

**Request Body:**
```json
{
  "new_price": 1199.99
}
```

**Effect:** Invalidates product cache.

#### `PATCH /api/v1/products/{product_id}/stock` — Update Stock

**Request Body:**
```json
{
  "delta": -5
}
```

**Effect:** Adjusts stock (can be negative) and invalidates product cache.

### 6.5 Order Endpoints

#### `POST /api/v1/orders` — Place Order (Checkout-Critical)

**Rate Limited:** Yes (token bucket, 429 if exceeded).  
**Performance:** p95 ≤ 300 ms, p99 ≤ 600 ms.

**Request Body:**
```json
{
  "customer_id": "00000000-0000-0000-0000-000000000001",
  "line_items": [
    {
      "product_id": "00000000-0000-0000-0000-000000000010",
      "quantity": 1,
      "unit_price": 1299.99
    }
  ]
}
```

**Response (201):**
```json
{
  "id": "order-uuid-here",
  "customer_id": "00000000-0000-0000-0000-000000000001",
  "line_items": [...],
  "subtotal": "1299.99",
  "tax": "104.00",
  "total_amount": "1403.99",
  "status": "CREATED",
  "created_at": "2025-07-10T12:00:00+00:00",
  "updated_at": "2025-07-10T12:00:00+00:00",
  "version": 1,
  ...
}
```

**Response (429):**
```json
{
  "detail": "Too many requests. Please retry after the Retry-After period."
}
```
Header: `Retry-After: 1`

#### `POST /api/v1/orders/payment` — Submit Payment (Checkout-Critical)

**Rate Limited:** Yes.  
**Idempotent:** Yes (idempotency key required).  
**Performance:** p95 ≤ 300 ms, p99 ≤ 600 ms.

**Request Body:**
```json
{
  "order_id": "order-uuid-here",
  "amount": 1403.99,
  "method": "CREDIT_CARD",
  "idempotency_key": "unique-key-for-retry-safety"
}
```

**Response (201):**
```json
{
  "id": "payment-uuid-here",
  "order_id": "order-uuid-here",
  "amount": 1403.99,
  "timestamp": "2025-07-10T12:00:00+00:00",
  "status": "COMPLETED",
  "method": "CREDIT_CARD",
  "idempotency_key": "unique-key-for-retry-safety"
}
```

**Response (503):** Circuit breaker open — payment gateway unavailable.
```json
{
  "detail": "Payment gateway circuit is OPEN -- rejecting request"
}
```
Header: `Retry-After: 30`

#### `GET /api/v1/orders` — List Orders

**Query Parameters:**
- `customer_id` (optional): Filter by customer UUID

**Response (200):** Array of order objects.

#### `GET /api/v1/orders/{order_id}` — Get Order by ID

**Response (200):** Single order object.  
**Response (404):** Order not found.

### 6.6 Back-Office Endpoints

All back-office endpoints have a relaxed performance target of **p95 ≤ 1,000 ms** (not customer-facing).

#### `POST /api/v1/orders/{order_id}/accept` — Accept Order

**Role:** Order Staff.  
**Transition:** CREATED → ACCEPTED.

**Request Body:**
```json
{
  "expected_version": 1
}
```

**Response (200):** Updated order with status `ACCEPTED`.

#### `POST /api/v1/orders/{order_id}/invoice` — Create Invoice

**Role:** Accountant.  
**Transition:** ACCEPTED → INVOICED.

**Request Body:**
```json
{
  "expected_version": 1
}
```

**Response (201):**
```json
{
  "id": "invoice-uuid-here",
  "order_id": "order-uuid-here",
  "billing_info": "Invoice for order order-uuid-here",
  "amount": 1403.99,
  "issue_date": "2025-07-10",
  "due_date": "2025-08-09",
  "status": "ISSUED"
}
```

#### `POST /api/v1/orders/{order_id}/verify-payment` — Verify Payment

**Role:** Accountant.  
**Transition:** PAID → PAID (no-op, confirms payment).

**Request Body:**
```json
{
  "expected_version": 1
}
```

**Response (200):** Current order (status remains `PAID`).

#### `POST /api/v1/orders/{order_id}/ship` — Ship Order

**Role:** Order Staff.  
**Transition:** PAID → SHIPPED.  
**Circuit Breaker:** Shipping provider (503 if open).

**Request Body:**
```json
{
  "expected_version": 1
}
```

**Response (200):** Updated order with status `SHIPPED`.

#### `POST /api/v1/orders/{order_id}/close` — Close Order

**Role:** Order Staff.  
**Transition:** SHIPPED → CLOSED.

**Request Body:**
```json
{
  "expected_version": 1
}
```

**Response (200):** Updated order with status `CLOSED`.

#### `POST /api/v1/orders/{order_id}/cancel` — Cancel Order

**Role:** Any (Customer, Order Staff).  
**Transition:** Any pre-SHIPPED state → CANCELLED.

**Request Body:**
```json
{
  "expected_version": 1
}
```

**Response (200):** Updated order with status `CANCELLED`.

---

## 7. User Workflows

### 7.1 Complete Order Lifecycle (Happy Path)

```bash
#!/bin/bash
# Full workflow demonstration

BASE="http://localhost:8000"
CUSTOMER_ID="00000000-0000-0000-0000-000000000001"
PRODUCT_ID="00000000-0000-0000-0000-000000000010"

# 1. Customer places order
echo "=== Step 1: Place Order ==="
ORDER_RESP=$(curl -s -X POST "$BASE/api/v1/orders/" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"$CUSTOMER_ID\",
    \"line_items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 1, \"unit_price\": 1299.99}]
  }")
echo "$ORDER_RESP" | python3 -m json.tool
ORDER_ID=$(echo "$ORDER_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
VERSION=$(echo "$ORDER_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])")
TOTAL=$(echo "$ORDER_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_amount'])")

# 2. Order Staff accepts
echo -e "\n=== Step 2: Accept Order ==="
curl -s -X POST "$BASE/api/v1/orders/$ORDER_ID/accept" \
  -H "Content-Type: application/json" \
  -d "{\"expected_version\": $VERSION}" | python3 -m json.tool
VERSION=$((VERSION + 1))

# 3. Accountant creates invoice
echo -e "\n=== Step 3: Create Invoice ==="
INVOICE_RESP=$(curl -s -X POST "$BASE/api/v1/orders/$ORDER_ID/invoice" \
  -H "Content-Type: application/json" \
  -d "{\"expected_version\": $VERSION}")
echo "$INVOICE_RESP" | python3 -m json.tool
VERSION=$((VERSION + 1))

# 4. Customer pays
echo -e "\n=== Step 4: Submit Payment ==="
curl -s -X POST "$BASE/api/v1/orders/payment" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"amount\": $TOTAL,
    \"method\": \"CREDIT_CARD\",
    \"idempotency_key\": \"pay-$ORDER_ID-$(date +%s)\"
  }" | python3 -m json.tool

# 5. Accountant verifies payment
echo -e "\n=== Step 5: Verify Payment ==="
curl -s -X POST "$BASE/api/v1/orders/$ORDER_ID/verify-payment" \
  -H "Content-Type: application/json" \
  -d "{\"expected_version\": $VERSION}" | python3 -m json.tool

# 6. Order Staff ships
echo -e "\n=== Step 6: Ship Order ==="
curl -s -X POST "$BASE/api/v1/orders/$ORDER_ID/ship" \
  -H "Content-Type: application/json" \
  -d "{\"expected_version\": $VERSION}" | python3 -m json.tool
VERSION=$((VERSION + 1))

# 7. Order Staff closes
echo -e "\n=== Step 7: Close Order ==="
curl -s -X POST "$BASE/api/v1/orders/$ORDER_ID/close" \
  -H "Content-Type: application/json" \
  -d "{\"expected_version\": $VERSION}" | python3 -m json.tool

echo -e "\n=== Workflow Complete ==="
```

### 7.2 Product Browsing & Search

```bash
# Search products
curl "http://localhost:8000/api/v1/products/search?q=laptop&limit=5"

# Get single product
curl "http://localhost:8000/api/v1/products/00000000-0000-0000-0000-000000000010"
```

### 7.3 Idempotent Payment Retry (Safe Under Spikes)

```bash
# First attempt
IDEM_KEY="unique-key-$(date +%s)"
curl -s -X POST "http://localhost:8000/api/v1/orders/payment" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"amount\": $TOTAL,
    \"method\": \"CREDIT_CARD\",
    \"idempotency_key\": \"$IDEM_KEY\"
  }"

# Retry with same idempotency key — safe, returns same result
curl -s -X POST "http://localhost:8000/api/v1/orders/payment" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"amount\": $TOTAL,
    \"method\": \"CREDIT_CARD\",
    \"idempotency_key\": \"$IDEM_KEY\"
  }"
```

### 7.4 Rate Limiting in Action

```bash
# Rapid-fire requests to trigger rate limiting
for i in {1..10}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" \
    -X POST "http://localhost:8000/api/v1/orders/" \
    -H "Content-Type: application/json" \
    -d "{
      \"customer_id\": \"00000000-0000-0000-0000-000000000001\",
      \"line_items\": [{\"product_id\": \"00000000-0000-0000-0000-000000000010\", \"quantity\": 1, \"unit_price\": 1299.99}]
    }"
done
# You'll see HTTP 429 after exhausting the token bucket
```

---

## 8. Load Testing

### 8.1 Test Scenarios

The system includes a comprehensive Locust-based load test suite with three scenarios:

#### Scenario 1: Baseline Steady Load

```bash
uv run locust -f oms/load_test/locustfile.py \
  --host http://localhost:8000 \
  --users 2000 \
  --spawn-rate 50 \
  --run-time 10m \
  --headless \
  --csv=baseline
```

- **Users:** 2,000 concurrent virtual users
- **Think time:** 1–5 seconds (uniform distribution)
- **Duration:** 10 minutes steady state
- **Pass criteria:**
  - Checkout p95 ≤ 300 ms
  - Checkout p99 ≤ 600 ms
  - Search p95 ≤ 150 ms
  - Error rate < 1%

#### Scenario 2: Sustained Load

```bash
uv run locust -f oms/load_test/locustfile.py \
  --host http://localhost:8000 \
  --users 5000 \
  --spawn-rate 100 \
  --run-time 10m \
  --headless \
  --csv=sustained
```

- **Users:** 5,000 concurrent active sessions
- **Duration:** ≥ 10 minutes
- **Pass criteria:**
  - Average request queueing time < 50 ms
  - CPU utilization 60–85%
  - No error rate increase over baseline

#### Scenario 3: 3× Spike

```bash
uv run locust -f oms/load_test/locustfile.py \
  --host http://localhost:8000 \
  --users 6000 \
  --spawn-rate 100 \
  --run-time 6m \
  --headless \
  --csv=spike
```

- **Ramp:** 0 → 6,000 users over 60 seconds (100 users/s)
- **Hold:** 5 minutes at peak
- **Pass criteria:**
  - No process crashes
  - No unbounded memory growth (hard ceiling: 4 GB container limit)
  - No silent request loss (all errors logged with correlation IDs)
  - Rate limiter returns 429 (not dropped connections)
  - Circuit breaker transitions visible in metrics

### 8.2 User Classes in Load Tests

The Locust file defines three user classes that simulate different roles:

| User Class | Endpoints | Latency Target | Think Time |
|------------|-----------|----------------|------------|
| `BrowseUser` | Product search | p95 ≤ 150 ms | 1–5 s |
| `CheckoutUser` | Place order, Submit payment | p95 ≤ 300 ms, p99 ≤ 600 ms | 1–5 s |
| `BackOfficeUser` | Accept, Invoice, Verify, Ship, Close | p95 ≤ 1,000 ms | 2–10 s |

### 8.3 Metrics Captured

Each test run produces a CSV file with:

| Metric | Description |
|--------|-------------|
| `p50` | Median latency per endpoint |
| `p95` | 95th percentile latency per endpoint |
| `p99` | 99th percentile latency per endpoint |
| `req/s` | Throughput (requests per second) |
| `error_rate` | Percentage of failed requests |
| `cpu_usage` | CPU utilization over time |
| `memory_usage` | Memory utilization over time |
| `queue_depth` | RabbitMQ queue depth over time |
| `circuit_breaker_state` | State transitions (closed/open/half-open) |

### 8.4 Running All Scenarios

```bash
# Run all three scenarios sequentially
./run_load_tests.sh
```

Or manually:

```bash
# Scenario 1: Baseline
uv run locust -f oms/load_test/locustfile.py --host http://localhost:8000 --users 2000 --spawn-rate 50 --run-time 10m --headless --csv=baseline

# Scenario 2: Sustained
uv run locust -f oms/load_test/locustfile.py --host http://localhost:8000 --users 5000 --spawn-rate 100 --run-time 10m --headless --csv=sustained

# Scenario 3: Spike
uv run locust -f oms/load_test/locustfile.py --host http://localhost:8000 --users 6000 --spawn-rate 100 --run-time 6m --headless --csv=spike
```

---

## 9. Monitoring & Metrics

### 9.1 Metrics Endpoint

The system exposes Prometheus-formatted metrics at:

```
GET http://localhost:8000/metrics
```

**Format:** Prometheus text exposition format (`Content-Type: text/plain; version=0.0.4`).

### 9.2 Available Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `oms_http_request_duration_seconds` | Histogram | `method`, `endpoint`, `status` | HTTP request latency |
| `oms_http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests |
| `oms_orders_created_total` | Counter | — | Total orders created |
| `oms_orders_transitions_total` | Counter | `to_status` | Order status transitions |
| `oms_queue_depth` | Gauge | — | Current RabbitMQ queue depth |
| `oms_rate_limiter_tokens` | Gauge | — | Available tokens in bucket |
| `oms_circuit_breaker_state` | Gauge | `name` | Circuit breaker state (0=closed, 1=open, 2=half-open) |

### 9.3 Example PromQL Queries

**p95 Latency (Checkout):**
```promql
histogram_quantile(0.95,
  sum(rate(oms_http_request_duration_seconds_bucket{
    endpoint=~"/api/v1/orders/?|/api/v1/orders/payment"
  }[5m])) by (le)
)
```

**p99 Latency (Checkout):**
```promql
histogram_quantile(0.99,
  sum(rate(oms_http_request_duration_seconds_bucket{
    endpoint=~"/api/v1/orders/?|/api/v1/orders/payment"
  }[5m])) by (le)
)
```

**p95 Latency (Product Search):**
```promql
histogram_quantile(0.95,
  sum(rate(oms_http_request_duration_seconds_bucket{
    endpoint="/api/v1/products/search"
  }[5m])) by (le)
)
```

**Request Rate:**
```promql
rate(oms_http_requests_total[1m])
```

**Error Rate:**
```promql
sum(rate(oms_http_requests_total{status=~"4..|5.."}[5m]))
/
sum(rate(oms_http_requests_total[5m]))
```

**Queue Depth:**
```promql
oms_queue_depth
```

**Rate Limiter Tokens:**
```promql
oms_rate_limiter_tokens
```

**Circuit Breaker State:**
```promql
oms_circuit_breaker_state{name="payment_gateway"}
```

**Order Status Transitions (per minute):**
```promql
rate(oms_orders_transitions_total[5m])
```

### 9.4 Example Grafana Dashboard

A sample dashboard configuration would include:

1. **Latency Panel:** p50/p95/p99 latency for checkout endpoints (line chart, 5m window)
2. **Search Latency Panel:** p50/p95 latency for product search (line chart)
3. **Throughput Panel:** Requests per second by endpoint (stacked area chart)
4. **Error Rate Panel:** Percentage of 4xx/5xx responses (gauge + time series)
5. **Queue Depth Panel:** RabbitMQ queue depth (gauge + time series)
6. **Rate Limiter Panel:** Available tokens (gauge)
7. **Circuit Breaker Panel:** State per breaker (state timeline)
8. **Resource Panel:** CPU and memory utilization (line chart)
9. **Order Transitions Panel:** Rate of status transitions per status (bar chart)

### 9.5 Structured Logging

Logs are output to stdout in the format:

```
2025-07-10T12:00:00+0000 | INFO     | oms.services.order_service | place_order called | customer_id=0000... | request_id=abc...
```

Each log entry includes:
- Timestamp (ISO 8601 with timezone)
- Log level (INFO, WARNING, ERROR)
- Logger name
- Message with structured context (correlation ID, entity IDs)

---

## 10. Troubleshooting

### 10.1 Common Issues

#### "Database already seeded, skipping"

The seed script is idempotent. If you need to re-seed, truncate the tables first:

```bash
# Connect to PostgreSQL and truncate
docker exec -it oms-postgres psql -U oms -d oms -c "TRUNCATE customers, products CASCADE;"
```

#### "Connection refused" on startup

Ensure all dependencies are running:

```bash
# Check PostgreSQL
docker exec oms-postgres pg_isready -U oms

# Check Redis
docker exec oms-redis redis-cli ping

# Check RabbitMQ
docker exec oms-rabbitmq rabbitmq-diagnostics check_port_connectivity
```

#### Rate Limiting (HTTP 429)

If you're getting 429 responses during normal use, the token bucket may need adjustment. Update in `.env`:

```env
OMS_RATE_LIMIT_CAPACITY=10000
OMS_RATE_LIMIT_REFILL_PER_SECOND=2000
```

#### Circuit Breaker Open (HTTP 503)

The circuit breaker opens after 50 failures. It will auto-recover after 30 seconds (half-open state). To reset manually, restart the application.

#### Optimistic Lock Conflicts

If you get "Optimistic lock conflict" errors, it means another request modified the order concurrently. Re-fetch the order to get the latest version and retry.

### 10.2 Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### 10.3 Viewing Logs

**Docker Compose:**
```bash
docker compose logs -f app
```

**Bare-metal:** Logs are printed to stdout.

### 10.4 RabbitMQ Management UI

Access the RabbitMQ management console at:

```
http://localhost:15672
```

- **Username:** guest
- **Password:** guest

Use this to monitor queue depth, consumer status, and message rates.

### 10.5 Resetting Everything

```bash
# Stop and remove all containers, volumes, and images
docker compose down -v

# Rebuild and start fresh
docker compose up --build -d
```

---

## Appendix A: Project Structure

```
oms/
├── __init__.py
├── main.py                          # FastAPI application entry point
├── openapi_spec.py                  # OpenAPI 3.0 specification
├── seed.py                          # Seed data script
├── domain/
│   ├── __init__.py
│   ├── enums.py                     # OrderStatus, PaymentStatus, etc.
│   ├── models.py                    # Pydantic domain models
│   └── state_machine.py             # Order state machine
├── controllers/
│   ├── __init__.py
│   ├── customer_controller.py       # Customer CRUD endpoints
│   ├── health_controller.py         # Health & metrics endpoints
│   ├── order_controller.py          # Order lifecycle endpoints
│   └── product_controller.py        # Product browse/search endpoints
├── services/
│   ├── __init__.py
│   ├── invoice_service.py           # Invoice business logic
│   ├── order_service.py             # Order business logic (core)
│   ├── payment_service.py           # Payment business logic
│   └── product_service.py           # Product business logic
├── repositories/
│   ├── __init__.py                  # BaseRepository (generic CRUD)
│   ├── customer_repo.py
│   ├── invoice_repo.py
│   ├── order_repo.py                # Optimistic-lock status updates
│   ├── payment_repo.py
│   └── product_repo.py              # Cache-aside integration
├── infrastructure/
│   ├── __init__.py
│   ├── cache.py                     # Redis cache-aside + idempotency
│   ├── circuit_breaker.py           # Async circuit breaker wrapper
│   ├── config.py                    # Pydantic settings (env-based)
│   ├── database.py                  # Async SQLAlchemy engine + session
│   ├── entities.py                  # SQLAlchemy ORM models
│   ├── metrics.py                   # Prometheus metric definitions
│   ├── queue.py                     # RabbitMQ producer/consumer
│   └── rate_limiter.py             # Token bucket rate limiter
├── middleware/
│   ├── __init__.py
│   ├── correlation_id.py            # X-Request-ID middleware
│   ├── logging_config.py            # Structured logging setup
│   └── metrics_middleware.py        # HTTP metrics recording
├── load_test/
│   ├── __init__.py
│   ├── locustfile.py                # Locust user classes
│   └── scenarios.py                 # Test scenario configurations
└── tests/
    ├── __init__.py
    └── test_state_machine.py        # Unit tests for domain layer
```

## Appendix B: Configuration Reference

All configuration is loaded from environment variables with the `OMS_` prefix, or from a `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_HOST` | `0.0.0.0` | Server bind address |
| `OMS_PORT` | `8000` | Server port |
| `OMS_WORKERS` | `4` | Number of Uvicorn workers |
| `OMS_DB_URL` | `postgresql+asyncpg://oms:oms@localhost:5432/oms` | PostgreSQL connection string |
| `OMS_DB_POOL_SIZE` | `16` | Database connection pool size |
| `OMS_DB_MAX_OVERFLOW` | `8` | Max overflow connections |
| `OMS_REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `OMS_PRODUCT_CACHE_TTL_SECONDS` | `60` | Product cache TTL (seconds) |
| `OMS_IDEMPOTENCY_TTL_SECONDS` | `3600` | Idempotency key TTL (seconds) |
| `OMS_RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection string |
| `OMS_QUEUE_NAME` | `oms_deferred_tasks` | Task queue name |
| `OMS_CONSUMER_CONCURRENCY` | `8` | Queue consumer concurrency |
| `OMS_RATE_LIMIT_CAPACITY` | `5000` | Token bucket capacity |
| `OMS_RATE_LIMIT_REFILL_PER_SECOND` | `1000` | Token refill rate |
| `OMS_CB_FAILURE_THRESHOLD` | `0.5` | Circuit breaker failure threshold |
| `OMS_CB_RECOVERY_TIMEOUT` | `30.0` | Circuit breaker recovery timeout (s) |
| `OMS_CB_HALF_OPEN_MAX_CALLS` | `3` | Half-open trial count |
| `OMS_METRICS_PORT` | `9090` | Metrics server port |

---

*© 2025 ChatDev — Order Management System v1.0.0*
