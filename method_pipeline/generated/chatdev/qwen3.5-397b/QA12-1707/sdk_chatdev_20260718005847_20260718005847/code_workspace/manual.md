# Order Management System (OMS) - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Main Functions](#main-functions)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the Server](#running-the-server)
7. [API Usage Guide](#api-usage-guide)
8. [Complete Workflow Example](#complete-workflow-example)
9. [Testing](#testing)
10. [NFR Verification](#nfr-verification)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

The Order Management System (OMS) is a production-grade, backend-only e-commerce order management system built with Python and FastAPI. It serves the complete order workflow from customer ordering through payment processing, invoicing, shipping, and closure.

### Key Features

- **Async-first architecture** for high concurrency and low latency
- **Three-layer architecture** (Controller-Service-Repository) for clean separation of concerns
- **SQLite database** with async driver for local deployment
- **Automatic OpenAPI documentation** at `/docs` endpoint
- **Graceful degradation** under high load
- **Fault detection and recovery** mechanisms

### User Roles

The system supports three roles (no authentication required):

1. **Customer**: Places orders, pays invoices
2. **Order Staff**: Reviews orders, ships orders, closes completed orders
3. **Accountant**: Creates invoices, verifies payments

---

## System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│  Controllers (REST API Endpoints)                        │
│  ├── Customer Controller                                 │
│  ├── Product Controller                                  │
│  ├── Order Controller                                    │
│  ├── Invoice Controller                                  │
│  └── Payment Controller                                  │
├─────────────────────────────────────────────────────────┤
│  Services (Business Logic)                               │
│  ├── Customer Service                                    │
│  ├── Product Service                                     │
│  ├── Order Service                                       │
│  ├── Invoice Service                                     │
│  └── Payment Service                                     │
├─────────────────────────────────────────────────────────┤
│  Repositories (Data Access)                              │
│  ├── Customer Repository                                 │
│  ├── Product Repository                                  │
│  ├── Order Repository                                    │
│  ├── Invoice Repository                                  │
│  └── Payment Repository                                  │
├─────────────────────────────────────────────────────────┤
│  Database (SQLite with async driver)                     │
└─────────────────────────────────────────────────────────┘
```

### Order Lifecycle

```
PENDING → REVIEWING → ACCEPTED → INVOICED → PAYMENT_PENDING → PAID → SHIPPING → SHIPPED → COMPLETED
              │
              └──→ REJECTED (terminal state)
```

---

## Main Functions

### 1. Customer Management

- Create, read, update, delete customers
- Search customers by email
- Store customer details including name, email, phone, address, and banking details

### 2. Product Management

- Create, read, update, delete products
- Search products by name or description
- Manage stock quantities
- Set pricing with currency support

### 3. Order Management

- Create orders with line items
- Review and accept/reject orders
- Track order status through complete lifecycle
- Ship and complete orders
- Queue management (max 1000 pending orders)

### 4. Invoice Management

- Create invoices for accepted orders
- Issue invoices with due dates
- Track invoice status (draft, issued, paid, overdue, cancelled)
- Automatic tax calculation

### 5. Payment Management

- Create payments for orders
- Process payments (simulated gateway)
- Verify payments
- Track payment status and methods

### 6. Health & Monitoring

- Health check endpoint (`/health`)
- Readiness check endpoint (`/ready`)
- Request logging middleware
- Error handling middleware

---

## Installation

### Prerequisites

- Python 3.11 or higher
- `uv` package manager (recommended) or `pip`

### Step 1: Clone/Access the Project

Ensure you are in the project root directory containing:
- `pyproject.toml`
- `main.py`
- `oms/` directory

### Step 2: Initialize Python Environment

Using `uv` (recommended):

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

Alternatively, using pip:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Step 3: Verify Installation

Run the import test to verify all dependencies are installed:

```bash
python test_imports.py
```

Expected output: All imports successful.

---

## Configuration

### Environment Variables

The system reads configuration from environment variables. Create a `.env` file or export variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./oms.db` | Database connection string |
| `DATABASE_ECHO` | `false` | Enable SQL logging |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8003` | Server port |
| `WORKERS` | `1` | Number of worker processes |
| `MAX_CONNECTIONS` | `100` | Database connection pool size |
| `REQUEST_TIMEOUT` | `30` | Request timeout in seconds |
| `ENABLE_DEGRADED_MODE` | `true` | Enable graceful degradation |
| `MAX_PENDING_ORDERS` | `1000` | Maximum pending orders before rejection |
| `DEBUG` | `false` | Enable debug mode |

### Example `.env` File

```bash
DATABASE_URL=sqlite+aiosqlite:///./oms.db
DATABASE_ECHO=false
HOST=0.0.0.0
PORT=8003
WORKERS=1
MAX_CONNECTIONS=100
ENABLE_DEGRADED_MODE=true
MAX_PENDING_ORDERS=1000
```

---

## Running the Server

### Method 1: Using main.py (Recommended for Development)

```bash
# Activate virtual environment first
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the server
python main.py
```

### Method 2: Using uv run

```bash
uv run python main.py
```

### Method 3: Using the package entry point

```bash
uv run oms
```

### Expected Output

```
2024-01-15 10:00:00 - oms.server - INFO - Starting OMS server on 0.0.0.0:8003
2024-01-15 10:00:00 - oms.server - INFO - Workers: 1
2024-01-15 10:00:01 - oms.app - INFO - Starting OMS application...
2024-01-15 10:00:01 - oms.config.database - INFO - Database initialized successfully
2024-01-15 10:00:01 - oms.app - INFO - Database connection established
INFO:     Uvicorn running on http://0.0.0.0:8003 (Press CTRL+C to quit)
```

### Access the API Documentation

Once running, open your browser to:
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc
- **OpenAPI JSON**: http://localhost:8003/openapi.json

---

## API Usage Guide

### Base URL

```
http://localhost:8003
```

### Health Check

```bash
curl http://localhost:8003/health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": 1704067200
}
```

---

### Customer API

#### Create Customer

```bash
curl -X POST http://localhost:8003/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-123-4567",
    "address": "123 Main St, City, State 12345"
  }'
```

Response:
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1-555-123-4567",
  "address": "123 Main St, City, State 12345",
  "banking_details": null,
  "created_at": "2024-01-15T10:00:00",
  "updated_at": null
}
```

#### Get Customer by ID

```bash
curl http://localhost:8003/api/v1/customers/1
```

#### List All Customers

```bash
curl "http://localhost:8003/api/v1/customers?skip=0&limit=100"
```

#### Update Customer

```bash
curl -X PUT http://localhost:8003/api/v1/customers/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Updated",
    "phone": "+1-555-999-9999"
  }'
```

#### Delete Customer

```bash
curl -X DELETE http://localhost:8003/api/v1/customers/1
```

---

### Product API

#### Create Product

```bash
curl -X POST http://localhost:8003/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Premium Widget",
    "description": "High-quality widget for all your needs",
    "base_price": 29.99,
    "currency": "USD",
    "stock_quantity": 100
  }'
```

Response:
```json
{
  "id": 1,
  "name": "Premium Widget",
  "description": "High-quality widget for all your needs",
  "base_price": 29.99,
  "currency": "USD",
  "stock_quantity": 100,
  "created_at": "2024-01-15T10:00:00",
  "updated_at": null
}
```

#### Search Products

```bash
curl "http://localhost:8003/api/v1/products/search?query=widget&skip=0&limit=10"
```

#### Get All Products

```bash
curl "http://localhost:8003/api/v1/products?skip=0&limit=100"
```

#### Update Product

```bash
curl -X PUT http://localhost:8003/api/v1/products/1 \
  -H "Content-Type: application/json" \
  -d '{
    "base_price": 24.99,
    "stock_quantity": 150
  }'
```

---

### Order API

#### Create Order (Customer Workflow Step 1)

```bash
curl -X POST http://localhost:8003/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "line_items": [
      {"product_id": 1, "quantity": 2},
      {"product_id": 2, "quantity": 1}
    ],
    "notes": "Please handle with care"
  }'
```

Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "pending",
  "total_amount": 89.97,
  "currency": "USD",
  "invoice_id": null,
  "notes": "Please handle with care",
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:00:00",
  "reviewed_at": null,
  "shipped_at": null,
  "completed_at": null,
  "line_items": [
    {"id": 1, "order_id": 1, "product_id": 1, "quantity": 2, "unit_price": 29.99, "subtotal": 59.98},
    {"id": 2, "order_id": 1, "product_id": 2, "quantity": 1, "unit_price": 29.99, "subtotal": 29.99}
  ]
}
```

#### Review Order (Order Staff Workflow Step 2)

```bash
# Accept the order
curl -X POST http://localhost:8003/api/v1/orders/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "accept": true,
    "notes": "Approved for processing"
  }'

# Or reject the order
curl -X POST http://localhost:8003/api/v1/orders/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "accept": false,
    "notes": "Out of stock"
  }'
```

#### Get Orders by Status

```bash
curl "http://localhost:8003/api/v1/orders?status=accepted"
```

#### Get Orders by Customer

```bash
curl "http://localhost:8003/api/v1/orders?customer_id=1"
```

---

### Invoice API

#### Create Invoice (Accountant Workflow Step 3)

```bash
curl -X POST http://localhost:8003/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "billing_name": "John Doe",
    "billing_address": "123 Main St, City, State 12345",
    "tax_rate": 0.1,
    "notes": "Thank you for your business",
    "due_days": 30
  }'
```

Response:
```json
{
  "id": 1,
  "order_id": 1,
  "billing_name": "John Doe",
  "billing_address": "123 Main St, City, State 12345",
  "subtotal": 89.97,
  "tax_amount": 8.997,
  "total_amount": 98.967,
  "currency": "USD",
  "issue_date": null,
  "due_date": null,
  "status": "draft",
  "notes": "Thank you for your business",
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:00:00"
}
```

#### Issue Invoice

```bash
curl -X POST http://localhost:8003/api/v1/invoices/1/issue
```

#### Get Invoice by Order ID

```bash
curl http://localhost:8003/api/v1/invoices/order/1
```

---

### Payment API

#### Create Payment (Customer Workflow Step 4)

```bash
curl -X POST http://localhost:8003/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "amount": 98.97,
    "currency": "USD",
    "method": "credit_card",
    "notes": "Payment via Visa ending 4242"
  }'
```

Response:
```json
{
  "id": 1,
  "order_id": 1,
  "invoice_id": 1,
  "amount": 98.97,
  "currency": "USD",
  "method": "credit_card",
  "status": "pending",
  "transaction_id": null,
  "notes": "Payment via Visa ending 4242",
  "processed_at": null,
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:00:00"
}
```

#### Process Payment

```bash
curl -X POST http://localhost:8003/api/v1/payments/1/process \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_123456789"
  }'
```

#### Verify Payment (Accountant Workflow Step 5)

```bash
curl -X POST http://localhost:8003/api/v1/payments/1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "confirmed": true,
    "notes": "Payment verified successfully"
  }'
```

---

### Shipping & Completion (Order Staff Workflow Steps 6-7)

#### Ship Order

```bash
curl -X POST http://localhost:8003/api/v1/orders/1/ship \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Shipped via FedEx, tracking: FX123456789"
  }'
```

#### Complete Order

```bash
curl -X POST http://localhost:8003/api/v1/orders/1/complete \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Delivered successfully, customer satisfied"
  }'
```

---

## Complete Workflow Example

This section demonstrates the complete order lifecycle from start to finish.

### Step 1: Setup - Create Customer and Product

```bash
# Create customer
CUSTOMER=$(curl -s -X POST http://localhost:8003/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Smith", "email": "alice@example.com"}')
CUSTOMER_ID=$(echo $CUSTOMER | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Created customer with ID: $CUSTOMER_ID"

# Create product
PRODUCT=$(curl -s -X POST http://localhost:8003/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "base_price": 999.99, "stock_quantity": 50}')
PRODUCT_ID=$(echo $PRODUCT | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Created product with ID: $PRODUCT_ID"
```

### Step 2: Customer Places Order

```bash
ORDER=$(curl -s -X POST http://localhost:8003/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\": $CUSTOMER_ID, \"line_items\": [{\"product_id\": $PRODUCT_ID, \"quantity\": 1}]}")
ORDER_ID=$(echo $ORDER | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Created order with ID: $ORDER_ID"
```

### Step 3: Order Staff Reviews & Accepts

```bash
curl -s -X POST http://localhost:8003/api/v1/orders/$ORDER_ID/review \
  -H "Content-Type: application/json" \
  -d '{"accept": true, "notes": "Order verified"}'
```

### Step 4: Accountant Creates Invoice

```bash
curl -s -X POST http://localhost:8003/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{\"order_id\": $ORDER_ID, \"billing_name\": \"Alice Smith\", \"tax_rate\": 0.08}"
```

### Step 5: Customer Pays Invoice

```bash
PAYMENT=$(curl -s -X POST http://localhost:8003/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"order_id\": $ORDER_ID, \"amount\": 1079.99, \"method\": \"credit_card\"}")
PAYMENT_ID=$(echo $PAYMENT | python -c "import sys, json; print(json.load(sys.stdin)['id'])")

# Process and verify payment
curl -s -X POST http://localhost:8003/api/v1/payments/$PAYMENT_ID/process \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "txn_abc123"}'

curl -s -X POST http://localhost:8003/api/v1/payments/$PAYMENT_ID/verify \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true}'
```

### Step 6: Order Staff Ships Order

```bash
curl -s -X POST http://localhost:8003/api/v1/orders/$ORDER_ID/ship \
  -H "Content-Type: application/json" \
  -d '{"notes": "Shipped via UPS"}'
```

### Step 7: Order Staff Closes Order

```bash
curl -s -X POST http://localhost:8003/api/v1/orders/$ORDER_ID/complete \
  -H "Content-Type: application/json" \
  -d '{"notes": "Delivered and confirmed"}'
```

---

## Testing

### Run the Test Suite

```bash
# Using the included test script
python test_oms.py
```

Expected output shows each step of the workflow being tested:
```
Testing health endpoint...
Health: {'status': 'healthy', 'database': 'connected', ...}

Testing root endpoint...
Root: {'message': 'OMS API is running', ...}

Creating customer...
Customer created: {'id': 1, 'name': 'Test Customer', ...}

Creating product...
Product created: {'id': 1, 'name': 'Test Product', ...}

Creating order...
Order created: {'id': 1, 'status': 'pending', ...}

Reviewing order (accept)...
Order reviewed: {'id': 1, 'status': 'accepted', ...}

Creating invoice...
Invoice created: {'id': 1, 'order_id': 1, ...}

Creating payment...
Payment created: {'id': 1, 'order_id': 1, ...}

Verifying payment...
Payment verified: {'id': 1, 'status': 'completed', ...}

Shipping order...
Order shipped: {'id': 1, 'status': 'shipped', ...}

Completing order...
Order completed: {'id': 1, 'status': 'completed', ...}
```

### Using TestClient for Development

```python
from fastapi.testclient import TestClient
from oms.app import app

client = TestClient(app)

# Test health endpoint
response = client.get("/health")
assert response.status_code == 200
assert response.json()["status"] == "healthy"

# Test creating customer
response = client.post("/api/v1/customers", json={
    "name": "Test User",
    "email": "test@example.com"
})
assert response.status_code == 201
```

---

## NFR Verification

### NFR 1.1: Response Time

**Verification Method:**

```bash
# Install Apache Bench if not installed
# Ubuntu: sudo apt-get install apache2-utils
# macOS: brew install apache-bench

# Test health endpoint latency under load
ab -n 1000 -c 10 http://localhost:8003/health

# Expected: Most requests complete in < 100ms
```

### NFR 1.2: Concurrency & Resource Utilization

**Verification Method:**

```bash
# Monitor CPU/memory during concurrent requests
# Terminal 1: Start server
python main.py

# Terminal 2: Monitor resources
htop

# Terminal 3: Send concurrent requests
ab -n 5000 -c 50 http://localhost:8003/api/v1/products
```

### NFR 1.3: Queue Management

**Verification Method:**

```bash
# Test queue limit (1000 pending orders)
for i in {1..1005}; do
  curl -s -X POST http://localhost:8003/api/v1/orders \
    -H "Content-Type: application/json" \
    -d "{\"customer_id\": 1, \"line_items\": [{\"product_id\": 1, \"quantity\": 1}]}" \
    -w "Order $i: %{http_code}\n" -o /dev/null
done

# Expected: First 1000 succeed (201), subsequent fail (400) with queue message
```

### NFR 2.1: Graceful Degradation

**Verification Method:**

```bash
# Set degraded mode
export ENABLE_DEGRADED_MODE=true

# Under load, non-essential features are disabled
# Core checkout (order creation, payment) remains available
# Verify by checking health endpoint status
curl http://localhost:8003/health

# Expected: status may show "degraded" but core functions work
```

### NFR 2.2: Fault Detection and Recovery

**Verification Method:**

```bash
# Check health endpoint
curl http://localhost:8003/health

# Simulate database issue (advanced: stop DB process)
# Restart server and verify automatic reconnection
# Check logs for recovery messages

# Expected: Server detects failure, logs error, recovers on restart
```

### NFR 2.3: State Preservation

**Verification Method:**

```bash
# Create an order
curl -X POST http://localhost:8003/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "line_items": [{"product_id": 1, "quantity": 1}]}'

# Kill server process (Ctrl+C)
# Restart server
python main.py

# Verify order persists
curl http://localhost:8003/api/v1/orders/1

# Expected: Order data is preserved in SQLite database
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port 8003
lsof -i :8003

# Kill the process
kill -9 <PID>

# Or use a different port
export PORT=8004
python main.py
```

#### 2. Database Lock Error

**Error:** `database is locked`

**Solution:**
```bash
# Ensure no other process is using the database
# Delete the database file (loses all data)
rm oms.db

# Restart server
python main.py
```

#### 3. Import Errors

**Error:** `ModuleNotFoundError`

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
uv sync
```

#### 4. Connection Refused

**Error:** `Connection refused`

**Solution:**
```bash
# Verify server is running
curl http://localhost:8003/health

# Check server logs for startup errors
# Ensure HOST is set to 0.0.0.0 or 127.0.0.1
```

### Log Files

Application logs are output to stdout. To save logs to a file:

```bash
python main.py > oms.log 2>&1
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export DATABASE_ECHO=true
python main.py
```

---

## API Reference Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/api/v1/customers` | GET, POST | List/Create customers |
| `/api/v1/customers/{id}` | GET, PUT, DELETE | Get/Update/Delete customer |
| `/api/v1/products` | GET, POST | List/Create products |
| `/api/v1/products/{id}` | GET, PUT, DELETE | Get/Update/Delete product |
| `/api/v1/products/search` | GET | Search products |
| `/api/v1/orders` | GET, POST | List/Create orders |
| `/api/v1/orders/{id}` | GET | Get order |
| `/api/v1/orders/{id}/review` | POST | Review order |
| `/api/v1/orders/{id}/ship` | POST | Ship order |
| `/api/v1/orders/{id}/complete` | POST | Complete order |
| `/api/v1/invoices` | GET, POST | List/Create invoices |
| `/api/v1/invoices/{id}` | GET, PUT | Get/Update invoice |
| `/api/v1/invoices/order/{order_id}` | GET | Get invoice by order |
| `/api/v1/payments` | GET, POST | List/Create payments |
| `/api/v1/payments/{id}` | GET | Get payment |
| `/api/v1/payments/{id}/process` | POST | Process payment |
| `/api/v1/payments/{id}/verify` | POST | Verify payment |

---

## Support

For issues or questions:
1. Check the `/docs` endpoint for interactive API documentation
2. Review logs for error messages
3. Verify environment configuration
4. Ensure all dependencies are installed correctly

---

*This manual covers the Order Management System version 1.0.0*
