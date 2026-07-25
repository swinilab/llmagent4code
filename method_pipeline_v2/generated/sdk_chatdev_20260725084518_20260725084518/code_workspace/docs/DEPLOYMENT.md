# Local Deployment Guide

## Prerequisites

- Python 3.11 or higher
- uv package manager

## Installation

1. **Initialize Python environment:**
   ```bash
   uv venv --python 3.11
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

## Running the Application

### Option 1: Using start_command.txt
```bash
cat start_command.txt | bash
```

### Option 2: Direct command
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 3: With auto-reload for development
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Verifying Deployment

1. **Check root endpoint:**
   ```bash
   curl http://localhost:8000
   ```

2. **Check health endpoints:**
   ```bash
   curl http://localhost:8000/api/v1/health/live
   curl http://localhost:8000/api/v1/health/ready
   curl http://localhost:8000/api/v1/health
   ```

3. **Check queue status:**
   ```bash
   curl http://localhost:8000/api/v1/health/queue
   ```

4. **Access OpenAPI docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Customers
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers` - List customers
- `GET /api/v1/customers/{id}` - Get customer

### Products
- `POST /api/v1/products` - Create product
- `GET /api/v1/products` - List products
- `GET /api/v1/products/{id}` - Get product

### Orders
- `POST /api/v1/orders` - Create order (async, returns 202)
- `GET /api/v1/orders` - List orders
- `GET /api/v1/orders/{id}` - Get order
- `GET /api/v1/orders/recent` - Get most recent orders
- `PUT /api/v1/orders/{id}/review` - Review order
- `PUT /api/v1/orders/{id}/accept` - Accept order
- `PUT /api/v1/orders/{id}/cancel` - Cancel order
- `PUT /api/v1/orders/{id}/ship` - Ship order
- `PUT /api/v1/orders/{id}/close` - Close order

### Invoices
- `POST /api/v1/invoices` - Create invoice
- `GET /api/v1/invoices` - List invoices
- `GET /api/v1/invoices/{id}` - Get invoice
- `GET /api/v1/invoices/order/{orderRef}` - Get invoice by order
- `PUT /api/v1/invoices/{id}/cancel` - Cancel invoice

### Payments
- `POST /api/v1/payments` - Create payment
- `GET /api/v1/payments` - List payments
- `GET /api/v1/payments/{id}` - Get payment
- `GET /api/v1/payments/order/{orderRef}` - Get payment by order
- `PUT /api/v1/payments/{id}/verify` - Verify payment
- `PUT /api/v1/payments/{id}/reject` - Reject payment

## Testing the Workflow

### Step 1: Create Customer
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": "123 Main Street, City",
    "phone": "+1234567890",
    "accountNumber": "123456789",
    "bankName": "Test Bank",
    "role": "CUSTOMER"
  }'
```

### Step 2: Create Product
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Test Product",
    "price": {
      "amount": "19.99",
      "currency": "USD"
    }
  }'
```

### Step 3: Create Order
```bash
curl -X POST http://localhost:8000/api/v1/orders \
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

### Step 4: Accept Order
```bash
curl -X PUT http://localhost:8000/api/v1/orders/<order-id>/accept
```

### Step 5: Create Invoice
```bash
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "<order-id>"
  }'
```

### Step 6: Create Payment
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "<order-id>",
    "amount": "39.98",
    "method": "CREDIT_CARD"
  }'
```

### Step 7: Verify Payment
```bash
curl -X PUT http://localhost:8000/api/v1/payments/<payment-id>/verify
```

### Step 8: Ship Order
```bash
curl -X PUT http://localhost:8000/api/v1/orders/<order-id>/ship
```

### Step 9: Close Order
```bash
curl -X PUT http://localhost:8000/api/v1/orders/<order-id>/close
```

## Infrastructure as Code (IaC)

See `iac/` directory for deployment configurations.

## Monitoring

- **Health:** `/api/v1/health`
- **Queue Status:** `/api/v1/health/queue`
- **Degradation Status:** `/api/v1/health/degradation`

## Shutdown

Press `Ctrl+C` to stop the server. The application will gracefully:
1. Stop queue workers
2. Close database connections
3. Save any pending state
