# OMS — Order Management System — User Manual

> **Version:** 1.0.0  
> **Tech Stack:** Python 3.12+ · FastAPI · Pydantic · Uvicorn  
> **Author:** ChatDev — Chief Product Officer

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Main Functions](#2-main-functions)
3. [System Architecture at a Glance](#3-system-architecture-at-a-glance)
4. [Installation & Environment Setup](#4-installation--environment-setup)
5. [Running the Application](#5-running-the-application)
6. [Complete Workflow Walkthrough](#6-complete-workflow-walkthrough)
7. [API Reference Summary](#7-api-reference-summary)
8. [How to Use the Interactive API Docs](#8-how-to-use-the-interactive-api-docs)
9. [Running the Automated Test Suite](#9-running-the-automated-test-suite)
10. [Configuration Guide (NFR 2.3)](#10-configuration-guide-nfr-23)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Introduction

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce backend that handles the complete order-to-delivery workflow:

1. **Customer** places an order
2. **Order Staff** reviews and accepts the order
3. **Accountant** creates an invoice
4. **Customer** pays the invoice
5. **Accountant** verifies the payment
6. **Order Staff** ships the order
7. **Order Staff** closes the completed order

The system serves **three roles**:

| Role | What they do |
|------|-------------|
| **Customer** | Places orders, makes payments |
| **Order Staff** | Accepts, ships, and closes orders |
| **Accountant** | Creates invoices, verifies payments |

No authentication is required — the system is designed as a pure backend API that can be integrated with any frontend.

---

## 2. Main Functions

### 2.1 Customer Management
- **Register** a new customer with name, address, phone, and banking details
- **List** all customers
- **Look up** a customer by ID

### 2.2 Product Catalog
- **Create** products with descriptions and prices
- **List** all products
- **Look up** a product by ID

### 2.3 Order Lifecycle (the core workflow)
- **Place Order** (Customer) — creates a new order with line items
- **Accept Order** (Order Staff) — reviews and approves the order
- **Create Invoice** (Accountant) — generates an invoice for the accepted order
- **Pay Invoice** (Customer) — submits payment matching the invoice total
- **Verify Payment** (Accountant) — confirms the payment is valid
- **Ship Order** (Order Staff) — marks the order as shipped
- **Close Order** (Order Staff) — marks the order as completed
- **Cancel Order** (any stage before completion)

### 2.4 Invoice Management
- **Create** invoices from accepted orders with automatic tax calculation
- **Mark overdue** invoices (past due date)
- **List** all invoices, optionally filtered by order

### 2.5 Payment Processing
- **Submit** payments against invoices
- **Verify** payments (accountant action)
- **List** all payments, optionally filtered by order

### 2.6 Financial Integrity Protections
- **Catalog price validation** — orders must use the exact catalog prices
- **Amount matching** — payments must exactly match the invoice total
- **Currency consistency** — all monetary values in an order must use the same currency
- **State machine enforcement** — orders can only transition through valid statuses

---

## 3. System Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Customers │  │ Products │  │  Orders  │  │ Invoices │  ...   │
│  │  Router   │  │  Router  │  │  Router  │  │  Router  │        │
│  └─────┬─────┘  └─────┬────┘  └────┬─────┘  └────┬─────┘        │
│        │              │            │              │              │
│  ┌─────┴──────────────┴────────────┴──────────────┴──────┐      │
│  │                   Service Layer                         │      │
│  │  (Business logic, validation, event publishing)         │      │
│  └────────────────────────┬───────────────────────────────┘      │
│                           │                                      │
│  ┌────────────────────────┴───────────────────────────────┐      │
│  │                Repository Layer                        │      │
│  │  (Thread-safe in-memory data stores)                   │      │
│  └────────────────────────────────────────────────────────┘      │
│                                                                  │
│  Cross-cutting: Event Bus · Error Handler · Config (pydantic)   │
└─────────────────────────────────────────────────────────────────┘
```

**API Prefix:** All endpoints are versioned under `/api/v1/...` (e.g., `/api/v1/orders`, `/api/v1/invoices`).

---

## 4. Installation & Environment Setup

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.12 or higher |
| [uv](https://docs.astral.sh/uv/) (recommended) | Latest |
| Docker (optional) | Latest |
| curl or httpie | Any version |

### 4.1 Clone the Project

```bash
cd oms-backend
```

The project structure is already set up. Verify with:

```bash
ls -la
# You should see: oms/  openapi.yaml  Dockerfile  docker-compose.yml  pyproject.toml  .env
```

### 4.2 Install Dependencies (Option A — using uv, recommended)

```bash
# uv sync reads pyproject.toml and creates a virtual environment automatically
uv sync

# Activate the virtual environment
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
```

### 4.3 Install Dependencies (Option B — using pip)

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install fastapi uvicorn[standard] pydantic pydantic-settings httpx pyyaml
```

### 4.4 Verify Installation

```bash
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
# Expected: FastAPI 0.139.0 or higher
```

---

## 5. Running the Application

### 5.1 Run Locally (Development)

```bash
# Make sure you're in the project root and the virtual environment is active
uv run python -m oms.main
```

Or if using pip:

```bash
python -m oms.main
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**The server is now running at:** `http://localhost:8000`

### 5.2 Run with Docker

```bash
# Build and start the container
docker compose up --build -d

# Check that it's running
docker compose ps

# View logs
docker compose logs -f

# Stop the container
docker compose down
```

### 5.3 Verify the Server is Running

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{"status":"ok"}
```

---

## 6. Complete Workflow Walkthrough

This section walks through the **entire 7-step order lifecycle** with real `curl` commands. You can copy-paste each block sequentially.

### Setup: Open a Terminal

Make sure the server is running (see section 5). All commands below are executed in a separate terminal.

---

### Step 0: Register a Customer

```bash
curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "address": {"street": "456 Oak Ave", "city": "Portland", "state": "OR", "zip_code": "97201", "country": "USA"},
    "phone": "+1-555-0200",
    "banking_details": {"bank_name": "Pacific Bank", "account_number": "987654321", "routing_number": "121000358"}
  }' | python -m json.tool
```

**What happens:** A new customer is registered. The response includes a UUID `id`.

Save the customer ID:
```bash
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "address": {"street": "456 Oak Ave", "city": "Portland", "state": "OR", "zip_code": "97201", "country": "USA"},
    "phone": "+1-555-0200",
    "banking_details": {"bank_name": "Pacific Bank", "account_number": "987654321", "routing_number": "121000358"}
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Customer ID: $CUSTOMER"
```

---

### Step 0b: Create a Product

```bash
curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Super Widget",
    "base_price": {"amount": 49.99, "currency": "USD"}
  }' | python -m json.tool
```

Save the product ID:
```bash
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Super Widget",
    "base_price": {"amount": 49.99, "currency": "USD"}
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PRODUCT"
```

---

### Step 1: Customer Places an Order

```bash
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"$CUSTOMER\",
    \"line_items\": [{
      \"product_id\": \"$PRODUCT\",
      \"product_description\": \"Super Widget\",
      \"quantity\": 3,
      \"unit_price\": {\"amount\": 49.99, \"currency\": \"USD\"}
    }]
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order ID: $ORDER"
```

**What happens:** The system validates that:
- The customer exists
- The product exists
- The unit price matches the catalog price (`49.99`)
- The currency is consistent

The order is created with status `"pending"`.

---

### Step 2: Order Staff Reviews and Accepts the Order

```bash
STAFF="00000000-0000-0000-0000-000000000001"

curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/accept" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool
```

**What happens:** The order status changes from `"pending"` → `"accepted"`. Only orders in `pending` status can be accepted.

---

### Step 3: Accountant Creates an Invoice

```bash
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER\",
    \"customer_id\": \"$CUSTOMER\",
    \"billing_address\": {\"street\": \"456 Oak Ave\", \"city\": \"Portland\", \"state\": \"OR\", \"zip_code\": \"97201\", \"country\": \"USA\"},
    \"tax\": {\"amount\": 7.50, \"currency\": \"USD\"},
    \"due_date\": \"2025-08-15\"
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Invoice ID: $INVOICE"
```

**What happens:** The system:
- Verifies the order is in `accepted` status
- Creates a deep copy of the order's line items (financial snapshot)
- Calculates `subtotal = 49.99 × 3 = 149.97`
- Calculates `total = subtotal + tax = 149.97 + 7.50 = 157.47`
- Sets invoice status to `"issued"`
- Updates the order status to `"invoiced"`

---

### Step 4: Customer Pays the Invoice

**First, try to pay the wrong amount to see the validation:**

```bash
curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER\",
    \"invoice_id\": \"$INVOICE\",
    \"amount\": {\"amount\": 0.01, \"currency\": \"USD\"},
    \"method\": \"credit_card\"
  }" | python -m json.tool
```

**Expected error:** `400 Bad Request` with `"Payment amount 0.01 does not match invoice total 157.47"`

**Now pay the correct amount:**

```bash
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER\",
    \"invoice_id\": \"$INVOICE\",
    \"amount\": {\"amount\": 157.47, \"currency\": \"USD\"},
    \"method\": \"credit_card\"
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Payment ID: $PAYMENT"
```

**What happens:** The payment is created with status `"pending"`, awaiting verification.

---

### Step 5: Accountant Verifies the Payment

```bash
ACCOUNTANT="00000000-0000-0000-0000-000000000002"

curl -s -X PATCH "http://localhost:8000/api/v1/payments/$PAYMENT/verify" \
  -H "Content-Type: application/json" \
  -d "{\"accountant_id\": \"$ACCOUNTANT\"}" | python -m json.tool
```

**What happens:** The system:
- Changes payment status to `"verified"`
- Updates the order status to `"paid"`
- Updates the invoice status to `"paid"`

---

### Step 6: Order Staff Ships the Order

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/ship" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool
```

**What happens:** The order status changes from `"paid"` → `"shipped"`.

---

### Step 7: Order Staff Closes the Order

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/close" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool
```

**What happens:** The order status changes from `"shipped"` → `"completed"`. The order lifecycle is complete!

---

### Verify the Final State

```bash
# Check the completed order
echo "=== FINAL ORDER STATE ==="
curl -s "http://localhost:8000/api/v1/orders/$ORDER" | python -m json.tool

# Check the paid invoice
echo "=== INVOICE STATE ==="
curl -s "http://localhost:8000/api/v1/invoices/$INVOICE" | python -m json.tool

# Check the verified payment
echo "=== PAYMENT STATE ==="
curl -s "http://localhost:8000/api/v1/payments/$PAYMENT" | python -m json.tool
```

---

### Bonus: Cancel an Order

You can cancel an order at any stage before it is completed or already cancelled:

```bash
# Create a new order
ORDER2=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"$CUSTOMER\",
    \"line_items\": [{
      \"product_id\": \"$PRODUCT\",
      \"product_description\": \"Super Widget\",
      \"quantity\": 1,
      \"unit_price\": {\"amount\": 49.99, \"currency\": \"USD\"}
    }]
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order 2 ID: $ORDER2"

# Cancel it with a reason
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER2/cancel" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Changed my mind"}' | python -m json.tool
```

---

## 7. API Reference Summary

### Endpoints Table

| Method | Endpoint | Step | Who | Description |
|--------|----------|------|-----|-------------|
| `GET` | `/health` | — | Anyone | Health check |
| `POST` | `/api/v1/customers` | — | Anyone | Register a customer |
| `GET` | `/api/v1/customers` | — | Anyone | List all customers |
| `GET` | `/api/v1/customers/{id}` | — | Anyone | Get customer by ID |
| `POST` | `/api/v1/products` | — | Anyone | Create a product |
| `GET` | `/api/v1/products` | — | Anyone | List all products |
| `GET` | `/api/v1/products/{id}` | — | Anyone | Get product by ID |
| `POST` | `/api/v1/orders` | **1** | Customer | Place an order |
| `PATCH` | `/api/v1/orders/{id}/accept` | **2** | Staff | Accept an order |
| `POST` | `/api/v1/invoices` | **3** | Accountant | Create an invoice |
| `POST` | `/api/v1/payments` | **4** | Customer | Make a payment |
| `PATCH` | `/api/v1/payments/{id}/verify` | **5** | Accountant | Verify a payment |
| `PATCH` | `/api/v1/orders/{id}/ship` | **6** | Staff | Ship an order |
| `PATCH` | `/api/v1/orders/{id}/close` | **7** | Staff | Close an order |
| `PATCH` | `/api/v1/orders/{id}/cancel` | — | Anyone | Cancel an order |
| `PATCH` | `/api/v1/invoices/{id}/mark-overdue` | — | Staff | Mark invoice overdue |
| `GET` | `/api/v1/orders` | — | Anyone | List orders (filterable by `?customer_id=`) |
| `GET` | `/api/v1/orders/{id}` | — | Anyone | Get order by ID |
| `GET` | `/api/v1/invoices` | — | Anyone | List invoices (filterable by `?order_id=`) |
| `GET` | `/api/v1/invoices/{id}` | — | Anyone | Get invoice by ID |
| `GET` | `/api/v1/payments` | — | Anyone | List payments (filterable by `?order_id=`) |
| `GET` | `/api/v1/payments/{id}` | — | Anyone | Get payment by ID |

### Order Status Lifecycle

```
pending → accepted → invoiced → paid → shipped → completed
    ↓         ↓          ↓        ↓        ↓
    └─────────┴──────────┴────────┴────────┘
                    cancelled
```

### Request Body Formats

**Create Order (POST /api/v1/orders):**
```json
{
  "customer_id": "uuid",
  "line_items": [
    {
      "product_id": "uuid",
      "product_description": "Widget A",
      "quantity": 2,
      "unit_price": {"amount": 29.99, "currency": "USD"}
    }
  ]
}
```

**Create Invoice (POST /api/v1/invoices):**
```json
{
  "order_id": "uuid",
  "customer_id": "uuid",
  "billing_address": {
    "street": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "zip_code": "62701",
    "country": "USA"
  },
  "tax": {"amount": 5.00, "currency": "USD"},
  "due_date": "2025-08-01"
}
```

**Staff Actions (PATCH .../accept, .../ship, .../close):**
```json
{
  "staff_id": "00000000-0000-0000-0000-000000000001"
}
```

**Accountant Actions (PATCH .../verify):**
```json
{
  "accountant_id": "00000000-0000-0000-0000-000000000002"
}
```

---

## 8. How to Use the Interactive API Docs

FastAPI automatically generates interactive OpenAPI documentation. Once the server is running:

1. **Open your browser** to `http://localhost:8000/docs`
2. You'll see the **Swagger UI** with all endpoints listed
3. Click any endpoint to expand it
4. Click **"Try it out"** to send real requests
5. Fill in the request body and click **"Execute"**
6. View the response status code and body

Alternative documentation (ReDoc) is at `http://localhost:8000/redoc`.

The raw OpenAPI specification is at `http://localhost:8000/openapi.json` and also available as a static file in `openapi.yaml`.

---

## 9. Running the Automated Test Suite

An integration test script is provided that runs the **entire 7-step workflow** plus edge case validations.

### Prerequisites

The server must be running on `http://localhost:8000`.

### Run the Tests

```bash
# Option A: with uv
uv run python test_workflow.py

# Option B: with pip (after activating virtual environment)
python test_workflow.py
```

### Expected Output

```
[PASS] Health check
[PASS] Customer created: <uuid>
[PASS] Product created: <uuid>
[PASS] Order placed: <uuid> (status: pending)
[PASS] Order accepted (status: accepted)
[PASS] Invoice created: <uuid> (status: issued)
[PASS] Payment amount mismatch correctly rejected: Payment amount 0.01 does not match invoice total 157.47
[PASS] Payment created: <uuid> (status: pending)
[PASS] Payment verified (status: verified)
[PASS] Order shipped (status: shipped)
[PASS] Order completed (status: completed)
[PASS] Final order state verified: completed
[PASS] Invoice status verified: paid
[PASS] Order cancellation works (status: cancelled)
[PASS] Payment currency mismatch correctly rejected: Payment currency EUR does not match invoice currency USD

=== ALL TESTS PASSED ===
```

### What the Tests Verify

| Test | What it validates |
|------|------------------|
| Health check | Server is running |
| Customer creation | Registration works |
| Product creation | Product catalog works |
| Order placement | Catalog price validation, customer exists |
| Order acceptance | State transition `pending → accepted` |
| Invoice creation | Deep copy of line items, status `issued` |
| Payment amount mismatch | Rejects wrong amount (financial integrity) |
| Payment creation | Correct amount accepted |
| Payment verification | State transition `pending → verified` |
| Order shipping | State transition `paid → shipped` |
| Order closing | State transition `shipped → completed` |
| Order cancellation | Cancellation at any stage before completion |
| Currency mismatch | Rejects wrong currency (financial integrity) |

---

## 10. Configuration Guide (NFR 2.3)

All configuration is stored in the `.env` file at the project root. You can change settings **without modifying any code**.

### Default Configuration

```ini
# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# API
API_PREFIX=/api/v1
OPENAPI_TITLE=OMS - Order Management System
OPENAPI_VERSION=1.0.0
OPENAPI_DESCRIPTION=Production-grade e-commerce Order Management System backend.
```

### How to Change Configuration

**Example: Change the server port to 8080**

1. Edit `.env`:
   ```ini
   PORT=8080
   ```

2. Restart the server:
   ```bash
   uv run python -m oms.main
   ```

3. Verify:
   ```bash
   curl http://localhost:8080/health
   ```

**Example: Override with environment variables (12-factor app style)**

```bash
PORT=9000 uv run python -m oms.main
```

The environment variable takes precedence over the `.env` file.

**Example: Change log level to DEBUG**

Edit `.env`:
```ini
LOG_LEVEL=DEBUG
```

Then restart. You'll see detailed debug logs for every request.

---

## 11. Troubleshooting

### Server won't start

**Symptom:** `Address already in use`  
**Solution:** Another process is using port 8000. Change the port in `.env` or kill the existing process:
```bash
lsof -i :8000  # Find the PID
kill -9 <PID>  # Kill it
```

**Symptom:** `ModuleNotFoundError: No module named 'oms'`  
**Solution:** Make sure you're running from the project root directory (where the `oms/` folder is located).

### API returns 400 Bad Request

**Symptom:** `"Customer <uuid> not found"`  
**Solution:** The customer ID in your request doesn't exist. Register a new customer first.

**Symptom:** `"Unit price 99.99 for product <uuid> does not match catalog price 49.99"`  
**Solution:** You must use the exact catalog price when placing an order. Check the product's `base_price`.

**Symptom:** `"Payment amount 10.00 does not match invoice total 157.47"`  
**Solution:** The payment amount must exactly match the invoice total (subtotal + tax).

### API returns 404 Not Found

**Symptom:** `"Order not found"` or `"Invoice not found"`  
**Solution:** The UUID you're referencing doesn't exist. Verify the ID by listing resources first:
```bash
curl -s http://localhost:8000/api/v1/orders | python -m json.tool
```

### Data resets on restart

This is expected behavior. The system uses in-memory storage, which means **all data is lost when the server stops**. This is by design for development and demonstration purposes. To make data persistent, the repository layer can be swapped for a real database (PostgreSQL, etc.) by implementing the same interface.

### OpenAPI docs not loading

**Symptom:** `http://localhost:8000/docs` returns a blank page or 404  
**Solution:** Make sure the server is running and accessible:
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### Docker container exits immediately

**Solution:** Check the logs:
```bash
docker compose logs -f
```

Common issues:
- Port 8000 already in use on the host
- Missing `.env` file (the container mounts it as a volume)

---

## Appendix: Quick Reference Card

```bash
# ──── ONE-LINER: Complete 7-step workflow ────

# 0. Setup
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers -H "Content-Type: application/json" \
  -d '{"name":"Jane","address":{"street":"123 Main","city":"Portland","state":"OR","zip_code":"97201","country":"USA"},"phone":"+1-555-0100","banking_details":{"bank_name":"Bank","account_number":"123","routing_number":"456"}}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products -H "Content-Type: application/json" \
  -d '{"description":"Widget","base_price":{"amount":29.99,"currency":"USD"}}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

STAFF="00000000-0000-0000-0000-000000000001"
ACCOUNTANT="00000000-0000-0000-0000-000000000002"

# 1. Place order
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER\",\"line_items\":[{\"product_id\":\"$PRODUCT\",\"product_description\":\"Widget\",\"quantity\":2,\"unit_price\":{\"amount\":29.99,\"currency\":\"USD\"}}]}" \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 2. Accept
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/accept" -H "Content-Type: application/json" \
  -d "{\"staff_id\":\"$STAFF\"}" > /dev/null

# 3. Create invoice
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER\",\"customer_id\":\"$CUSTOMER\",\"billing_address\":{\"street\":\"123 Main\",\"city\":\"Portland\",\"state\":\"OR\",\"zip_code\":\"97201\",\"country\":\"USA\"},\"tax\":{\"amount\":5.00,\"currency\":\"USD\"},\"due_date\":\"2025-08-01\"}" \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 4. Pay (total = 59.98 + 5.00 = 64.98)
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER\",\"invoice_id\":\"$INVOICE\",\"amount\":{\"amount\":64.98,\"currency\":\"USD\"},\"method\":\"credit_card\"}" \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 5. Verify
curl -s -X PATCH "http://localhost:8000/api/v1/payments/$PAYMENT/verify" -H "Content-Type: application/json" \
  -d "{\"accountant_id\":\"$ACCOUNTANT\"}" > /dev/null

# 6. Ship
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/ship" -H "Content-Type: application/json" \
  -d "{\"staff_id\":\"$STAFF\"}" > /dev/null

# 7. Close
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/close" -H "Content-Type: application/json" \
  -d "{\"staff_id\":\"$STAFF\"}" > /dev/null

# Verify
curl -s "http://localhost:8000/api/v1/orders/$ORDER" | python -m json.tool
```

---

*End of User Manual — OMS v1.0.0*