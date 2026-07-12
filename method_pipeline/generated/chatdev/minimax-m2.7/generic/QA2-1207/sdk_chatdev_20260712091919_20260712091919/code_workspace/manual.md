# OMS Backend User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Main Functions](#main-functions)
4. [Installation and Setup](#installation-and-setup)
5. [How to Use the System](#how-to-use-the-system)
6. [NFR Verification Guide](#nfr-verification-guide)
7. [Deployment](#deployment)

---

## Introduction

The **Order Management System (OMS) Backend** is a production-grade, backend-only system that handles the complete e-commerce workflow:

1. **Customer places order**
2. **Order Staff reviews & accepts**
3. **Accountant creates invoice**
4. **Customer pays invoice**
5. **Accountant verifies payment**
6. **Order Staff ships paid order**
7. **Order Staff closes completed order**

The system implements three Non-Functional Requirements (NFRs):

| NFR | Description |
|-----|-------------|
| **NFR 2.1** | Graceful Degradation - Core checkout remains available under resource contention |
| **NFR 2.2** | Fault Detection and Recovery - Automatic detection and recovery from component failures |
| **NFR 2.3** | State Preservation - Restore operational state after unexpected crashes |

### Tech Stack
- **Framework**: FastAPI (Python 3.10+)
- **Database**: SQLite with WAL journal mode (crash-safe)
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **Server**: Uvicorn

---

## System Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      API Layer                          │
│   /api/v1/customers  /api/v1/orders  /api/v1/invoices   │
│   /api/v1/payments   /api/v1/products /api/v1/health    │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                  Controller Layer                       │
│  CustomerController  OrderController  InvoiceController │
│  PaymentController   ProductController  HealthController│
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                         │
│   CustomerService  OrderService  InvoiceService         │
│   PaymentService   ProductService                       │
│   CircuitBreaker   StateManager   FeatureFlags         │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                Infrastructure Layer                     │
│   SQLAlchemy Repositories  SQLite Database              │
│   Health Checks  State Snapshots                        │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                     Domain Layer                        │
│   Customer  Order  Product  Payment  Invoice  LineItem  │
└─────────────────────────────────────────────────────────┘
```

### Domain Entities

| Entity | Description |
|--------|-------------|
| **Customer** | id, name, email, phone, address, banking_details, role |
| **Order** | id, customer_id, line_items, status, amounts, timestamps, invoice_id |
| **Product** | id, sku, description, base_price, currency, stock_quantity |
| **Payment** | id, order_id, invoice_id, amount, status, method, transaction_ref |
| **Invoice** | id, order_id, billing_info, amounts, dates, status |

### Order Status Lifecycle

```
PENDING → ACCEPTED → INVOICED → PAID → SHIPPED → COMPLETED
    │         │
    └─────────┴──────→ REJECTED / CANCELLED
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/customers` | Create customer |
| GET | `/api/v1/customers` | List customers |
| GET | `/api/v1/customers/{id}` | Get customer |
| POST | `/api/v1/products` | Create product |
| GET | `/api/v1/products` | List products |
| POST | `/api/v1/orders` | Place order |
| GET | `/api/v1/orders` | List orders |
| GET | `/api/v1/orders/{id}` | Get order |
| PATCH | `/api/v1/orders/{id}/accept` | Accept order |
| PATCH | `/api/v1/orders/{id}/reject` | Reject order |
| PATCH | `/api/v1/orders/{id}/ship` | Ship order |
| PATCH | `/api/v1/orders/{id}/close` | Close order |
| POST | `/api/v1/invoices` | Create invoice |
| PATCH | `/api/v1/invoices/{id}/issue` | Issue invoice |
| POST | `/api/v1/payments` | Create payment |
| POST | `/api/v1/payments/{id}/verify` | Verify payment |
| GET | `/api/v1/health` | System health |
| GET | `/api/v1/health/nfr-verification` | NFR status |

---

## Main Functions

### 1. Customer Management

**Create Customer:**
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "address": {
      "street": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "USA"
    }
  }'
```

### 2. Product Catalog

**Create Product:**
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "LAPTOP-001",
    "description": "Gaming Laptop",
    "base_price": 1299.99,
    "currency": "USD",
    "stock_quantity": 50
  }'
```

### 3. Order Workflow

**Place Order (Step 1):**
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<customer_id>",
    "line_items": [
      {
        "product_id": "<product_id>",
        "product_description": "Gaming Laptop",
        "quantity": 1,
        "unit_price": 1299.99
      }
    ],
    "shipping_address": {
      "street": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "USA"
    },
    "notes": "Please gift wrap"
  }'
```

**Accept Order (Step 2):**
```bash
curl -X PATCH http://localhost:8000/api/v1/orders/<order_id>/accept
```

### 4. Invoice Management

**Create Invoice (Step 3):**
```bash
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<order_id>",
    "customer_id": "<customer_id>",
    "billing_address": {
      "street": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "USA"
    },
    "due_date_days": 30
  }'
```

**Issue Invoice:**
```bash
curl -X PATCH http://localhost:8000/api/v1/invoices/<invoice_id>/issue
```

### 5. Payment Processing

**Create Payment (Step 4):**
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<order_id>",
    "invoice_id": "<invoice_id>",
    "customer_id": "<customer_id>",
    "amount": 1429.99,
    "method": "bank_transfer"
  }'
```

**Verify Payment (Step 5):**
```bash
curl -X POST http://localhost:8000/api/v1/payments/<payment_id>/verify
```

### 6. Shipping and Closure

**Ship Order (Step 6):**
```bash
curl -X PATCH http://localhost:8000/api/v1/orders/<order_id>/ship \
  -H "Content-Type: application/json" \
  -d '{"tracking_number": "TRK123456789"}'
```

**Close Order (Step 7):**
```bash
curl -X PATCH http://localhost:8000/api/v1/orders/<order_id>/close
```

---

## Installation and Setup

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- curl or httpie for API testing

### Local Installation

#### Option 1: Using Virtual Environment

```bash
cd oms_backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Option 2: Using uv (Recommended)

```bash
cd oms_backend

# Install dependencies with uv
uv sync

# Or install directly
uv pip install -r requirements.txt
```

### Start the Server

```bash
# From the oms_backend directory
python -m src.main

# Or using uvicorn directly
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

### Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# View API documentation
open http://localhost:8000/docs  # Swagger UI
open http://localhost:8000/redoc  # ReDoc
```

---

## How to Use the System

### Complete Workflow Example

Run the automated workflow verification script:

```bash
cd oms_backend
./verify_workflow.sh
```

This script executes all 7 steps of the order workflow:
1. Health check
2. Create customer
3. Create product
4. Place order
5. Accept order
6. Create invoice
7. Issue invoice
8. Create payment
9. Verify payment
10. Ship order
11. Close order

### Manual Workflow Walkthrough

```bash
BASE_URL="http://localhost:8000"

# Step 1: Create a customer
CUSTOMER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/customers" \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "email": "jane@example.com", "phone": "+1987654321"}')
echo $CUSTOMER_RESPONSE

# Step 2: Create a product
PRODUCT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/products" \
  -H "Content-Type: application/json" \
  -d '{"sku": "PHONE-001", "description": "Smartphone", "base_price": 699.99, "stock_quantity": 100}')
echo $PRODUCT_RESPONSE

# Step 3: Place an order
ORDER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<customer_id>",
    "line_items": [{"product_id": "<product_id>", "product_description": "Smartphone", "quantity": 1, "unit_price": 699.99}],
    "shipping_address": {"street": "456 Oak Ave", "city": "Los Angeles", "state": "CA", "postal_code": "90001", "country": "USA"}
  }')
echo $ORDER_RESPONSE

# Step 4: Accept the order
curl -X PATCH "$BASE_URL/api/v1/orders/<order_id>/accept"

# Step 5: Create invoice
curl -X POST "$BASE_URL/api/v1/invoices" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "<order_id>", "customer_id": "<customer_id>", "billing_address": {...}}'

# Step 6: Issue invoice
curl -X PATCH "$BASE_URL/api/v1/invoices/<invoice_id>/issue"

# Step 7: Create payment
curl -X POST "$BASE_URL/api/v1/payments" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "<order_id>", "invoice_id": "<invoice_id>", "customer_id": "<customer_id>", "amount": 769.99}'

# Step 8: Verify payment
curl -X POST "$BASE_URL/api/v1/payments/<payment_id>/verify"

# Step 9: Ship order
curl -X PATCH "$BASE_URL/api/v1/orders/<order_id>/ship" \
  -H "Content-Type: application/json" \
  -d '{"tracking_number": "FEDEX123456"}'

# Step 10: Close order
curl -X PATCH "$BASE_URL/api/v1/orders/<order_id>/close"
```

---

## NFR Verification Guide

### NFR 2.1: Graceful Degradation

**Requirement:** Under extreme resource contention, core checkout functionality must remain available.

**Verification:**

```bash
# 1. Check current feature flags
curl http://localhost:8000/api/v1/health/features

# 2. Disable non-essential features (simulating resource contention)
curl -X POST http://localhost:8000/api/v1/health/features/disable-non-essential

# 3. Verify core endpoints still work
curl http://localhost:8000/api/v1/health/live
curl -X POST http://localhost:8000/api/v1/orders  # Should still work
```

**Expected Response:**
```json
{
  "analytics_enabled": false,
  "notifications_enabled": false,
  "audit_log_enabled": false,
  "non_core_features_enabled": false,
  "payment_gateway_enabled": true,
  "core_checkout_enabled": true
}
```

### NFR 2.2: Fault Detection and Recovery

**Requirement:** The application must detect internal component failures and automatically attempt to recover.

**Verification:**

```bash
# 1. Overall health check
curl http://localhost:8000/api/v1/health

# 2. Component-level health
curl http://localhost:8000/api/v1/health/nfr-verification

# 3. Database health (verifies WAL mode)
curl http://localhost:8000/api/v1/health/db

# 4. Readiness probe
curl http://localhost:8000/api/v1/health/ready
```

**Expected Response for NFR Verification:**
```json
{
  "nfr_2_1_graceful_degradation": {
    "status": "operational",
    "feature_flags": {...},
    "core_checkout_enabled": true
  },
  "nfr_2_2_fault_detection": {
    "status": "healthy",
    "component_count": 1,
    "components": {"database": {...}}
  },
  "nfr_2_3_state_preservation": {
    "status": "operational",
    "pending_recoveries": 0
  }
}
```

### NFR 2.3: State Preservation

**Requirement:** System must restore operational state after unexpected crashes with minimal data loss.

**Verification:**

```bash
# 1. Check WAL mode is enabled
curl http://localhost:8000/api/v1/health/db | grep wal_mode
# Expected: "wal_mode": "wal"

# 2. Test idempotency - same key should return same order
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key": "test-key-123", ...}'
# Repeat - should return same order

# 3. Check pending recoveries
curl http://localhost:8000/api/v1/health/nfr-verification | jq .nfr_2_3_state_preservation
```

**Crash Recovery Test:**

1. Start server and place an order
2. Kill the server process (`Ctrl+C` or `kill`)
3. Restart the server
4. Check recovery: `curl http://localhost:8000/api/v1/health/nfr-verification`
5. Verify order still exists: `curl http://localhost:8000/api/v1/orders/<order_id>`

---

## Deployment

### Local Deployment with Docker

#### Build and Run

```bash
cd oms_backend

# Build Docker image
docker build -t oms-backend .

# Run container
docker run -p 8000:8000 oms-backend
```

#### Using Docker Compose

```bash
cd oms_backend

# Start all services
docker-compose up

# Stop services
docker-compose down
```

### Production Considerations

1. **Database**: The system uses SQLite with WAL mode for crash safety. For multi-instance deployments, consider migrating to PostgreSQL.

2. **Environment Variables**: Override configuration via environment variables:
   ```bash
   export OMS_DB_URL="postgresql://user:pass@host:5432/oms"
   export OMS_DEBUG=false
   ```

3. **Reverse Proxy**: Use nginx or similar for production:
   ```nginx
   location / {
       proxy_pass http://localhost:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

4. **Process Management**: Use systemd or supervisor for production:
   ```ini
   [Unit]
   Description=OMS Backend
   After=network.target

   [Service]
   ExecStart=/opt/oms/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
   WorkingDirectory=/opt/oms
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

---

## Configuration

The system is configured via `config.json`:

```json
{
  "app": {
    "name": "OMS Backend",
    "version": "1.0.0",
    "host": "0.0.0.0",
    "port": 8000
  },
  "database": {
    "url": "sqlite:///./oms.db",
    "echo": false
  },
  "resilience": {
    "circuit_breaker": {
      "failure_threshold": 5,
      "recovery_timeout": 60
    },
    "state_snapshot_interval": 30
  }
}
```

---

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.yaml

---

## Troubleshooting

### Server Won't Start

1. Check if port 8000 is already in use:
   ```bash
   lsof -i :8000
   ```

2. Verify Python version (3.10+ required):
   ```bash
   python --version
   ```

3. Check database permissions:
   ```bash
   ls -la oms_backend/oms.db
   ```

### Database Issues

1. Reset database:
   ```bash
   rm oms_backend/oms.db
   python -m src.main  # Recreates database
   ```

2. Check WAL mode:
   ```bash
   sqlite3 oms_backend/oms.db "PRAGMA journal_mode;"
   # Should return: wal
   ```

### NFR Verification Failures

1. **Graceful Degradation not working**: Check feature flags endpoint
2. **Fault Detection not working**: Verify health check components are registered
3. **State Preservation not working**: Check WAL mode and snapshot directory permissions

---

## File Structure

```
oms_backend/
├── config.json              # Application configuration
├── Dockerfile               # Docker container definition
├── docker-compose.yml      # Docker Compose configuration
├── openapi.yaml            # OpenAPI specification
├── pyproject.toml          # Python project configuration
├── requirements.txt        # Python dependencies
├── README.md               # Project overview
├── docs/
│   ├── ADR.md              # Architectural Decision Records
│   ├── ARCHITECTURE.md     # Architecture overview
│   ├── DATA_ARCHITECTURE.md # Database schema documentation
│   ├── DEPLOYMENT.md       # Deployment guide
│   ├── NFR_TRACEABILITY.md # NFR to component mapping
│   └── NFR_VERIFICATION.md # NFR verification steps
├── data/
│   └── snapshots/          # State snapshots for crash recovery
├── src/
│   ├── __init__.py
│   ├── main.py             # FastAPI application entry point
│   ├── api/
│   │   └── __init__.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── customer_controller.py
│   │   ├── health_controller.py
│   │   ├── invoice_controller.py
│   │   ├── order_controller.py
│   │   ├── payment_controller.py
│   │   └── product_controller.py
│   ├── domain/
│   │   ├── __init__.py
│   │   └── models.py       # Domain models (shared)
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database.py     # SQLAlchemy setup with WAL
│   │   ├── models.py      # ORM models
│   │   └── repositories.py # Data access layer
│   ├── services/
│   │   ├── __init__.py
│   │   ├── customer_service.py
│   │   ├── invoice_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   └── product_service.py
│   └── utils/
│       ├── __init__.py
│       └── resilience.py   # Circuit breaker, feature flags, state manager
└── tests/
    ├── __init__.py
    └── test_oms.py         # Unit tests
```

---

## Support

For issues or questions:
1. Check the NFR verification endpoints
2. Review logs in the console output
3. Consult the documentation in `docs/`
4. Examine the OpenAPI spec at `/docs`
