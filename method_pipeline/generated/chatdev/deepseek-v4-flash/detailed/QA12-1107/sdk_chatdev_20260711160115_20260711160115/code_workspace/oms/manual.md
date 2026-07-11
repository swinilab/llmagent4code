# Order Management System (OMS) — User Manual

> **Version:** 1.0.0  
> **Technology Stack:** Python 3.12 + FastAPI (async) | PostgreSQL 16 | Redis 7 | RabbitMQ 3  
> **Target Hardware:** 16-core CPU, 98GB RAM  
> **Role:** Chief Product Officer, ChatDev

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Quick Start Guide](#3-quick-start-guide)
4. [API Reference](#4-api-reference)
5. [User Roles & Workflows](#5-user-roles--workflows)
6. [Order Lifecycle & State Machine](#6-order-lifecycle--state-machine)
7. [Installation & Deployment](#7-installation--deployment)
8. [Configuration Reference](#8-configuration-reference)
9. [Performance Testing](#9-performance-testing)
10. [Reliability Testing](#10-reliability-testing)
11. [Monitoring & Health Checks](#11-monitoring--health-checks)
12. [Troubleshooting](#12-troubleshooting)
13. [Architecture Deep Dive](#13-architecture-deep-dive)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that serves the complete order-to-closure workflow:

```
Customer Ordering → Payment Processing → Invoicing → Shipping → Closure
```

It is designed to handle **5,000 concurrent active sessions** with **p95 checkout latency ≤ 300ms** and **p99 ≤ 600ms**, while providing **graceful degradation**, **automatic fault recovery**, and **state preservation** across process crashes.

### Who Is This For?

| Role | What They Do |
|------|-------------|
| **Customer** | Browse products, place orders, pay invoices |
| **Order Staff** | Review, accept, ship, and close orders |
| **Accountant** | Create invoices, verify payments |

### Key Capabilities

- **RESTful API** with versioned endpoints (`/api/v1/`)
- **Automatic OpenAPI documentation** at `/docs` (Swagger UI) and `/redoc` (ReDoc)
- **Redis-backed cache-aside** for sub-150ms product searches
- **Token-bucket rate limiting** (5,000 req/s sustained, 10,000 burst)
- **Circuit breaker** for non-essential features (recommendations)
- **Transactional Outbox** pattern for crash-safe state transitions
- **Health checks** with liveness, readiness, and dependency probes
- **Structured JSON logging** to stdout
- **Metrics endpoint** at `/metrics` for load-test instrumentation

---

## 2. System Overview

### Architecture Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Customer  │     │ Order Staff │     │ Accountant  │
│   (Browser) │     │   (Browser) │     │   (Browser) │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │  FastAPI    │  ←── Rate Limiter (Token Bucket)
                    │  (8 async   │  ←── Circuit Breaker (non-essential)
                    │  workers)   │  ←── Cache-Aside (Redis)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼────┐ ┌─────▼─────┐
        │PostgreSQL│ │  Redis  │ │ RabbitMQ  │
        │   (DB)   │ │ (Cache) │ │  (Queue)  │
        └──────────┘ └─────────┘ └───────────┘
```

### Component Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Server** | Python 3.12 + FastAPI (async) | REST endpoints, business logic, orchestration |
| **Database** | PostgreSQL 16 + asyncpg | ACID-compliant durable storage |
| **Cache** | Redis 7 (allkeys-lru) | Cache-aside for hot reads, rate limiter state, circuit breaker state |
| **Message Queue** | RabbitMQ 3 + aio-pika | Deferrable work, transactional outbox delivery |
| **Async Runtime** | uvloop + httptools | High-performance async I/O |
| **Containerization** | Docker + Docker Compose | Local deployment |

---

## 3. Quick Start Guide

### Prerequisites

- **Docker** and **Docker Compose** (recommended)
- OR **Python 3.12+**, **PostgreSQL 16+**, **Redis 7+**, **RabbitMQ 3+** (bare-metal)
- At least **8GB RAM** available for the full stack

### Option A: Docker Compose (Recommended)

```bash
# 1. Navigate to the project
cd oms

# 2. Start all services
docker compose -f deploy/docker-compose.yml up -d

# 3. Verify all services are healthy
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"...","checks":{"database":"up","redis":"up","rabbitmq":"up"}}

# 4. Seed test data
python tests/seed_data.py

# 5. Open the API documentation
open http://localhost:8000/docs
```

### Option B: Bare-Metal Deployment

```bash
# 1. Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql redis-server rabbitmq-server

# 2. Setup Python environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure PostgreSQL
sudo -u postgres createuser oms -P   # password: oms
sudo -u postgres createdb oms -O oms

# 4. Start services
sudo systemctl start postgresql redis rabbitmq-server

# 5. Run the application
uvicorn oms.main:app --host 0.0.0.0 --port 8000 --workers 8 --loop uvloop --http httptools
```

### Verify It Works

```bash
# Health check
curl http://localhost:8000/health

# Create a customer
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","address":"123 Main St","phone":"+1-555-0101","banking_details":"ACC-001"}'

# List products (after seeding)
curl http://localhost:8000/api/v1/products

# View API docs
open http://localhost:8000/docs
```

---

## 4. API Reference

### Endpoint Summary

| Method | Path | Description | Criticality | Latency Budget |
|--------|------|-------------|-------------|---------------|
| `POST` | `/api/v1/customers` | Create customer | Core | Relaxed |
| `GET` | `/api/v1/customers` | List customers | Core | Relaxed |
| `GET` | `/api/v1/customers/{id}` | Get customer | Core | Relaxed |
| `POST` | `/api/v1/products` | Create product | Core | Relaxed |
| `GET` | `/api/v1/products` | List/search products | **Core** | **p95 ≤ 150ms** |
| `GET` | `/api/v1/products/{id}` | Get product | **Core** | **p95 ≤ 150ms** |
| `POST` | `/api/v1/orders` | **Place order (Step 1)** | **Core** | **p95 ≤ 300ms** |
| `GET` | `/api/v1/orders` | List orders | Core | Relaxed |
| `GET` | `/api/v1/orders/{id}` | Get order | Core | Relaxed |
| `POST` | `/api/v1/orders/{id}/accept` | **Accept order (Step 2)** | Core | Relaxed |
| `POST` | `/api/v1/orders/{id}/invoice` | **Invoice order (Step 3)** | Core | Relaxed |
| `POST` | `/api/v1/orders/{id}/pay` | **Pay order (Step 4)** | **Core** | **p95 ≤ 300ms** |
| `GET` | `/api/v1/orders/{id}/payment` | **Verify payment (Step 5)** | Core | Relaxed |
| `POST` | `/api/v1/orders/{id}/ship` | **Ship order (Step 6)** | Core | Relaxed |
| `POST` | `/api/v1/orders/{id}/close` | **Close order (Step 7)** | Core | Relaxed |
| `POST` | `/api/v1/orders/{id}/cancel` | Cancel order | Core | Relaxed |
| `GET` | `/api/v1/recommendations/{id}` | Recommendations | **Non-essential** | Relaxed |
| `GET` | `/health` | Full health check | Monitoring | — |
| `GET` | `/health/ready` | Readiness probe | Monitoring | — |
| `GET` | `/health/live` | Liveness probe | Monitoring | — |
| `GET` | `/metrics` | Internal metrics | Monitoring | — |

### Complete Workflow Example

```bash
# ===== STEP 1: Customer places order =====

# Create a customer
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice Johnson","address":"123 Main St","phone":"+1-555-0101","banking_details":"ACC-001"}' | jq .
# → {"id":"uuid-1","name":"Alice Johnson",...}

# Create a product
curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Wireless Mouse","description":"Ergonomic mouse","base_price":29.99,"stock_available":500}' | jq .
# → {"id":"uuid-2","name":"Wireless Mouse",...}

# Place an order
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"uuid-1","line_items":[{"product_id":"uuid-2","quantity":2}]}' | jq .
# → {"id":"order-uuid","status":"CREATED","version":1,...}

# ===== STEP 2: Order Staff accepts =====
curl -s -X POST http://localhost:8000/api/v1/orders/order-uuid/accept \
  -H "Content-Type: application/json" \
  -H "X-User-Role: ORDER_STAFF" \
  -d '{"version":1}' | jq .
# → {"status":"ACCEPTED","version":2,...}

# ===== STEP 3: Accountant creates invoice =====
curl -s -X POST http://localhost:8000/api/v1/orders/order-uuid/invoice \
  -H "Content-Type: application/json" \
  -H "X-User-Role: ACCOUNTANT" \
  -d '{"version":2,"billing_address":"123 Main St, Springfield"}' | jq .
# → {"invoice_id":"inv-uuid","order_id":"order-uuid","total":"59.98"}

# ===== STEP 4: Customer pays =====
curl -s -X POST http://localhost:8000/api/v1/orders/order-uuid/pay \
  -H "Content-Type: application/json" \
  -d '{"amount":59.98,"method":"CREDIT_CARD","idempotency_key":"pay-order-uuid-001"}' | jq .
# → {"payment_id":"pay-uuid","order_id":"order-uuid","status":"COMPLETED"}

# ===== STEP 5: Accountant verifies payment =====
curl -s http://localhost:8000/api/v1/orders/order-uuid/payment | jq .
# → {"payment_id":"pay-uuid","order_id":"order-uuid","status":"COMPLETED","amount":"59.98",...}

# ===== STEP 6: Order Staff ships =====
curl -s -X POST http://localhost:8000/api/v1/orders/order-uuid/ship \
  -H "Content-Type: application/json" \
  -H "X-User-Role: ORDER_STAFF" \
  -d '{"version":3}' | jq .
# → {"status":"SHIPPED","version":4,...}

# ===== STEP 7: Order Staff closes =====
curl -s -X POST http://localhost:8000/api/v1/orders/order-uuid/close \
  -H "Content-Type: application/json" \
  -H "X-User-Role: ORDER_STAFF" \
  -d '{"version":4}' | jq .
# → {"status":"CLOSED","version":5,...}
```

### Idempotent Payment

Payments are idempotent — submitting the same `idempotency_key` twice returns the same result without double-charging:

```bash
# First call — processes payment
curl -s -X POST http://localhost:8000/api/v1/orders/order-uuid/pay \
  -H "Content-Type: application/json" \
  -d '{"amount":59.98,"method":"CREDIT_CARD","idempotency_key":"unique-key-123"}' | jq .
# → {"payment_id":"pay-uuid","status":"COMPLETED","idempotent":false}

# Second call with same key — returns cached result
curl -s -X POST http://localhost:8000/api/v1/orders/order-uuid/pay \
  -H "Content-Type: application/json" \
  -d '{"amount":59.98,"method":"CREDIT_CARD","idempotency_key":"unique-key-123"}' | jq .
# → {"payment_id":"pay-uuid","status":"COMPLETED","idempotent":true}
```

### Role-Based Access

The `X-User-Role` header controls authorization (no authentication required per spec):

| Header Value | Allowed Actions |
|-------------|----------------|
| `CUSTOMER` (default) | Create orders, pay orders, cancel own orders |
| `ORDER_STAFF` | Accept orders, ship orders, close orders |
| `ACCOUNTANT` | Accept orders, create invoices, verify payments |

```bash
# Order Staff accepting an order
curl -X POST ... -H "X-User-Role: ORDER_STAFF" -d '{"version":1}'

# Accountant creating an invoice
curl -X POST ... -H "X-User-Role: ACCOUNTANT" -d '{"version":2,"billing_address":"..."}'
```

---

## 5. User Roles & Workflows

### Role: Customer

**What they can do:**
- Browse and search products
- Place orders
- Pay invoices
- Cancel orders (if not yet shipped)
- View their order history

**Typical flow:**
```
Browse Products → Place Order → Pay Invoice → Track Order Status
```

### Role: Order Staff

**What they can do:**
- View all orders
- Accept pending orders
- Ship paid orders
- Close completed orders

**Typical flow:**
```
Review New Orders → Accept → Ship Paid Orders → Close Completed
```

### Role: Accountant

**What they can do:**
- View all orders
- Accept pending orders
- Create invoices for accepted orders
- Verify payments

**Typical flow:**
```
Review Accepted Orders → Create Invoice → Verify Payments
```

---

## 6. Order Lifecycle & State Machine

### State Diagram

```
                    ┌─────────┐
                    │ CREATED │
                    └────┬────┘
                         │ accept
                    ┌────▼─────┐
                    │ ACCEPTED │
                    └────┬─────┘
                         │ invoice
                    ┌─────▼──────┐
                    │  INVOICED  │
                    └─────┬──────┘
                         │ pay
                    ┌────▼───┐
                    │  PAID  │
                    └────┬───┘
                         │ ship
                    ┌─────▼──────┐
                    │  SHIPPED   │
                    └─────┬──────┘
                         │ close
                    ┌───────▼──────┐
                    │    CLOSED    │  ← Terminal (success)
                    └──────────────┘

  CANCELLED (terminal exception state)
  ↑         ↑         ↑         ↑
  │ cancel  │ cancel  │ cancel  │ cancel
  CREATED  ACCEPTED  INVOICED   PAID
```

### State Transition Table

| From | Event | To | Guard | Persistence |
|------|-------|----|-------|-------------|
| `CREATED` | `accept` | `ACCEPTED` | Role = ORDER_STAFF or ACCOUNTANT | Synchronous (DB write before response) |
| `ACCEPTED` | `invoice` | `INVOICED` | Role = ACCOUNTANT | Synchronous |
| `INVOICED` | `pay` | `PAID` | Payment verified, idempotent | Synchronous (with `FOR UPDATE` lock) |
| `PAID` | `ship` | `SHIPPED` | Role = ORDER_STAFF | Synchronous |
| `SHIPPED` | `close` | `CLOSED` | Role = ORDER_STAFF | Synchronous |
| `CREATED` | `cancel` | `CANCELLED` | Not CLOSED or SHIPPED | Synchronous (restores stock) |
| `ACCEPTED` | `cancel` | `CANCELLED` | Not CLOSED or SHIPPED | Synchronous |
| `INVOICED` | `cancel` | `CANCELLED` | Not CLOSED or SHIPPED | Synchronous |
| `PAID` | `cancel` | `CANCELLED` | Not CLOSED or SHIPPED | Synchronous |

**Key rules:**
- All transitions are **persisted synchronously** (DB write before HTTP response)
- `CANCELLED` is a **terminal exception state** — no transitions out of it
- `SHIPPED` and `CLOSED` cannot be cancelled
- Cancelling an order **restores product stock** automatically
- The `version` field implements **optimistic locking** to prevent concurrent state conflicts

---

## 7. Installation & Deployment

### Docker Compose (Development/Production)

The `deploy/docker-compose.yml` file defines all four services with resource limits:

| Service | CPU Limit | Memory Limit | Purpose |
|---------|-----------|-------------|---------|
| `postgres` | 2 CPUs | 2GB | Database |
| `redis` | 1 CPU | 1GB | Cache & rate limiter |
| `rabbitmq` | 1 CPU | 1GB | Message queue |
| `oms-api` | 4 CPUs | 4GB | API server (8 workers) |

```bash
# Start everything
docker compose -f deploy/docker-compose.yml up -d

# View logs
docker compose -f deploy/docker-compose.yml logs -f oms-api

# Stop everything
docker compose -f deploy/docker-compose.yml down

# Reset data (delete volumes)
docker compose -f deploy/docker-compose.yml down -v
```

### Bare-Metal with systemd

1. **Install the application:**
```bash
sudo mkdir -p /opt/oms
sudo cp -r . /opt/oms/
cd /opt/oms
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Install the systemd service:**
```bash
sudo cp deploy/oms.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oms
sudo systemctl start oms
sudo systemctl status oms
```

3. **Verify:**
```bash
journalctl -u oms -f  # Follow logs
curl http://localhost:8000/health
```

### Resource Sizing Justification

**Target Hardware:** 16-core CPU, 98GB RAM

**Pool Sizing Formulas (NFR 1.2):**

| Resource | Formula | Calculation | Result |
|----------|---------|-------------|--------|
| **Uvicorn Workers** | `CPU_CORES × 0.5` | `16 × 0.5` | **8 async workers** |
| **DB Connection Pool** | `Tn × (Cm - 1) + 1` | `8 × (2 - 1) + 1 = 9` → rounded | **20 base + 10 overflow = 30 max** |
| **Redis Pool** | `Workers × 2` | `8 × 2` | **16 connections** |
| **Rate Limiter** | Sustained throughput | 5,000 tokens/s refill | **10,000 burst** |
| **Queue Capacity** | Bounded | 10,000 messages | **Drop oldest on overflow** |

---

## 8. Configuration Reference

All configuration is via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://oms:oms@localhost:5432/oms` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection string |
| `APP_HOST` | `0.0.0.0` | Bind address |
| `APP_PORT` | `8000` | HTTP port |
| `WORKERS` | `8` | Number of uvicorn workers |
| `DEBUG` | `false` | Enable debug logging |
| `RATE_LIMIT_REFILL_RATE` | `5000.0` | Token bucket refill (tokens/s) |
| `RATE_LIMIT_BURST` | `10000` | Token bucket burst capacity |
| `CB_FAILURE_THRESHOLD` | `5` | Circuit breaker opens after N failures |
| `CB_SUCCESS_THRESHOLD` | `3` | Circuit breaker closes after N successes |
| `CB_OPEN_DURATION_MS` | `30000` | How long circuit stays open (ms) |
| `CB_TIMEOUT_SECONDS` | `5.0` | Timeout for protected downstream calls |
| `CACHE_TTL_PRODUCTS` | `60` | Product cache TTL (seconds) |
| `CACHE_TTL_ORDERS` | `30` | Order cache TTL (seconds) |
| `QUEUE_MAX_SIZE` | `10000` | Bounded queue capacity |
| `QUEUE_WORKER_COUNT` | `4` | Background worker count |
| `RETRY_MAX_ATTEMPTS` | `3` | Max retry attempts for transient errors |
| `RETRY_BASE_DELAY_MS` | `100` | Base delay for exponential backoff (ms) |

Create a `.env` file in the project root:

```bash
DATABASE_URL=postgresql+asyncpg://oms:oms@localhost:5432/oms
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
APP_HOST=0.0.0.0
APP_PORT=8000
WORKERS=8
```

---

## 9. Performance Testing

### Load Test Tool: Locust

The load test plan is defined in `tests/locustfile.py` with three scenarios:

### Scenario 1: Baseline (500 users)

```bash
locust -f tests/locustfile.py \
  --host http://localhost:8000 \
  --users 500 \
  --spawn-rate 10 \
  --run-time 15m
```

**Pass criteria:**
- Checkout p95 ≤ 300ms, p99 ≤ 600ms
- Product search p95 ≤ 150ms
- Error rate < 1%
- Zero 5xx errors

### Scenario 2: Sustained 5,000 Sessions

```bash
locust -f tests/locustfile.py \
  --host http://localhost:8000 \
  --users 5000 \
  --spawn-rate 50 \
  --run-time 20m
```

**Pass criteria (NFR 1.2):**
- Average queueing time < 50ms
- CPU utilization 60–85% at peak
- Zero crashes or OOM
- All latency targets met

### Scenario 3: 3x Spike (1,500 → 4,500 over 60s)

```bash
locust -f tests/locustfile.py \
  --host http://localhost:8000 \
  --users 1500 \
  --spawn-rate 25 \
  --run-time 5m
# Then manually increase to 4500 users
```

**Pass criteria (NFR 1.3):**
- Zero crashes
- No unbounded memory growth
- No silent request loss
- Queue depth < 10,000
- Circuit-breaker transitions logged

### Monitoring During Tests

```bash
# Watch metrics in real-time
watch -n 1 'curl -s http://localhost:8000/metrics | jq .'

# Watch health
watch -n 1 'curl -s http://localhost:8000/health | jq .'

# Watch CPU
top -p $(pgrep -f uvicorn) -d 1

# Watch Docker stats
docker stats
```

### Metrics Endpoint

```json
{
  "rate_limiter": {
    "available_tokens": 8500,
    "refill_rate": 5000.0,
    "burst": 10000
  },
  "circuit_breakers": [
    {
      "name": "recommendations",
      "state": "CLOSED",
      "failure_count": 0,
      "success_count": 0
    }
  ]
}
```

---

## 10. Reliability Testing

### Run All Reliability Tests

```bash
python tests/test_reliability.py
```

### Test 1: Degradation Test (NFR 2.1)

**What it tests:** Under extreme load, non-essential features (recommendations) gracefully degrade while core checkout remains available.

**How to run manually:**
```bash
# 1. Send burst of requests to recommendations
for i in {1..50}; do
  curl -s http://localhost:8000/api/v1/recommendations/$CUSTOMER_ID &
done
wait

# 2. Verify core checkout still works
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"...","line_items":[{"product_id":"...","quantity":1}]}'
```

**Pass criteria:**
- Core checkout returns HTTP 200/201
- Recommendations return fallback (generic "Popular Item" responses) or circuit breaker opens

### Test 2: Recovery Test (NFR 2.2)

**What it tests:** The system auto-recovers from transient DB failures without manual restart.

**How to run manually:**
```bash
# 1. Verify normal operation
curl http://localhost:8000/health

# 2. Simulate DB failure (block port 5432)
sudo iptables -A INPUT -p tcp --dport 5432 -j DROP

# 3. Observe health endpoint reports degraded
curl http://localhost:8000/health
# → {"status":"degraded","checks":{"database":"down",...}}

# 4. Restore DB access
sudo iptables -D INPUT -p tcp --dport 5432 -j DROP

# 5. Verify auto-recovery
curl http://localhost:8000/health
# → {"status":"healthy","checks":{"database":"up",...}}
```

**Pass criteria:**
- Errors spike briefly then auto-recover
- No manual restart required
- Health endpoint correctly reports degraded → up

### Test 3: State Preservation Test (NFR 2.3)

**What it tests:** After a process crash, all committed transactions survive and in-flight orders can be recovered.

**How to run manually:**
```bash
# 1. Create an order
ORDER_ID=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"...","line_items":[{"product_id":"...","quantity":1}]}' | jq -r '.id')

# 2. Force-kill the process
kill -9 $(pgrep -f uvicorn)

# 3. Restart the service
docker compose -f deploy/docker-compose.yml up -d oms-api

# 4. Verify the order survived
curl http://localhost:8000/api/v1/orders/$ORDER_ID
# → Should return the order with status "CREATED"
```

**Pass criteria:**
- All committed transactions survive the crash
- In-flight orders are logged during startup recovery
- Outbox entries are re-published on restart

---

## 11. Monitoring & Health Checks

### Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|------------------|
| `GET /health` | Full health check (DB, Redis, RabbitMQ) | `{"status":"healthy","checks":{"database":"up","redis":"up","rabbitmq":"up"}}` |
| `GET /health/ready` | Readiness probe (Kubernetes/Docker) | `{"status":"ready"}` |
| `GET /health/live` | Liveness probe | `{"status":"alive"}` |

### Metrics Endpoint

`GET /metrics` returns:
- Rate limiter state (available tokens, refill rate, burst)
- Circuit breaker states (CLOSED/OPEN/HALF_OPEN, failure/success counts)

### Logging

All logs are structured JSON to stdout:

```json
{"timestamp":"2025-07-11T15:30:00.123Z","level":"INFO","logger":"oms","message":"POST /api/v1/orders -> 201 (45.2ms)"}
```

### Docker Health Check

The Dockerfile includes a built-in health check:
```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health/live').raise_for_status()"
```

---

## 12. Troubleshooting

### Common Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| `Connection refused` on startup | PostgreSQL not running | `docker compose up -d postgres` or `sudo systemctl start postgresql` |
| `429 Too Many Requests` | Rate limit exceeded | Wait for token bucket to refill (1s) or increase `RATE_LIMIT_REFILL_RATE` |
| `Optimistic lock conflict` | Concurrent order modification | Retry the request with the latest `version` from `GET /api/v1/orders/{id}` |
| `Role not authorized` | Wrong `X-User-Role` header | Use `ORDER_STAFF` or `ACCOUNTANT` as appropriate |
| `Insufficient stock` | Product out of stock | Check `stock_available` via `GET /api/v1/products/{id}` |
| Circuit breaker OPEN | Downstream service failing | Check `/metrics` for circuit breaker state; wait 30s for auto-recovery |
| Health shows `degraded` | One or more dependencies down | Check individual component status in health response |

### Checking Logs

```bash
# Docker
docker compose -f deploy/docker-compose.yml logs -f oms-api

# systemd
journalctl -u oms -f

# Direct (if running in terminal)
# Logs are printed to stdout
```

### Resetting the Database

```bash
# Docker: delete volumes and restart
docker compose -f deploy/docker-compose.yml down -v
docker compose -f deploy/docker-compose.yml up -d

# Bare-metal: drop and recreate
sudo -u postgres psql -c "DROP DATABASE oms;"
sudo -u postgres psql -c "CREATE DATABASE oms OWNER oms;"
# Restart the app to recreate tables
```

---

## 13. Architecture Deep Dive

### Why Python + FastAPI?

**Decision:** Python 3.12 with FastAPI (async)

**Rationale:**
- The workload is **I/O-bound** (DB, cache, queue calls) — Python's async model excels here
- FastAPI provides **automatic OpenAPI generation** (satisfies API definition requirement)
- **8 async workers** handle 5,000 concurrent sessions via cooperative multitasking
- uvloop provides ~2x throughput improvement over asyncio's default event loop

**Trade-off:** Python's GIL limits CPU-bound parallelism, but the OMS workload is predominantly I/O-bound.

### Why PostgreSQL?

**Decision:** PostgreSQL 16 with SQLAlchemy 2.0 (async) + asyncpg

**Rationale:**
- Full ACID compliance for order state transitions
- `SELECT ... FOR UPDATE` enables pessimistic locking for stock decrement and payment idempotency
- Connection pool sized at 20 (base) + 10 (overflow) = 30 max connections

### Why Redis?

**Decision:** Redis 7 with allkeys-lru eviction

**Rationale:**
- Cache-aside pattern for sub-150ms product searches
- Shared state for token-bucket rate limiter across 8 workers
- Shared state for circuit breakers across 8 workers
- Connection pool: 16 connections (8 workers × 2)

### Why RabbitMQ?

**Decision:** RabbitMQ 3 with aio-pika

**Rationale:**
- Transactional Outbox pattern: events written to `order_outbox` table in same DB transaction
- Background processor polls and forwards to RabbitMQ
- Durable queues with persistent messages
- Dead-letter exchange for failed messages

### Performance/Reliability Tension Resolutions

| Tension | Resolution |
|---------|-----------|
| **Retry logic increases checkout time** | Retry only for transient DB errors. Max 3 attempts with exponential backoff (100ms base, 5s max). Expected added latency: ~200ms worst case (still within 300ms p95 budget). |
| **Circuit breaker timeout vs. response time** | Circuit breaker timeout (5s) is longer than p95 checkout budget (300ms). The breaker only protects non-essential features; core checkout has no circuit breaker on its own path. |
| **Pessimistic locking vs. throughput** | `FOR UPDATE` locks held for < 50ms (single row update). Lock contention is low because payments are serialized per-order. |
| **Outbox pattern adds write latency** | Outbox insert is in the same DB transaction as the order update (no extra round-trip). Added latency: ~2ms per write. |
| **Rate limiting adds latency** | Redis-backed token check adds ~1ms per request. In-memory fallback adds ~0.01ms. Both well within budget. |

### Graceful Degradation (NFR 2.1)

The `RecommendationService` is protected by a circuit breaker:

```python
# In services/order_service.py
class RecommendationService:
    def __init__(self):
        self.cb = get_circuit_breaker("recommendations")

    async def get_recommendations(self, customer_id: str) -> list[dict]:
        async def _fetch():
            # Simulate external API call with 2s timeout
            async with asyncio.timeout(2.0):
                await asyncio.sleep(0.05)
                return [{"name": "Recommended Item 1", ...}]

        async def _fallback():
            # Return generic popular items when circuit is open
            return [{"name": "Popular Item 1", ...}]

        return await self.cb.call(_fetch, fallback=_fallback)
```

When the recommendation service fails 5 times, the circuit opens for 30 seconds, during which all calls return the fallback response immediately.

### Fault Detection & Recovery (NFR 2.2)

The retry mechanism uses tenacity with exponential backoff:

```python
# In infrastructure/retry.py
def db_retry_policy():
    return AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=5.0),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    )
```

Health checks probe all dependencies every request to `/health`.

### State Preservation (NFR 2.3)

The Transactional Outbox pattern ensures crash-safe state transitions:

1. Order state change is written to DB (synchronous)
2. Outbox entry is written in the **same DB transaction**
3. Background processor polls outbox and forwards to RabbitMQ
4. On restart, `startup_recovery()` processes any unprocessed outbox entries

```python
# In infrastructure/state_recovery.py
async def startup_recovery():
    """Run recovery routines on application startup."""
    in_flight = await recover_in_flight_orders()
    await process_outbox()
```

---

## Appendix: File Structure

```
oms/
├── __init__.py
├── main.py                    # FastAPI app entry point
├── config.py                  # Environment configuration
├── openapi.yaml               # Versioned OpenAPI specification
├── manual.md                  # THIS FILE — User manual
├── ARCHITECTURE.md            # Architecture document (ADRs, NFR matrix)
├── DEPLOYMENT.md              # Deployment guide
├── check_all_imports.py       # Import verification script
├── check_imports.py           # Quick import check
├── test_app.py                # App creation test
├── test_routes.py             # Route registration test
├── test_state_machine.py      # State machine unit test
├── domain/
│   ├── __init__.py
│   ├── enums.py               # OrderStatus, PaymentStatus, etc.
│   ├── models.py              # Pydantic domain models
│   └── order_state.py         # Order state machine
├── api/
│   ├── __init__.py
│   ├── controllers.py         # REST endpoint handlers
│   ├── schemas.py             # Request/response Pydantic schemas
│   └── middleware.py          # Rate limiting & logging middleware
├── services/
│   ├── __init__.py
│   └── order_service.py       # Business logic (OrderService, ProductService, RecommendationService)
├── repositories/
│   ├── __init__.py
│   └── orm_models.py          # SQLAlchemy ORM models & repository classes
├── infrastructure/
│   ├── __init__.py
│   ├── cache.py               # Redis cache-aside layer
│   ├── circuit_breaker.py     # Resilience4j-style circuit breaker
│   ├── database.py            # Async SQLAlchemy engine & sessions
│   ├── health.py              # Health check endpoints
│   ├── message_queue.py       # RabbitMQ client
│   ├── rate_limiter.py        # Token-bucket rate limiter
│   ├── retry.py               # Exponential backoff retry
│   └── state_recovery.py      # Transactional outbox & startup recovery
├── deploy/
│   ├── docker-compose.yml     # Docker Compose configuration
│   ├── Dockerfile             # Multi-stage Docker build
│   └── oms.service            # systemd unit file
└── tests/
    ├── locustfile.py          # Load test plan (Locust)
    ├── seed_data.py           # Test data seeder
    └── test_reliability.py    # Reliability verification suite
```

---

*© 2025 ChatDev — Order Management System. Built with ❤️ by the Chief Product Officer.*
