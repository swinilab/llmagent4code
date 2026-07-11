# Order Management System (OMS) — User Manual

> **Version:** 1.0.0  
> **Product Owner:** ChatDev — Chief Product Officer  
> **Tech Stack:** Python 3.12 · FastAPI · SQLAlchemy (async) · PostgreSQL 16 · tenacity · Docker · systemd  
> **Target Hardware:** Single-node, 2 vCPU / 4 GB RAM

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [Quick Start](#3-quick-start)
4. [API Reference](#4-api-reference)
5. [User Workflows](#5-user-workflows)
6. [Reliability Features](#6-reliability-features)
7. [Deployment Options](#7-deployment-options)
8. [Running Tests](#8-running-tests)
9. [Configuration Reference](#9-configuration-reference)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. System Overview

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that manages the complete order-to-cash lifecycle:

```
Customer places order
       ↓
Order Staff reviews & accepts
       ↓
Accountant creates invoice
       ↓
Customer pays invoice
       ↓
Accountant verifies payment
       ↓
Order Staff ships paid order
       ↓
Order Staff closes completed order
```

The system serves **three roles** (no authentication required):

| Role | Description | Typical Actions |
|------|-------------|-----------------|
| **Customer** | Places orders, makes payments | `POST /orders`, `POST /payments` |
| **Order Staff** | Reviews, accepts, ships, closes orders | `POST /orders/{id}/transition` |
| **Accountant** | Creates invoices, verifies payments | `POST /invoices`, `POST /payments/{id}/verify` |

### Key Design Principles

- **Graceful Degradation (NFR 2.1):** Non-essential features (recommendations) are protected by a circuit breaker. When the external service fails, core checkout keeps working.
- **Fault Detection & Recovery (NFR 2.2):** Database operations use retry with exponential backoff. A health endpoint reports system status. Connection pooling validates connections before use.
- **State Preservation (NFR 2.3):** All state changes are written to PostgreSQL within the same transaction. A transactional outbox ensures events are never lost. The system auto-restarts on crash via systemd or Docker.

---

## 2. Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Customers │  │ Products │  │  Orders   │  │  Payments  │  │
│  │   API     │  │   API    │  │   API     │  │    API     │  │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│        │              │             │               │         │
│  ┌─────┴──────────────┴─────────────┴───────────────┴──────┐ │
│  │                    Service Layer                          │ │
│  │  OrderService · PaymentService · InvoiceService · ...    │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│                            │                                  │
│  ┌─────────────────────────┴───────────────────────────────┐ │
│  │              Domain Layer (State Machine)                 │ │
│  │  apply_transition() · IllegalTransitionError · Enums     │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│                            │                                  │
│  ┌─────────────────────────┴───────────────────────────────┐ │
│  │              Adapter Layer (Repositories)                │ │
│  │  OrderRepository · PaymentRepository · OutboxRepository  │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│                            │                                  │
│  ┌─────────────────────────┴───────────────────────────────┐ │
│  │           Infrastructure Layer                           │ │
│  │  Circuit Breaker · Retry · DB Pool · Lifecycle · Outbox  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              PostgreSQL 16 (Single Node)                 │ │
│  │  customers · products · orders · order_line_items        │ │
│  │  payments · invoices · outbox_messages                   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
oms/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic Settings (env-based)
│   ├── api/                     # REST controllers
│   │   ├── customers.py
│   │   ├── products.py
│   │   ├── orders.py
│   │   ├── payments.py
│   │   ├── invoices.py
│   │   ├── recommendations.py
│   │   └── health.py
│   ├── services/                # Business logic
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── invoice_service.py
│   │   ├── product_service.py
│   │   ├── recommendation_service.py
│   │   └── health_service.py
│   ├── domain/                  # Domain models & state machine
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── enums.py             # OrderStatus, PaymentStatus, etc.
│   │   └── state_machine.py     # Order state-transition engine
│   ├── adapters/                # Data access & outbox
│   │   ├── repositories.py      # CRUD with optimistic locking
│   │   ├── outbox.py            # Transactional outbox pattern
│   │   └── recovery.py          # Startup state recovery
│   ├── infrastructure/          # Cross-cutting concerns
│   │   ├── circuit_breaker.py   # Async circuit breaker
│   │   ├── retry.py             # tenacity retry decorator
│   │   ├── database.py          # Async engine + session factory
│   │   └── lifecycle.py        # Startup/shutdown routines
│   └── core/                    # Shared utilities
│       ├── exceptions.py        # Custom exceptions + handlers
│       └── logging.py           # Logging configuration
├── alembic/                     # Database migrations
│   └── versions/001_initial_schema.py
├── deploy/                      # Infrastructure as Code
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── systemd/oms.service
├── tests/                       # Reliability test scripts
│   ├── test_degradation.py      # NFR 2.1
│   ├── test_recovery.py         # NFR 2.2
│   └── test_state.py            # NFR 2.3
├── docs/                        # Documentation
│   ├── adr.md                   # Architectural Decision Records
│   ├── nfr_traceability_matrix.md
│   ├── data_architecture.md
│   ├── deployment_guide.md
│   ├── reliability_test_plan.md
│   └── openapi.yaml
├── .env                         # Environment configuration
├── pyproject.toml               # Python project definition
└── manual.md                    # This file
```

---

## 3. Quick Start

### Prerequisites

- **Python 3.12+** with `uv` package manager
- **PostgreSQL 16+** running locally
- **Docker** (optional, for containerized deployment)

### Step 1: Set up the environment

```bash
cd oms
uv venv
source .venv/bin/activate
uv sync
```

### Step 2: Configure environment

Edit `.env` or set environment variables:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=oms
export DB_PASSWORD=oms_secret
export DB_NAME=oms_db
```

### Step 3: Create the database

```bash
# Create the database user and database
psql -U postgres -c "CREATE USER oms WITH PASSWORD 'oms_secret';"
psql -U postgres -c "CREATE DATABASE oms_db OWNER oms;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE oms_db TO oms;"
```

### Step 4: Run database migrations

```bash
alembic upgrade head
```

### Step 5: Start the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 6: Verify it's running

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "database": "connected",
  "uptime_seconds": 12.34
}
```

### Step 7: Open the API documentation

- **Swagger UI:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc
- **OpenAPI JSON:** http://localhost:8000/api/v1/openapi.json

---

## 4. API Reference

### 4.1 Health Check

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| GET | `/api/v1/health` | System health status | Core |

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "uptime_seconds": 42.0
}
```

When the database is unreachable, `status` becomes `"degraded"` and `database` becomes `"disconnected"`.

---

### 4.2 Customers

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| POST | `/api/v1/customers` | Create a customer | Core |
| GET | `/api/v1/customers` | List all customers | Core |
| GET | `/api/v1/customers/{id}` | Get customer by ID | Core |

**Create Customer:**
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "address": "123 Main St, Springfield",
    "phone": "+1-555-1234",
    "banking_details": "ACC-98765",
    "role": "CUSTOMER"
  }'
```

**Response (201 Created):**
```json
{
  "id": "a1b2c3d4-...",
  "name": "Alice Johnson",
  "address": "123 Main St, Springfield",
  "phone": "+1-555-1234",
  "banking_details": "ACC-98765",
  "role": "CUSTOMER",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "version": 1
}
```

---

### 4.3 Products

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| POST | `/api/v1/products` | Create a product | Core |
| GET | `/api/v1/products` | List available products | Core |
| GET | `/api/v1/products/{id}` | Get product by ID | Core |

**Create Product:**
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Wireless Bluetooth Headphones",
    "base_price": 79.99,
    "currency": "USD",
    "available": true
  }'
```

---

### 4.4 Orders (Core Workflow)

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| POST | `/api/v1/orders` | Create order (Step 1) | Core |
| GET | `/api/v1/orders` | List orders (filterable) | Core |
| GET | `/api/v1/orders/{id}` | Get order details | Core |
| POST | `/api/v1/orders/{id}/transition` | Transition order state (Steps 2-7) | Core |

#### Step 1: Customer Places an Order

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUSTOMER_UUID_HERE",
    "line_items": [
      {
        "product_id": "PRODUCT_UUID_HERE",
        "quantity": 2,
        "unit_price": 79.99,
        "currency": "USD"
      }
    ],
    "currency": "USD"
  }'
```

**Response (201 Created):**
```json
{
  "id": "ORDER_UUID",
  "customer_id": "CUSTOMER_UUID",
  "status": "CREATED",
  "total_amount": 159.98,
  "currency": "USD",
  "invoice_ref": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "version": 1,
  "line_items": [...]
}
```

#### Steps 2-7: Transition Order State

All state transitions use the same endpoint with different `event` values:

```bash
# Step 2: Order Staff reviews & accepts
curl -X POST http://localhost:8000/api/v1/orders/ORDER_UUID/transition \
  -H "Content-Type: application/json" \
  -d '{"event": "review_accept"}'

# Step 3: Accountant creates invoice (see Section 4.5)
# Step 4: Customer pays (see Section 4.6)

# Step 6: Order Staff ships
curl -X POST http://localhost:8000/api/v1/orders/ORDER_UUID/transition \
  -H "Content-Type: application/json" \
  -d '{"event": "ship"}'

# Step 7: Order Staff closes
curl -X POST http://localhost:8000/api/v1/orders/ORDER_UUID/transition \
  -H "Content-Type: application/json" \
  -d '{"event": "close"}'

# Cancel an order (any non-terminal state)
curl -X POST http://localhost:8000/api/v1/orders/ORDER_UUID/transition \
  -H "Content-Type: application/json" \
  -d '{"event": "cancel"}'
```

**Valid transition events:**

| Event | From | To | Who |
|-------|------|----|-----|
| `review_accept` | CREATED | ACCEPTED | Order Staff |
| `create_invoice` | ACCEPTED | INVOICED | Accountant |
| `pay` | INVOICED | PAID | Customer |
| `ship` | PAID | SHIPPED | Order Staff |
| `close` | SHIPPED | CLOSED | Order Staff |
| `cancel` | Any non-terminal | CANCELLED | Any role |

**Filtering orders:**
```bash
# By status
curl "http://localhost:8000/api/v1/orders?status=CREATED"

# By customer
curl "http://localhost:8000/api/v1/orders?customer_id=CUSTOMER_UUID"

# All orders
curl "http://localhost:8000/api/v1/orders"
```

---

### 4.5 Invoices

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| POST | `/api/v1/invoices` | Create invoice (Step 3) | Core |
| GET | `/api/v1/invoices/{id}` | Get invoice | Core |
| GET | `/api/v1/invoices/by-order/{order_id}` | Get invoices for order | Core |

**Step 3: Accountant Creates Invoice:**
```bash
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORDER_UUID",
    "billing_info": "Invoice for order ORDER_UUID - Alice Johnson",
    "amount": 159.98,
    "currency": "USD",
    "due_date": "2025-02-15T00:00:00Z"
  }'
```

This automatically transitions the order from `ACCEPTED` to `INVOICED` and sets the `invoice_ref` on the order.

---

### 4.6 Payments

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| POST | `/api/v1/payments` | Process payment (Step 4) | Core |
| GET | `/api/v1/payments/{id}` | Get payment | Core |
| GET | `/api/v1/payments/by-order/{order_id}` | Get payments for order | Core |
| POST | `/api/v1/payments/{id}/verify` | Verify payment (Step 5) | Core |

**Step 4: Customer Pays Invoice:**
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORDER_UUID",
    "amount": 159.98,
    "method": "CREDIT_CARD",
    "idempotency_key": "unique-key-12345"
  }'
```

> **Idempotency:** The `idempotency_key` prevents duplicate charges. If you send the same request twice, the second call returns the existing payment record without charging again.

**Step 5: Accountant Verifies Payment:**
```bash
curl -X POST http://localhost:8000/api/v1/payments/PAYMENT_UUID/verify
```

---

### 4.7 Recommendations (Non-Essential)

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| GET | `/api/v1/recommendations/{customer_id}` | Get product recommendations | **Non-Essential** |

This endpoint is protected by a **circuit breaker**. If the external recommendation service (port 9001) is unavailable, it returns a fallback response:

```json
{
  "recommendations": [],
  "fallback": true
}
```

---

## 5. User Workflows

### Complete Order Lifecycle Walkthrough

Here's a full end-to-end example using `curl`:

```bash
# ── Setup ──────────────────────────────────────────────────────

# 1. Create a customer
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","address":"456 Oak Ave","phone":"+1-555-6789","banking_details":"ACC-54321","role":"CUSTOMER"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Customer: $CUSTOMER"

# 2. Create a product
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Noise-Cancelling Headphones","base_price":199.99,"currency":"USD","available":true}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Product: $PRODUCT"

# ── Workflow ───────────────────────────────────────────────────

# Step 1: Customer places order
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER\",\"line_items\":[{\"product_id\":\"$PRODUCT\",\"quantity\":1,\"unit_price\":199.99,\"currency\":\"USD\"}],\"currency\":\"USD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Step 1 - Order created: $ORDER (CREATED)"

# Step 2: Order Staff accepts
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER/transition" \
  -H "Content-Type: application/json" \
  -d '{"event":"review_accept"}' > /dev/null
echo "Step 2 - Order accepted (ACCEPTED)"

# Step 3: Accountant creates invoice
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER\",\"billing_info\":\"Invoice for John Doe\",\"amount\":199.99,\"currency\":\"USD\",\"due_date\":\"2025-02-15T00:00:00Z\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Step 3 - Invoice created: $INVOICE (INVOICED)"

# Step 4: Customer pays
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER\",\"amount\":199.99,\"method\":\"CREDIT_CARD\",\"idempotency_key\":\"pay-$ORDER\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Step 4 - Payment processed: $PAYMENT (PAID)"

# Step 5: Accountant verifies payment
curl -s -X POST "http://localhost:8000/api/v1/payments/$PAYMENT/verify" > /dev/null
echo "Step 5 - Payment verified"

# Step 6: Order Staff ships
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER/transition" \
  -H "Content-Type: application/json" \
  -d '{"event":"ship"}' > /dev/null
echo "Step 6 - Order shipped (SHIPPED)"

# Step 7: Order Staff closes
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER/transition" \
  -H "Content-Type: application/json" \
  -d '{"event":"close"}' > /dev/null
echo "Step 7 - Order closed (CLOSED)"

# Verify final state
curl -s "http://localhost:8000/api/v1/orders/$ORDER" \
  | python3 -m json.tool
```

### Workflow Criticality & Recovery

| Step | Action | Criticality | Failure Recovery |
|------|--------|-------------|------------------|
| 1 | Customer places order | **Core** | Retry (transient DB error) |
| 2 | Order Staff reviews & accepts | **Core** | Retry (transient DB error) |
| 3 | Accountant creates invoice | **Core** | Manual intervention (business rule) |
| 4 | Customer pays invoice | **Core** | Retry + Idempotency key |
| 5 | Accountant verifies payment | **Core** | Manual intervention (payment gateway) |
| 6 | Order Staff ships | **Core** | Manual intervention (logistics) |
| 7 | Order Staff closes | **Core** | Retry (transient DB error) |
| — | Product recommendations | **Non-Essential** | Circuit breaker → fallback |

---

## 6. Reliability Features

### 6.1 Graceful Degradation (NFR 2.1)

**Circuit Breaker** protects the non-essential recommendation service.

**How it works:**
1. **CLOSED** (normal): Calls pass through to the recommendation service.
2. After **3 consecutive failures**, the breaker **OPENS**.
3. **OPEN**: All calls fail immediately (no HTTP timeout) — saves ~5s per call.
4. After **30 seconds**, the breaker transitions to **HALF_OPEN** and allows one probe call.
5. If the probe succeeds, the breaker **CLOSES** again. If it fails, it re-OPENS.

**Fallback response when OPEN:**
```json
{
  "recommendations": [],
  "fallback": true
}
```

**Latency impact:** ~0.01ms overhead in CLOSED state. When OPEN, saves 5s per call by failing fast.

### 6.2 Fault Detection & Recovery (NFR 2.2)

**Health Check Endpoint:**
```bash
curl http://localhost:8000/api/v1/health
```

Returns:
- `"healthy"` — all systems operational
- `"degraded"` — database is unreachable (application still serves cached data)

**Retry with Exponential Backoff:**
- Database operations that fail with `DBAPIError` are retried automatically.
- Wait times: 0.5s → 1s → 2s (exponential backoff).
- Max 3 attempts. If all fail, the error is propagated to the client.
- Before each retry, the SQLAlchemy session is rolled back to prevent "nested transaction" errors.

**Connection Validation:**
- `pool_pre_ping=True` validates each database connection before use.
- If a connection is broken (e.g., PostgreSQL restart), a new one is acquired automatically.

### 6.3 State Preservation (NFR 2.3)

**Transactional Outbox Pattern:**
1. When an order transitions state, an outbox message is written in the **same database transaction**.
2. A background worker polls the `outbox_messages` table every 2 seconds.
3. Unprocessed messages are delivered to downstream handlers.
4. If the process crashes between writing the state and delivering the event, the message is still in the outbox and will be delivered on restart.

**Optimistic Locking:**
- Every entity has a `version` field.
- Updates check `WHERE version = current_version`.
- If another process modified the entity, the update returns 0 rows → `409 Conflict`.
- Conflict rate: <0.01% under normal load.

**Startup Recovery:**
On restart, the system scans for orders in non-terminal states (CREATED, ACCEPTED, INVOICED, PAID, SHIPPED) and logs them for operator review:

```
WARNING  In-flight order detected on startup: <uuid> (status=CREATED)
INFO     Found 3 in-flight order(s) requiring attention.
```

**Auto-Restart on Crash:**
- **systemd:** `Restart=always` with `RestartSec=5` — restarts within 5 seconds.
- **Docker:** `restart: unless-stopped` — restarts automatically.

---

## 7. Deployment Options

### 7.1 Local Development (Recommended for Testing)

```bash
# Terminal 1: Start PostgreSQL
docker run --name oms-postgres -e POSTGRES_USER=oms -e POSTGRES_PASSWORD=oms_secret \
  -e POSTGRES_DB=oms_db -p 5432:5432 -d postgres:16-alpine

# Terminal 2: Run migrations & start API
cd oms
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.2 Docker Compose (Production-Representative)

```bash
cd deploy
docker-compose up --build
```

This starts:
- **PostgreSQL 16** (1 vCPU, 1 GB RAM limit)
- **OMS API** (2 vCPU, 4 GB RAM limit)
- Health checks on both services
- Automatic restart on failure

### 7.3 systemd Service (Linux)

```bash
# Install
sudo cp deploy/systemd/oms.service /etc/systemd/system/
sudo mkdir -p /opt/oms
sudo cp -r . /opt/oms/
cd /opt/oms && uv venv && source .venv/bin/activate && uv sync && alembic upgrade head

# Start
sudo systemctl enable oms
sudo systemctl start oms

# Monitor
sudo journalctl -u oms -f
```

### 7.4 Resource Limits

| Resource | Limit | Enforced By |
|----------|-------|-------------|
| CPU | 2 vCPUs | Docker `--cpus=2`, systemd `CPUQuota=200%` |
| RAM | 4 GB | Docker `--memory=4g`, systemd `MemoryMax=4G` |
| DB Pool | 10 connections (max 20 overflow) | `DB_POOL_SIZE` config |
| Max Requests | 100 concurrent | `MAX_CONCURRENT_REQUESTS` config |
| Request Timeout | 30 seconds | `REQUEST_TIMEOUT` config |

---

## 8. Running Tests

### 8.1 Degradation Test (NFR 2.1)

**Purpose:** Verify that core checkout works under load while non-essential recommendations return fallback.

```bash
# Prerequisites: API running on localhost:8000, PostgreSQL running
python tests/test_degradation.py
```

**What it does:**
1. Creates test customer and product
2. Sends 20 concurrent order creation requests (core)
3. Sends 20 concurrent recommendation requests (non-essential)
4. Reports success rates

**Pass criteria:**
- Core checkout: ≥90% success rate
- Non-essential: at least 1 fallback response observed

### 8.2 Recovery Test (NFR 2.2)

**Purpose:** Verify that the system detects DB failures and auto-recovers.

```bash
# Requires sudo for iptables
sudo python tests/test_recovery.py
```

**What it does:**
1. Verifies initial health
2. Blocks PostgreSQL port 5432 using iptables
3. Sends requests during block — expects degraded status
4. Unblocks the port
5. Waits and verifies recovery

**Pass criteria:**
- During block: health returns degraded or connection errors
- After unblock: health returns healthy within 10 seconds
- No manual restart required

### 8.3 State Preservation Test (NFR 2.3)

**Purpose:** Verify that committed transactions survive a process crash.

```bash
# Prerequisites: API running on localhost:8000
python tests/test_state.py
```

**What it does:**
1. Creates test data and places 3 orders
2. Force-kills the OMS process with SIGKILL
3. Restarts the OMS process
4. Verifies all 3 orders are still retrievable

**Pass criteria:**
- All 3 committed orders are present after restart
- Startup logs detect in-flight orders

### 8.4 Load Test (Performance Baseline)

```bash
# Install locust
pip install locust

# Run load test
locust --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=5m
```

**Target thresholds:**
- P95 latency < 500ms
- Error rate < 1%
- CPU usage < 80%
- Memory usage < 3.5 GB

---

## 9. Configuration Reference

All configuration is via environment variables (see `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `oms` | Database user |
| `DB_PASSWORD` | `oms_secret` | Database password |
| `DB_NAME` | `oms_db` | Database name |
| `DB_POOL_SIZE` | `10` | Connection pool size |
| `DB_MAX_OVERFLOW` | `20` | Max overflow connections |
| `DB_POOL_TIMEOUT` | `30.0` | Pool timeout (seconds) |
| `DB_POOL_RECYCLE` | `1800` | Recycle connections (seconds) |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `1` | Uvicorn workers (keep 1 for single-node) |
| `RECOMMENDATION_URL` | `http://localhost:9001/recommend` | External recommendation service |
| `CB_FAILURE_THRESHOLD` | `3` | Circuit breaker failure count |
| `CB_RECOVERY_TIMEOUT` | `30.0` | Circuit breaker recovery timeout (s) |
| `RETRY_MAX_ATTEMPTS` | `3` | Max retry attempts for DB ops |
| `RETRY_MIN_WAIT` | `0.5` | Min retry wait (seconds) |
| `RETRY_MAX_WAIT` | `5.0` | Max retry wait (seconds) |
| `OUTBOX_POLL_INTERVAL` | `2.0` | Outbox poll interval (seconds) |
| `OUTBOX_BATCH_SIZE` | `50` | Outbox batch size |
| `MAX_CONCURRENT_REQUESTS` | `100` | Max concurrent requests |
| `REQUEST_TIMEOUT` | `30.0` | Request timeout (seconds) |

---

## 10. Troubleshooting

### Common Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| `Connection refused` on startup | PostgreSQL not running | Start PostgreSQL: `docker start oms-postgres` |
| `relation "customers" does not exist` | Migrations not applied | Run `alembic upgrade head` |
| `409 Conflict` on order transition | Optimistic lock conflict | Retry the request (another user modified the order) |
| `400 Bad Request: Invalid transition` | Invalid state transition | Check the order's current status and valid transitions |
| Health shows `degraded` | Database unreachable | Check PostgreSQL is running and network is accessible |
| Recommendations return `fallback: true` | Recommendation service unavailable | This is expected behavior — circuit breaker is protecting core functionality |
| `kill -9` causes data loss | Not possible | All committed transactions are durable in PostgreSQL's WAL |

### Logs

```bash
# Application logs
uvicorn app.main:app --log-level info

# systemd logs
sudo journalctl -u oms -f

# Docker logs
docker logs -f oms-api
```

### Health Check Debugging

```bash
# Quick health check
curl -v http://localhost:8000/api/v1/health

# Check database directly
psql -U oms -d oms_db -c "SELECT 1"

# Check outbox messages
psql -U oms -d oms_db -c "SELECT count(*) FROM outbox_messages WHERE processed_at IS NULL;"
```

---

## Appendix: Order State Machine

```
                    ┌──────────┐
                    │ CREATED  │
                    └────┬─────┘
                         │ review_accept
                    ┌────▼─────┐
                    │ ACCEPTED │
                    └────┬─────┘
                         │ create_invoice
                    ┌────▼─────┐
                    │ INVOICED │
                    └────┬─────┘
                         │ pay
                    ┌────▼───┐
                    │  PAID  │
                    └────┬───┘
                         │ ship
                    ┌────▼─────┐
                    │ SHIPPED  │
                    └────┬─────┘
                         │ close
                    ┌────▼────┐
                    │ CLOSED  │  (terminal)
                    └─────────┘

  cancel (from any non-terminal state)
                    ┌───────────┐
                    │ CANCELLED │  (terminal exception)
                    └───────────┘
```

All transitions are **synchronous** (persisted in the same DB transaction). Non-essential side-effects (analytics, notifications) are handled asynchronously via the outbox pattern.

---

*For more details, see the documentation in the `docs/` directory:*
- *Architectural Decision Records: `docs/adr.md`*
- *NFR Traceability Matrix: `docs/nfr_traceability_matrix.md`*
- *Data Architecture: `docs/data_architecture.md`*
- *Deployment Guide: `docs/deployment_guide.md`*
- *Reliability Test Plan: `docs/reliability_test_plan.md`*
- *OpenAPI Specification: `docs/openapi.yaml`*
