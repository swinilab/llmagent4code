# OMS Backend - Local Deployment Guide

## Prerequisites

- Python 3.11+
- uv (Python package manager)

## Quick Start

### 1. Install Dependencies

```bash
cd oms-backend
uv sync
```

### 2. Start the Server

```bash
uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the start command file:

```bash
cat /start_command.txt
# Output: uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 3. Verify Server is Running

```bash
curl http://127.0.0.1:8000/health
```

Expected response:
```json
{"status":"healthy","timestamp":1234567890.123}
```

## API Endpoints

### Customer
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers/{id}` - Get customer by ID
- `GET /api/v1/customers` - List all customers

### Product
- `POST /api/v1/products` - Create product
- `GET /api/v1/products/{id}` - Get product by ID
- `GET /api/v1/products` - List all products

### Order
- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders/{id}` - Get order by ID
- `GET /api/v1/orders` - List all orders
- `POST /api/v1/orders/{id}/accept` - Accept order (Order Staff)
- `POST /api/v1/orders/{id}/ship` - Ship order (Order Staff)
- `POST /api/v1/orders/{id}/close` - Close order (Order Staff)
- `POST /api/v1/orders/{id}/cancel` - Cancel order

### Invoice
- `POST /api/v1/invoices` - Create invoice (Accountant)
- `GET /api/v1/invoices/{id}` - Get invoice by ID
- `GET /api/v1/invoices` - List all invoices
- `GET /api/v1/invoices/order/{order_id}` - Get invoice by order

### Payment
- `POST /api/v1/payments` - Create payment
- `GET /api/v1/payments/{id}` - Get payment by ID
- `GET /api/v1/payments` - List all payments
- `POST /api/v1/payments/{id}/verify` - Verify payment (Accountant)
- `POST /api/v1/payments/{id}/reject` - Reject payment (Accountant)

## Example Workflow

### 1. Create Customer
```bash
curl -X POST http://127.0.0.1:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": "123 Main Street, New York, NY 10001",
    "phone": "+12125551234",
    "bankingDetails": {
      "accountNumber": "123456789",
      "bankName": "Chase Bank"
    },
    "role": "CUSTOMER"
  }'
```

### 2. Create Product
```bash
curl -X POST http://127.0.0.1:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Premium Widget",
    "price": {
      "amount": "29.99",
      "currency": "USD"
    }
  }'
```

### 3. Create Order
```bash
curl -X POST http://127.0.0.1:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerRef": "<customer-id>",
    "lineItems": [
      {
        "productRef": "<product-id>",
        "quantity": 2
      }
    ]
  }'
```

### 4. Accept Order (Order Staff)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/orders/<order-id>/accept
```

### 5. Create Invoice (Accountant)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "<order-id>",
    "billingInfo": {
      "name": "John Doe",
      "address": "123 Main Street, New York, NY 10001"
    }
  }'
```

### 6. Create Payment (Customer)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "<order-id>",
    "amount": "59.98",
    "method": "CREDIT_CARD"
  }'
```

### 7. Verify Payment (Accountant)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/payments/<payment-id>/verify
```

### 8. Ship Order (Order Staff)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/orders/<order-id>/ship
```

### 9. Close Order (Order Staff)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/orders/<order-id>/close
```

## Running NFR Verification Suite

### Run All Tests
```bash
cd oms-backend
bash verification/run_all.sh
```

### Run Individual Tests
```bash
# NFR 1.1 - Rate Limiting
uv run python verification/verify_nfr_1_1.py

# NFR 1.2 - Multiple Data Copies
uv run python verification/verify_nfr_1_2.py

# NFR 2.1 - Timeout Detection
uv run python verification/verify_nfr_2_1.py

# NFR 2.2 - Graceful Degradation
uv run python verification/verify_nfr_2_2.py

# NFR 2.3 - State Resynchronization
uv run python verification/verify_nfr_2_3.py

# NFR 2.4 - Transactions
uv run python verification/verify_nfr_2_4.py
```

### View Results
```bash
cat verification/results/nfr-*.json
```

## Data Persistence

Data is stored in SQLite database file `oms.db` in the project root. The database persists across application restarts.

### Database Tables
- `customers` - Customer records
- `products` - Product records
- `orders` - Order records
- `payments` - Payment records
- `invoices` - Invoice records

### Reset Database
```bash
rm oms.db
# Server will recreate tables on next start
```

## Configuration

### Rate Limiting (NFR 1.1)
Default: 100 requests per 60 seconds
Modify in `src/services/services.py`:
```python
rate_limiter = RateLimiter(max_events=100, window_seconds=60)
```

### Request Timeout (NFR 2.1)
Default: 30 seconds
Modify in `src/main.py`:
```python
timeout_seconds = 30
```

## OpenAPI Documentation

Access interactive API documentation at:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
