# OMS Backend - Local Deployment Guide

## Prerequisites
- Python 3.10+
- Docker (optional, for containerized deployment)
- curl or httpie (for API testing)

## Local Deployment (Python Virtual Environment)

### 1. Create Virtual Environment

```bash
cd oms_backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Database Migration (Automatic)

On first startup, the database tables are created automatically:
```
python -m src.main
```

### 4. Start the Server

```bash
python -m src.main
```

Or using uvicorn directly:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 5. Verify Server is Running

```bash
curl http://localhost:8000/api/v1/health
```

## Docker Deployment

### 1. Build and Run

```bash
docker-compose up --build
```

### 2. Verify Docker Deployment

```bash
curl http://localhost:8000/api/v1/health
```

## Verification Steps

### Step 1: Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Step 2: NFR Verification
```bash
curl http://localhost:8000/api/v1/health/nfr-verification
```

### Step 3: Create a Customer
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

### Step 4: Create a Product
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "PROD-001",
    "description": "Test Product",
    "base_price": 99.99,
    "stock_quantity": 100
  }'
```

### Step 5: Place Order (Workflow Step 1)
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<customer_id>",
    "line_items": [
      {
        "product_id": "<product_id>",
        "product_description": "Test Product",
        "quantity": 2,
        "unit_price": 99.99
      }
    ],
    "shipping_address": {
      "street": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "USA"
    }
  }'
```

### Step 6: Accept Order (Workflow Step 2)
```bash
curl -X PATCH http://localhost:8000/api/v1/orders/<order_id>/accept
```

### Step 7: Create Invoice (Workflow Step 3)
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
    }
  }'
```

### Step 8: Issue Invoice
```bash
curl -X PATCH http://localhost:8000/api/v1/invoices/<invoice_id>/issue
```

### Step 9: Create Payment (Workflow Step 4)
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<order_id>",
    "invoice_id": "<invoice_id>",
    "customer_id": "<customer_id>",
    "amount": 219.98
  }'
```

### Step 10: Process Payment
```bash
curl -X POST http://localhost:8000/api/v1/payments/<payment_id>/process
```

### Step 11: Verify Payment (Workflow Step 5)
```bash
curl -X POST http://localhost:8000/api/v1/payments/<payment_id>/verify
```

### Step 12: Ship Order (Workflow Step 6)
```bash
curl -X PATCH "http://localhost:8000/api/v1/orders/<order_id>/ship?tracking_number=TRACK-123"
```

### Step 13: Close Order (Workflow Step 7)
```bash
curl -X PATCH http://localhost:8000/api/v1/orders/<order_id>/close
```

## Running Tests

```bash
pytest tests/ -v
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
