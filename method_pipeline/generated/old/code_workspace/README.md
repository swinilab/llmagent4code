# Order Management System (OMS)

A production-grade, backend-only e-commerce Order Management System built with Python and FastAPI.

## Overview

This OMS serves three roles:
- **Customer**: Place orders, view order history, make payments
- **Order Staff**: Review orders, accept/reject, ship orders, close completed orders
- **Accountant**: Create invoices, verify payments, manage invoice status

## Order Lifecycle

```
PENDING → REVIEWING → ACCEPTED → INVOICED → PAID → SHIPPED → COMPLETED
                ↓
            REJECTED/CANCELLED
```

1. **Customer places order** → Status: `PENDING`
2. **Order Staff reviews & accepts** → Status: `ACCEPTED`
3. **Accountant creates invoice** → Status: `INVOICED`
4. **Customer pays invoice** → Status: `PAID`
5. **Order Staff ships order** → Status: `SHIPPED`
6. **Order Staff closes order** → Status: `COMPLETED`

## Quick Start

### Prerequisites
- Python 3.11+
- uv (Python package manager)

### Installation

```bash
# Clone the repository
cd code_workspace

# Create virtual environment and install dependencies
uv sync

# Run the server
uv run python server.py
```

### Access the API

- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Customers
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/customers` | Create customer |
| GET | `/api/v1/customers` | List all customers |
| GET | `/api/v1/customers/{id}` | Get customer by ID |
| PUT | `/api/v1/customers/{id}` | Update customer |
| DELETE | `/api/v1/customers/{id}` | Delete customer |

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/products` | Create product |
| GET | `/api/v1/products` | List all products |
| GET | `/api/v1/products/available` | List available products |
| GET | `/api/v1/products/search?q=name` | Search products |
| GET | `/api/v1/products/{id}` | Get product by ID |
| PATCH | `/api/v1/products/{id}/stock` | Update stock |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/orders` | Create order (Customer) |
| GET | `/api/v1/orders` | List all orders |
| GET | `/api/v1/orders/pending` | List pending orders |
| GET | `/api/v1/orders/shipping` | List orders ready to ship |
| POST | `/api/v1/orders/{id}/review?accept=true` | Review order (Staff) |
| POST | `/api/v1/orders/{id}/ship` | Ship order (Staff) |
| POST | `/api/v1/orders/{id}/complete` | Complete order (Staff) |
| POST | `/api/v1/orders/{id}/cancel` | Cancel order |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payments` | Create payment (Customer) |
| GET | `/api/v1/payments` | List pending payments |
| POST | `/api/v1/payments/{id}/verify` | Verify payment (Accountant) |
| POST | `/api/v1/payments/{id}/refund` | Refund payment |

### Invoices
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/invoices` | Create invoice (Accountant) |
| GET | `/api/v1/invoices` | List all invoices |
| GET | `/api/v1/invoices/overdue` | List overdue invoices |
| POST | `/api/v1/invoices/{id}/mark-paid` | Mark as paid |
| POST | `/api/v1/invoices/{id}/cancel` | Cancel invoice |

## Example Workflow

### 1. Create a Customer
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "address": "123 Main St, City, Country"
  }'
```

### 2. Create Products
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "base_price": 999.99,
    "currency": "USD",
    "stock_quantity": 50
  }'
```

### 3. Create an Order (Customer)
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "line_items": [
      {"product_id": 1, "quantity": 1}
    ],
    "shipping_address": "123 Main St, City, Country"
  }'
```

### 4. Review Order (Order Staff)
```bash
curl -X POST "http://localhost:8000/api/v1/orders/1/review?accept=true"
```

### 5. Create Invoice (Accountant)
```bash
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "billing_name": "John Doe",
    "billing_address": "123 Main St, City, Country",
    "tax_rate": 0.1,
    "due_date": "2024-12-31T23:59:59"
  }'
```

### 6. Make Payment (Customer)
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "amount": 1099.99,
    "method": "credit_card",
    "transaction_id": "TXN123456"
  }'
```

### 7. Verify Payment (Accountant)
```bash
curl -X POST http://localhost:8000/api/v1/payments/1/verify
```

### 8. Ship Order (Order Staff)
```bash
curl -X POST http://localhost:8000/api/v1/orders/1/ship
```

### 9. Complete Order (Order Staff)
```bash
curl -X POST http://localhost:8000/api/v1/orders/1/complete
```

## Architecture

### Project Structure
```
oms/
├── __init__.py
├── app.py                 # FastAPI application
├── config/
│   └── database.py        # Database configuration
├── controllers/           # API endpoints
│   ├── customer_controller.py
│   ├── product_controller.py
│   ├── order_controller.py
│   ├── payment_controller.py
│   └── invoice_controller.py
├── models/
│   ├── entities.py        # SQLAlchemy ORM models
│   └── schemas.py         # Pydantic schemas
├── repositories/          # Data access layer
│   ├── base.py
│   ├── customer_repository.py
│   ├── product_repository.py
│   ├── order_repository.py
│   ├── payment_repository.py
│   └── invoice_repository.py
├── services/              # Business logic
│   ├── customer_service.py
│   ├── product_service.py
│   ├── order_service.py
│   ├── payment_service.py
│   └── invoice_service.py
├── docs/
│   ├── ADR.md             # Architectural Decision Records
│   └── NFR_MATRIX.md      # NFR Traceability Matrix
└── infrastructure/
    ├── Dockerfile
    ├── docker-compose.yml
    └── kubernetes.yaml
```

### Design Patterns
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation
- **Dependency Injection**: FastAPI Depends for service injection
- **Async/Await**: Non-blocking I/O throughout

## NFR Compliance

| NFR | Implementation |
|-----|----------------|
| **1.1 Response Time** | Async I/O, connection pooling, database indexes |
| **1.2 Concurrency** | Uvicorn workers, async sessions, efficient resource usage |
| **1.3 Queue Management** | Error handling, transaction rollback, graceful degradation |

See `oms/docs/NFR_MATRIX.md` for detailed traceability.

## Deployment

### Local Development
```bash
uv run python server.py
```

### Docker
```bash
cd oms/infrastructure
docker-compose up
```

### Kubernetes
```bash
kubectl apply -f oms/infrastructure/kubernetes.yaml
```

## Testing

Run the application and test via:
- Swagger UI: http://localhost:8000/docs
- curl commands (see examples above)
- Postman/Insomnia with OpenAPI spec import

## License

MIT License - ChatDev
