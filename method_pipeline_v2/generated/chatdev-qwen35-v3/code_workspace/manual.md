# Order Management System (OMS) - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Installation & Setup](#installation--setup)
4. [Starting the Server](#starting-the-server)
5. [API Reference](#api-reference)
6. [Workflow Guide](#workflow-guide)
7. [Field Validation Rules](#field-validation-rules)
8. [NFR Verification Suite](#nfr-verification-suite)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

The Order Management System (OMS) is a production-grade, backend-only e-commerce platform developed by ChatDev. It serves the complete order workflow: customer ordering → payment processing → invoicing → shipping → closure.

This system is designed for three user roles:
- **Customer**: Places orders and makes payments
- **Order Staff**: Reviews, accepts, ships, and closes orders
- **Accountant**: Creates invoices and verifies payments

**No authentication is required** - the system focuses on demonstrating architectural patterns and non-functional requirements.

---

## System Overview

### Architecture

The OMS backend is built with:
- **FastAPI** - Async-first web framework
- **SQLAlchemy + aiosqlite** - Async ORM with SQLite database
- **Pydantic** - Request/response validation
- **Tenacity** - Retry logic for fault tolerance

### Key Features

- Complete order lifecycle management
- ACID transaction support
- Rate limiting (100 requests/second)
- In-memory caching for performance
- Automatic retry with exponential backoff
- State synchronization for high availability
- Comprehensive field validation

### Project Structure

```
code_workspace/
├── oms_backend/
│   ├── config/          # Configuration settings
│   ├── controller/      # REST API controllers
│   ├── domain/          # Models and schemas
│   ├── infrastructure/  # Rate limiter, fault injection, state sync
│   ├── repository/      # Data access layer
│   ├── service/         # Business logic layer
│   ├── docs/            # Documentation (ADRs, NFR matrix, etc.)
│   ├── main.py          # Entry point
│   └── server.py        # FastAPI application
├── verification/        # NFR test suite
├── create_apis.json     # API manifest for entity creation
├── workflow_apis.json   # API manifest for workflow steps
├── nfr-trace.json       # NFR traceability (machine-readable)
├── start_command.txt    # Single command to start server
└── pyproject.toml       # Dependencies
```

---

## Installation & Setup

### Prerequisites

- **Python 3.12+**
- **uv package manager** - Install from https://docs.astral.sh/uv/

### Step 1: Initialize Environment

```bash
cd code_workspace

# Create virtual environment (if not already done)
uv venv --python 3.12

# Activate the environment
# On Linux/Mac:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
uv sync
```

This installs all required packages:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` + `aiosqlite` - Database
- `pydantic` + `pydantic-settings` - Validation
- `tenacity` - Retry logic
- `httpx` - HTTP client (for tests)
- `pytest` - Testing framework

### Step 3: Verify Installation

```bash
# Check that dependencies are installed
uv run python -c "import fastapi; print(fastapi.__version__)"
```

---

## Starting the Server

### Quick Start

```bash
# From the project root directory
uv run python -m oms_backend.main
```

Or use the command from `start_command.txt`:

```bash
cat start_command.txt  # Shows: uv run python -m oms_backend.main
```

### Alternative: Direct Uvicorn

```bash
uv run uvicorn oms_backend.server:app --host 0.0.0.0 --port 8000
```

### Verify Server is Running

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "version": "1.0.0"}
```

### Access OpenAPI Documentation

Open your browser and navigate to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Reference

### Base URL

All API endpoints are prefixed with `/api/v1`

```
http://localhost:8000/api/v1
```

### Entity Endpoints

The following entities are available (see `create_apis.json`):

#### Customer

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| Create | POST | `/api/v1/customers` | Create a new customer |
| Get One | GET | `/api/v1/customers/{id}` | Get customer by ID |
| List All | GET | `/api/v1/customers` | Get all customers |

**Create Customer Example:**

```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": "123 Main Street, Cityville",
    "phone": "+1234567890",
    "bankingDetails": {
      "accountNumber": "123456789012",
      "bankName": "First National Bank"
    },
    "role": "CUSTOMER"
  }'
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "John Doe",
  "address": "123 Main Street, Cityville",
  "phone": "+1234567890",
  "bankingDetails": {
    "accountNumber": "123456789012",
    "bankName": "First National Bank"
  },
  "role": "CUSTOMER",
  "orderHistory": [],
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:30:00Z"
}
```

#### Product

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| Create | POST | `/api/v1/products` | Create a new product |
| Get One | GET | `/api/v1/products/{id}` | Get product by ID |
| List All | GET | `/api/v1/products` | Get all products |

**Create Product Example:**

```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Premium Wireless Headphones",
    "price": {
      "amount": "99.99",
      "currency": "USD"
    }
  }'
```

**Supported Currencies:** `USD`, `VND`, `EUR`

#### Order

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| Create | POST | `/api/v1/orders` | Place a new order |
| Get One | GET | `/api/v1/orders/{id}` | Get order by ID |
| List All | GET | `/api/v1/orders` | Get all orders |

**Create Order Example:**

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerRef": "550e8400-e29b-41d4-a716-446655440000",
    "lineItems": [
      {
        "productRef": "660e8400-e29b-41d4-a716-446655440001",
        "quantity": 2
      }
    ]
  }'
```

**Note:** `totalAmount` and `unitPriceSnapshot` are computed server-side and cannot be set by the client.

#### Payment

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| Create | POST | `/api/v1/payments` | Create a payment |
| Get One | GET | `/api/v1/payments/{id}` | Get payment by ID |
| List All | GET | `/api/v1/payments` | Get all payments |

**Create Payment Example:**

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "770e8400-e29b-41d4-a716-446655440002",
    "amount": "199.98",
    "method": "CREDIT_CARD"
  }'
```

**Supported Payment Methods:** `CREDIT_CARD`, `BANK_TRANSFER`, `E_WALLET`

#### Invoice

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| Create | POST | `/api/v1/invoices` | Create an invoice |
| Get One | GET | `/api/v1/invoices/{id}` | Get invoice by ID |
| List All | GET | `/api/v1/invoices` | Get all invoices |

**Create Invoice Example:**

```bash
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "770e8400-e29b-41d4-a716-446655440002",
    "issueDate": "15/01/2024",
    "dueDate": "22/01/2024"
  }'
```

**Note:** `billingInfo` and `totalAmount` are copied from the order/customer server-side.

---

## Workflow Guide

The OMS implements a complete order lifecycle. See `workflow_apis.json` for all workflow endpoints.

### Order Lifecycle State Machine

```
PLACED → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED → CLOSED
                                    ↓
                                CANCELLED
```

### Step-by-Step Workflow

#### Step 1: Customer Places Order

```bash
# Create customer first
CUSTOMER_ID=$(curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","address":"123 Main St, City","phone":"+1234567890","bankingDetails":{"accountNumber":"123456789012","bankName":"Bank"},"role":"CUSTOMER"}' | jq -r '.id')

# Create product
PRODUCT_ID=$(curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Widget","price":{"amount":"50.00","currency":"USD"}}' | jq -r '.id')

# Place order (status: PLACED)
ORDER_ID=$(curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customerRef\":\"$CUSTOMER_ID\",\"lineItems\":[{\"productRef\":\"$PRODUCT_ID\",\"quantity\":2}]}" | jq -r '.id')
```

#### Step 2: Order Staff Accepts Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/accept
```

**Precondition:** Order status must be `PLACED`  
**Result:** Order status changes to `ACCEPTED`

#### Step 3: Accountant Creates Invoice

```bash
INVOICE_ID=$(curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/invoice \
  -H "Content-Type: application/json" \
  -d '{"issueDate":"15/01/2024","dueDate":"22/01/2024"}' | jq -r '.id')
```

**Precondition:** Order status must be `ACCEPTED`  
**Result:** Invoice created, Order status changes to `INVOICED`

#### Step 4: Customer Pays Invoice

```bash
PAYMENT_ID=$(curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"orderRef\":\"$ORDER_ID\",\"amount\":\"100.00\",\"method\":\"CREDIT_CARD\"}" | jq -r '.id')
```

**Precondition:** Order status must be `INVOICED`  
**Result:** Payment created with status `PENDING`, Order status changes to `PAID`

#### Step 5: Accountant Verifies Payment

```bash
curl -X POST http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify
```

**Precondition:** Payment status must be `PENDING`  
**Result:** Payment status changes to `VERIFIED`, Order status changes to `VERIFIED`

#### Step 6: Order Staff Ships Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/ship
```

**Precondition:** Order status must be `VERIFIED`  
**Result:** Order status changes to `SHIPPED`

#### Step 7: Order Staff Closes Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/close
```

**Precondition:** Order status must be `SHIPPED`  
**Result:** Order status changes to `CLOSED`

### Workflow Summary Table

| Step | Endpoint | Precondition | Result |
|------|----------|--------------|--------|
| Accept Order | `POST /api/v1/orders/{id}/accept` | PLACED | → ACCEPTED |
| Create Invoice | `POST /api/v1/orders/{id}/invoice` | ACCEPTED | → INVOICED |
| Pay Invoice | `POST /api/v1/payments` | INVOICED | → PAID |
| Verify Payment | `POST /api/v1/payments/{id}/verify` | PENDING | → VERIFIED |
| Verify Order | `POST /api/v1/orders/{id}/verify` | PAID | → VERIFIED |
| Ship Order | `POST /api/v1/orders/{id}/ship` | VERIFIED | → SHIPPED |
| Close Order | `POST /api/v1/orders/{id}/close` | SHIPPED | → CLOSED |

**Note:** Attempting a workflow step when the precondition is not met returns `409 Conflict`.

---

## Field Validation Rules

All fields must comply with the Field Constraint Table. Invalid requests return `400 Bad Request`.

### Customer Fields

| Field | Type | Constraints | Example |
|-------|------|-------------|---------|
| `name` | string | 2-100 chars, letters/spaces/dots/hyphens/apostrophes | `"John Doe"` |
| `address` | string | 5-255 chars, not blank | `"123 Main St, City"` |
| `phone` | string | E.164 format, 8-15 digits | `"+1234567890"` |
| `bankingDetails.accountNumber` | string | 6-20 digits | `"123456789012"` |
| `bankingDetails.bankName` | string | 2-100 chars | `"First Bank"` |
| `role` | enum | `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT` | `"CUSTOMER"` |

### Product Fields

| Field | Type | Constraints | Example |
|-------|------|-------------|---------|
| `description` | string | 3-500 chars | `"Premium Widget"` |
| `price.amount` | decimal | 0.01-999999.99, exactly 2 decimal places | `"99.99"` |
| `price.currency` | enum | `USD`, `VND`, `EUR` | `"USD"` |

### Order Fields

| Field | Type | Constraints | Example |
|-------|------|-------------|---------|
| `customerRef` | UUID | Must reference existing customer | `"550e8400-..."` |
| `lineItems[].productRef` | UUID | Must reference existing product | `"660e8400-..."` |
| `lineItems[].quantity` | int | 1-1000 | `2` |
| `status` | enum | See state machine above | `"PLACED"` |

### Payment Fields

| Field | Type | Constraints | Example |
|-------|------|-------------|---------|
| `orderRef` | UUID | Must reference INVOICED order | `"770e8400-..."` |
| `amount` | decimal | Must match invoice total exactly | `"100.00"` |
| `method` | enum | `CREDIT_CARD`, `BANK_TRANSFER`, `E_WALLET` | `"CREDIT_CARD"` |

### Invoice Fields

| Field | Type | Constraints | Example |
|-------|------|-------------|---------|
| `orderRef` | UUID | Must reference ACCEPTED order | `"770e8400-..."` |
| `issueDate` | date | `dd/MM/yyyy` format, valid calendar date | `"15/01/2024"` |
| `dueDate` | date | `dd/MM/yyyy`, must be >= issueDate | `"22/01/2024"` |

### Validation Error Response

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "Name must be 2-100 characters",
      "type": "value_error"
    }
  ]
}
```

---

## NFR Verification Suite

The system includes automated tests for all Non-Functional Requirements (NFRs).

### Running the Full Suite

```bash
cd verification
chmod +x run_all_tests.sh
./run_all_tests.sh
```

### Running Individual Tests

```bash
# NFR 1.1 - Rate Limiting
python verification/test_nfr_1_1.py

# NFR 1.2 - Caching
python verification/test_nfr_1_2.py

# NFR 2.1 - Timeout Detection
python verification/test_nfr_2_1.py

# NFR 2.2 - Graceful Degradation
python verification/test_nfr_2_2.py

# NFR 2.3 - State Resynchronization
python verification/test_nfr_2_3.py

# NFR 2.4 - Transactions
python verification/test_nfr_2_4.py
```

### Test Results

Results are saved to `verification/results/`:

```json
{
  "nfr": "NFR 1.1 Limit Event Response",
  "tacticUsed": "Performance > Limit Event Response",
  "faultInduced": {
    "description": "Burst of requests exceeding rate limit",
    "mechanism": "concurrent_http_requests",
    "verified": true
  },
  "baseline": {"metric": "success_rate", "value": 1.0},
  "observed": [
    {"metric": "rate_limit_triggered", "value": 45},
    {"metric": "success_count", "value": 105}
  ],
  "threshold": [
    {"metric": "rate_limit_triggered", "operator": ">=", "value": 1}
  ],
  "passed": true
}
```

### NFR Summary

| NFR | Description | Tactic | Verification |
|-----|-------------|--------|--------------|
| 1.1 | Limit Event Response | Token bucket rate limiter | Burst 150+ requests, verify 429 |
| 1.2 | Maintain Multiple Copies | In-memory caching | Compare 1st vs 2nd request time |
| 2.1 | Exception Detection | Timeout + retry | Verify no hanging requests |
| 2.2 | Graceful Degradation | Retry with backoff | >90% availability under faults |
| 2.3 | State Resynchronization | Background sync task | Query `/nfr-stats` endpoint |
| 2.4 | Transactions | ACID via SQLAlchemy | Verify referential integrity |

---

## Troubleshooting

### Server Won't Start

**Error: Module not found**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
uv sync
```

**Error: Port already in use**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uv run uvicorn oms_backend.server:app --port 8001
```

### Database Issues

**Reset the database:**
```bash
# Delete the database file
rm oms.db

# Restart server - database will be recreated
uv run python -m oms_backend.main
```

### API Returns 400 Bad Request

Check field validation rules above. Common issues:
- Phone number not in E.164 format
- Amount not exactly 2 decimal places
- Date format incorrect (must be `dd/MM/yyyy`)
- UUID format invalid

### API Returns 404 Not Found

- Entity ID doesn't exist
- UUID format is invalid (should return 400 instead)

### API Returns 409 Conflict

- Workflow step precondition not met (e.g., trying to accept an already-shipped order)
- Check the order/payment status before proceeding

### Rate Limiting (429 Too Many Requests)

The system limits to 100 requests/second. Wait and retry, or reduce request rate.

### NFR Tests Failing

1. Ensure server is running at `http://localhost:8000`
2. Check `verification/results/*.json` for detailed error messages
3. Some tests (NFR 2.1, 2.2) use fault injection - ensure `ENABLE_FAULT_INJECTION=true` if needed

---

## Additional Resources

### Documentation Files

- **ADRs**: `oms_backend/docs/ADRS.md` - Architectural Decision Records
- **NFR Matrix**: `oms_backend/docs/NFR_TRACEABILITY_MATRIX.md` - NFR traceability
- **Data Architecture**: `oms_backend/docs/DATA_ARCHITECTURE.md` - Schema and ERD
- **Deployment**: `oms_backend/docs/DEPLOYMENT.md` - Deployment guide

### Machine-Readable Files

- **`create_apis.json`** - Entity creation API manifest
- **`workflow_apis.json`** - Workflow step API manifest
- **`nfr-trace.json`** - NFR traceability (JSON format)
- **`start_command.txt`** - Single command to start server

### OpenAPI Specification

Access the live OpenAPI spec at:
- http://localhost:8000/openapi.json

---

## Support

For issues or questions about this OMS implementation, refer to the ChatDev documentation or consult the source code in the `oms_backend/` directory.

**Built by ChatDev** - Changing the digital world through programming.
