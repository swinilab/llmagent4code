# OMS Backend — Order Management System — User Manual

> **Version:** 1.0.0  
> **Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0, SQLite  
> **Author:** ChatDev — Chief Product Officer

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Main Functions](#2-main-functions)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Installation & Environment Setup](#4-installation--environment-setup)
5. [Running the Application](#5-running-the-application)
6. [API Reference — Complete Workflow](#6-api-reference--complete-workflow)
7. [Role-Based Workflow Walkthrough](#7-role-based-workflow-walkthrough)
8. [Non-Functional Requirements — How to Observe](#8-non-functional-requirements--how-to-observe)
9. [Configuration Reference](#9-configuration-reference)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade, backend-only REST API that serves the complete e-commerce order lifecycle:

1. **Customer** places an order
2. **Order Staff** reviews and accepts the order
3. **Accountant** creates an invoice for the accepted order
4. **Customer** pays the invoice
5. **Accountant** verifies the payment
6. **Order Staff** ships the paid order
7. **Order Staff** closes the completed order

The system is built with three non-functional requirements (NFRs) baked into its architecture:

| NFR | What it means |
|-----|---------------|
| **Graceful Degradation** | Under resource contention, non-essential features (invoicing, shipping) degrade while core checkout stays available |
| **Fault Detection & Recovery** | The system detects internal failures and automatically attempts recovery |
| **State Preservation** | After a crash, the system restores its operational state and resumes processing pending orders |

---

## 2. Main Functions

### 2.1 Entity Management

| Function | Endpoint | Description |
|----------|----------|-------------|
| Register Customer | `POST /api/v1/customers` | Create a new customer (CUSTOMER, ORDER_STAFF, or ACCOUNTANT role) |
| List Customers | `GET /api/v1/customers` | Retrieve all registered customers |
| Get Customer | `GET /api/v1/customers/{id}` | Retrieve a single customer by UUID |
| Create Product | `POST /api/v1/products` | Create a new product with price and currency |
| List Products | `GET /api/v1/products` | Retrieve all products |
| Get Product | `GET /api/v1/products/{id}` | Retrieve a single product by UUID |

### 2.2 Order Lifecycle (7-Step Workflow)

| Step | Action | Endpoint | Performed By |
|------|--------|----------|-------------|
| 1 | Place order | `POST /api/v1/orders` | Customer |
| 2 | Accept order | `PATCH /api/v1/orders/{id}/accept` | Order Staff |
| 3 | Create invoice | `POST /api/v1/orders/{id}/invoice` | Accountant |
| 4 | Record payment | `POST /api/v1/orders/{id}/payments` | Customer |
| 5 | Verify payment | `POST /api/v1/orders/payments/{id}/verify` | Accountant |
| 6 | Ship order | `PATCH /api/v1/orders/{id}/ship` | Order Staff |
| 7 | Close order | `PATCH /api/v1/orders/{id}/close` | Order Staff |
| — | Cancel order | `PATCH /api/v1/orders/{id}/cancel` | Order Staff |

### 2.3 Infrastructure

| Function | Endpoint | Description |
|----------|----------|-------------|
| Health Check | `GET /health` | Reports database health, circuit breaker states, and app version |
| API Docs (Swagger) | `GET /docs` | Interactive OpenAPI documentation |
| API Docs (ReDoc) | `GET /redoc` | Alternative API documentation |
| OpenAPI Spec | `GET /openapi.json` | Raw OpenAPI 3.1 specification |

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Application                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │  Controllers  │──▶│   Services   │──▶│ Repositories │ │
│  │  (REST API)   │   │  (Business)  │   │   (Data)     │ │
│  └──────────────┘   └──────────────┘   └──────────────┘ │
│                            │                              │
│                            ▼                              │
│                   ┌──────────────────┐                   │
│                   │  Infrastructure   │                   │
│                   │  • Circuit Breaker│                   │
│                   │  • Event Log     │                   │
│                   │  • Health Check  │                   │
│                   └──────────────────┘                   │
│                            │                              │
│                            ▼                              │
│                   ┌──────────────────┐                   │
│                   │  SQLite Database │                   │
│                   │  (oms.db)        │                   │
│                   └──────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Database** | SQLite + SQLAlchemy ORM | Zero-config local deployment; swap to PostgreSQL for production |
| **Web Framework** | FastAPI | Native async, automatic OpenAPI generation, dependency injection |
| **Graceful Degradation** | Circuit Breaker pattern | Non-essential features (invoice, shipping, payment) use separate breakers; core checkout uses a higher-threshold breaker |
| **State Preservation** | Append-only Event Log | Every state transition is recorded; on startup, pending orders are recovered from the log |
| **Layered Architecture** | Controller → Service → Repository | Strict separation of concerns; each layer independently testable |

---

## 4. Installation & Environment Setup

### 4.1 Prerequisites

- **Python 3.12+** (required)
- **uv** (fast Python package manager) — *recommended*
- **Docker & Docker Compose** — *optional, for containerized deployment*

### 4.2 Verify Python Version

```bash
python --version
# Must be Python 3.12 or higher
```

### 4.3 Install `uv` (if not already installed)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### 4.4 Clone / Navigate to the Project

The OMS code lives in the `oms/` subdirectory. All commands below assume you are inside `oms/`:

```bash
cd oms
```

### 4.5 Create Virtual Environment & Install Dependencies

```bash
# Create a virtual environment
uv venv

# Activate it
# macOS / Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install all dependencies
uv sync
```

This installs:

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ≥0.139.0 | Web framework |
| `uvicorn[standard]` | ≥0.51.0 | ASGI server |
| `sqlalchemy` | ≥2.0.51 | ORM / database |
| `pydantic` | ≥2.13.4 | Data validation |
| `pydantic-settings` | ≥2.14.2 | Configuration management |
| `pyyaml` | ≥6.0.3 | YAML parsing (OpenAPI) |

### 4.6 Verify Installation

```bash
# Quick smoke test — loads the app and prints all registered routes
uv run python ../test_import.py
```

Expected output:

```
App loaded successfully
  Route: /health
  Route: /api/v1/customers
  Route: /api/v1/customers/{customer_id}
  Route: /api/v1/products
  Route: /api/v1/products/{product_id}
  Route: /api/v1/orders
  Route: /api/v1/orders/{order_id}
  Route: /api/v1/orders/{order_id}/accept
  Route: /api/v1/orders/{order_id}/invoice
  Route: /api/v1/orders/{order_id}/payments
  Route: /api/v1/orders/payments/{payment_id}/verify
  Route: /api/v1/orders/{order_id}/ship
  Route: /api/v1/orders/{order_id}/close
  Route: /api/v1/orders/{order_id}/cancel
```

---

## 5. Running the Application

### 5.1 Option A — Direct (No Docker)

```bash
cd oms
source .venv/bin/activate   # or .venv\Scripts\activate

# Run with hot-reload (development)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run in production mode
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5.2 Option B — Using the CLI Entry Point

```bash
cd oms
uv run oms
```

### 5.3 Option C — Docker Compose (Recommended for Production-like Environment)

```bash
cd oms
docker compose up --build
```

This will:
- Build the Docker image from `Dockerfile`
- Start the service on port `8000`
- Mount a persistent volume for the SQLite database (`oms_data`)
- Configure a health check (curl `http://localhost:8000/health` every 30s)

### 5.4 Verify the Application is Running

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "database": "healthy",
  "circuit_breakers": {
    "invoice": "CLOSED",
    "checkout": "CLOSED",
    "payment": "CLOSED",
    "shipping": "CLOSED"
  },
  "version": "1.0.0"
}
```

### 5.5 Open API Documentation

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 6. API Reference — Complete Workflow

### 6.1 Create a Customer

```bash
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "address": "123 Main St, Springfield",
    "phone": "+1-555-0100",
    "banking_details": "Bank of America, Account #12345",
    "role": "CUSTOMER"
  }'
```

**Response** (201 Created):

```json
{
  "id": "a1b2c3d4-...",
  "name": "Alice Johnson",
  "address": "123 Main St, Springfield",
  "phone": "+1-555-0100",
  "banking_details": "Bank of America, Account #12345",
  "role": "CUSTOMER"
}
```

> **Save the `id`** — you will need it as `customer_id` when placing an order.

### 6.2 Create an Order Staff User

```bash
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bob Staff",
    "address": "456 Office Blvd, Metropolis",
    "phone": "+1-555-0200",
    "banking_details": "",
    "role": "ORDER_STAFF"
  }'
```

### 6.3 Create an Accountant User

```bash
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Carol Accountant",
    "address": "789 Finance Ave, Gotham",
    "phone": "+1-555-0300",
    "banking_details": "Chase, Account #67890",
    "role": "ACCOUNTANT"
  }'
```

### 6.4 Create a Product

```bash
curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Wireless Bluetooth Headphones",
    "base_price": 79.99,
    "currency": "USD"
  }'
```

**Response** (201 Created):

```json
{
  "id": "e5f6a7b8-...",
  "description": "Wireless Bluetooth Headphones",
  "base_price": 79.99,
  "currency": "USD"
}
```

> **Save the `id`** — you will need it as `product_id` when placing an order.

### 6.5 List All Customers

```bash
curl -s http://localhost:8000/api/v1/customers | python -m json.tool
```

### 6.6 List All Products

```bash
curl -s http://localhost:8000/api/v1/products | python -m json.tool
```

---

## 7. Role-Based Workflow Walkthrough

This section walks through the complete 7-step order lifecycle using `curl` commands.

### Step 1 — Customer Places an Order

```bash
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<CUSTOMER_UUID>",
    "line_items": [
      {
        "product_id": "<PRODUCT_UUID>",
        "quantity": 2,
        "unit_price": 79.99,
        "currency": "USD"
      }
    ]
  }'
```

**Response** (201 Created):

```json
{
  "id": "order-uuid-1",
  "customer_id": "<CUSTOMER_UUID>",
  "status": "PENDING",
  "created_at": "2025-07-11T01:43:42Z",
  "updated_at": "2025-07-11T01:43:42Z",
  "invoice_id": null,
  "payment_id": null,
  "total_amount": 159.98,
  "line_items": [
    {
      "id": "line-item-uuid",
      "product_id": "<PRODUCT_UUID>",
      "quantity": 2,
      "unit_price": 79.99,
      "currency": "USD",
      "total": 159.98
    }
  ]
}
```

> **Save the order `id`** — you will use it in all subsequent steps.

### Step 2 — Order Staff Accepts the Order

```bash
curl -s -X PATCH http://localhost:8000/api/v1/orders/<ORDER_UUID>/accept
```

**Response** (200 OK):

```json
{
  "id": "order-uuid-1",
  "status": "ACCEPTED",
  ...
}
```

### Step 3 — Accountant Creates an Invoice

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/<ORDER_UUID>/invoice \
  -H "Content-Type: application/json" \
  -d '{
    "billing_name": "Alice Johnson",
    "billing_address": "123 Main St, Springfield",
    "due_days": 30
  }'
```

**Response** (200 OK):

```json
{
  "id": "invoice-uuid",
  "order_id": "<ORDER_UUID>",
  "billing_name": "Alice Johnson",
  "billing_address": "123 Main St, Springfield",
  "total_amount": 159.98,
  "currency": "USD",
  "issue_date": "2025-07-11T01:44:00Z",
  "due_date": "2025-08-10T01:44:00Z",
  "status": "ISSUED"
}
```

The order status automatically advances to `INVOICED`.

### Step 4 — Customer Pays the Invoice

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/<ORDER_UUID>/payments \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 159.98,
    "currency": "USD",
    "method": "CREDIT_CARD"
  }'
```

**Response** (200 OK):

```json
{
  "id": "payment-uuid",
  "order_id": "<ORDER_UUID>",
  "amount": 159.98,
  "currency": "USD",
  "method": "CREDIT_CARD",
  "status": "PENDING",
  "timestamp": "2025-07-11T01:44:10Z"
}
```

> **Save the payment `id`** — you will need it for verification.

### Step 5 — Accountant Verifies the Payment

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/payments/<PAYMENT_UUID>/verify \
  -H "Content-Type: application/json" \
  -d '{
    "verified": true
  }'
```

**Response** (200 OK):

```json
{
  "id": "payment-uuid",
  "status": "VERIFIED",
  ...
}
```

The order status automatically advances to `PAID` and the invoice status changes to `PAID`.

### Step 6 — Order Staff Ships the Order

```bash
curl -s -X PATCH http://localhost:8000/api/v1/orders/<ORDER_UUID>/ship
```

**Response** (200 OK):

```json
{
  "id": "order-uuid-1",
  "status": "SHIPPED",
  ...
}
```

### Step 7 — Order Staff Closes the Order

```bash
curl -s -X PATCH http://localhost:8000/api/v1/orders/<ORDER_UUID>/close
```

**Response** (200 OK):

```json
{
  "id": "order-uuid-1",
  "status": "CLOSED",
  ...
}
```

### Cancelling an Order

You can cancel an order that is still `PENDING` or `ACCEPTED`:

```bash
curl -s -X PATCH http://localhost:8000/api/v1/orders/<ORDER_UUID>/cancel
```

### Querying Orders

List all orders:

```bash
curl -s http://localhost:8000/api/v1/orders | python -m json.tool
```

Filter by status:

```bash
curl -s "http://localhost:8000/api/v1/orders?status=PAID" | python -m json.tool
```

Get a single order:

```bash
curl -s http://localhost:8000/api/v1/orders/<ORDER_UUID> | python -m json.tool
```

---

## 8. Non-Functional Requirements — How to Observe

### 8.1 NFR 2.1 — Graceful Degradation

The system uses **Circuit Breakers** to protect non-essential features. There are four breakers:

| Circuit Breaker | Feature | Threshold | Degradation Behavior |
|----------------|---------|-----------|---------------------|
| `checkout` | Order placement (core) | 10 failures (2× default) | **Never degrades** — highest threshold |
| `invoice` | Invoice creation | 5 failures | Degrades — returns 503 |
| `payment` | Payment recording & verification | 5 failures | Degrades — returns 503 |
| `shipping` | Shipping orders | 5 failures | Degrades — returns 503 |

**How to observe:**

```bash
# 1. Trigger 6 failures on the invoice circuit (by passing a fake order ID)
for i in $(seq 1 6); do
  curl -s -X POST http://localhost:8000/api/v1/orders/00000000-0000-0000-0000-000000000000/invoice \
    -H "Content-Type: application/json" \
    -d '{"billing_name":"Test","billing_address":"Addr","due_days":30}'
  echo ""
done

# 2. Check health — invoice circuit should be OPEN
curl -s http://localhost:8000/health | python -m json.tool
# Expected: "invoice": "OPEN"

# 3. Core checkout still works (place a valid order)
# This uses the checkout circuit which has a higher threshold
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<VALID_CUSTOMER_UUID>",
    "line_items": [{"product_id": "<VALID_PRODUCT_UUID>", "quantity": 1, "unit_price": 10.00}]
  }'
# Expected: 201 Created (checkout circuit is still CLOSED)
```

**What to look for:** The `/health` endpoint shows `"invoice": "OPEN"` while `"checkout": "CLOSED"`. The invoice endpoint returns HTTP 503, but the order placement endpoint still works.

### 8.2 NFR 2.2 — Fault Detection and Recovery

The system exposes a `/health` endpoint that reports:
- **Database health** — checks if the database is reachable
- **Circuit breaker states** — shows the state of each breaker

**How to observe:**

```bash
# 1. Normal state
curl -s http://localhost:8000/health | python -m json.tool
# {"status": "healthy", "database": "healthy", ...}

# 2. Simulate database failure
# Stop the application, rename the database file:
mv oms.db oms.db.backup
# Restart the application

# 3. Health check shows degradation
curl -s http://localhost:8000/health | python -m json.tool
# {"status": "degraded", "database": "unhealthy: ...", ...}

# 4. Restore the database
# Stop the app, restore the file:
mv oms.db.backup oms.db
# Restart the app

# 5. Health check recovers
curl -s http://localhost:8000/health | python -m json.tool
# {"status": "healthy", "database": "healthy", ...}
```

**Automatic recovery via Circuit Breaker:** When a circuit breaker is OPEN, it waits for `recovery_timeout` (default 30 seconds), then transitions to HALF_OPEN. If a probe request succeeds, the breaker closes. If it fails, the breaker re-opens.

### 8.3 NFR 2.3 — State Preservation

The system records every order state transition in an `event_log` table. On startup, it scans for non-terminal orders (not CLOSED or CANCELLED) and logs a recovery event.

**How to observe:**

```bash
# 1. Start the application
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Walk through steps 1-3 (place order → accept → create invoice)
# (Use the curl commands from Section 7)

# 3. While the order is in INVOICED state, kill the process
# Press Ctrl+C

# 4. Restart the application
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. Check the application logs — you should see:
#    "Recovered 1 pending order(s) from event log."
#    "Recovered order <uuid> (status=INVOICED)"

# 6. Verify the order status is preserved
curl -s http://localhost:8000/api/v1/orders/<ORDER_UUID> | python -m json.tool
# Expected: "status": "INVOICED"
```

**What to look for in logs:**

```
2025-07-11 01:45:00 [INFO] oms: OMS Backend starting up ...
2025-07-11 01:45:00 [INFO] oms: Database tables created / verified.
2025-07-11 01:45:00 [INFO] oms: Recovered 1 pending order(s) from event log.
2025-07-11 01:45:00 [INFO] oms:   Recovered order a1b2c3d4-... (status=INVOICED)
```

### 8.4 Running the Automated Test Suite

```bash
# Test circuit breaker behavior (business vs infrastructure exceptions)
cd oms
uv run python ../test_circuit_breaker_fix.py

# Quick integration test
uv run python ../test_oms.py
```

---

## 9. Configuration Reference

All configuration is managed via environment variables with the `OMS_` prefix. You can also create a `.env` file in the `oms/` directory.

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_APP_NAME` | `OMS Backend` | Application name (shown in OpenAPI docs) |
| `OMS_APP_VERSION` | `1.0.0` | Application version |
| `OMS_DEBUG` | `false` | Enable debug mode (hot-reload, verbose logging) |
| `OMS_DATABASE_URL` | `sqlite:///./oms.db` | Database connection string |
| `OMS_DATABASE_ECHO` | `false` | Log all SQL queries |
| `OMS_HOST` | `0.0.0.0` | Server bind address |
| `OMS_PORT` | `8000` | Server port |
| `OMS_WORKERS` | `1` | Number of uvicorn workers |
| `OMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `OMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `30.0` | Seconds before half-open probe |
| `OMS_CIRCUIT_BREAKER_HALF_OPEN_MAX_REQUESTS` | `3` | Max probe requests in half-open |
| `OMS_STATE_SNAPSHOT_INTERVAL_SECONDS` | `60` | (Reserved) Snapshot interval |
| `OMS_EVENT_LOG_MAX_SIZE` | `10000` | (Reserved) Max event log entries |

**Example `.env` file:**

```env
OMS_DATABASE_URL=sqlite:///./data/oms.db
OMS_DEBUG=true
OMS_PORT=8000
OMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD=10
```

---

## 10. Troubleshooting

### 10.1 Database File Not Found

**Symptom:** `sqlalchemy.exc.OperationalError: unable to open database file`

**Solution:** The database file is created automatically in the current working directory. Ensure you are running from the `oms/` directory:

```bash
cd oms
uv run uvicorn app.main:app
```

### 10.2 Port Already in Use

**Symptom:** `OSError: [Errno 48] Address already in use`

**Solution:** Either kill the existing process or change the port:

```bash
# Find and kill the process on port 8000
lsof -i :8000
kill -9 <PID>

# Or use a different port
OMS_PORT=8001 uv run uvicorn app.main:app --port 8001
```

### 10.3 Circuit Breaker Stuck OPEN

**Symptom:** All requests to invoice/shipping/payment return 503.

**Solution:** The breaker will automatically transition to HALF_OPEN after `recovery_timeout` (default 30 seconds). If you need to reset immediately:

```bash
# Restart the application — all breakers reset to CLOSED on startup
# Or wait 30 seconds for automatic recovery
```

### 10.4 Order State Transition Errors

**Symptom:** `{"detail": "Cannot accept order in status ..."}`

**Solution:** The order status lifecycle is strict. You can only transition in this order:

```
PENDING → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED
```

You cannot skip steps or go backward. Use the cancel endpoint for PENDING or ACCEPTED orders.

### 10.5 Docker Volume Permissions

**Symptom:** `PermissionError` when using Docker Compose on Linux.

**Solution:** The SQLite database is stored in a Docker volume. Ensure the volume is writable:

```bash
# If using bind mount instead of named volume
chmod 777 ./data
```

### 10.6 Viewing the Database Directly

You can inspect the SQLite database with any SQLite client:

```bash
# Using sqlite3 CLI
sqlite3 oms.db

# List tables
.tables

# View orders
SELECT * FROM orders;

# View event log
SELECT * FROM event_log;
```

---

## Appendix: File Structure

```
oms/
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── pyproject.toml          # Python project metadata & dependencies
├── README.md               # Project README
└── app/
    ├── __init__.py          # Package marker
    ├── config.py            # Environment-based configuration (pydantic-settings)
    ├── controllers.py      # REST endpoint handlers (FastAPI routers)
    ├── dependencies.py      # FastAPI dependency injection (DB sessions)
    ├── domain.py            # Pure domain models (dataclasses, enums)
    ├── infrastructure.py    # Circuit breaker, health check, event log, recovery
    ├── main.py              # FastAPI app creation, lifecycle, health endpoint
    ├── models.py            # SQLAlchemy ORM models + engine + init_db()
    ├── openapi.yaml         # OpenAPI 3.1 specification (hand-written)
    ├── repositories.py      # Data access layer (CRUD per entity)
    ├── routes.py            # Route registration
    ├── schemas.py           # Pydantic request/response schemas
    └── services.py          # Business logic & workflow orchestration
```

---

*This manual was prepared by the ChatDev Chief Product Officer. For questions or feature requests, please refer to the project repository.*
