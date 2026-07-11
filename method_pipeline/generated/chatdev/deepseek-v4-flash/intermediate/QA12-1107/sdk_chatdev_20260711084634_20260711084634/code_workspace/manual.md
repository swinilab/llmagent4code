# Order Management System (OMS) — User Manual

**Version:** 1.0.0  
**Product Owner:** Chief Product Officer, ChatDev  
**Tech Stack:** Python 3.12, FastAPI, PostgreSQL 16, Redis 7, SQLAlchemy 2.0, asyncpg  
**License:** Proprietary — ChatDev Software

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Architecture at a Glance](#3-architecture-at-a-glance)
4. [Quick Start](#4-quick-start)
5. [API Reference](#5-api-reference)
6. [User Roles & Workflow](#6-user-roles--workflow)
7. [Key Features](#7-key-features)
8. [Performance & Reliability](#8-performance--reliability)
9. [Testing](#9-testing)
10. [Configuration Reference](#10-configuration-reference)
11. [Troubleshooting](#11-troubleshooting)
12. [FAQ](#12-faq)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that manages the complete order lifecycle — from customer checkout through payment processing, invoicing, shipping, and order closure. It is designed to handle high traffic volumes on a single-node deployment (up to 98 GB RAM, multi-core CPU) while meeting strict performance and reliability targets.

### Who Is This For?

| Role | What They Do |
|------|-------------|
| **Customer** | Browses products, places orders, pays invoices |
| **Order Staff** | Reviews orders, accepts/rejects, ships, closes |
| **Accountant** | Creates invoices, verifies payments |
| **System Admin** | Deploys, monitors, configures the system |

### What Problem Does It Solve?

E-commerce businesses need a reliable order processing pipeline that:
- Handles **2,000+ concurrent users** with sub-300ms checkout latency
- Survives **3x traffic spikes** without crashing
- Preserves **order state** across process crashes
- **Degrades gracefully** under extreme load (non-essential features turn off, checkout stays up)
- Enforces a **strict 7-step order workflow** with domain-level state machine validation

---

## 2. System Overview

### 2.1 Domain Model

The system is built around five core entities:

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Customer │────▶│  Order   │◀────│ Product  │
└──────────┘     └──────────┘     └──────────┘
                      │
              ┌───────┴───────┐
              ▼               ▼
          ┌────────┐     ┌──────────┐
          │Payment │     │ Invoice  │
          └────────┘     └──────────┘
```

**Customer** — id, name, address, phone, banking details, order history, role  
**Order** — id, customer ref, line items, amounts, status (state machine), timestamps, invoice ref, version (optimistic lock)  
**Product** — id, description, pricing (base + currency), stock/availability  
**Payment** — id, order ref, amount, timestamp, status, method  
**Invoice** — id, order ref, billing info, amounts, issue/due dates, status

### 2.2 Order State Machine

The order lifecycle follows a strict 7-step workflow enforced in the domain layer:

```
CREATED ──▶ ACCEPTED ──▶ INVOICED ──▶ PAID ──▶ SHIPPED ──▶ CLOSED
    │            │            │           │
    └──── CANCELLED ◀─────────┴───────────┘
```

**Allowed transitions (enforced by code):**

| Current Status | Can Transition To |
|---------------|-------------------|
| CREATED | ACCEPTED, CANCELLED |
| ACCEPTED | INVOICED, CANCELLED |
| INVOICED | PAID, CANCELLED |
| PAID | SHIPPED, CANCELLED |
| SHIPPED | CLOSED |
| CLOSED | *(none)* |
| CANCELLED | *(none)* |

### 2.3 The 7-Step Workflow

| Step | Action | Performed By | Endpoint | Status Change |
|------|--------|-------------|----------|---------------|
| 1 | Place order | Customer | `POST /api/v1/orders` | → CREATED |
| 2 | Review & accept | Order Staff | `POST /api/v1/orders/{id}/accept` | CREATED → ACCEPTED |
| 3 | Create invoice | Accountant | *(auto via background worker)* | ACCEPTED → INVOICED |
| 4 | Pay invoice | Customer | `POST /api/v1/orders/{id}/pay` | INVOICED → PAID |
| 5 | Verify payment | Accountant | `POST /api/v1/orders/{id}/verify-payment` | *(verification step)* |
| 6 | Ship order | Order Staff | `POST /api/v1/orders/{id}/ship` | PAID → SHIPPED |
| 7 | Close order | Order Staff | `POST /api/v1/orders/{id}/close` | SHIPPED → CLOSED |

**Important:** Steps 3 (invoice generation) is handled asynchronously by a background worker. Steps 5 (payment verification) is a verification step that does not change the order status but is required before shipping.

---

## 3. Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     HTTP Client (curl/Postman/App)          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (Uvicorn)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Controllers │  │   Services   │  │  Circuit Breaker │   │
│  │  (REST API)  │  │  (Business)  │  │  (NFR 2.1)       │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘   │
│         │                 │                                  │
│         ▼                 ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Repositories (Data Access)               │   │
│  │         Cache-Aside (Redis) + Optimistic Locking      │   │
│  └──────────┬───────────────────────────┬────────────────┘   │
│             │                           │                     │
└─────────────┼───────────────────────────┼─────────────────────┘
              │                           │
              ▼                           ▼
     ┌──────────────┐           ┌──────────────────┐
     │  PostgreSQL   │           │     Redis 7      │
     │  (ACID, Durable)│         │  (Cache + Streams)│
     └──────────────┘           └────────┬─────────┘
                                          │
                                          ▼
                              ┌──────────────────────┐
                              │  Background Worker   │
                              │  (Invoice Gen, Ship  │
                              │   Preparation)        │
                              └──────────────────────┘
```

### Technology Choices & Justification

| Component | Choice | Why |
|-----------|--------|-----|
| **Language** | Python 3.12 | Async/await native, rich ecosystem, FastAPI for high-throughput async I/O |
| **Web Framework** | FastAPI | Async-native, automatic OpenAPI docs, pydantic validation, high performance |
| **Database** | PostgreSQL 16 | ACID compliance for order durability, JSONB for flexible schemas, optimistic locking via version column |
| **Cache** | Redis 7 | Sub-millisecond reads for hot data, Streams for durable task queues, AOF persistence |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, well-tested, async support via asyncpg driver, connection pooling |
| **Task Queue** | Redis Streams | Built into Redis (no extra broker), at-least-once delivery, consumer groups, crash recovery via pending list |
| **Retry** | Tenacity | Exponential backoff with jitter, configurable per operation type |
| **Server** | Uvicorn | ASGI server, uvloop for maximum async performance |

---

## 4. Quick Start

### 4.1 Prerequisites

- **Docker** and **Docker Compose** (recommended)
- OR Python 3.12+, PostgreSQL 16, Redis 7 (for local development)

### 4.2 Docker Deployment (Recommended)

```bash
# 1. Clone the repository
cd oms

# 2. Start all services (PostgreSQL, Redis, App, Worker)
docker compose up -d

# 3. Verify everything is running
curl http://localhost:8000/health/live
# → {"status":"alive","uptime_seconds":5.23}

curl http://localhost:8000/health/ready
# → {"status":"ready","checks":{"database":"pass","cache":"pass"}}

# 4. View logs
docker compose logs -f app worker
```

### 4.3 Local Development Setup

```bash
# 1. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install uv
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL and Redis connection details

# 4. Initialize database
psql -U oms -d oms -f init.sql

# 5. Start the application
uvicorn oms.main:app --reload --host 0.0.0.0 --port 8000

# 6. In a separate terminal, start the background worker
python -c "from oms.worker import start_worker; import asyncio; asyncio.run(start_worker())"
```

### 4.4 Verify the Installation

```bash
# Check all health endpoints
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/circuits
curl http://localhost:8000/health/queue

# Open API documentation
open http://localhost:8000/docs   # Swagger UI
open http://localhost:8000/redoc  # ReDoc
```

---

## 5. API Reference

All API endpoints are versioned under `/api/v1/`. The full OpenAPI specification is available at `/openapi.json` or via the Swagger UI at `/docs`.

### 5.1 Health & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/live` | Liveness probe — returns 200 if process is running |
| GET | `/health/ready` | Readiness probe — checks DB and Redis connectivity |
| GET | `/health/circuits` | Returns state of all circuit breakers |
| GET | `/health/queue` | Returns backlog depth of all task queues |

### 5.2 Customer Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/customers` | Create a new customer |
| GET | `/api/v1/customers/{id}` | Get customer by ID |
| PATCH | `/api/v1/customers/{id}` | Update customer details |

**Example — Create a customer:**
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "phone": "+1-555-0100",
    "address": {
      "street": "123 Main St",
      "city": "Springfield",
      "state": "IL",
      "zip_code": "62701",
      "country": "US"
    }
  }'
```

### 5.3 Product Catalog

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/products` | Create a new product |
| GET | `/api/v1/products` | List all available products |
| GET | `/api/v1/products/{id}` | Get product by ID |
| PATCH | `/api/v1/products/{id}` | Update product details |

**Example — Create a product:**
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Headphones",
    "description": "Noise-cancelling Bluetooth headphones",
    "price_amount": 79.99,
    "price_currency": "USD",
    "stock": 100
  }'
```

### 5.4 Order Management (Core Workflow)

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | `/api/v1/orders` | Place a new order (checkout) | Customer |
| GET | `/api/v1/orders` | List orders (filter by `customer_id` or `status`) | All |
| GET | `/api/v1/orders/{id}` | Get order by ID | All |
| POST | `/api/v1/orders/{id}/accept` | Accept an order | Order Staff |
| POST | `/api/v1/orders/{id}/pay` | Pay for an order | Customer |
| POST | `/api/v1/orders/{id}/verify-payment` | Verify payment | Accountant |
| POST | `/api/v1/orders/{id}/ship` | Ship an order | Order Staff |
| POST | `/api/v1/orders/{id}/close` | Close a completed order | Order Staff |
| POST | `/api/v1/orders/{id}/cancel` | Cancel an order | Order Staff |

**Example — Complete 7-step workflow:**

```bash
# Step 1: Customer places an order
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<customer_id>",
    "items": [{"product_id": "<product_id>", "quantity": 2}]
  }'
# Response: order with status "CREATED"

# Step 2: Order Staff accepts the order
curl -X POST http://localhost:8000/api/v1/orders/<order_id>/accept
# Response: order with status "ACCEPTED"
# (Background worker automatically generates invoice → status becomes "INVOICED")

# Step 4: Customer pays the invoice
curl -X POST http://localhost:8000/api/v1/orders/<order_id>/pay \
  -H "Content-Type: application/json" \
  -d '{"amount": 159.98, "currency": "USD", "method": "CREDIT_CARD"}'
# Response: order with status "PAID"

# Step 5: Accountant verifies payment
curl -X POST http://localhost:8000/api/v1/orders/<order_id>/verify-payment
# Response: order with status "PAID" (verified)

# Step 6: Order Staff ships the order
curl -X POST http://localhost:8000/api/v1/orders/<order_id>/ship
# Response: order with status "SHIPPED"

# Step 7: Order Staff closes the order
curl -X POST http://localhost:8000/api/v1/orders/<order_id>/close
# Response: order with status "CLOSED"
```

### 5.5 Payment & Invoice Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/payments/{id}` | Get payment by ID |
| GET | `/api/v1/orders/{id}/payments` | Get all payments for an order |
| GET | `/api/v1/invoices/{id}` | Get invoice by ID |
| GET | `/api/v1/orders/{id}/invoices` | Get all invoices for an order |

---

## 6. User Roles & Workflow

### 6.1 Role-Based Operations

The system supports three roles (no authentication required — roles are assigned at customer creation):

| Role | Can Do |
|------|--------|
| **CUSTOMER** | Browse products, place orders, pay invoices |
| **ORDER_STAFF** | Accept orders, ship orders, close orders, cancel orders |
| **ACCOUNTANT** | Create invoices (auto), verify payments |

### 6.2 Complete Workflow Walkthrough

Here is a complete end-to-end example using `curl`:

```bash
# ============================================
# SETUP: Create test data
# ============================================

# Create a customer
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "phone": "+1-555-1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Customer ID: $CUSTOMER"

# Create a product
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Smart Watch", "price_amount": 199.99, "stock": 50}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PRODUCT"

# ============================================
# STEP 1: Customer places order
# ============================================
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\": \"$CUSTOMER\", \"items\": [{\"product_id\": \"$PRODUCT\", \"quantity\": 1}]}" | python3 -c "import sys,json; o=json.load(sys.stdin); print(o['id'])")
echo "Order ID: $ORDER (status: CREATED)"

# ============================================
# STEP 2: Order Staff accepts
# ============================================
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER/accept" | python3 -c "import sys,json; print('Status:', json.load(sys.stdin)['status'])"
# Wait a moment for the background worker to generate the invoice
sleep 2

# ============================================
# STEP 3: Invoice is auto-generated (by worker)
# ============================================
curl -s "http://localhost:8000/api/v1/orders/$ORDER" | python3 -c "import sys,json; o=json.load(sys.stdin); print('Status:', o['status'], '| Invoice:', o.get('invoice_ref'))"

# ============================================
# STEP 4: Customer pays
# ============================================
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER/pay" \
  -H "Content-Type: application/json" \
  -d '{"amount": 199.99, "currency": "USD", "method": "CREDIT_CARD"}' | python3 -c "import sys,json; print('Status:', json.load(sys.stdin)['status'])"

# ============================================
# STEP 5: Accountant verifies payment
# ============================================
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER/verify-payment" | python3 -c "import sys,json; print('Status:', json.load(sys.stdin)['status'])"

# ============================================
# STEP 6: Order Staff ships
# ============================================
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER/ship" | python3 -c "import sys,json; print('Status:', json.load(sys.stdin)['status'])"

# ============================================
# STEP 7: Order Staff closes
# ============================================
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER/close" | python3 -c "import sys,json; print('Status:', json.load(sys.stdin)['status'])"

echo "Order $ORDER completed successfully!"
```

---

## 7. Key Features

### 7.1 Redis-Backed Cache-Aside (NFR 1.1)

Hot data (products, customers) is cached in Redis for sub-millisecond reads:

```
Request → Check Redis → Hit? → Return cached data
                     → Miss? → Query PostgreSQL → Write to Redis → Return
```

**Cache TTLs:**
| Entity | TTL | Rationale |
|--------|-----|-----------|
| Product | 5 minutes | Changes infrequently |
| Customer | 10 minutes | Profile data is stable |
| Order | 2 minutes | Status changes frequently |
| Invoice | 5 minutes | Moderate change frequency |
| Payment | 2 minutes | Status changes frequently |

### 7.2 Connection Pooling (NFR 1.2)

Database connection pool is sized for the target hardware:

- **Pool size:** 20 connections (core pool)
- **Max overflow:** 10 connections (burst capacity)
- **Total max:** 30 concurrent DB connections
- **Pool pre-ping:** Verifies connections before use (NFR 2.2)
- **Pool recycle:** Every 3600 seconds

**Sizing rationale:** With 8+ CPU cores and SSD storage, the formula `(core_count × 2) + effective_spindle_count` gives ~20 connections. The overflow of 10 handles traffic spikes without over-saturating PostgreSQL.

### 7.3 Durable Task Queue with Admission Control (NFR 1.3, NFR 2.3)

Redis Streams provide at-least-once delivery with crash recovery:

- **Admission control:** If the stream backlog exceeds 10,000 messages, new enqueues are rejected (prevents unbounded memory growth)
- **Consumer groups:** Multiple workers can consume from the same stream
- **Pending list:** Messages that are delivered but not acknowledged remain in the pending list
- **Crash recovery:** On startup, the worker claims pending messages that have been idle for >30 seconds
- **Dead-lettering:** Messages delivered more than 3 times are automatically acknowledged (dead-lettered)

### 7.4 Circuit Breaker Pattern (NFR 2.1)

Non-essential features are protected by circuit breakers:

```
CLOSED (normal) → failures exceed threshold → OPEN (fail fast)
OPEN → after recovery timeout → HALF_OPEN (probe)
HALF_OPEN → success → CLOSED
HALF_OPEN → failure → OPEN
```

**Protected features:**
- Invoice history queries
- Payment history queries

When these circuits are OPEN, the system returns empty results instead of waiting for a failing dependency, ensuring the core checkout path remains available.

### 7.5 Retry with Exponential Backoff (NFR 2.2)

Transient errors (connection errors, timeouts) are automatically retried:

| Policy | Max Attempts | Min Wait | Max Wait | Used For |
|--------|-------------|----------|----------|----------|
| `checkout_retry_policy` | 2 | 100ms | 1s | Checkout (latency-critical) |
| `background_retry_policy` | 5 | 1s | 60s | Background tasks |

**Trade-off:** Retries add latency. For the latency-critical checkout path, we limit retries to 2 attempts with a short backoff. For non-critical background operations, we allow more retries.

### 7.6 Optimistic Locking (NFR 2.3)

Every entity has a `version` field that is incremented on each update. When two concurrent updates try to modify the same entity, the second one fails with a `ConcurrencyConflictError` (HTTP 409). This prevents lost updates and ensures data consistency.

### 7.7 Health Endpoints (NFR 2.2)

Four health endpoints provide comprehensive monitoring:

- **`/health/live`** — Simple liveness probe (always returns 200 if process is running)
- **`/health/ready`** — Readiness probe (checks PostgreSQL and Redis connectivity)
- **`/health/circuits`** — Returns state of all circuit breakers
- **`/health/queue`** — Returns backlog depth of all task queues

---

## 8. Performance & Reliability

### 8.1 Performance Targets

| Metric | Target | Measured At |
|--------|--------|-------------|
| Checkout p95 latency | ≤ 300ms | 2,000 concurrent virtual users |
| Browse/search p95 latency | ≤ 150ms | 2,000 concurrent virtual users |
| Concurrent active sessions | 5,000 | Target hardware (8+ cores, 98GB RAM) |
| Average queueing time | < 50ms | Under sustained load |
| Traffic spike absorption | 3x within 60s | No crashes, no unbounded memory growth |

### 8.2 Reliability Guarantees

| Scenario | Behavior |
|----------|----------|
| DB disconnect | Automatic reconnection via `pool_pre_ping` and retry logic |
| Process crash | Pending orders recovered via Redis Streams pending list |
| Traffic spike | Admission control rejects excess queue messages, circuit breakers degrade non-essential features |
| Resource contention | Non-essential features degrade, core checkout remains available |

### 8.3 Performance vs. Reliability Trade-offs

| Mechanism | Performance Impact | Reliability Benefit |
|-----------|-------------------|-------------------|
| Retry logic | Adds latency (especially on checkout path) | Ensures transient failures don't cause request loss |
| Circuit breaker | May return stale/empty data | Prevents cascading failures |
| Optimistic locking | Requires version check on every write | Prevents data corruption from concurrent updates |
| Cache-aside | Cache miss adds one extra Redis round-trip | Reduces DB load by 10-100x for hot data |
| Durable queue | Adds Redis write latency for each enqueue | Ensures no order state is lost on crash |

---

## 9. Testing

### 9.1 Load Testing

The load test suite (`load_test.py`) performs four tests:

```bash
# Run all load tests (requires running application)
python load_test.py
```

**Test scenarios:**

| Test | Description | Pass/Fail Criteria |
|------|-------------|-------------------|
| 1. Baseline Checkout | 100 concurrent users, 30 seconds | p95 ≤ 300ms |
| 2. Browse Products | 200 concurrent users, 30 seconds | p95 ≤ 150ms |
| 3. Sustained Concurrency | 2,000 concurrent users, 60 seconds | Error rate < 1% |
| 4. Spike Test | 3x traffic spike within 60 seconds | Error rate < 5% |

**Metrics collected:**
- p50/p95/p99 latency (ms)
- Throughput (requests/second)
- Error rate (%)
- System health status

### 9.2 Reliability Testing

The reliability test suite (`reliability_test.py`) performs three tests:

```bash
# Run all reliability tests (requires running application)
python reliability_test.py
```

**Test 1: Degradation (NFR 2.1)**
- Simulates load and verifies non-essential features degrade
- Checks circuit breaker states via `/health/circuits`
- Verifies checkout remains available after degradation

**Test 2: Recovery (NFR 2.2)**
- Verifies health endpoints detect DB connectivity
- Checks that `pool_pre_ping` and retry logic are operational
- Verifies liveness and readiness probes work correctly

**Test 3: State Preservation (NFR 2.3)**
- Creates an order and verifies it's persisted
- Accepts the order and verifies the state transition is durable
- Checks optimistic locking (version increment)
- Verifies the order can be retrieved after a simulated crash

---

## 10. Configuration Reference

All configuration is via environment variables (see `oms/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://oms:oms@localhost:5432/oms` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `4` | Number of Uvicorn workers |
| `DEBUG` | `false` | Enable debug mode |
| `DB_POOL_SIZE` | `20` | Database connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `CB_FAILURE_THRESHOLD` | `5` | Circuit breaker failure threshold |
| `CB_RECOVERY_TIMEOUT` | `30.0` | Circuit breaker recovery timeout (seconds) |
| `MAX_QUEUE_BACKLOG` | `10000` | Maximum queue backlog before admission control |
| `RETRY_ATTEMPTS` | `3` | Retry attempts for transient failures |
| `RETRY_MIN_WAIT` | `0.5` | Minimum retry wait (seconds) |
| `RETRY_MAX_WAIT` | `30.0` | Maximum retry wait (seconds) |

### Docker Compose Resource Limits

| Service | CPU Limit | Memory Limit |
|---------|-----------|-------------|
| PostgreSQL | 2 CPUs | 2 GB |
| Redis | 1 CPU | 1 GB |
| App | 4 CPUs | 4 GB |
| Worker | 2 CPUs | 2 GB |

---

## 11. Troubleshooting

### Common Issues

**Problem: Application won't start**
```
Error: connection to server at "localhost" (127.0.0.1), port 5432 failed
```
→ Ensure PostgreSQL is running: `docker compose up -d postgres`

**Problem: Redis connection refused**
```
Error: Error -2 connecting to redis://localhost:6379/0
```
→ Ensure Redis is running: `docker compose up -d redis`

**Problem: Order state transition fails**
```
HTTP 409: Cannot transition from PAID to ACCEPTED
```
→ Orders follow a strict state machine. You cannot skip steps. Follow the 7-step workflow in order.

**Problem: Background worker not processing tasks**
```
No messages found in stream "orders:invoice"
```
→ Check the worker logs: `docker compose logs worker`. Ensure the worker is running and connected to Redis.

**Problem: Circuit breaker is OPEN**
```
Circuit breaker 'invoice_history' is open — call rejected
```
→ This is normal under load. The circuit will automatically close after the recovery timeout (default: 30 seconds). Check `/health/circuits` for current states.

**Problem: Queue backlog is growing**
```
Stream orders:invoice backlog 12000 >= 10000 — rejecting message
```
→ The admission control is working. Scale up the worker or increase `MAX_QUEUE_BACKLOG` if this is expected traffic.

### Health Check Diagnostics

```bash
# Check if the process is alive
curl http://localhost:8000/health/live

# Check if dependencies are healthy
curl http://localhost:8000/health/ready

# Check circuit breaker states
curl http://localhost:8000/health/circuits

# Check queue backlog depths
curl http://localhost:8000/health/queue
```

---

## 12. FAQ

**Q: Can I run multiple application instances?**  
A: Yes. The application is stateless. Run behind a load balancer for horizontal scaling. Each instance should use `workers=1` to avoid competing consumers on Redis Streams.

**Q: How do I run dedicated worker containers?**  
A: Set `WORKER_MODE=true` in the environment. This prevents the embedded worker from starting in the app container. Run separate containers with the worker command.

**Q: What happens if Redis goes down?**  
A: The cache becomes unavailable (reads go directly to PostgreSQL). The task queue becomes unavailable (new async tasks are rejected). The application continues to serve requests, but with reduced performance.

**Q: What happens if PostgreSQL goes down?**  
A: The readiness probe returns 503. All write operations fail. Read operations that hit the cache may still succeed. The circuit breaker may open for non-essential features.

**Q: How is data backed up?**  
A: PostgreSQL data is stored in a Docker volume (`pgdata`). Redis data is stored in `redisdata` with AOF persistence (appendfsync every second). Regular backups should be configured for production.

**Q: Can I change the database pool size?**  
A: Yes. Set `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` environment variables. The formula `pool_size = (core_count × 2) + effective_spindle_count` is a good starting point.

**Q: How do I reset the database?**  
A: Stop the containers, remove the volumes, and restart:
```bash
docker compose down -v
docker compose up -d
```

---

*For additional support, contact the ChatDev Product Team.*  
*© 2024 ChatDev Software — Changing the digital world through programming.*
