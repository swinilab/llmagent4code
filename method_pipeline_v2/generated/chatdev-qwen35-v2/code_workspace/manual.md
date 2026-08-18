# Order Management System (OMS) - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Starting the Application](#starting-the-application)
6. [API Reference](#api-reference)
7. [Complete Workflow Guide](#complete-workflow-guide)
8. [Field Validation Rules](#field-validation-rules)
9. [NFR Verification](#nfr-verification)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

The Order Management System (OMS) is a production-grade, backend-only e-commerce platform that manages the complete order lifecycle from customer ordering through payment processing, invoicing, shipping, and closure.

### Key Features

- **Complete Order Lifecycle Management**: PLACED → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED → CLOSED
- **Multi-Role Support**: Customer, Order Staff, and Accountant roles
- **Production-Ready Architecture**: FastAPI backend with async SQLAlchemy, caching, and rate limiting
- **Comprehensive Validation**: All field constraints from the Field Constraint Table are enforced
- **NFR Compliance**: Implements all 6 non-functional requirements with traceable code

### Technology Stack

- **Framework**: FastAPI (async web framework)
- **Database**: SQLite with async SQLAlchemy (AISQLite)
- **Validation**: Pydantic v2 with custom validators
- **Caching**: In-memory cache with TTL
- **Rate Limiting**: Token bucket algorithm
- **Package Manager**: uv

---

## System Overview

### Architecture

The OMS follows a layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    Controllers                           │
│  (REST endpoints, request/response mapping, validation) │
├─────────────────────────────────────────────────────────┤
│                     Services                             │
│  (Business logic, transactions, orchestration)          │
├─────────────────────────────────────────────────────────┤
│                   Repositories                           │
│  (Data access, CRUD operations)                         │
├─────────────────────────────────────────────────────────┤
│               Infrastructure                             │
│  (Database, Cache, Rate Limiter, Exceptions)            │
└─────────────────────────────────────────────────────────┘
```

### Domain Entities

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| **Customer** | User account with banking details | id, name, address, phone, bankingDetails, role, orderHistory |
| **Product** | Sellable item with pricing | id, description, price (amount, currency) |
| **Order** | Customer order with line items | id, customerRef, lineItems, totalAmount, status, invoiceRef |
| **Payment** | Payment transaction | id, orderRef, amount, timestamp, status, method |
| **Invoice** | Billing document | id, orderRef, billingInfo, totalAmount, issueDate, dueDate, status |

### State Machines

#### Order Status Flow
```
PLACED → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED → CLOSED
   ↓         ↓          ↓
CANCELLED  CANCELLED   CANCELLED
```

#### Payment Status Flow
```
PENDING → VERIFIED
      → REJECTED
```

#### Invoice Status Flow
```
ISSUED → PAID
      → OVERDUE → PAID
      → CANCELLED
```

---

## Installation

### Prerequisites

- **Python**: Version 3.12 or higher
- **uv**: Python package manager (install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Step 1: Navigate to Project Directory

```bash
cd /path/to/code_workspace
```

### Step 2: Install Dependencies

Run the following command to install all required Python packages:

```bash
uv sync
```

This will install:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - ORM with async support
- `aiosqlite` - Async SQLite driver
- `pydantic` - Data validation
- `phonenumbers` - Phone number validation
- `tenacity` - Retry library
- `python-multipart` - Form data support
- `pyyaml` - YAML support

### Step 3: Verify Installation

Check that all packages are installed correctly:

```bash
uv run python -c "import fastapi, sqlalchemy, pydantic; print('Dependencies OK')"
```

---

## Configuration

The OMS uses environment variables for configuration. All settings have sensible defaults.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_HOST` | `0.0.0.0` | Server bind address |
| `OMS_PORT` | `8080` | Server port |
| `OMS_DATABASE_URL` | `sqlite+aiosqlite:///./oms.db` | Database connection string |
| `OMS_CACHE_TTL` | `300` | Cache TTL in seconds (5 minutes) |
| `OMS_RATE_LIMIT` | `100` | Maximum events per window |
| `OMS_RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |

### Setting Environment Variables

#### Linux/macOS

```bash
export OMS_HOST=0.0.0.0
export OMS_PORT=8080
export OMS_DATABASE_URL="sqlite+aiosqlite:///./oms.db"
export OMS_CACHE_TTL=300
export OMS_RATE_LIMIT=100
export OMS_RATE_LIMIT_WINDOW=60
```

#### Windows (PowerShell)

```powershell
$env:OMS_HOST="0.0.0.0"
$env:OMS_PORT="8080"
$env:OMS_DATABASE_URL="sqlite+aiosqlite:///./oms.db"
$env:OMS_CACHE_TTL="300"
$env:OMS_RATE_LIMIT="100"
$env:OMS_RATE_LIMIT_WINDOW="60"
```

#### Using a .env File

Create a `.env` file in the project root:

```env
OMS_HOST=0.0.0.0
OMS_PORT=8080
OMS_DATABASE_URL=sqlite+aiosqlite:///./oms.db
OMS_CACHE_TTL=300
OMS_RATE_LIMIT=100
OMS_RATE_LIMIT_WINDOW=60
```

---

## Starting the Application

### Method 1: Using the Start Command (Recommended)

The project includes a pre-configured start command:

```bash
cat start_command.txt | bash
```

Or directly:

```bash
uv run python main.py
```

### Method 2: Direct uv Run

```bash
uv run python main.py
```

### Method 3: Using uvicorn Directly

```bash
uv run uvicorn oms.app:app --host 0.0.0.0 --port 8080
```

### Verifying the Application Started

1. **Health Check Endpoint**

   Open a terminal and run:
   ```bash
   curl http://localhost:8080/health
   ```
   
   Expected response:
   ```json
   {"status": "healthy"}
   ```

2. **OpenAPI Documentation**

   Navigate to: http://localhost:8080/docs

   This displays the interactive Swagger UI with all available endpoints.

3. **Alternative OpenAPI UI**

   Navigate to: http://localhost:8080/redoc

---

## API Reference

### Base URL

All API endpoints are prefixed with: `http://localhost:8080/api/v1`

### Customers API

#### List All Customers
```http
GET /api/v1/customers
```
**Response**: `200 OK` - Array of Customer objects

#### Get Customer by ID
```http
GET /api/v1/customers/{customer_id}
```
**Response**: 
- `200 OK` - Customer object
- `404 Not Found` - Customer not found

#### Create Customer
```http
POST /api/v1/customers
Content-Type: application/json
```

**Request Body**:
```json
{
  "name": "John Doe",
  "address": "123 Main Street, New York, NY 10001",
  "phone": "+12125551234",
  "bankingDetails": {
    "accountNumber": "123456789012",
    "bankName": "Chase Bank"
  },
  "role": "CUSTOMER"
}
```

**Response**: `201 Created` - Created Customer object

#### Update Customer
```http
PUT /api/v1/customers/{customer_id}
Content-Type: application/json
```

**Request Body**: Same as Create Customer

**Response**: `200 OK` - Updated Customer object

#### Delete Customer
```http
DELETE /api/v1/customers/{customer_id}
```
**Response**: `204 No Content`

---

### Products API

#### List All Products
```http
GET /api/v1/products
```

#### Get Product by ID
```http
GET /api/v1/products/{product_id}
```

#### Create Product
```http
POST /api/v1/products
Content-Type: application/json
```

**Request Body**:
```json
{
  "description": "Premium Wireless Headphones",
  "price": {
    "amount": "199.99",
    "currency": "USD"
  }
}
```

**Response**: `201 Created` - Created Product object

#### Update Product
```http
PUT /api/v1/products/{product_id}
```

#### Delete Product
```http
DELETE /api/v1/products/{product_id}
```

---

### Orders API

#### List All Orders
```http
GET /api/v1/orders
```

#### Get Order by ID
```http
GET /api/v1/orders/{order_id}
```

#### Get Orders by Customer
```http
GET /api/v1/orders/customer/{customer_id}
```

#### Get Orders by Status
```http
GET /api/v1/orders/status/{status}
```
**Status values**: PLACED, ACCEPTED, INVOICED, PAID, VERIFIED, SHIPPED, CLOSED, CANCELLED

#### Create Order
```http
POST /api/v1/orders
Content-Type: application/json
```

**Request Body**:
```json
{
  "customerRef": "550e8400-e29b-41d4-a716-446655440000",
  "lineItems": [
    {
      "productRef": "660e8400-e29b-41d4-a716-446655440001",
      "quantity": 2
    },
    {
      "productRef": "660e8400-e29b-41d4-a716-446655440002",
      "quantity": 1
    }
  ]
}
```

**Response**: `201 Created` - Created Order object (with server-computed totalAmount)

#### Update Order Status
```http
PUT /api/v1/orders/{order_id}/status
Content-Type: application/json
```

**Request Body**:
```json
{
  "status": "ACCEPTED"
}
```

**Response**: `200 OK` - Updated Order object

#### Delete Order
```http
DELETE /api/v1/orders/{order_id}
```

---

### Payments API

#### List All Payments
```http
GET /api/v1/payments
```

#### Get Payment by ID
```http
GET /api/v1/payments/{payment_id}
```

#### Get Payments by Order
```http
GET /api/v1/payments/order/{order_id}
```

#### Create Payment
```http
POST /api/v1/payments
Content-Type: application/json
```

**Request Body**:
```json
{
  "orderRef": "770e8400-e29b-41d4-a716-446655440002",
  "amount": "399.98",
  "method": "CREDIT_CARD"
}
```

**Response**: `201 Created` - Created Payment object (status: PENDING)

#### Verify Payment (Accountant Only)
```http
PUT /api/v1/payments/{payment_id}/verify
Content-Type: application/json
```

**Request Body**:
```json
{
  "status": "VERIFIED"
}
```

**Valid status values**: VERIFIED, REJECTED

**Response**: `200 OK` - Updated Payment object

#### Delete Payment
```http
DELETE /api/v1/payments/{payment_id}
```

---

### Invoices API

#### List All Invoices
```http
GET /api/v1/invoices
```

#### Get Invoice by ID
```http
GET /api/v1/invoices/{invoice_id}
```

#### Get Invoice by Order
```http
GET /api/v1/invoices/order/{order_id}
```

#### Create Invoice (Accountant Only)
```http
POST /api/v1/invoices
Content-Type: application/json
```

**Request Body**:
```json
{
  "orderRef": "770e8400-e29b-41d4-a716-446655440002",
  "issueDate": "15/03/2025",
  "dueDate": "22/03/2025"
}
```

**Note**: If issueDate and dueDate are omitted, defaults are used:
- issueDate: Current server date
- dueDate: issueDate + 7 days

**Response**: `201 Created` - Created Invoice object (also updates Order status to INVOICED)

#### Update Invoice Status (Accountant Only)
```http
PUT /api/v1/invoices/{invoice_id}/status?new_status=PAID
```

**Valid status values**: PAID, OVERDUE, CANCELLED

**Response**: `200 OK` - Updated Invoice object

#### Delete Invoice
```http
DELETE /api/v1/invoices/{invoice_id}
```

---

## Complete Workflow Guide

This section demonstrates the complete order lifecycle from customer creation to order closure.

### Prerequisites

Ensure the application is running:
```bash
uv run python main.py
```

### Step 1: Create a Customer

```bash
curl -X POST http://localhost:8080/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "address": "456 Oak Avenue, Los Angeles, CA 90001",
    "phone": "+13105551234",
    "bankingDetails": {
      "accountNumber": "987654321098",
      "bankName": "Bank of America"
    },
    "role": "CUSTOMER"
  }'
```

**Save the response `id`** for later use (e.g., `customer-uuid-123`).

### Step 2: Create Products

```bash
# Product 1
curl -X POST http://localhost:8080/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Wireless Bluetooth Headphones",
    "price": {
      "amount": "79.99",
      "currency": "USD"
    }
  }'

# Product 2
curl -X POST http://localhost:8080/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "USB-C Charging Cable",
    "price": {
      "amount": "19.99",
      "currency": "USD"
    }
  }'
```

**Save both product IDs** (e.g., `product-uuid-1`, `product-uuid-2`).

### Step 3: Customer Places Order

```bash
curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerRef": "customer-uuid-123",
    "lineItems": [
      {
        "productRef": "product-uuid-1",
        "quantity": 2
      },
      {
        "productRef": "product-uuid-2",
        "quantity": 3
      }
    ]
  }'
```

**Expected Response** (status: PLACED):
```json
{
  "id": "order-uuid-456",
  "customerRef": "customer-uuid-123",
  "lineItems": [
    {"productRef": "product-uuid-1", "quantity": 2, "unitPriceSnapshot": "79.99"},
    {"productRef": "product-uuid-2", "quantity": 3, "unitPriceSnapshot": "19.99"}
  ],
  "totalAmount": "219.95",
  "status": "PLACED",
  "createdAt": "2025-03-15T10:30:00Z",
  "updatedAt": "2025-03-15T10:30:00Z",
  "invoiceRef": null
}
```

**Save the order ID** for subsequent steps.

### Step 4: Order Staff Accepts Order

```bash
curl -X PUT http://localhost:8080/api/v1/orders/order-uuid-456/status \
  -H "Content-Type: application/json" \
  -d '{"status": "ACCEPTED"}'
```

**Response**: Order with status changed to ACCEPTED.

### Step 5: Accountant Creates Invoice

```bash
curl -X POST http://localhost:8080/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "order-uuid-456"
  }'
```

**Expected Response**:
```json
{
  "id": "invoice-uuid-789",
  "orderRef": "order-uuid-456",
  "billingInfo": {
    "name": "Alice Johnson",
    "address": "456 Oak Avenue, Los Angeles, CA 90001"
  },
  "totalAmount": "219.95",
  "issueDate": "15/03/2025",
  "dueDate": "22/03/2025",
  "status": "ISSUED"
}
```

**Note**: The order status is automatically updated to INVOICED.

### Step 6: Customer Makes Payment

```bash
curl -X POST http://localhost:8080/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "order-uuid-456",
    "amount": "219.95",
    "method": "CREDIT_CARD"
  }'
```

**Response**: Payment with status PENDING.

**Important**: The amount MUST exactly match the invoice totalAmount (no partial or over payments).

### Step 7: Accountant Verifies Payment

```bash
# Get payment ID first
curl http://localhost:8080/api/v1/payments/order/order-uuid-456

# Then verify
curl -X PUT http://localhost:8080/api/v1/payments/payment-uuid-abc/verify \
  -H "Content-Type: application/json" \
  -d '{"status": "VERIFIED"}'
```

**Response**: Payment with status VERIFIED. The order status is automatically updated to PAID.

### Step 8: Order Staff Ships Order

```bash
curl -X PUT http://localhost:8080/api/v1/orders/order-uuid-456/status \
  -H "Content-Type: application/json" \
  -d '{"status": "SHIPPED"}'
```

**Note**: You must first transition through VERIFIED status:
```bash
curl -X PUT http://localhost:8080/api/v1/orders/order-uuid-456/status \
  -H "Content-Type: application/json" \
  -d '{"status": "VERIFIED"}'
```

Then ship:
```bash
curl -X PUT http://localhost:8080/api/v1/orders/order-uuid-456/status \
  -H "Content-Type: application/json" \
  -d '{"status": "SHIPPED"}'
```

### Step 9: Order Staff Closes Order

```bash
curl -X PUT http://localhost:8080/api/v1/orders/order-uuid-456/status \
  -H "Content-Type: application/json" \
  -d '{"status": "CLOSED"}'
```

**Response**: Order with status CLOSED - workflow complete!

---

## Field Validation Rules

All fields are validated according to the Field Constraint Table. Below are the key validation rules:

### Customer Fields

| Field | Validation Rule | Error Example |
|-------|-----------------|---------------|
| `name` | 2-100 chars, letters/spaces/dots/apostrophes/hyphens only | "A" (too short), "John123" (invalid chars) |
| `address` | 5-255 chars, not blank | "123" (too short) |
| `phone` | E.164 format, 8-15 digits, must start with 1-9 after optional + | "+0123456789" (starts with 0), "1234567" (too short) |
| `bankingDetails.accountNumber` | 6-20 digits only | "12345" (too short), "123abc" (non-numeric) |
| `bankingDetails.bankName` | 2-100 chars, letters/digits/spaces/dots/ampersands/hyphens | "A" (too short) |
| `role` | Must be exactly: CUSTOMER, ORDER_STAFF, or ACCOUNTANT | "customer" (wrong case), "ADMIN" (invalid) |

### Product Fields

| Field | Validation Rule | Error Example |
|-------|-----------------|---------------|
| `description` | 3-500 chars, not blank | "AB" (too short) |
| `price.amount` | Exactly 2 decimal places, 0.01-999999.99 | "19.9" (1 decimal), "19.999" (3 decimals), "0.00" (too low) |
| `price.currency` | 3 uppercase letters, must be USD/VND/EUR | "usd" (lowercase), "GBP" (not supported) |

### Order Fields

| Field | Validation Rule | Error Example |
|-------|-----------------|---------------|
| `customerRef` | Valid UUIDv4 format, must reference existing customer | "not-a-uuid", "00000000-0000-0000-0000-000000000000" (non-existent) |
| `lineItems` | 1-100 items, no duplicate productRef | [] (empty), 101 items (too many) |
| `lineItems[].quantity` | Integer 1-1000 | 0 (too low), 1001 (too high), 1.5 (not integer) |
| `status` | Must follow state machine transitions | Setting CLOSED on PLACED order (invalid transition) |

### Payment Fields

| Field | Validation Rule | Error Example |
|-------|-----------------|---------------|
| `orderRef` | Valid UUID, order must be INVOICED | Order in PLACED status (409 Conflict) |
| `amount` | Must exactly match invoice totalAmount | Invoice is 100.00, payment is 99.00 (ValidationException) |
| `method` | Must be: CREDIT_CARD, BANK_TRANSFER, or E_WALLET | "PAYPAL" (invalid) |
| `status` (verify) | Must be VERIFIED or REJECTED | "PENDING" (invalid for verification) |

### Invoice Fields

| Field | Validation Rule | Error Example |
|-------|-----------------|---------------|
| `orderRef` | Valid UUID, order must be ACCEPTED | Order in PLACED status (409 Conflict) |
| `issueDate` | dd/MM/yyyy format, valid calendar date | "31/02/2025" (invalid date), "2025-03-15" (wrong format) |
| `dueDate` | dd/MM/yyyy format, must be >= issueDate | "10/03/2025" when issueDate is "15/03/2025" |

---

## NFR Verification

This section explains how to verify each Non-Functional Requirement is satisfied.

### NFR 1.1 - Limit Event Response

**Tactic**: Throttling (Token Bucket Rate Limiter)

**Implementation**: `oms/infrastructure/event/rate_limiter.py`

**Verification Steps**:

1. Start the application
2. Send more than 100 requests to a create endpoint within 60 seconds:

```bash
for i in {1..105}; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/api/v1/products \
    -H "Content-Type: application/json" \
    -d '{"description": "Test Product '"$i"'", "price": {"amount": "10.00", "currency": "USD"}}'
done
```

3. Observe that requests after the 100th return HTTP 429 (Too Many Requests)

**Expected Output**: First 100 requests return 201, subsequent requests return 429.

---

### NFR 1.2 - Maintain Multiple Copies of Data

**Tactic**: Maintain Multiple Copies (In-Memory Cache)

**Implementation**: `oms/infrastructure/cache/memory_cache.py`

**Verification Steps**:

1. Create a customer:
```bash
curl -X POST http://localhost:8080/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "Cache Test", "address": "123 Cache Street, City", "phone": "+12345678901", "bankingDetails": {"accountNumber": "123456789012", "bankName": "Test Bank"}, "role": "CUSTOMER"}'
```

2. Save the customer ID from the response

3. Request the same customer twice rapidly:
```bash
curl http://localhost:8080/api/v1/customers/{customer-id}
curl http://localhost:8080/api/v1/customers/{customer-id}
```

4. Check application logs for cache hit messages (second request should use cache)

**Expected Behavior**: Second request retrieves data from cache instead of database.

---

### NFR 2.1 - Exception Detection

**Tactic**: Detect Faults (Custom Exception Hierarchy)

**Implementation**: `oms/infrastructure/exceptions.py`

**Verification Steps**:

1. **Validation Error (400)**:
```bash
curl -X POST http://localhost:8080/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "A", "address": "123", "phone": "invalid", "bankingDetails": {"accountNumber": "123", "bankName": "X"}, "role": "CUSTOMER"}'
```
Expected: 400 Bad Request with validation error details

2. **Not Found (404)**:
```bash
curl http://localhost:8080/api/v1/customers/00000000-0000-0000-0000-000000000000
```
Expected: 404 Not Found

3. **Conflict (409)** - Invalid state transition:
```bash
curl -X PUT http://localhost:8080/api/v1/orders/{order-id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "CLOSED"}'
```
(On an order in PLACED status)
Expected: 409 Conflict

---

### NFR 2.2 - Graceful Degradation

**Tactic**: Graceful Degradation (503 on Database Failure)

**Implementation**: `oms/infrastructure/exceptions.py::sqlalchemy_exception_handler`

**Verification Method**:

The system is designed to return HTTP 503 (Service Unavailable) when database errors occur, allowing clients to implement retry logic.

To test this in production:
1. Simulate database failure (e.g., lock the database file)
2. Make any API request
3. Verify 503 response instead of 500

**Note**: In normal operation, you won't see this behavior. It's a fail-safe mechanism.

---

### NFR 2.3 - State Resynchronization

**Tactic**: Resynchronize State (Cache Invalidation)

**Implementation**: Cache invalidation in all service update/delete methods

**Verification Steps**:

1. Create a customer
2. Retrieve the customer (cached)
3. Update the customer:
```bash
curl -X PUT http://localhost:8080/api/v1/customers/{customer-id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name", "address": "123 Cache Street, City", "phone": "+12345678901", "bankingDetails": {"accountNumber": "123456789012", "bankName": "Test Bank"}, "role": "CUSTOMER"}'
```

4. Retrieve the customer again:
```bash
curl http://localhost:8080/api/v1/customers/{customer-id}
```

**Expected Behavior**: The cache entry is invalidated on update, so the next GET retrieves fresh data from the database and repopulates the cache.

---

### NFR 2.4 - Transactions

**Tactic**: Atomicity (SQLAlchemy Async Transactions)

**Implementation**: `oms/infrastructure/database.py::transaction_session`

**Verification Steps**:

1. Create an order with multiple line items:
```bash
curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerRef": "{customer-id}",
    "lineItems": [
      {"productRef": "{product-id-1}", "quantity": 2},
      {"productRef": "{product-id-2}", "quantity": 3}
    ]
  }'
```

2. Verify atomicity:
   - Check that the order is created
   - Check that ALL line items are created
   - Check that the customer's orderHistory is updated

3. All operations succeed or all fail together (ACID properties)

**Expected Behavior**: If any part of the transaction fails (e.g., invalid product reference), the entire order creation rolls back and no partial data is persisted.

---

## Troubleshooting

### Application Won't Start

**Symptom**: Error when running `uv run python main.py`

**Solutions**:

1. **Check Python Version**:
   ```bash
   python --version
   ```
   Must be 3.12 or higher.

2. **Reinstall Dependencies**:
   ```bash
   rm -rf .venv
   uv sync
   ```

3. **Check Port Availability**:
   ```bash
   lsof -i :8080
   ```
   If another process is using port 8080, either stop it or change `OMS_PORT`.

---

### Database Errors

**Symptom**: "Database temporarily unavailable" (503)

**Solutions**:

1. **Delete and Recreate Database**:
   ```bash
   rm oms.db
   uv run python main.py
   ```
   The database will be recreated automatically on startup.

2. **Check File Permissions**:
   ```bash
   ls -la oms.db
   chmod 644 oms.db
   ```

---

### Validation Errors

**Symptom**: 400 Bad Request with validation error details

**Solutions**:

1. **Check Field Formats**: Review the [Field Validation Rules](#field-validation-rules) section

2. **Common Issues**:
   - Phone number not in E.164 format: Use `+12345678901` format
   - Price amount wrong decimals: Use exactly 2 decimal places (e.g., "19.99")
   - Date format wrong: Use `dd/MM/yyyy` (e.g., "15/03/2025")
   - Invalid UUID format: Ensure UUIDs are valid v4 format

3. **Read Error Details**: The response body contains specific validation error messages

---

### Rate Limit Errors

**Symptom**: 429 Too Many Requests

**Solutions**:

1. **Wait for Window Reset**: Rate limit resets after 60 seconds (default)

2. **Increase Rate Limit** (for testing):
   ```bash
   export OMS_RATE_LIMIT=1000
   uv run python main.py
   ```

3. **Implement Client-Side Throttling**: Add delays between requests

---

### State Machine Errors

**Symptom**: 409 Conflict - "Invalid status transition"

**Solutions**:

1. **Check Current Order Status**:
   ```bash
   curl http://localhost:8080/api/v1/orders/{order-id}
   ```

2. **Follow Valid Transitions**:
   - PLACED → ACCEPTED or CANCELLED
   - ACCEPTED → INVOICED or CANCELLED
   - INVOICED → PAID or CANCELLED
   - PAID → VERIFIED
   - VERIFIED → SHIPPED
   - SHIPPED → CLOSED

3. **Cannot Skip States**: You must transition through each state in order

---

### Cache Issues

**Symptom**: Stale data returned

**Solutions**:

1. **Clear Cache**: Restart the application (cache is in-memory)

2. **Reduce TTL** (for testing):
   ```bash
   export OMS_CACHE_TTL=30
   uv run python main.py
   ```

---

## Additional Resources

### File Structure

```
code_workspace/
├── main.py                 # Application entry point
├── start_command.txt       # Start command
├── create_apis.json        # API manifest for testing
├── nfr-trace.json          # NFR traceability (machine-readable)
├── ARCHITECTURE.md         # Architecture documentation
├── DEPLOYMENT.md           # Deployment guide
├── pyproject.toml          # Python dependencies
├── oms/
│   ├── app.py              # FastAPI application factory
│   ├── server.py           # Server setup and startup
│   ├── config/
│   │   └── app_config.py   # Configuration settings
│   ├── controller/         # REST controllers
│   │   ├── customer_controller.py
│   │   ├── product_controller.py
│   │   ├── order_controller.py
│   │   ├── payment_controller.py
│   │   └── invoice_controller.py
│   ├── service/            # Business logic services
│   │   ├── customer_service.py
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   └── invoice_service.py
│   ├── repository/         # Data access layer
│   │   ├── customer_repository.py
│   │   ├── product_repository.py
│   │   ├── order_repository.py
│   │   ├── payment_repository.py
│   │   └── invoice_repository.py
│   ├── domain/
│   │   └── models.py       # Pydantic models and validation
│   └── infrastructure/
│       ├── database.py     # Database setup and models
│       ├── exceptions.py   # Exception handling
│       ├── cache/
│       │   └── memory_cache.py
│       └── event/
│           └── rate_limiter.py
└── oms.db                  # SQLite database
```

### Key Configuration Files

- **`pyproject.toml`**: Python dependencies
- **`oms/config/app_config.py`**: Application settings
- **`create_apis.json`**: API endpoints for automated testing
- **`nfr-trace.json`**: NFR implementation traceability

### API Documentation

Once the application is running, access:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/api/v1/openapi.json

---

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions
3. Consult the [DEPLOYMENT.md](DEPLOYMENT.md) for deployment guidance
4. Examine the OpenAPI documentation at http://localhost:8080/docs

---

*Document Version: 1.0.0*  
*Last Updated: 2025*  
*OMS Version: 1.0.0*
