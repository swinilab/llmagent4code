# Order Management System (OMS) - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [API Reference](#api-reference)
6. [Complete Workflow Guide](#complete-workflow-guide)
7. [Field Validation Rules](#field-validation-rules)
8. [Troubleshooting](#troubleshooting)

---

## Introduction

The Order Management System (OMS) is a production-grade, backend-only e-commerce system that serves APIs for the complete order workflow: **customer ordering → payment processing → invoicing → shipping → closure**.

This system is designed to serve three roles:
- **Customer**: Places orders and makes payments
- **Order Staff**: Reviews/accepts orders, ships orders, and closes completed orders
- **Accountant**: Creates invoices and verifies payments

### Key Features

- **Complete Order Lifecycle Management**: From order placement to closure
- **Production-Grade Architecture**: PostgreSQL database, Redis caching, rate limiting
- **Comprehensive Validation**: All fields validated according to strict business rules
- **ACID Transactions**: Ensures data consistency across all operations
- **Graceful Degradation**: Continues functioning even when Redis is unavailable
- **Automatic OpenAPI Documentation**: Interactive API docs at `/api/docs`

---

## System Overview

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   FastAPI   │────▶│   Redis     │
│             │     │   Server    │     │   Cache     │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │  PostgreSQL │
                    │   Database  │
                    └─────────────┘
```

### Technology Stack

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic
- **Deployment**: Docker & Docker Compose

### Domain Entities

| Entity | Description |
|--------|-------------|
| Customer | Customer information including banking details and order history |
| Product | Product catalog with pricing in multiple currencies |
| Order | Customer orders with line items and status tracking |
| Payment | Payment records linked to orders |
| Invoice | Invoices generated for accepted orders |

---

## Installation

### Prerequisites

- **Docker** and **Docker Compose** (recommended), OR
- **Python 3.12+** with **uv** package manager

### Option 1: Docker Installation (Recommended)

#### Step 1: Clone or Navigate to Project Directory

```bash
cd /path/to/oms_project
```

#### Step 2: Start All Services

```bash
docker-compose -f iac/docker-compose.yml up -d --build
```

This command starts:
- **PostgreSQL** database on port 5432
- **Redis** cache on port 6379
- **OMS Backend API** on port 8000

#### Step 3: Initialize the Database

```bash
docker exec oms_postgres psql -U postgres -d oms_db -f /docker-entrypoint-initdb.d/init.sql
```

Or manually:

```bash
docker cp iac/init_db.sql oms_postgres:/tmp/init.sql
docker exec oms_postgres psql -U postgres -d oms_db -f /tmp/init.sql
```

#### Step 4: Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Access API documentation
open http://localhost:8000/api/docs
```

### Option 2: Local Development Installation

#### Step 1: Install Dependencies

```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
uv sync
```

#### Step 2: Start PostgreSQL

```bash
docker run -d --name oms_postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=oms_db \
  -p 5432:5432 \
  postgres:15-alpine
```

#### Step 3: Start Redis

```bash
docker run -d --name oms_redis \
  -p 6379:6379 \
  redis:7-alpine
```

#### Step 4: Initialize Database

```bash
psql -U postgres -d oms_db -f iac/init_db.sql
```

#### Step 5: Set Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oms_db
REDIS_URL=redis://localhost:6379/0
DEBUG=true
ENABLE_CACHING=true
ENABLE_RATE_LIMITING=true
```

#### Step 6: Run the Application

```bash
uv run python main.py
```

Or using uvicorn directly:

```bash
uvicorn oms_backend.server:app --reload --host 0.0.0.0 --port 8000
```

---

## Quick Start

### 1. Access API Documentation

Open your browser and navigate to:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

### 2. Create Your First Customer

```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": "123 Main Street, City, Country",
    "phone": "+1234567890",
    "bankingDetails": {
      "accountNumber": "123456789",
      "bankName": "First National Bank"
    },
    "role": "CUSTOMER"
  }'
```

**Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "John Doe",
  "address": "123 Main Street, City, Country",
  "phone": "+1234567890",
  "bankingDetails": {
    "accountNumber": "123456789",
    "bankName": "First National Bank"
  },
  "role": "CUSTOMER",
  "orderHistory": [],
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:30:00Z"
}
```

### 3. Create a Product

```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Premium Widget",
    "price": {
      "amount": "99.99",
      "currency": "USD"
    }
  }'
```

### 4. Place an Order

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerRef": "550e8400-e29b-41d4-a716-446655440000",
    "lineItems": [
      {
        "productRef": "product-id-here",
        "quantity": 2
      }
    ]
  }'
```

---

## API Reference

### Base URL

```
http://localhost:8000/api/v1
```

### Endpoints Overview

| Entity | Create | Get All | Get One | Update | Delete |
|--------|--------|---------|---------|--------|--------|
| Customer | POST /customers | GET /customers | GET /customers/{id} | PUT /customers/{id} | DELETE /customers/{id} |
| Product | POST /products | GET /products | GET /products/{id} | PUT /products/{id} | DELETE /products/{id} |
| Order | POST /orders | GET /orders | GET /orders/{id} | - | - |
| Payment | POST /payments | GET /payments | GET /payments/{id} | - | - |
| Invoice | POST /invoices | GET /invoices | GET /invoices/{id} | - | - |

---

### Customer API

#### Create Customer

**Endpoint**: `POST /api/v1/customers`

**Request Body**:
```json
{
  "name": "John Doe",
  "address": "123 Main Street, City, Country",
  "phone": "+1234567890",
  "bankingDetails": {
    "accountNumber": "123456789",
    "bankName": "First National Bank"
  },
  "role": "CUSTOMER"
}
```

**Validation Rules**:
- `name`: 2-100 characters, letters/spaces/apostrophes/hyphens only
- `address`: 5-255 characters
- `phone`: E.164 format (8-15 digits, optional leading +)
- `bankingDetails.accountNumber`: 6-20 digits
- `bankingDetails.bankName`: 2-100 characters
- `role`: Must be one of: `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT`

**Response**: `201 Created` with customer object

#### Get Customer

**Endpoint**: `GET /api/v1/customers/{id}`

**Response**: `200 OK` with customer object, `404 Not Found` if not found

#### Get All Customers

**Endpoint**: `GET /api/v1/customers`

**Response**: `200 OK` with array of customers

#### Update Customer

**Endpoint**: `PUT /api/v1/customers/{id}`

**Request Body**: Same as create (all fields updatable except id)

**Response**: `200 OK` with updated customer object

#### Delete Customer

**Endpoint**: `DELETE /api/v1/customers/{id}`

**Response**: `204 No Content`

---

### Product API

#### Create Product

**Endpoint**: `POST /api/v1/products`

**Request Body**:
```json
{
  "description": "Premium Widget",
  "price": {
    "amount": "99.99",
    "currency": "USD"
  }
}
```

**Validation Rules**:
- `description`: 3-500 characters
- `price.amount`: 0.01 to 999999.99, exactly 2 decimal places
- `price.currency`: Must be one of: `USD`, `VND`, `EUR`

**Response**: `201 Created` with product object

#### Get Product

**Endpoint**: `GET /api/v1/products/{id}`

**Response**: `200 OK` with product object

#### Get All Products

**Endpoint**: `GET /api/v1/products`

**Response**: `200 OK` with array of products

#### Update Product

**Endpoint**: `PUT /api/v1/products/{id}`

**Response**: `200 OK` with updated product object

#### Delete Product

**Endpoint**: `DELETE /api/v1/products/{id}`

**Response**: `204 No Content`

---

### Order API

#### Create Order

**Endpoint**: `POST /api/v1/orders`

**Request Body**:
```json
{
  "customerRef": "customer-uuid-here",
  "lineItems": [
    {
      "productRef": "product-uuid-here",
      "quantity": 2
    }
  ]
}
```

**Validation Rules**:
- `customerRef`: Must reference an existing customer
- `lineItems`: 1-100 items, no duplicate productRef
- `lineItems[].quantity`: 1-1000
- `status`: Auto-set to `PLACED` on creation

**Computed Fields** (server-side, not client-settable):
- `lineItems[].unitPriceSnapshot`: Copied from product price at order time
- `totalAmount`: Sum of (quantity × unitPriceSnapshot) for all line items

**Response**: `201 Created` with order object including computed fields

#### Get Order

**Endpoint**: `GET /api/v1/orders/{id}`

**Response**: `200 OK` with order object

#### Get All Orders

**Endpoint**: `GET /api/v1/orders`

**Response**: `200 OK` with array of orders

#### Order Workflow Actions

| Action | Endpoint | Role | Description |
|--------|----------|------|-------------|
| Accept | `POST /api/v1/orders/{id}/accept` | Order Staff | Transition from PLACED to ACCEPTED |
| Cancel | `POST /api/v1/orders/{id}/cancel` | Order Staff | Cancel order (from PLACED or ACCEPTED) |
| Verify | `POST /api/v1/orders/{id}/verify` | Accountant | Verify order after payment (from PAID to VERIFIED) |
| Ship | `POST /api/v1/orders/{id}/ship` | Order Staff | Ship order (from VERIFIED to SHIPPED) |
| Close | `POST /api/v1/orders/{id}/close` | Order Staff | Close completed order (from SHIPPED to CLOSED) |

**Order Status State Machine**:
```
PLACED ──▶ ACCEPTED ──▶ INVOICED ──▶ PAID ──▶ VERIFIED ──▶ SHIPPED ──▶ CLOSED
   │            │            │
   │            │            └──────▶ CANCELLED
   │            │
   └────────────└──────▶ CANCELLED
```

---

### Payment API

#### Create Payment

**Endpoint**: `POST /api/v1/payments`

**Request Body**:
```json
{
  "orderRef": "order-uuid-here",
  "amount": "99.99",
  "method": "CREDIT_CARD"
}
```

**Validation Rules**:
- `orderRef`: Must reference an existing order with status `INVOICED`
- `amount`: Must exactly match the invoice totalAmount (no partial/over payments)
- `method`: Must be one of: `CREDIT_CARD`, `BANK_TRANSFER`, `E_WALLET`

**Computed Fields**:
- `timestamp`: Server-generated at submission
- `status`: Auto-set to `PENDING` on creation

**Response**: `201 Created` with payment object

#### Get Payment

**Endpoint**: `GET /api/v1/payments/{id}`

**Response**: `200 OK` with payment object

#### Get All Payments

**Endpoint**: `GET /api/v1/payments`

**Response**: `200 OK` with array of payments

#### Payment Workflow Actions

| Action | Endpoint | Role | Description |
|--------|----------|------|-------------|
| Verify | `POST /api/v1/payments/{id}/verify` | Accountant | Transition from PENDING to VERIFIED |
| Reject | `POST /api/v1/payments/{id}/reject` | Accountant | Transition from PENDING to REJECTED |

**Payment Status State Machine**:
```
PENDING ──▶ VERIFIED
     │
     └──────▶ REJECTED
```

---

### Invoice API

#### Create Invoice

**Endpoint**: `POST /api/v1/invoices`

**Request Body**:
```json
{
  "orderRef": "order-uuid-here",
  "billingInfo": {
    "name": "John Doe",
    "address": "123 Main Street, City, Country"
  },
  "totalAmount": "99.99",
  "issueDate": "15/01/2024",
  "dueDate": "22/01/2024"
}
```

**Validation Rules**:
- `orderRef`: Must reference an existing order with status `ACCEPTED`
- `billingInfo.name`: 2-100 characters (snapshot from customer)
- `billingInfo.address`: 5-255 characters (snapshot from customer)
- `totalAmount`: Must equal the referenced order's totalAmount
- `issueDate`: dd/MM/yyyy format, must be a valid calendar date
- `dueDate`: dd/MM/yyyy format, must be >= issueDate, valid calendar date

**Computed Fields**:
- `status`: Auto-set to `ISSUED` on creation

**Response**: `201 Created` with invoice object

#### Get Invoice

**Endpoint**: `GET /api/v1/invoices/{id}`

**Response**: `200 OK` with invoice object

#### Get All Invoices

**Endpoint**: `GET /api/v1/invoices`

**Response**: `200 OK` with array of invoices

#### Invoice Workflow Actions

| Action | Endpoint | Role | Description |
|--------|----------|------|-------------|
| Mark Paid | `POST /api/v1/invoices/{id}/mark-paid` | Accountant | Transition from ISSUED to PAID |
| Mark Overdue | `POST /api/v1/invoices/{id}/mark-overdue` | System | Transition from ISSUED to OVERDUE |
| Cancel | `POST /api/v1/invoices/{id}/cancel` | Accountant | Transition to CANCELLED |

**Invoice Status State Machine**:
```
ISSUED ──▶ PAID
    │
    ├──▶ OVERDUE
    │
    └──▶ CANCELLED
```

---

## Complete Workflow Guide

This section demonstrates the complete order lifecycle from customer registration to order closure.

### Step 1: Create a Customer

```bash
CUSTOMER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "address": "456 Oak Avenue, Springfield, USA",
    "phone": "+14155551234",
    "bankingDetails": {
      "accountNumber": "987654321",
      "bankName": "Springfield Bank"
    },
    "role": "CUSTOMER"
  }')

CUSTOMER_ID=$(echo $CUSTOMER_RESPONSE | jq -r '.id')
echo "Customer ID: $CUSTOMER_ID"
```

### Step 2: Create Products

```bash
PRODUCT1_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Wireless Mouse",
    "price": {
      "amount": "29.99",
      "currency": "USD"
    }
  }')

PRODUCT1_ID=$(echo $PRODUCT1_RESPONSE | jq -r '.id')

PRODUCT2_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Mechanical Keyboard",
    "price": {
      "amount": "89.99",
      "currency": "USD"
    }
  }')

PRODUCT2_ID=$(echo $PRODUCT2_RESPONSE | jq -r '.id')

echo "Product 1 ID: $PRODUCT1_ID"
echo "Product 2 ID: $PRODUCT2_ID"
```

### Step 3: Customer Places Order

```bash
ORDER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customerRef\": \"$CUSTOMER_ID\",
    \"lineItems\": [
      {
        \"productRef\": \"$PRODUCT1_ID\",
        \"quantity\": 2
      },
      {
        \"productRef\": \"$PRODUCT2_ID\",
        \"quantity\": 1
      }
    ]
  }")

ORDER_ID=$(echo $ORDER_RESPONSE | jq -r '.id')
TOTAL_AMOUNT=$(echo $ORDER_RESPONSE | jq -r '.totalAmount')

echo "Order ID: $ORDER_ID"
echo "Total Amount: $TOTAL_AMOUNT"
echo "Order Status: $(echo $ORDER_RESPONSE | jq -r '.status')"
# Expected: PLACED
```

### Step 4: Order Staff Accepts Order

```bash
ACCEPT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/accept \
  -H "Content-Type: application/json")

echo "Order Status after Accept: $(echo $ACCEPT_RESPONSE | jq -r '.status')"
# Expected: ACCEPTED
```

### Step 5: Accountant Creates Invoice

```bash
INVOICE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{
    \"orderRef\": \"$ORDER_ID\",
    \"billingInfo\": {
      \"name\": \"Alice Johnson\",
      \"address\": \"456 Oak Avenue, Springfield, USA"
    },
    \"totalAmount\": \"$TOTAL_AMOUNT\",
    \"issueDate\": \"15/01/2024\",
    \"dueDate\": \"22/01/2024\"
  }")

INVOICE_ID=$(echo $INVOICE_RESPONSE | jq -r '.id')
echo "Invoice ID: $INVOICE_ID"
echo "Invoice Status: $(echo $INVOICE_RESPONSE | jq -r '.status')"
# Expected: ISSUED
```

### Step 6: Customer Pays Invoice

```bash
PAYMENT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{
    \"orderRef\": \"$ORDER_ID\",
    \"amount\": \"$TOTAL_AMOUNT\",
    \"method\": \"CREDIT_CARD"
  }")

PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.id')
echo "Payment ID: $PAYMENT_ID"
echo "Payment Status: $(echo $PAYMENT_RESPONSE | jq -r '.status')"
# Expected: PENDING
```

### Step 7: Accountant Verifies Payment

```bash
VERIFY_PAYMENT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify \
  -H "Content-Type: application/json")

echo "Payment Status after Verify: $(echo $VERIFY_PAYMENT_RESPONSE | jq -r '.status')"
# Expected: VERIFIED

# This also updates the order status to PAID
ORDER_AFTER_PAYMENT=$(curl -s http://localhost:8000/api/v1/orders/$ORDER_ID)
echo "Order Status after Payment Verify: $(echo $ORDER_AFTER_PAYMENT | jq -r '.status')"
# Expected: PAID
```

### Step 8: Accountant Verifies Order (Optional Quality Check)

```bash
VERIFY_ORDER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/verify \
  -H "Content-Type: application/json")

echo "Order Status after Order Verify: $(echo $VERIFY_ORDER_RESPONSE | jq -r '.status')"
# Expected: VERIFIED
```

### Step 9: Order Staff Ships Order

```bash
SHIP_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/ship \
  -H "Content-Type: application/json")

echo "Order Status after Ship: $(echo $SHIP_RESPONSE | jq -r '.status')"
# Expected: SHIPPED
```

### Step 10: Order Staff Closes Order

```bash
CLOSE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/close \
  -H "Content-Type: application/json")

echo "Order Status after Close: $(echo $CLOSE_RESPONSE | jq -r '.status')"
# Expected: CLOSED
```

### Verify Complete Workflow

```bash
FINAL_ORDER=$(curl -s http://localhost:8000/api/v1/orders/$ORDER_ID)
echo "Final Order Status: $(echo $FINAL_ORDER | jq -r '.status')"
# Expected: CLOSED
```

---

## Field Validation Rules

This section provides a comprehensive reference for all field validation rules. All rules are enforced server-side.

### Customer Fields

| Field | Type | Required | Min | Max | Format/Regex | Notes |
|-------|------|----------|-----|-----|--------------|-------|
| id | UUID | Server-generated | - | - | UUIDv4 | Immutable |
| name | string | Yes | 2 chars | 100 chars | `^[\p{L} .'-]+$` | Letters, spaces, apostrophes, hyphens |
| address | string | Yes | 5 chars | 255 chars | Free text | Not blank |
| phone | string | Yes | 8 digits | 15 digits | `^\+?[1-9]\d{7,14}$` | E.164 format |
| bankingDetails.accountNumber | string | Yes | 6 digits | 20 digits | `^\d{6,20}$` | Numeric only |
| bankingDetails.bankName | string | Yes | 2 chars | 100 chars | `^[\p{L}0-9 .&-]+$` | Alphanumeric |
| role | enum | Yes | - | - | Exact match | `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT` |
| orderHistory | array | Read-only | 0 | 10,000 | - | Server-derived |

### Product Fields

| Field | Type | Required | Min | Max | Format/Regex | Notes |
|-------|------|----------|-----|-----|--------------|-------|
| id | UUID | Server-generated | - | - | UUIDv4 | Immutable |
| description | string | Yes | 3 chars | 500 chars | Free text | Not blank |
| price.amount | decimal | Yes | 0.01 | 999999.99 | `^\d{1,6}\.\d{2}$` | Exactly 2 decimal places |
| price.currency | string | Yes | 3 chars | 3 chars | `^[A-Z]{3}$` | `USD`, `VND`, `EUR` |

### Order Fields

| Field | Type | Required | Min | Max | Format/Regex | Notes |
|-------|------|----------|-----|-----|--------------|-------|
| id | UUID | Server-generated | - | - | UUIDv4 | Immutable |
| customerRef | UUID | Yes | - | - | UUIDv4 | Must exist |
| lineItems | array | Yes | 1 item | 100 items | - | No duplicate productRef |
| lineItems[].productRef | UUID | Yes | - | - | UUIDv4 | Must exist |
| lineItems[].quantity | integer | Yes | 1 | 1000 | `^\d+$` | Whole number |
| lineItems[].unitPriceSnapshot | decimal | Server-computed | 0.01 | 999999.99 | `^\d{1,6}\.\d{2}$` | From product at order time |
| totalAmount | decimal | Server-computed | 0.01 | 99999999.99 | `^\d{1,8}\.\d{2}$` | Sum of line items |
| status | enum | Yes | - | - | Exact match | See state machine |
| invoiceRef | UUID | Optional | - | - | UUIDv4 | Set when invoiced |

### Payment Fields

| Field | Type | Required | Min | Max | Format/Regex | Notes |
|-------|------|----------|-----|-----|--------------|-------|
| id | UUID | Server-generated | - | - | UUIDv4 | - |
| orderRef | UUID | Yes | - | - | UUIDv4 | Order must be INVOICED |
| amount | decimal | Yes | 0.01 | 99999999.99 | `^\d{1,8}\.\d{2}$` | Must match invoice total |
| timestamp | datetime | Server-generated | - | - | ISO 8601 UTC | - |
| status | enum | Yes | - | - | Exact match | `PENDING`, `VERIFIED`, `REJECTED` |
| method | enum | Yes | - | - | Exact match | `CREDIT_CARD`, `BANK_TRANSFER`, `E_WALLET` |

### Invoice Fields

| Field | Type | Required | Min | Max | Format/Regex | Notes |
|-------|------|----------|-----|-----|--------------|-------|
| id | UUID | Server-generated | - | - | UUIDv4 | - |
| orderRef | UUID | Yes | - | - | UUIDv4 | Order must be ACCEPTED |
| billingInfo.name | string | Yes | 2 chars | 100 chars | `^[\p{L} .'-]+$` | Snapshot from customer |
| billingInfo.address | string | Yes | 5 chars | 255 chars | Free text | Snapshot from customer |
| totalAmount | decimal | Yes | 0.01 | 99999999.99 | `^\d{1,8}\.\d{2}$` | Must match order total |
| issueDate | date | Yes | - | - | `dd/MM/yyyy` | Valid calendar date |
| dueDate | date | Yes | - | - | `dd/MM/yyyy` | >= issueDate, valid date |
| status | enum | Yes | - | - | Exact match | `ISSUED`, `PAID`, `OVERDUE`, `CANCELLED` |

### Important Validation Notes

1. **UUID Validation**: Two-step process
   - Format validation (400 if malformed)
   - Existence validation (404 if not found)

2. **Decimal Precision**: Exactly 2 decimal places required - additional precision is rejected, not rounded

3. **Date Validation**: Two independent checks
   - Regex format check (`dd/MM/yyyy`)
   - Calendar semantic validity (e.g., 31/02/2024 is rejected)

4. **Computed Fields**: `totalAmount` and `unitPriceSnapshot` are always server-computed - client values are ignored

5. **State Transitions**: Invalid state transitions return `409 Conflict`

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Symptoms**: Application fails to start, error messages about database connection

**Solutions**:
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs oms_postgres

# Test connection
docker exec oms_postgres psql -U postgres -d oms_db -c "SELECT 1"

# Restart PostgreSQL
docker-compose restart postgres
```

#### 2. Redis Connection Failed

**Symptoms**: Caching not working, rate limiting not enforced

**Solutions**:
```bash
# Check if Redis is running
docker ps | grep redis

# Test Redis connection
docker exec oms_redis redis-cli ping
# Expected: PONG

# Restart Redis
docker-compose restart redis
```

**Note**: The application is designed for graceful degradation - it will continue working with in-memory fallback if Redis is unavailable.

#### 3. Rate Limiting Triggered (429 Too Many Requests)

**Symptoms**: Requests return 429 status code

**Solutions**:
- Wait for rate limit to reset (default: 100 requests/second)
- Increase rate limit by setting `RATE_LIMIT_MAX_EVENTS` environment variable
- Implement request throttling on client side

#### 4. Validation Errors (400 Bad Request)

**Symptoms**: Requests return 400 with validation error messages

**Solutions**:
- Check field validation rules in this manual
- Ensure all required fields are present
- Verify field formats (phone, dates, UUIDs, decimals)
- Check field length constraints

#### 5. Not Found Errors (404 Not Found)

**Symptoms**: GET requests return 404

**Solutions**:
- Verify the ID exists in the database
- Check UUID format (must be valid UUIDv4)
- Ensure entity wasn't deleted

#### 6. Conflict Errors (409 Conflict)

**Symptoms**: Workflow actions return 409

**Solutions**:
- Check current entity status
- Verify state transition is valid (see state machines)
- Example: Cannot verify payment that's already verified

### View Application Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f oms_backend
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Reset Database

If you need to reset the database to a clean state:

```bash
# Stop all services
docker-compose down

# Remove PostgreSQL volume (WARNING: deletes all data)
docker volume rm oms_postgres_data

# Restart
docker-compose up -d

# Re-initialize database
docker exec oms_postgres psql -U postgres -d oms_db -f /docker-entrypoint-initdb.d/init.sql
```

### Health Check

```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "database": "connected", "cache": "connected"}
```

### Performance Issues

If experiencing slow responses:

1. **Check Database Performance**:
   ```bash
   docker exec oms_postgres psql -U postgres -d oms_db -c "SELECT * FROM pg_stat_activity;"
   ```

2. **Check Cache Hit Rate**:
   ```bash
   docker exec oms_redis redis-cli INFO stats | grep keyspace_hits
   docker exec oms_redis redis-cli INFO stats | grep keyspace_misses
   ```

3. **Enable Debug Mode**:
   Set `DEBUG=true` in environment variables for detailed logging

---

## Support and Resources

### API Documentation
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

### Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/oms_db` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `DEBUG` | `false` | Enable debug mode |
| `ENABLE_CACHING` | `true` | Enable Redis caching |
| `ENABLE_RATE_LIMITING` | `true` | Enable rate limiting |
| `RATE_LIMIT_MAX_EVENTS` | `100` | Max events per second |
| `REDIS_CACHE_TTL` | `300` | Cache TTL in seconds (5 minutes) |

### File Structure

```
oms_backend/
├── config/           # Configuration settings
├── controller/       # REST API controllers
├── domain/           # Domain models
├── infrastructure/   # Database and external services
├── repository/       # Data access layer
├── service/          # Business logic layer
├── utils/            # Utilities (cache, rate limiter, validators)
└── server.py         # Main application entry point
```

### Key Documentation Files

- `ARCHITECTURE.md` - System architecture and design decisions
- `DEPLOYMENT.md` - Detailed deployment instructions
- `VERIFICATION.md` - NFR verification steps
- `create_apis.json` - API endpoint mapping for automated testing
- `nfr-trace.json` - NFR traceability matrix (machine-readable)

---

## Appendix: Example Request/Response Pairs

### Create Customer - Success

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": "123 Main St",
    "phone": "+1234567890",
    "bankingDetails": {"accountNumber": "123456", "bankName": "Test Bank"},
    "role": "CUSTOMER"
  }'
```

**Response** (201):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "John Doe",
  "address": "123 Main St",
  "phone": "+1234567890",
  "bankingDetails": {"accountNumber": "123456", "bankName": "Test Bank"},
  "role": "CUSTOMER",
  "orderHistory": [],
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:30:00Z"
}
```

### Create Order - Validation Error

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerRef": "invalid-uuid",
    "lineItems": [{"productRef": "product-id", "quantity": 0}]
  }'
```

**Response** (400):
```json
{
  "detail": "Invalid UUID format for customerRef"
}
```

### Order State Transition - Conflict

**Request** (trying to skip states):
```bash
curl -X POST http://localhost:8000/api/v1/orders/{order-id}/ship \
  -H "Content-Type: application/json"
```

**Response** (409 - order is still PLACED, not VERIFIED):
```json
{
  "detail": "Invalid state transition: cannot ship order in PLACED status"
}
```

---

*End of User Manual*
