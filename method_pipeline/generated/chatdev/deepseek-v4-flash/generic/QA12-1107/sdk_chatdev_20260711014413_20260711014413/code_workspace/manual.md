# Order Management System (OMS) — User Manual

**Version:** 1.0.0  
**Product Owner:** ChatDev — Chief Product Officer  
**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), SQLite (WAL mode), asyncio  

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Main Features](#3-main-features)
4. [Architecture at a Glance](#4-architecture-at-a-glance)
5. [Installation & Environment Setup](#5-installation--environment-setup)
6. [Running the Application](#6-running-the-application)
7. [API Reference](#7-api-reference)
8. [Complete User Workflow (7-Step Guide)](#8-complete-user-workflow-7-step-guide)
9. [Role-Based Operations](#9-role-based-operations)
10. [Infrastructure & Non-Functional Features](#10-infrastructure--non-functional-features)
11. [Testing & Verification](#11-testing--verification)
12. [Configuration Reference](#12-configuration-reference)
13. [Docker Deployment](#13-docker-deployment)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that manages the complete order lifecycle:

```
Customer Ordering → Payment Processing → Invoicing → Shipping → Closure
```

It serves **three roles**:
- **Customer** — places orders and makes payments
- **Order Staff** — reviews, accepts, ships, and closes orders
- **Accountant** — creates invoices and verifies payments

The system is built with **resilience, performance, and fault-tolerance** in mind, implementing circuit breakers, graceful degradation, async queue management, and state preservation.

---

## 2. System Overview

### Domain Model

| Entity | Description |
|--------|-------------|
| **Customer** | Person using the system (name, address, phone, banking details, role) |
| **Product** | Sellable item (name, description, base price, currency, stock) |
| **Order** | Customer purchase request with line items and full status lifecycle |
| **OrderItem** | Individual product within an order (quantity, unit price, total) |
| **Payment** | Financial transaction for an order (amount, method, status) |
| **Invoice** | Billing document for an order (billing info, dates, status) |

### Order Status Lifecycle

```
PENDING → REVIEWED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED
    ↑         ↑          ↑           ↑
    └─────────┴──────────┴───────────┘
                    ↓
               CANCELLED
```

### Entity-Relationship Diagram

```
┌──────────┐       ┌──────────┐       ┌───────────┐
│ Customer │1───N→│  Order   │1───1→│  Invoice  │
└──────────┘       └──────────┘       └───────────┘
                        │ 1                   │
                        │                     │
                        │ N                   │
                   ┌──────────┐          ┌──────────┐
                   │OrderItem │          │ Payment  │
                   └──────────┘          └──────────┘
                        │ N
                        │ 1
                   ┌──────────┐
                   │ Product  │
                   └──────────┘
```

---

## 3. Main Features

### 3.1 Core Business Features

| Feature | Description |
|---------|-------------|
| **Customer Management** | Create and list customers with role assignment |
| **Product Catalog** | Create, search, and browse products with stock tracking |
| **Order Placement** | Customers place orders with multiple line items; stock is decremented |
| **Order Review & Acceptance** | Order Staff reviews and accepts pending orders |
| **Invoice Creation** | Accountant creates invoices for accepted orders |
| **Payment Processing** | Customers pay invoices via multiple methods (credit card, debit card, bank transfer, digital wallet) |
| **Payment Verification** | Accountant verifies completed payments |
| **Shipping & Closure** | Order Staff ships paid orders and closes completed ones |
| **Order Cancellation** | Cancel orders at any stage before shipping (stock is restored) |

### 3.2 Infrastructure & Resilience Features

| Feature | NFR | Description |
|---------|-----|-------------|
| **Async Queue** | NFR 1.3 | Bounded priority queue with backpressure; drops non-essential tasks under load |
| **Graceful Degradation** | NFR 2.1 | Monitors memory/CPU; disables product search, order history, invoice listing under resource contention |
| **Circuit Breaker** | NFR 2.2 | Prevents cascading failures for external service calls; auto-recovers |
| **State Preservation** | NFR 2.3 | Heartbeat-based crash detection; restores pending orders on restart |
| **Request ID Tracing** | NFR 2.2 | Every request gets a unique X-Request-ID for log correlation |
| **Health Endpoints** | All | Liveness, readiness, degradation status, queue metrics, state info |
| **OpenAPI Documentation** | All | Auto-generated Swagger UI at `/docs` and ReDoc at `/redoc` |

---

## 4. Architecture at a Glance

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                        │
├─────────────────────────────────────────────────────────────┤
│  Middleware: Request ID, CORS, Global Error Handler          │
├─────────────────────────────────────────────────────────────┤
│  Controllers (REST endpoints, validation, routing)          │
├─────────────────────────────────────────────────────────────┤
│  Services (Business logic, transaction boundaries)          │
├─────────────────────────────────────────────────────────────┤
│  Repositories (Data access via SQLAlchemy async sessions)    │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                       │
│  ┌──────────┬──────────────┬──────────┬──────────────┐     │
│  │ Queue    │ Degradation  │ Circuit  │ State        │     │
│  │ Manager  │ Manager      │ Breaker  │ Manager      │     │
│  └──────────┴──────────────┴──────────┴──────────────┘     │
├─────────────────────────────────────────────────────────────┤
│  Database: SQLite (WAL mode) via aiosqlite                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **FastAPI + async** | Native async/await for high throughput; automatic OpenAPI docs |
| **SQLite WAL mode** | Zero-config, crash-safe writes, concurrent reads |
| **Async Priority Queue** | In-process backpressure; no external dependencies |
| **Circuit Breaker** | Prevents cascading failures; auto-recovery |
| **3-Layer Separation** | Controller → Service → Repository for testability |

---

## 5. Installation & Environment Setup

### Prerequisites

- **Python 3.12+** (required)
- **uv** (Python package manager) — [Install uv](https://docs.astral.sh/uv/)

### Step 1: Clone the Repository

```bash
cd oms-backend
```

### Step 2: Create Virtual Environment & Install Dependencies

```bash
uv sync
```

This creates a `.venv` directory and installs all dependencies from `pyproject.toml` and `uv.lock`.

### Step 3: Verify Installation

```bash
uv run python -c "import fastapi; print(f'FastAPI {fastapi.__version__} installed')"
```

Expected output:
```
FastAPI 0.139.0 installed
```

### Step 4: (Optional) Create a `.env` File

```bash
cat > .env << 'EOF'
OMS_DATABASE_URL=sqlite+aiosqlite:///./oms.db
OMS_PORT=8000
OMS_QUEUE_MAX_SIZE=1000
OMS_QUEUE_WORKER_COUNT=4
OMS_DEGRADATION_MEMORY_THRESHOLD_MB=512
OMS_DEGRADATION_CPU_THRESHOLD_PERCENT=90.0
EOF
```

---

## 6. Running the Application

### 6.1 Local Development Mode

```bash
uv run python -m app.main
```

The server starts at **http://localhost:8000**.

### 6.2 With Auto-Reload (for development)

```bash
OMS_RELOAD=true uv run python -m app.main
```

### 6.3 Using Uvicorn Directly

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6.4 Verify the Server is Running

```bash
curl http://localhost:8000/health/live
```

Expected response:
```json
{"status":"alive","uptime_seconds":2.34}
```

### 6.5 Access API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI Spec:** http://localhost:8000/openapi.json

---

## 7. API Reference

### 7.1 Complete Endpoint List

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/customers` | Any | Create a new customer |
| `GET` | `/api/v1/customers` | Any | List all customers |
| `GET` | `/api/v1/customers/{id}` | Any | Get customer by ID |
| `POST` | `/api/v1/products` | Any | Create a new product |
| `GET` | `/api/v1/products` | Any | Search products (degradable) |
| `GET` | `/api/v1/products/{id}` | Any | Get product by ID |
| `POST` | `/api/v1/orders` | Customer | Place order (queued, returns 202) |
| `GET` | `/api/v1/orders` | Any | List orders (filterable by status) |
| `GET` | `/api/v1/orders/{id}` | Any | Get order by ID |
| `PUT` | `/api/v1/orders/{id}/review` | Staff | Review pending order |
| `PUT` | `/api/v1/orders/{id}/accept` | Staff | Accept reviewed order |
| `PUT` | `/api/v1/orders/{id}/cancel` | Staff | Cancel order (before shipping) |
| `PUT` | `/api/v1/orders/{id}/ship` | Staff | Ship paid order |
| `PUT` | `/api/v1/orders/{id}/close` | Staff | Close shipped order |
| `POST` | `/api/v1/invoices` | Accountant | Create invoice (queued, returns 202) |
| `GET` | `/api/v1/invoices` | Any | List invoices (degradable) |
| `GET` | `/api/v1/invoices/{id}` | Any | Get invoice by ID |
| `POST` | `/api/v1/payments` | Customer | Process payment (queued, returns 202) |
| `GET` | `/api/v1/payments` | Any | List payments |
| `GET` | `/api/v1/payments/{id}` | Any | Get payment by ID |
| `PUT` | `/api/v1/payments/{id}/verify` | Accountant | Verify payment |
| `GET` | `/health/live` | Any | Liveness probe |
| `GET` | `/health/ready` | Any | Readiness probe (checks DB) |
| `GET` | `/health/degradation` | Any | Degradation status |
| `GET` | `/health/queue` | Any | Queue metrics |
| `GET` | `/health/state` | Any | State manager info |

### 7.2 Request/Response Examples

#### Create Customer

```bash
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "address": "123 Main Street, Springfield",
    "phone": "+1-555-0100",
    "banking_details": "Bank: Chase, Acc: 123456789"
  }' | python3 -m json.tool
```

Response (201 Created):
```json
{
  "id": "a1b2c3d4e5f6...",
  "name": "Alice Johnson",
  "address": "123 Main Street, Springfield",
  "phone": "+1-555-0100",
  "banking_details": "Bank: Chase, Acc: 123456789",
  "role": "CUSTOMER",
  "created_at": "2025-07-11T01:44:13Z",
  "updated_at": "2025-07-11T01:44:13Z"
}
```

#### Create Product

```bash
curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Bluetooth Headphones",
    "description": "Noise-cancelling over-ear headphones",
    "base_price": 79.99,
    "currency": "USD",
    "stock_quantity": 150
  }' | python3 -m json.tool
```

Response (201 Created):
```json
{
  "id": "b2c3d4e5f6a7...",
  "name": "Wireless Bluetooth Headphones",
  "description": "Noise-cancelling over-ear headphones",
  "base_price": 79.99,
  "currency": "USD",
  "stock_quantity": 150,
  "created_at": "2025-07-11T01:44:13Z"
}
```

#### Place Order (Queued)

```bash
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "a1b2c3d4e5f6...",
    "items": [
      {"product_id": "b2c3d4e5f6a7...", "quantity": 2}
    ]
  }' | python3 -m json.tool
```

Response (202 Accepted):
```json
{
  "status": "accepted",
  "message": "Order queued for processing"
}
```

#### Get Order

```bash
curl -s http://localhost:8000/api/v1/orders/ORDER_ID | python3 -m json.tool
```

Response (200 OK):
```json
{
  "id": "c3d4e5f6a7b8...",
  "customer_id": "a1b2c3d4e5f6...",
  "customer_name": "Alice Johnson",
  "invoice_id": null,
  "status": "PENDING",
  "total_amount": 159.98,
  "currency": "USD",
  "line_items": [
    {
      "id": "d4e5f6a7b8c9...",
      "product_id": "b2c3d4e5f6a7...",
      "product_name": "Wireless Bluetooth Headphones",
      "quantity": 2,
      "unit_price": 79.99,
      "total_price": 159.98
    }
  ],
  "created_at": "2025-07-11T01:44:13Z",
  "updated_at": "2025-07-11T01:44:13Z"
}
```

---

## 8. Complete User Workflow (7-Step Guide)

This section walks through the **complete order lifecycle** from placement to closure.

### Step 1: Customer Places Order

**Role:** Customer  
**Endpoint:** `POST /api/v1/orders`  
**Status Transition:** → `PENDING`

```bash
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":2}]}")
echo "Order queued: $ORDER"

# Wait for queue to process
sleep 1

# Get the order ID
ORDER_ID=$(curl -s "http://localhost:8000/api/v1/orders?limit=1" | python3 -c "import sys,json; print(json.load(sys.stdin)['orders'][0]['id'])")
echo "Order ID: $ORDER_ID"
```

### Step 2a: Order Staff Reviews Order

**Role:** Order Staff  
**Endpoint:** `PUT /api/v1/orders/{id}/review`  
**Status Transition:** `PENDING` → `REVIEWED`

```bash
curl -s -X PUT "http://localhost:8000/api/v1/orders/$ORDER_ID/review" | python3 -m json.tool
```

### Step 2b: Order Staff Accepts Order

**Role:** Order Staff  
**Endpoint:** `PUT /api/v1/orders/{id}/accept`  
**Status Transition:** `REVIEWED` → `ACCEPTED`

```bash
curl -s -X PUT "http://localhost:8000/api/v1/orders/$ORDER_ID/accept" | python3 -m json.tool
```

### Step 3: Accountant Creates Invoice

**Role:** Accountant  
**Endpoint:** `POST /api/v1/invoices`  
**Status Transition:** `ACCEPTED` → `INVOICED`

```bash
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"billing_info\":\"Invoice for Alice - 2x Headphones\"}")
echo "Invoice queued: $INVOICE"

# Wait for queue to process
sleep 1

# Get the invoice ID
INVOICE_ID=$(curl -s "http://localhost:8000/api/v1/invoices?limit=1" | python3 -c "import sys,json; print(json.load(sys.stdin)['invoices'][0]['id'])")
echo "Invoice ID: $INVOICE_ID"
```

### Step 4: Customer Pays Invoice

**Role:** Customer  
**Endpoint:** `POST /api/v1/payments`  
**Status Transition:** `INVOICED` → `PAID`

```bash
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"amount\":159.98,\"method\":\"CREDIT_CARD\"}")
echo "Payment queued: $PAYMENT"

# Wait for queue to process
sleep 1

# Get the payment ID
PAYMENT_ID=$(curl -s "http://localhost:8000/api/v1/payments?limit=1" | python3 -c "import sys,json; print(json.load(sys.stdin)['payments'][0]['id'])")
echo "Payment ID: $PAYMENT_ID"
```

### Step 5: Accountant Verifies Payment

**Role:** Accountant  
**Endpoint:** `PUT /api/v1/payments/{id}/verify`  
**Status:** Payment remains `COMPLETED`; invoice marked as `PAID`

```bash
curl -s -X PUT "http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify" | python3 -m json.tool
```

### Step 6: Order Staff Ships Order

**Role:** Order Staff  
**Endpoint:** `PUT /api/v1/orders/{id}/ship`  
**Status Transition:** `PAID` → `SHIPPED`

```bash
curl -s -X PUT "http://localhost:8000/api/v1/orders/$ORDER_ID/ship" | python3 -m json.tool
```

### Step 7: Order Staff Closes Order

**Role:** Order Staff  
**Endpoint:** `PUT /api/v1/orders/{id}/close`  
**Status Transition:** `SHIPPED` → `CLOSED`

```bash
curl -s -X PUT "http://localhost:8000/api/v1/orders/$ORDER_ID/close" | python3 -m json.tool
```

### Verify Final State

```bash
curl -s "http://localhost:8000/api/v1/orders/$ORDER_ID" | python3 -m json.tool
```

Expected output:
```json
{
  "id": "...",
  "status": "CLOSED",
  "invoice_id": "...",
  ...
}
```

---

## 9. Role-Based Operations

### Customer Operations

| Action | Endpoint | Notes |
|--------|----------|-------|
| Create account | `POST /api/v1/customers` | Default role is CUSTOMER |
| Browse products | `GET /api/v1/products` | May be degraded under load |
| Place order | `POST /api/v1/orders` | Returns 202 (queued) |
| Pay invoice | `POST /api/v1/payments` | Returns 202 (queued) |

### Order Staff Operations

| Action | Endpoint | Notes |
|--------|----------|-------|
| Review order | `PUT /api/v1/orders/{id}/review` | Order must be PENDING |
| Accept order | `PUT /api/v1/orders/{id}/accept` | Order must be REVIEWED |
| Cancel order | `PUT /api/v1/orders/{id}/cancel` | Before shipping only |
| Ship order | `PUT /api/v1/orders/{id}/ship` | Order must be PAID |
| Close order | `PUT /api/v1/orders/{id}/close` | Order must be SHIPPED |

### Accountant Operations

| Action | Endpoint | Notes |
|--------|----------|-------|
| Create invoice | `POST /api/v1/invoices` | Order must be ACCEPTED; returns 202 |
| Verify payment | `PUT /api/v1/payments/{id}/verify` | Payment must be COMPLETED |

---

## 10. Infrastructure & Non-Functional Features

### 10.1 Async Queue Manager (NFR 1.3)

The system uses a **bounded `asyncio.PriorityQueue`** with configurable size and worker count.

**Priority Levels:**

| Priority | Value | Task Types |
|----------|-------|------------|
| CRITICAL | 0 | `process_payment` |
| HIGH | 1 | `place_order`, `create_invoice` |
| NORMAL | 2 | `review_order`, `ship_order`, `close_order` |
| LOW | 3 | `send_notification`, `generate_report` |

**Behavior:**
- When the queue is full, **non-essential tasks are dropped** (counted in `dropped_count`)
- **Essential tasks** (checkout, payment) block until space is available
- Workers process tasks concurrently (configurable via `OMS_QUEUE_WORKER_COUNT`)

**Check queue metrics:**
```bash
curl http://localhost:8000/health/queue
```

Response:
```json
{
  "queue_size": 0,
  "peak_queue_size": 12,
  "dropped_count": 5,
  "processed_count": 47,
  "error_count": 0
}
```

### 10.2 Graceful Degradation (NFR 2.1)

The `GracefulDegradationManager` monitors system resources and disables non-essential features under load.

**Monitored Resources:**
- **Memory (RSS):** Cross-platform detection (Linux `/proc`, macOS `ps`, psutil fallback)
- **CPU:** Load average (Linux) or psutil

**Disabled Features Under Load:**
- Product search (`GET /api/v1/products?q=...`)
- Order history listing
- Invoice listing

**Core checkout flow is always preserved.**

**Check degradation status:**
```bash
curl http://localhost:8000/health/degradation
```

Response (normal):
```json
{
  "degraded": false,
  "product_search_disabled": false,
  "order_history_disabled": false,
  "invoice_listing_disabled": false,
  "reason": ""
}
```

Response (degraded):
```json
{
  "degraded": true,
  "product_search_disabled": true,
  "order_history_disabled": true,
  "invoice_listing_disabled": true,
  "reason": "memory=612MB > 512MB; cpu=95.2% > 90.0%"
}
```

### 10.3 Circuit Breaker (NFR 2.2)

The `CircuitBreaker` protects external service calls (e.g., payment gateway) from cascading failures.

**States:**
- **CLOSED** — Normal operation; calls pass through
- **OPEN** — Failures exceed threshold; calls are rejected immediately
- **HALF_OPEN** — After recovery timeout; one test call is allowed

**Configuration:**
- `OMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD` (default: 5)
- `OMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT` (default: 30.0 seconds)

**Metrics tracked:** total calls, successes, failures, state transitions.

### 10.4 State Preservation (NFR 2.3)

The `StateManager` ensures the system can recover from crashes.

**How it works:**
1. A **heartbeat** is written to the database every 5 seconds
2. On startup, the system checks if the previous instance crashed (heartbeat status = "running")
3. All orders in **non-terminal states** (PENDING, REVIEWED, ACCEPTED, INVOICED, PAID) are logged for recovery
4. On graceful shutdown, a final heartbeat with status "shutdown" is written

**Check state info:**
```bash
curl http://localhost:8000/health/state
```

**Simulate crash recovery:**
```bash
# 1. Create and progress an order
# 2. Kill the server (Ctrl+C or kill -9)
# 3. Restart the server
# 4. Check logs for: "State recovery: found X orders pending processing"
```

### 10.5 Request ID Tracing

Every HTTP request receives a unique `X-Request-ID` header for log correlation.

```bash
curl -v http://localhost:8000/health/live 2>&1 | grep X-Request-ID
```

Output:
```
< X-Request-ID: a1b2c3d4e5f6
```

You can also pass your own:
```bash
curl -H "X-Request-ID: my-custom-trace-id" http://localhost:8000/health/live
```

### 10.6 Health Endpoints

| Endpoint | Purpose | Expected Status |
|----------|---------|-----------------|
| `/health/live` | Liveness probe (process alive) | Always 200 |
| `/health/ready` | Readiness probe (DB connected) | 200 or 503 |
| `/health/degradation` | Degradation state | Always 200 |
| `/health/queue` | Queue metrics | Always 200 |
| `/health/state` | State manager info | Always 200 |

---

## 11. Testing & Verification

### 11.1 Run Automated Integration Test (Full Workflow)

This test exercises the complete 7-step workflow using the FastAPI TestClient:

```bash
uv run python test_workflow.py
```

Expected output:
```
✅ Health checks passed
✅ Customer created: a1b2...
✅ Product created: b2c3...
✅ Order queued: {'status': 'accepted', 'message': 'Order queued for processing'}
✅ Order placed: c3d4..., status: PENDING
✅ Order reviewed: REVIEWED
✅ Order accepted: ACCEPTED
✅ Invoice queued: {'status': 'accepted', 'message': 'Invoice queued for processing'}
✅ Invoice created: d4e5..., status: ISSUED
✅ Payment queued: {'status': 'accepted', 'message': 'Payment queued for processing'}
✅ Payment processed: e5f6..., status: COMPLETED
✅ Invoice correctly marked as PAID after payment
✅ Payment verified: COMPLETED
✅ Order shipped: SHIPPED
✅ Order closed: CLOSED

📋 Final Order: { ... "status": "CLOSED" ... }

🎉 All tests passed!
```

### 11.2 Run HTTP Integration Test (Requires Running Server)

```bash
# Start the server in one terminal
uv run python -m app.main

# In another terminal, run the test
uv run python test_integration.py
```

### 11.3 NFR Verification Steps

#### NFR 1.1 — Response Time

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Run load test
ab -n 200 -c 20 http://localhost:8000/api/v1/products

# Expected: avg latency < 200ms, no failed requests
```

#### NFR 1.2 — Concurrency

```bash
# Send 10 concurrent order placements
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8000/api/v1/orders \
    -H "Content-Type: application/json" \
    -d "{\"customer_id\":\"$CUSTOMER_ID\",\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":1}]}" &
done
wait

# Check queue processed all
curl http://localhost:8000/health/queue
```

#### NFR 1.3 — Queue Management

```bash
# Set small queue size
export OMS_QUEUE_MAX_SIZE=10

# Restart server, then rapidly enqueue many tasks
for i in $(seq 1 100); do
  curl -s -X POST http://localhost:8000/api/v1/orders \
    -H "Content-Type: application/json" \
    -d "{\"customer_id\":\"$CUSTOMER_ID\",\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":1}]}" &
done
wait

# Verify dropped_count > 0
curl http://localhost:8000/health/queue
```

#### NFR 2.1 — Graceful Degradation

```bash
# Set a very low memory threshold
export OMS_DEGRADATION_MEMORY_THRESHOLD_MB=1

# Restart server, then try product search
curl http://localhost:8000/api/v1/products?q=test
# Expected: 503 Service Unavailable

# Check degradation status
curl http://localhost:8000/health/degradation
# {"degraded":true,"product_search_disabled":true,...}
```

#### NFR 2.2 — Fault Detection & Recovery

The circuit breaker is used for the simulated payment gateway call. To observe it:

1. Check the application logs for circuit breaker state transitions
2. The circuit breaker metrics are tracked in-memory
3. After `OMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD` failures, the circuit opens
4. After `OMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT` seconds, it transitions to HALF_OPEN

#### NFR 2.3 — State Preservation

```bash
# 1. Create an order and progress it to REVIEWED
# 2. Kill the server process (kill -9)
# 3. Restart the server
# 4. Check logs for: "State recovery: found 1 orders pending processing"
# 5. Verify the order is still in REVIEWED status
curl http://localhost:8000/api/v1/orders/<id>
```

---

## 12. Configuration Reference

All configuration is via environment variables with the `OMS_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_DATABASE_URL` | `sqlite+aiosqlite:///./oms.db` | Database connection string |
| `OMS_DATABASE_ECHO` | `false` | Log all SQL queries |
| `OMS_DATABASE_POOL_SIZE` | `10` | Connection pool size |
| `OMS_DATABASE_MAX_OVERFLOW` | `20` | Max overflow connections |
| `OMS_HOST` | `0.0.0.0` | Server bind address |
| `OMS_PORT` | `8000` | Server port |
| `OMS_RELOAD` | `false` | Auto-reload on code changes |
| `OMS_REQUEST_TIMEOUT_SECONDS` | `30` | Request timeout |
| `OMS_QUEUE_MAX_SIZE` | `1000` | Max async queue size |
| `OMS_QUEUE_WORKER_COUNT` | `4` | Number of queue workers |
| `OMS_QUEUE_POLL_INTERVAL_SECONDS` | `0.1` | Queue poll interval |
| `OMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `OMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `30.0` | Seconds before half-open retry |
| `OMS_DEGRADATION_MEMORY_THRESHOLD_MB` | `512` | Memory threshold for degradation |
| `OMS_DEGRADATION_CPU_THRESHOLD_PERCENT` | `90.0` | CPU threshold for degradation |
| `OMS_STATE_POLL_INTERVAL_SECONDS` | `5.0` | Heartbeat interval |

### Using a `.env` File

```bash
echo "OMS_DATABASE_URL=sqlite+aiosqlite:///./oms.db" > .env
echo "OMS_PORT=8000" >> .env
echo "OMS_QUEUE_WORKER_COUNT=8" >> .env
uv run python -m app.main
```

---

## 13. Docker Deployment

### 13.1 Build and Run with Docker Compose

```bash
# Build the image
docker compose build

# Start the service
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### 13.2 Verify Docker Deployment

```bash
curl http://localhost:8000/health/live
# {"status":"alive","uptime_seconds":12.34}

curl http://localhost:8000/health/ready
# {"status":"ready"}
```

### 13.3 Docker Compose Configuration

The `docker-compose.yml` includes:
- **Resource limits:** 512MB memory, 1 CPU
- **Health check:** Every 30s via `/health/live`
- **Persistent volume:** `oms_data` for SQLite database
- **Restart policy:** `unless-stopped`

### 13.4 Manual Docker Build

```bash
docker build -t oms-backend .
docker run -d \
  --name oms-backend \
  -p 8000:8000 \
  -v oms_data:/app/data \
  -e OMS_DATABASE_URL=sqlite+aiosqlite:///data/oms.db \
  oms-backend
```

---

## 14. Troubleshooting

### 14.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'app'` | Not running from project root | Run from the `oms-backend` directory |
| `sqlite3.OperationalError: unable to open database file` | Permission issue | Ensure write access to the project directory |
| `Port 8000 already in use` | Another process on the port | Change port: `OMS_PORT=8001 uv run python -m app.main` |
| Queue tasks not processing | Workers not started | Check logs for "QueueManager started" |
| Product search returns 503 | System is degraded | Check `/health/degradation`; reduce load or increase thresholds |
| `ValueError: Cannot pay order in status ...` | Wrong workflow step | Follow the 7-step workflow in order |
| Database locked errors | Multiple processes accessing SQLite | Use a single server process; SQLite WAL mode helps |

### 14.2 Checking Logs

```bash
# Local development
uv run python -m app.main 2>&1 | grep -i "error\|warning\|exception"

# Docker
docker compose logs -f | grep -i "error\|warning\|exception"
```

### 14.3 Resetting the Database

```bash
# Stop the server, then delete the database file
rm -f oms.db oms.db-wal oms.db-shm

# Restart the server (tables will be recreated)
uv run python -m app.main
```

### 14.4 Performance Tuning

For higher throughput:

```bash
# Increase queue workers
export OMS_QUEUE_WORKER_COUNT=8

# Increase queue size
export OMS_QUEUE_MAX_SIZE=5000

# Increase connection pool
export OMS_DATABASE_POOL_SIZE=20
export OMS_DATABASE_MAX_OVERFLOW=40

# Increase resource thresholds
export OMS_DEGRADATION_MEMORY_THRESHOLD_MB=1024
export OMS_DEGRADATION_CPU_THRESHOLD_PERCENT=95.0
```

---

## Appendix: Project Structure

```
oms-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application entry point, DI wiring
│   ├── config.py            # Environment-based configuration
│   ├── database.py          # SQLAlchemy engine, session factory, WAL mode
│   ├── models/
│   │   ├── __init__.py
│   │   ├── entities.py      # SQLAlchemy ORM models
│   │   └── enums.py         # Domain enums (OrderStatus, PaymentStatus, etc.)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── customer_schema.py
│   │   ├── product_schema.py
│   │   ├── order_schema.py
│   │   ├── payment_schema.py
│   │   └── invoice_schema.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py          # Generic CRUD base repository
│   │   ├── customer_repo.py
│   │   ├── product_repo.py
│   │   ├── order_repo.py
│   │   ├── payment_repo.py
│   │   └── invoice_repo.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── customer_service.py
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   └── invoice_service.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── customer_controller.py
│   │   ├── product_controller.py
│   │   ├── order_controller.py
│   │   ├── payment_controller.py
│   │   └── invoice_controller.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── queue_manager.py         # Async priority queue (NFR 1.3)
│       ├── graceful_degradation.py  # Resource monitoring (NFR 2.1)
│       ├── circuit_breaker.py       # Fault detection (NFR 2.2)
│       ├── state_manager.py         # State preservation (NFR 2.3)
│       └── health_check.py         # Health endpoints
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── docker-compose.yml
├── openapi.yaml
├── test_workflow.py         # Full workflow integration test
├── test_integration.py      # HTTP-based integration test
├── README.md                # Technical documentation
└── manual.md                # This user manual
```

---

*© 2025 ChatDev. This document is maintained by the Chief Product Officer.*
