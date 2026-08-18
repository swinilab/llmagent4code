# OMS Deployment Guide

## Prerequisites
- Python 3.11 or higher
- uv package manager

## Local Deployment

### 1. Install Dependencies
```bash
uv sync
```

### 2. Start the Application
```bash
uv run python main.py
```

Or use the start command:
```bash
cat start_command.txt | bash
```

### 3. Verify Deployment
Open browser or use curl:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### 4. Access OpenAPI Documentation
Navigate to: http://localhost:8000/docs

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OMS_HOST | 0.0.0.0 | Server bind address |
| OMS_PORT | 8000 | Server port |
| OMS_DATABASE_URL | sqlite+aiosqlite:///./oms.db | Database connection string |
| OMS_CACHE_TTL | 300 | Cache TTL in seconds |
| OMS_RATE_LIMIT | 100 | Max events per window |
| OMS_RATE_LIMIT_WINDOW | 60 | Rate limit window in seconds |

## Testing the Workflow

### 1. Create a Customer
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": "123 Main Street, City",
    "phone": "+1234567890",
    "bankingDetails": {
      "accountNumber": "123456789012",
      "bankName": "Test Bank"
    },
    "role": "CUSTOMER"
  }'
```

### 2. Create a Product
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

### 3. Create an Order
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerRef": "<customer-id>",
    "lineItems": [{
      "productRef": "<product-id>",
      "quantity": 2
    }]
  }'
```

### 4. Accept Order (Order Staff)
```bash
curl -X PUT http://localhost:8000/api/v1/orders/<order-id>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "ACCEPTED"}'
```

### 5. Create Invoice (Accountant)
```bash
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "<order-id>"
  }'
```

### 6. Create Payment (Customer)
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "orderRef": "<order-id>",
    "amount": "<invoice-amount>",
    "method": "CREDIT_CARD"
  }'
```

### 7. Verify Payment (Accountant)
```bash
curl -X PUT http://localhost:8000/api/v1/payments/<payment-id>/verify \
  -H "Content-Type: application/json" \
  -d '{"status": "VERIFIED"}'
```

### 8. Ship Order (Order Staff)
```bash
curl -X PUT http://localhost:8000/api/v1/orders/<order-id>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "SHIPPED"}'
```

### 9. Close Order (Order Staff)
```bash
curl -X PUT http://localhost:8000/api/v1/orders/<order-id>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "CLOSED"}'
```

## NFR Verification Steps

### NFR 1.1 - Limit Event Response
1. Send more than 100 requests to any create endpoint within 60 seconds
2. Verify 429 response after limit exceeded

### NFR 1.2 - Maintain Multiple copies of Data
1. Create an entity
2. Request same entity twice
3. Check logs for cache hit on second request

### NFR 2.1 - Exception Detection
1. Send invalid request (e.g., missing required field)
2. Verify 400 response with error details

### NFR 2.2 - Graceful Degradation
1. Simulate database failure (stop database)
2. Verify 503 response instead of 500

### NFR 2.3 - State Resynchronization
1. Create entity
2. Update entity
3. Verify cache is invalidated (next get fetches from DB)

### NFR 2.4 - Transactions
1. Create order with multiple line items
2. Verify all line items are created atomically
3. Check database for consistent state
