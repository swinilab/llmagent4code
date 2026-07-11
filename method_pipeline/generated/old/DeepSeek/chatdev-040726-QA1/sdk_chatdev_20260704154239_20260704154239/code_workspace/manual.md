# Order Management System (OMS) — User Manual

> **Version:** 1.0.0  
> **Tech Stack:** FastAPI + SQLAlchemy + SQLite  
> **Roles:** Customer, Order Staff, Accountant

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Installation & Environment Setup](#3-installation--environment-setup)
4. [Running the Application](#4-running-the-application)
5. [API Reference](#5-api-reference)
6. [Complete Workflow Walkthrough](#6-complete-workflow-walkthrough)
7. [Testing](#7-testing)
8. [Configuration Reference](#8-configuration-reference)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce backend that manages the complete order lifecycle:

- **Customer ordering** → **Payment processing** → **Invoicing** → **Shipping** → **Closure**

It serves three distinct roles:

| Role | Description |
|------|-------------|
| **Customer** | Places orders, pays invoices |
| **Order Staff** | Reviews/accepts orders, ships, closes |
| **Accountant** | Creates invoices, verifies payments |

The system is built with **FastAPI** (Python async web framework), **SQLAlchemy** (ORM), and **SQLite** (zero-config database). It is designed for local development and can be deployed to production by swapping the database URL to PostgreSQL.

---

## 2. System Overview

### 2.1 Order Lifecycle

The order lifecycle follows a strict 7-step state machine:

```
PENDING → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED → CLOSED
```

| Step | Action | Performed By | Endpoint |
|------|--------|-------------|----------|
| 1 | Place order | Customer | `POST /api/v1/orders` |
| 2 | Accept order | Order Staff | `POST /api/v1/workflow/orders/{id}/accept` |
| 3 | Create invoice | Accountant | `POST /api/v1/workflow/orders/{id}/invoice` |
| 4 | Pay invoice | Customer | `POST /api/v1/workflow/invoices/{id}/pay` |
| 5 | Verify payment | Accountant | `POST /api/v1/workflow/payments/{id}/verify` |
| 6 | Ship order | Order Staff | `POST /api/v1/workflow/orders/{id}/ship` |
| 7 | Close order | Order Staff | `POST /api/v1/workflow/orders/{id}/close` |

### 2.2 Domain Entities

| Entity | Description |
|--------|-------------|
| **Customer** | Name, address, phone, banking details, role |
| **Product** | Name, description, base price, currency |
| **Order** | Customer ref, line items, total amount, status, invoice ref |
| **OrderItem** | Product ref, quantity, unit price (line item within an order) |
| **Payment** | Order ref, amount, method, status, timestamps |
| **Invoice** | Order ref, billing info, amount, issue/due dates, status |

### 2.3 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Routers   │────▶│   Services   │────▶│    Models    │
│  (REST API) │     │ (Biz Logic)  │     │   (ORM)     │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                                        ┌───────▼───────┐
                                        │   SQLite DB   │
                                        │   (oms.db)    │
                                        └───────────────┘
```

Cross-cutting concerns:
- **Rate Limiting** — Sliding-window per-IP (100 req/min) prevents crash under spikes
- **Request Timing** — Logs slow requests (>500ms) for latency monitoring
- **Global Exception Handler** — Returns structured 500 instead of crashing
- **Connection Pooling** — Reuses DB connections for high concurrency

---

## 3. Installation & Environment Setup

### 3.1 Prerequisites

- **Python 3.12+**
- **pip** or **uv** (recommended)
- **curl** (for API testing)
- **wrk** (optional, for load testing)

### 3.2 Quick Start with uv (Recommended)

```bash
# Navigate to the project directory
cd oms

# Create virtual environment and install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows
```

### 3.3 Quick Start with pip

```bash
cd oms

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3.4 Docker Setup

```bash
cd oms
docker compose up --build
```

This builds the Docker image and starts the service on port 8000 with 4 workers, health checks, and resource limits (512MB max memory).

---

## 4. Running the Application

### 4.1 Development Mode (with auto-reload)

```bash
cd oms
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 Production Mode (with multiple workers)

```bash
cd oms
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4.3 Using the run.py Launcher

```bash
cd oms
uv run python run.py
```

This launches uvicorn with settings from environment variables (workers, port, etc.).

### 4.4 Verify the Server is Running

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","version":"1.0.0"}
```

### 4.5 Access the API Documentation

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI (interactive API docs) |
| `http://localhost:8000/redoc` | ReDoc UI (alternative docs) |
| `http://localhost:8000/openapi.yaml` | OpenAPI spec as JSON |

---

## 5. API Reference

### 5.1 Customer Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/customers` | Create a new customer |
| `GET` | `/api/v1/customers` | List all customers |
| `GET` | `/api/v1/customers/{id}` | Get customer by ID |
| `PATCH` | `/api/v1/customers/{id}` | Update customer |
| `DELETE` | `/api/v1/customers/{id}` | Delete customer |

**Create Customer Example:**
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "address": "123 Main St, Springfield",
    "phone": "+1-555-0100",
    "banking_details": "Bank of America, acct: 12345678",
    "role": "customer"
  }'
```

### 5.2 Product Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/products` | Create a new product |
| `GET` | `/api/v1/products` | List/search products |
| `GET` | `/api/v1/products/{id}` | Get product by ID |
| `PATCH` | `/api/v1/products/{id}` | Update product |
| `DELETE` | `/api/v1/products/{id}` | Delete product |

**Search Products Example:**
```bash
curl "http://localhost:8000/api/v1/products?query=wireless"
```

### 5.3 Order Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/orders` | Place a new order |
| `GET` | `/api/v1/orders` | List orders (filter by `customer_id`) |
| `GET` | `/api/v1/orders/{id}` | Get order by ID |
| `PATCH` | `/api/v1/orders/{id}/status` | Update order status |
| `DELETE` | `/api/v1/orders/{id}` | Delete order |

**Place Order Example:**
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<CUSTOMER_ID>",
    "line_items": [
      {
        "product_id": "<PRODUCT_ID>",
        "quantity": 2,
        "unit_price": 29.99,
        "currency": "USD"
      }
    ]
  }'
```

### 5.4 Payment Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/payments` | Create a payment record |
| `GET` | `/api/v1/payments` | List payments (filter by `order_id`) |
| `GET` | `/api/v1/payments/{id}` | Get payment by ID |
| `POST` | `/api/v1/payments/{id}/pay` | Mark payment as paid |
| `POST` | `/api/v1/payments/{id}/verify` | Verify payment |
| `DELETE` | `/api/v1/payments/{id}` | Delete payment |

### 5.5 Invoice Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/invoices` | Create an invoice |
| `GET` | `/api/v1/invoices` | List invoices (filter by `order_id`) |
| `GET` | `/api/v1/invoices/{id}` | Get invoice by ID |
| `POST` | `/api/v1/invoices/{id}/issue` | Issue invoice |
| `PATCH` | `/api/v1/invoices/{id}/status` | Update invoice status |
| `DELETE` | `/api/v1/invoices/{id}` | Delete invoice |

### 5.6 Workflow Endpoints (Orchestrated Lifecycle)

| Method | Path | Description | Step |
|--------|------|-------------|------|
| `POST` | `/api/v1/workflow/orders/{id}/accept` | Staff accepts order | 2 |
| `POST` | `/api/v1/workflow/orders/{id}/invoice` | Accountant creates invoice | 3 |
| `POST` | `/api/v1/workflow/invoices/{id}/pay` | Customer pays invoice | 4 |
| `POST` | `/api/v1/workflow/payments/{id}/verify` | Accountant verifies payment | 5 |
| `POST` | `/api/v1/workflow/orders/{id}/ship` | Staff ships order | 6 |
| `POST` | `/api/v1/workflow/orders/{id}/close` | Staff closes order | 7 |

### 5.7 System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |
| `GET` | `/openapi.yaml` | OpenAPI spec |

---

## 6. Complete Workflow Walkthrough

This section walks through the full 7-step order lifecycle with actual `curl` commands.

### Step 0: Prerequisites — Create a Customer and a Product

```bash
# Create a customer
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "address": "123 Main St, Springfield",
    "phone": "+1-555-0100",
    "banking_details": "Bank of America, acct: 12345678",
    "role": "customer"
  }' | python -m json.tool
```
Save the `id` from the response as `CUSTOMER_ID`.

```bash
# Create a product
curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Mouse",
    "description": "Ergonomic wireless mouse with USB receiver",
    "base_price": 29.99,
    "currency": "USD"
  }' | python -m json.tool
```
Save the `id` from the response as `PRODUCT_ID`.

### Step 1: Customer Places Order

```bash
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'"$CUSTOMER_ID"'",
    "line_items": [
      {
        "product_id": "'"$PRODUCT_ID"'",
        "quantity": 2,
        "unit_price": 29.99,
        "currency": "USD"
      }
    ]
  }' | python -m json.tool
```
Save the `id` from the response as `ORDER_ID`. The order status will be `"pending"`.

### Step 2: Order Staff Reviews & Accepts

```bash
curl -s -X POST http://localhost:8000/api/v1/workflow/orders/$ORDER_ID/accept \
  -H "Content-Type: application/json" | python -m json.tool
```
Order status changes to `"accepted"`.

### Step 3: Accountant Creates Invoice

```bash
curl -s -X POST http://localhost:8000/api/v1/workflow/orders/$ORDER_ID/invoice \
  -H "Content-Type: application/json" \
  -d '{"billing_info": "Invoice for Alice - 2x Wireless Mouse"}' | python -m json.tool
```
Save the `id` from the response as `INVOICE_ID`. Invoice status is `"issued"`, order status becomes `"invoiced"`.

### Step 4: Customer Pays Invoice

```bash
curl -s -X POST http://localhost:8000/api/v1/workflow/invoices/$INVOICE_ID/pay \
  -H "Content-Type: application/json" \
  -d '{"payment_method": "credit_card"}' | python -m json.tool
```
Save the `id` from the response as `PAYMENT_ID`. Payment status is `"paid"`, order status becomes `"paid"`.

### Step 5: Accountant Verifies Payment

```bash
curl -s -X POST http://localhost:8000/api/v1/workflow/payments/$PAYMENT_ID/verify \
  -H "Content-Type: application/json" | python -m json.tool
```
Payment status becomes `"verified"`, order status becomes `"verified"`.

### Step 6: Order Staff Ships Order

```bash
curl -s -X POST http://localhost:8000/api/v1/workflow/orders/$ORDER_ID/ship \
  -H "Content-Type: application/json" | python -m json.tool
```
Order status becomes `"shipped"`.

### Step 7: Order Staff Closes Order

```bash
curl -s -X POST http://localhost:8000/api/v1/workflow/orders/$ORDER_ID/close \
  -H "Content-Type: application/json" | python -m json.tool
```
Order status becomes `"closed"`.

### Verify Final State

```bash
curl -s http://localhost:8000/api/v1/orders/$ORDER_ID | python -m json.tool
```

Expected output (truncated):
```json
{
  "id": "...",
  "status": "closed",
  "total_amount": 59.98,
  "invoice_ref": "...",
  ...
}
```

---

## 7. Testing

### 7.1 Automated Integration Test

The project includes a complete integration test that runs the full 7-step workflow automatically:

```bash
cd oms
python test_workflow.py
```

This script:
1. Starts the server in a subprocess
2. Waits for it to be ready (polling `/health`)
3. Creates a customer, product, and runs all 7 workflow steps
4. Verifies each step's response
5. Cleans up the database file

Expected output:
```
Server ready after ~1.0s
Health: 200 {'status': 'healthy', 'version': '1.0.0'}
Create Customer: 201
Create Product: 201
Create Order: 201
Accept Order: 200
Create Invoice: 200
Pay Invoice: 200
Verify Payment: 200
Ship Order: 200
Close Order: 200

Final Order: closed

=== ALL WORKFLOW STEPS PASSED ===
Cleaned up oms.db
```

### 7.2 Unit Tests

```bash
cd oms
pytest tests/ -v
```

Expected output: **23 passed** (covering all service layers, state transitions, and the full workflow lifecycle).

### 7.3 Load Testing (NFR Verification)

**NFR 1.1 — Response Time:**
```bash
# Measure latency for core journeys
time curl -s "http://localhost:8000/api/v1/products?query=laptop"

# Load test with wrk
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/products
# Expected: p95 latency < 500ms, no errors
```

**NFR 1.2 — Concurrency & Resource Utilization:**
```bash
# Run load test while monitoring resources
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/products &
htop
# Expected: CPU < 80%, RAM < 512MB per worker
```

**NFR 1.3 — Queue Management (Rate Limiting):**
```bash
# Rapid-fire requests from same IP
for i in $(seq 1 120); do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
done
# After ~100 requests you should see 429 responses

# Verify rate limit resets after 60 seconds
sleep 60
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
# Should return 200
```

---

## 8. Configuration Reference

All configuration is loaded from environment variables with the `OMS_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_APP_TITLE` | `Order Management System` | Application title |
| `OMS_APP_VERSION` | `1.0.0` | Application version |
| `OMS_DATABASE_URL` | `sqlite:///./oms.db` | Database connection URL |
| `OMS_DEBUG` | `false` | Enable debug mode |
| `OMS_MAX_WORKERS` | `8` | Max thread pool workers |
| `OMS_DB_POOL_SIZE` | `20` | SQLAlchemy connection pool size |
| `OMS_DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `OMS_RATE_LIMIT_PER_MINUTE` | `100` | Max requests per minute per IP |
| `OMS_UVICORN_WORKERS` | `4` | Number of uvicorn workers |

**Example with custom settings:**
```bash
OMS_DATABASE_URL="postgresql://user:pass@localhost:5432/omsdb" \
OMS_DB_POOL_SIZE=50 \
OMS_RATE_LIMIT_PER_MINUTE=200 \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 8
```

---

## 9. Troubleshooting

### 9.1 Server won't start

**Symptom:** `ModuleNotFoundError: No module named 'app'`

**Solution:** Run from the `oms/` directory:
```bash
cd oms
uv run uvicorn app.main:app --reload
```

### 9.2 Database locked errors

**Symptom:** `sqlite3.OperationalError: database is locked`

**Solution:** SQLite has limited concurrent write support. Either:
- Reduce the number of workers: `--workers 2`
- Switch to PostgreSQL: `OMS_DATABASE_URL="postgresql://..."`

### 9.3 Rate limiting too aggressive

**Symptom:** Getting `429` responses during normal use

**Solution:** Increase the rate limit:
```bash
OMS_RATE_LIMIT_PER_MINUTE=500 uv run uvicorn app.main:app
```

### 9.4 Slow requests

**Symptom:** "SLOW REQUEST" warnings in logs

**Solution:** Check for N+1 queries or increase connection pool:
```bash
OMS_DB_POOL_SIZE=50 OMS_DB_MAX_OVERFLOW=20 uv run uvicorn app.main:app
```

### 9.5 Port already in use

**Symptom:** `Address already in use`

**Solution:** Kill the existing process or use a different port:
```bash
# Find and kill the process
lsof -i :8000
kill -9 <PID>

# Or use a different port
uv run uvicorn app.main:app --port 8001
```

---

## Project Structure

```
oms/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, middleware, routers
│   ├── config.py            # Pydantic Settings with env vars
│   ├── database.py          # Engine, session, Base with connection pooling
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── customer.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── invoice.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── customer.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── invoice.py
│   ├── services/            # Business logic
│   │   ├── customer_service.py
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── invoice_service.py
│   │   └── workflow_service.py
│   ├── routers/             # FastAPI routers
│   │   ├── customer_router.py
│   │   ├── product_router.py
│   │   ├── order_router.py
│   │   ├── payment_router.py
│   │   ├── invoice_router.py
│   │   └── workflow_router.py
│   └── middleware/          # Cross-cutting concerns
│       └── rate_limit.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_services.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── run.py                   # Dev launcher
├── test_workflow.py         # Integration test
└── README.md
```
