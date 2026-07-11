# Order Management System (OMS) — User Manual

> **Product:** OMS Backend  
> **Version:** 1.0.0  
> **Author:** ChatDev — Chief Product Officer  
> **Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / SQLite / Docker

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Installation & Deployment](#3-installation--deployment)
4. [Quick Start Guide](#4-quick-start-guide)
5. [Complete User Workflow](#5-complete-user-workflow)
6. [API Reference](#6-api-reference)
7. [Fault Tolerance Features](#7-fault-tolerance-features)
8. [Reliability Verification](#8-reliability-verification)
9. [Project Structure](#9-project-structure)
10. [Configuration Reference](#10-configuration-reference)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that manages the complete order lifecycle:

```
Customer Ordering → Payment Processing → Invoicing → Shipping → Closure
```

It serves three distinct roles:

| Role | Description |
|------|-------------|
| **Customer** | Places orders, makes payments |
| **Order Staff** | Reviews, accepts, ships, and closes orders |
| **Accountant** | Creates invoices, verifies payments |

The system is built with **reliability and fault tolerance** as first-class concerns:

- **Graceful Degradation (NFR 2.1):** Under extreme load, non-essential features (recommendations, analytics) automatically turn off while core checkout stays up.
- **Fault Detection & Recovery (NFR 2.2):** Health endpoints monitor system health; database connection drops are detected and automatically recovered.
- **State Preservation (NFR 2.3):** A transactional outbox pattern ensures zero order state loss even if the process is killed mid-operation.

---

## 2. System Overview

### 2.1 Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Routers     │  │  Services    │  │  Middleware       │  │
│  │  (REST API)  │──│  (Business   │──│  (Degradation)   │  │
│  │              │  │   Logic)     │  │  (Circuit Brkr)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                          │                                   │
│  ┌───────────────────────┴──────────────────────────────┐   │
│  │              Repositories (Data Access)                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │   │
│  │  │ Customer │ │  Order   │ │  Outbox (NFR 2.3)    │  │   │
│  │  │ Product  │ │ Payment  │ │  (State Preservation)│  │   │
│  │  │          │ │ Invoice  │ │                      │  │   │
│  │  └──────────┘ └──────────┘ └──────────────────────┘  │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                   │
│  ┌───────────────────────┴──────────────────────────────┐   │
│  │              SQLite (WAL mode)                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │   │
│  │  │ customers│ │  orders  │ │  outbox_messages     │  │   │
│  │  │ products │ │ payments │ │  (durable queue)     │  │   │
│  │  │          │ │ invoices │ │                      │  │   │
│  │  └──────────┘ └──────────┘ └──────────────────────┘  │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────┐
  │  Background  │  Outbox Worker (daemon thread)
  │  Worker      │  Polls outbox_messages every 2s
  └──────────────┘
```

### 2.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Language** | Python 3.12 | Rich ecosystem, async support, rapid development |
| **Framework** | FastAPI | Async-first, automatic OpenAPI docs, high performance |
| **Database** | SQLite (WAL mode) | Zero-infrastructure, crash-safe durability via WAL journaling |
| **State Preservation** | Transactional Outbox | Same-DB outbox table ensures atomicity; no external broker needed |
| **Fault Tolerance** | Circuit Breaker + Health Endpoints | Prevents cascading failures; enables orchestration-level recovery |
| **Deployment** | Docker Compose | `restart: always` policy ensures auto-recovery on crash |

---

## 3. Installation & Deployment

### 3.1 Prerequisites

- **Python 3.12+** (for local development)
- **uv** (Python package manager) — install with `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker & Docker Compose** (for containerized deployment)
- **stress** (for degradation testing) — `apt install stress` or `brew install stress`

### 3.2 Local Installation (No Docker)

```bash
# 1. Clone or navigate to the project directory
cd oms-backend

# 2. Install dependencies using uv
uv sync

# 3. Run the server
uv run python -m oms.main
```

The API will be available at **http://localhost:8000**.

### 3.3 Docker Deployment

```bash
# Build and start the container
docker compose up --build

# Run in detached mode
docker compose up -d --build

# View logs
docker compose logs -f

# Stop the service
docker compose down
```

The API will be available at **http://localhost:8000**.

### 3.4 Docker Compose Configuration

The `docker-compose.yml` includes:

- **`restart: always`** — automatically restarts the container if the process crashes (NFR 2.3)
- **Health check** — pings `/api/v1/health/ping` every 10 seconds
- **Persistent volume** — SQLite database stored in a Docker volume for data durability
- **Configurable environment variables** — all settings can be overridden

### 3.5 systemd Service (Alternative)

For non-Docker Linux deployments, create `/etc/systemd/system/oms.service`:

```ini
[Unit]
Description=OMS Backend
After=network.target

[Service]
Type=simple
User=oms
WorkingDirectory=/opt/oms
ExecStart=/opt/oms/.venv/bin/uvicorn oms.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable oms
sudo systemctl start oms
```

---

## 4. Quick Start Guide

### 4.1 Verify the Service is Running

```bash
# Liveness check
curl http://localhost:8000/api/v1/health/ping

# Expected response:
# {"status":"alive","uptime_seconds":12.34}

# Readiness check (includes DB health)
curl http://localhost:8000/api/v1/health/readiness

# Expected response:
# {"status":"ready","database":"healthy"}

# Degradation status
curl http://localhost:8000/api/v1/health/degradation

# Expected response:
# {"degraded":false,"cpu_percent":12.5,"memory_percent":45.2,...}
```

### 4.2 Interactive API Documentation

Open your browser to: **http://localhost:8000/docs**

This provides a fully interactive Swagger UI where you can explore and test every endpoint.

### 4.3 Seed Data Script

Run the following commands to create test data:

```bash
# Create a Customer
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "address": "123 Main St, Springfield",
    "phone": "+1-555-0100",
    "banking_details": "Bank of America, Account #12345"
  }'

# Create an Order Staff user
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bob (Staff)",
    "address": "456 Oak Ave",
    "phone": "+1-555-0200",
    "banking_details": "N/A",
    "role": "ORDER_STAFF"
  }'

# Create an Accountant user
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Carol (Accountant)",
    "address": "789 Pine Rd",
    "phone": "+1-555-0300",
    "banking_details": "N/A",
    "role": "ACCOUNTANT"
  }'

# Create a Product
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Wireless Bluetooth Headphones",
    "base_price": 79.99
  }'

# Create another Product
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "USB-C Charging Cable",
    "base_price": 12.99
  }'
```

---

## 5. Complete User Workflow

This section walks through the **full 7-step order lifecycle** with example API calls.

### Step 1: Customer Places an Order

**Actor:** Customer  
**Criticality:** ⚠️ **Critical** — must not fail

```bash
# First, capture the customer and product IDs
CUSTOMER_ID="<paste-customer-id-from-step-4>"
PRODUCT_ID_1="<paste-product-id-1>"
PRODUCT_ID_2="<paste-product-id-2>"

# Place an order with two line items
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"$CUSTOMER_ID\",
    \"line_items\": [
      {\"product_id\": \"$PRODUCT_ID_1\", \"quantity\": 2, \"unit_price\": 79.99},
      {\"product_id\": \"$PRODUCT_ID_2\", \"quantity\": 1, \"unit_price\": 12.99}
    ]
  }"

# Save the order ID
ORDER_ID="<paste-order-id-from-response>"
```

**What happens internally:**
1. Customer existence is validated
2. Product existence is validated
3. All line items must share the same currency
4. Order is created with status `CREATED`
5. An outbox message (`order.created`) is written in the **same database transaction**
6. The transaction is committed **before** the HTTP response is sent (NFR 2.3)

### Step 2: Order Staff Reviews & Accepts

**Actor:** Order Staff  
**Criticality:** ⚠️ **Critical**

```bash
# Accept the order (transition CREATED → ACCEPTED)
curl -X PATCH http://localhost:8000/api/v1/orders/$ORDER_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "ACCEPTED"}'
```

**State machine rules:**
- `CREATED` → `ACCEPTED` (allowed)
- `CREATED` → `CANCELLED` (allowed)
- Order must have at least one line item before acceptance

### Step 3: Accountant Creates Invoice

**Actor:** Accountant  
**Criticality:** ⚠️ **Critical**

```bash
# Create an invoice for the accepted order
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"billing_name\": \"Alice Johnson\",
    \"billing_address\": \"123 Main St, Springfield\",
    \"total_amount\": 172.97,
    \"currency\": \"USD\"
  }"

# Save the invoice ID
INVOICE_ID="<paste-invoice-id-from-response>"
```

**What happens internally:**
1. Order must be in `ACCEPTED` status
2. Duplicate invoices for the same order are prevented
3. Invoice amount must match order total
4. Invoice currency must match order currency
5. Order is transitioned to `INVOICED` with `invoice_ref` set
6. Outbox messages are written for both the invoice and the order status change

### Step 4: Customer Pays Invoice

**Actor:** Customer  
**Criticality:** ⚠️ **Critical**

```bash
# Make a payment
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER_ID\",
    \"amount\": 172.97,
    \"currency\": \"USD\",
    \"method\": \"CREDIT_CARD\"
  }"

# Save the payment ID
PAYMENT_ID="<paste-payment-id-from-response>"
```

**Validation rules:**
- Order must be in `INVOICED` status
- Payment amount must match order total
- Payment currency must match order currency

### Step 5: Accountant Verifies Payment

**Actor:** Accountant  
**Criticality:** ⚠️ **Critical**

```bash
# Verify the payment
curl -X POST http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify
```

**What happens internally (all in one transaction):**
1. Payment status changes from `PENDING` → `COMPLETED`
2. Order status changes from `INVOICED` → `PAID`
3. Invoice status changes from `ISSUED` → `PAID`
4. Outbox messages are written for all three entities
5. Optimistic locking prevents concurrent modifications

### Step 6: Order Staff Ships Paid Order

**Actor:** Order Staff  
**Criticality:** ⚠️ **Critical**

```bash
# Ship the order (transition PAID → SHIPPED)
curl -X PATCH http://localhost:8000/api/v1/orders/$ORDER_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "SHIPPED"}'
```

**Precondition:** Order must be in `PAID` status.

### Step 7: Order Staff Closes Completed Order

**Actor:** Order Staff  
**Criticality:** ⚠️ **Critical**

```bash
# Close the order (transition SHIPPED → CLOSED)
curl -X PATCH http://localhost:8000/api/v1/orders/$ORDER_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "CLOSED"}'
```

**Precondition:** Order must be in `SHIPPED` status.

### Complete State Machine

```
CREATED ──→ ACCEPTED ──→ INVOICED ──→ PAID ──→ SHIPPED ──→ CLOSED
    │            │            │
    └──→ CANCELLED ←──┘            └──→ CANCELLED
```

---

## 6. API Reference

### 6.1 Health Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Root info (service name, version, docs link) |
| `GET` | `/api/v1/health/ping` | Liveness probe — always returns 200 if process is alive |
| `GET` | `/api/v1/health/readiness` | Readiness probe — checks DB connectivity |
| `GET` | `/api/v1/health/degradation` | Reports CPU/memory load and degradation status |

### 6.2 Customer Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/customers` | Create a new customer |
| `GET` | `/api/v1/customers` | List all customers |
| `GET` | `/api/v1/customers/{id}` | Get a customer by ID |
| `PUT` | `/api/v1/customers/{id}` | Update a customer |
| `DELETE` | `/api/v1/customers/{id}` | Delete a customer |

**Customer Create Request Body:**
```json
{
  "name": "Alice Johnson",
  "address": "123 Main St",
  "phone": "+1-555-0100",
  "banking_details": "Bank of America, Account #12345",
  "role": "CUSTOMER"
}
```

**Roles:** `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT`

### 6.3 Product Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/products` | Create a new product |
| `GET` | `/api/v1/products` | List all products |
| `GET` | `/api/v1/products/{id}` | Get a product by ID |
| `PUT` | `/api/v1/products/{id}` | Update a product |
| `DELETE` | `/api/v1/products/{id}` | Delete a product |

**Product Create Request Body:**
```json
{
  "description": "Wireless Bluetooth Headphones",
  "base_price": 79.99,
  "currency": "USD"
}
```

### 6.4 Order Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/orders` | Place a new order |
| `GET` | `/api/v1/orders` | List orders (with optional filters) |
| `GET` | `/api/v1/orders/{id}` | Get an order by ID |
| `PATCH` | `/api/v1/orders/{id}/status` | Transition order status |

**Order Create Request Body:**
```json
{
  "customer_id": "uuid-here",
  "line_items": [
    {"product_id": "uuid-here", "quantity": 2, "unit_price": 79.99, "currency": "USD"},
    {"product_id": "uuid-here", "quantity": 1, "unit_price": 12.99, "currency": "USD"}
  ]
}
```

**Order Status Transition Request Body:**
```json
{
  "status": "ACCEPTED"
}
```

**Valid status values:** `CREATED`, `ACCEPTED`, `INVOICED`, `PAID`, `SHIPPED`, `CLOSED`, `CANCELLED`

**List Orders Query Parameters:**
- `status` — filter by status (e.g., `?status=PAID`)
- `customer_id` — filter by customer (e.g., `?customer_id=uuid`)
- `skip` — pagination offset (default: 0)
- `limit` — pagination limit (default: 100)

### 6.5 Payment Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/payments` | Create a payment |
| `GET` | `/api/v1/payments/{id}` | Get a payment by ID |
| `POST` | `/api/v1/payments/{id}/verify` | Verify a payment (mark as completed) |
| `GET` | `/api/v1/payments/by-order/{order_id}` | List payments for an order |

**Payment Create Request Body:**
```json
{
  "order_id": "uuid-here",
  "amount": 172.97,
  "currency": "USD",
  "method": "CREDIT_CARD"
}
```

**Payment methods:** `CREDIT_CARD`, `DEBIT_CARD`, `BANK_TRANSFER`, `DIGITAL_WALLET`

### 6.6 Invoice Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/invoices` | Create an invoice |
| `GET` | `/api/v1/invoices` | List all invoices |
| `GET` | `/api/v1/invoices/{id}` | Get an invoice by ID |
| `GET` | `/api/v1/invoices/by-order/{order_id}` | List invoices for an order |

**Invoice Create Request Body:**
```json
{
  "order_id": "uuid-here",
  "billing_name": "Alice Johnson",
  "billing_address": "123 Main St, Springfield",
  "total_amount": 172.97,
  "currency": "USD",
  "due_date": "2025-12-31T23:59:59Z"
}
```

> **Note:** `due_date` is optional; defaults to 30 days from creation.

---

## 7. Fault Tolerance Features

### 7.1 Graceful Degradation (NFR 2.1)

**How it works:**

The `DegradationMiddleware` monitors system resources (CPU and memory) by reading `/proc/stat` and `/proc/meminfo` every 5 seconds. When thresholds are exceeded:

- **Non-essential paths** (e.g., `/api/v1/recommendations`, `/api/v1/analytics`, `/api/v1/debug`) return HTTP **503 Service Unavailable**
- **Core paths** (orders, payments, invoices, customers, products, health) continue to operate normally

**Configuration:**

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OMS_DEGRADATION_CPU_THRESHOLD` | `80.0` | CPU % that triggers degradation |
| `OMS_DEGRADATION_MEM_THRESHOLD` | `85.0` | Memory % that triggers degradation |

**Non-essential paths (degraded under load):**
- `/api/v1/recommendations`
- `/api/v1/analytics`
- `/api/v1/logs`
- `/api/v1/debug`

**Core paths (never degraded):**
- `/api/v1/orders`, `/api/v1/payments`, `/api/v1/invoices`
- `/api/v1/customers`, `/api/v1/products`
- `/api/v1/health`
- `/docs`, `/redoc`, `/openapi.json`

### 7.2 Circuit Breaker (NFR 2.1 & 2.2)

**How it works:**

The `CircuitBreaker` class implements a three-state circuit breaker:

```
CLOSED ──(failures ≥ threshold)──→ OPEN
  ↑                                      │
  │                                      │ (recovery_timeout elapsed)
  │                                      ▼
  └────(probe succeeds)── HALF_OPEN ←────┘
```

- **CLOSED:** Normal operation — all calls pass through
- **OPEN:** Calls are rejected immediately; fallback is used
- **HALF_OPEN:** Limited probe calls are allowed to test recovery

**Configuration:**

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OMS_CB_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `OMS_CB_RECOVERY_TIMEOUT` | `30.0` | Seconds before attempting half-open |
| `OMS_CB_HALF_OPEN_MAX_CALLS` | `3` | Probe calls allowed in half-open state |

**Where it's used:**
- **Health Service DB check** — prevents cascading failures when the database is down
- **Extensible** — can wrap any external service call

### 7.3 Health Endpoints (NFR 2.2)

Three health probes are available:

| Endpoint | Type | What it checks |
|----------|------|----------------|
| `/api/v1/health/ping` | Liveness | Process is alive (always 200) |
| `/api/v1/health/readiness` | Readiness | Database connectivity (SELECT 1) |
| `/api/v1/health/degradation` | Status | CPU/memory load vs. thresholds |

The readiness check uses a **circuit breaker** so that repeated DB failures don't cascade.

### 7.4 Transactional Outbox (NFR 2.3)

**How it works:**

Every critical state transition follows this pattern:

```
1. Begin transaction
2. Update domain entity (order, payment, invoice)
3. Write outbox message (same transaction)
4. Commit transaction
5. Send HTTP response
```

A **background worker thread** polls the `outbox_messages` table every 2 seconds for `PENDING` messages and processes them (e.g., sending notifications, updating search indexes).

**On restart after a crash:**
1. The server starts
2. The outbox worker begins polling
3. Any `PENDING` or `FAILED` (retry_count < 5) messages are replayed
4. No order state is lost

**Outbox message retry:** Failed messages are retried up to 5 times.

**Configuration:**

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OMS_OUTBOX_POLL_INTERVAL` | `2.0` | Seconds between outbox polls |

### 7.5 Database Connection Pool Pre-Ping (NFR 2.2)

The SQLAlchemy engine is configured with `pool_pre_ping=True`, which verifies database connections before each use. If a connection is stale or dropped, it is automatically replaced.

### 7.6 Optimistic Locking

Every entity has a `version` column. Updates use:

```sql
UPDATE table SET version = version + 1, ... WHERE id = :id AND version = :current_version
```

If the version doesn't match (concurrent modification), the update returns 0 rows and a `409 Conflict` is returned to the client.

---

## 8. Reliability Verification

### 8.1 Degradation Test (NFR 2.1)

**Goal:** Verify that under CPU saturation, non-essential features return 503 while core checkout remains available.

**Prerequisites:** Install `stress` (`apt install stress` or `brew install stress`)

**Steps:**

```bash
# Terminal 1: Start the OMS server
uv run python -m oms.main

# Terminal 2: Verify normal operation first
curl http://localhost:8000/api/v1/health/degradation
# → {"degraded":false,...}

# Terminal 3: Saturate CPU with 4 workers for 60 seconds
stress --cpu 4 --timeout 60

# While stress is running, in Terminal 2:
# 1. Check degradation status
curl http://localhost:8000/api/v1/health/degradation
# → {"degraded":true,"cpu_percent":95.0,...}

# 2. Non-essential path returns 503
curl -v http://localhost:8000/api/v1/recommendations
# → HTTP/1.1 503 Service Unavailable
# → {"error":"Service Unavailable","detail":"System is under heavy load...","degraded":true}

# 3. Core checkout still works
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health/ping
# → 200

curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/orders
# → 200

# After stress completes, verify recovery
curl http://localhost:8000/api/v1/health/degradation
# → {"degraded":false,...}
```

**Expected behavior:**
- During CPU saturation: degradation is `true`, non-essential paths return 503, core paths return 200
- After stress ends: degradation returns to `false` automatically

### 8.2 Recovery Test (NFR 2.2)

**Goal:** Verify that the system detects a database failure and automatically recovers without manual restart.

**Prerequisites:** The server must be running with a file-based SQLite database.

**Steps:**

```bash
# Terminal 1: Watch the readiness endpoint
watch -n 1 "curl -s http://localhost:8000/api/v1/health/readiness"

# Terminal 2: Simulate DB failure by removing permissions
# (Find the database file first - it's in the project root or /app/data)
chmod 000 oms_data.db

# Terminal 1 will show:
# → {"status":"degraded","database":"unhealthy"}

# Terminal 2: Restore access
chmod 644 oms_data.db

# Terminal 1 will auto-recover (within ~15 seconds due to circuit breaker):
# → {"status":"ready","database":"healthy"}
```

**Expected behavior:**
- When DB is inaccessible: readiness shows `"database": "unhealthy"`, `"status": "degraded"`
- When DB is restored: readiness auto-recovers to `"database": "healthy"`, `"status": "ready"`
- No server restart is required

### 8.3 State Preservation Test (NFR 2.3)

**Goal:** Verify that killing the process mid-operation does not result in data loss, and pending orders are recovered on restart.

**Steps:**

```bash
# Terminal 1: Start the server
uv run python -m oms.main

# Terminal 2: Create test data
CUSTOMER_ID=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","address":"123 Test St","phone":"555-0000","banking_details":"Test Bank"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

PRODUCT_ID=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Test Widget","base_price":25.00}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Place an order
ORDER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"line_items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":1,\"unit_price\":25.00}]}")
echo "$ORDER_RESPONSE" | python -c "import sys,json; d=json.load(sys.stdin); print('Order ID:', d['id'], 'Status:', d['status'])"
# → Order ID: <uuid> Status: CREATED

# Terminal 1: Kill the process forcefully
kill -9 $(pgrep -f "python -m oms.main")

# Terminal 1: Restart the server
uv run python -m oms.main

# Terminal 2: Verify the order still exists
curl http://localhost:8000/api/v1/orders
# → The order should be listed with status CREATED

# Verify outbox messages were processed (check logs for "Outbox message ... processed")
```

**Expected behavior:**
- After `kill -9` and restart, all orders created before the kill are still present
- The outbox worker replays any unprocessed messages
- No data loss occurs

### 8.4 Docker Crash Recovery Test

```bash
# Start the container
docker compose up -d

# Find the container ID
CONTAINER_ID=$(docker ps -q --filter "name=oms-backend")

# Kill the main process inside the container
docker exec $CONTAINER_ID kill -9 $(pgrep -f uvicorn)

# Docker will automatically restart the container (restart: always)
sleep 5

# Verify the service is back
curl http://localhost:8000/api/v1/health/ping
# → {"status":"alive",...}
```

---

## 9. Project Structure

```
oms-backend/
├── oms/                          # Main application package
│   ├── __init__.py               # Package marker
│   ├── config.py                 # Environment-based configuration
│   ├── database.py               # SQLAlchemy engine + session management
│   ├── main.py                   # FastAPI app + outbox worker (NFR 2.3)
│   │
│   ├── models/                   # Domain models (SQLAlchemy ORM)
│   │   ├── enums.py              # OrderStatus, PaymentStatus, etc.
│   │   └── entities.py           # CustomerModel, OrderModel, etc.
│   │
│   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── customer.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── invoice.py
│   │
│   ├── repositories/             # Data access layer
│   │   ├── base.py               # Generic CRUD + outbox helpers
│   │   ├── customer_repo.py
│   │   ├── product_repo.py
│   │   ├── order_repo.py
│   │   ├── payment_repo.py
│   │   ├── invoice_repo.py
│   │   └── outbox_repo.py        # Outbox polling + retry (NFR 2.2, 2.3)
│   │
│   ├── services/                 # Business logic
│   │   ├── order_service.py      # Order lifecycle + state machine
│   │   ├── payment_service.py    # Payment creation + verification
│   │   ├── invoice_service.py    # Invoice creation
│   │   ├── health_service.py     # Health probes (NFR 2.2)
│   │   └── circuit_breaker.py    # Circuit breaker (NFR 2.1)
│   │
│   ├── routers/                  # REST API endpoints
│   │   ├── health.py             # Health endpoints (NFR 2.2)
│   │   ├── customer.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── invoice.py
│   │
│   ├── middleware/
│   │   └── degradation.py        # Graceful degradation (NFR 2.1)
│   │
│   └── utils/
│       └── system.py             # CPU/memory monitoring
│
├── Dockerfile                    # Multi-stage Docker build
├── docker-compose.yml            # Docker Compose with restart: always
├── openapi.yaml                  # OpenAPI 3.1 specification
├── pyproject.toml                # Python project config
├── README.md                     # Technical documentation
└── manual.md                     # This user manual
```

---

## 10. Configuration Reference

All configuration is via environment variables with sensible defaults.

### 10.1 Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_HOST` | `0.0.0.0` | Bind address |
| `OMS_PORT` | `8000` | HTTP port |
| `OMS_RELOAD` | `false` | Auto-reload on code changes (dev only) |

### 10.2 Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_DATABASE_URL` | `sqlite:///./oms_data.db` | Database connection string |
| `OMS_DB_POOL_SIZE` | `5` | Connection pool size |
| `OMS_DB_MAX_OVERFLOW` | `10` | Max overflow connections |

> **Note:** For PostgreSQL, set `OMS_DATABASE_URL` to `postgresql://user:pass@host:5432/omsdb`.

### 10.3 Circuit Breaker Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_CB_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `OMS_CB_RECOVERY_TIMEOUT` | `30.0` | Seconds before half-open attempt |
| `OMS_CB_HALF_OPEN_MAX_CALLS` | `3` | Probe calls in half-open state |

### 10.4 Retry Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_RETRY_MAX_ATTEMPTS` | `3` | Max retry attempts |
| `OMS_RETRY_MIN_WAIT` | `1.0` | Initial retry delay (seconds) |
| `OMS_RETRY_MAX_WAIT` | `10.0` | Maximum retry delay (seconds) |

### 10.5 Degradation Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_DEGRADATION_CPU_THRESHOLD` | `80.0` | CPU % threshold |
| `OMS_DEGRADATION_MEM_THRESHOLD` | `85.0` | Memory % threshold |

### 10.6 Outbox Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_OUTBOX_POLL_INTERVAL` | `2.0` | Outbox poll interval (seconds) |

### 10.7 Example Configuration

```bash
# Production-like configuration
export OMS_DATABASE_URL="sqlite:////app/data/oms_data.db"
export OMS_HOST="0.0.0.0"
export OMS_PORT="8000"
export OMS_CB_FAILURE_THRESHOLD="5"
export OMS_CB_RECOVERY_TIMEOUT="30.0"
export OMS_DEGRADATION_CPU_THRESHOLD="80.0"
export OMS_DEGRADATION_MEM_THRESHOLD="85.0"
export OMS_OUTBOX_POLL_INTERVAL="2.0"
```

---

## 11. Troubleshooting

### 11.1 Common Issues

| Issue | Likely Cause | Solution |
|-------|-------------|----------|
| `sqlite3.OperationalError: database is locked` | Concurrent write contention | SQLite is single-writer; reduce concurrent write requests or switch to PostgreSQL |
| `ModuleNotFoundError: No module named 'oms'` | Wrong working directory | Run from the project root (where `oms/` directory is) |
| `Connection refused` on port 8000 | Server not running | Check `docker ps` or `pgrep -f uvicorn` |
| `409 Conflict` on update | Concurrent modification | Retry the request (another client modified the entity) |
| `400 Bad Request: Cannot transition from X to Y` | Invalid state transition | Check the state machine rules in Section 5 |
| Degradation shows `true` unexpectedly | High system load | Check CPU/memory with `top` or `htop` |
| Readiness shows `"database": "unhealthy"` | DB file permissions | Check `chmod` on the SQLite file |

### 11.2 Logs

The application logs to stdout with the format:

```
2025-07-11 07:05:11,123 [INFO] oms.main: Outbox worker started – polling every 2.0 s
2025-07-11 07:05:11,456 [INFO] oms.services.order_service: Order <uuid> created for customer <uuid>
2025-07-11 07:05:11,789 [WARNING] oms.middleware.degradation: Degradation triggered: cpu=95.3% mem=72.1%
```

To increase log verbosity, set the `LOG_LEVEL` environment variable (not yet implemented — logs are set to INFO level in `main.py`).

### 11.3 Database File Location

- **Local:** `./oms_data.db` (in the project root)
- **Docker:** `/app/data/oms_data.db` (persisted in Docker volume `oms-data`)

### 11.4 Resetting the Database

To start fresh:

```bash
# Local
rm oms_data.db oms_data.db-wal oms_data.db-shm

# Docker
docker compose down -v  # -v removes the volume
docker compose up -d
```

---

## Appendix: NFR Traceability Matrix

| NFR | Mechanism | Component | How to Verify |
|-----|-----------|-----------|---------------|
| **2.1 Graceful Degradation** | DegradationMiddleware monitors CPU/mem; CircuitBreaker wraps DB calls | `middleware/degradation.py`, `services/circuit_breaker.py`, `utils/system.py` | Run `stress --cpu 4 --timeout 60`; non-essential paths return 503, core paths return 200 |
| **2.2 Fault Detection & Recovery** | Health endpoints (ping/readiness/degradation); `pool_pre_ping=True`; CircuitBreaker auto-recovery | `routers/health.py`, `services/health_service.py`, `database.py` | `chmod 000` on DB file; readiness shows unhealthy; `chmod 644` restores healthy without restart |
| **2.3 State Preservation** | Transactional outbox pattern; same-DB outbox table; background worker replays on restart | `models/entities.py` (OutboxMessage), `repositories/outbox_repo.py`, `main.py` (outbox_worker) | `kill -9` the process; restart; verify orders exist and outbox messages were processed |

---

*This manual was prepared by the ChatDev Chief Product Officer. For technical support, refer to the README.md or open an issue in the project repository.*
