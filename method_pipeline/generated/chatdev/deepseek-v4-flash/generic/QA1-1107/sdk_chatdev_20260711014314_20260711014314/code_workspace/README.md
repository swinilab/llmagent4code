# Order Management System (OMS)

Production-grade backend for e-commerce order management with a complete 7-step workflow.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Customer  │  │ Product  │  │  Order   │  │ Payment  │   │
│  │Controller│  │Controller│  │Controller│  │Controller│   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐    │
│  │              Service Layer (Business Logic)        │    │
│  └────┬─────────────┬─────────────┬─────────────┬────┘    │
│       │             │             │             │          │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐    │
│  │         Workflow Layer (Orchestration)             │    │
│  └────┬─────────────┬─────────────┬─────────────┬────┘    │
│       │             │             │             │          │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐    │
│  │              Data Layer (SQLAlchemy ORM)           │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Background Task Processor (asyncio)         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Middleware: Rate Limiter + Request Logger          │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component       | Technology                          |
|----------------|-------------------------------------|
| Web Framework  | FastAPI (async)                     |
| ORM            | SQLAlchemy 2.0 (async)             |
| Validation     | Pydantic v2                         |
| Database       | SQLite (dev) / PostgreSQL (prod)    |
| Task Queue     | Celery + Redis (prod) / asyncio (dev) |
| API Docs       | OpenAPI (auto-generated at /docs)   |

## Project Structure

```
oms/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration via pydantic-settings
│   ├── database.py          # Async engine, session, base model
│   ├── enums.py             # Domain enums (OrderStatus, etc.)
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── customer.py
│   │   ├── order.py
│   │   ├── product.py
│   │   ├── payment.py
│   │   └── invoice.py
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic layer
│   ├── controllers/         # REST API routers
│   ├── workflows/           # Order workflow orchestrator
│   ├── tasks/               # Background task processing
│   └── middleware/          # Rate limiter, request logger
├── alembic/                 # Database migrations
├── Dockerfile               # Production container
├── docker-compose.yml       # Local deployment
└── README.md
```

## API Endpoints

### Customers (`/api/v1/customers`)
- `POST /` - Create customer
- `GET /` - List customers
- `GET /{id}` - Get customer
- `PATCH /{id}` - Update customer
- `DELETE /{id}` - Delete customer

### Products (`/api/v1/products`)
- `POST /` - Create product
- `GET /` - List/search products (`?search=term`)
- `GET /{id}` - Get product
- `PATCH /{id}` - Update product
- `DELETE /{id}` - Delete product

### Orders (`/api/v1/orders`)
- `POST /` - Place order (Step 1)
- `GET /` - List orders (`?status=PAID&customer_id=...`)
- `GET /{id}` - Get order
- `PATCH /{id}` - Update order
- `POST /{id}/review` - Review order (Step 2a)
- `POST /{id}/accept` - Accept order (Step 2b)
- `POST /{id}/ship` - Ship order (Step 6)
- `POST /{id}/close` - Close order (Step 7)
- `DELETE /{id}` - Delete order

### Invoices (`/api/v1/invoices`)
- `POST /` - Create invoice (Step 3)
- `GET /` - List invoices
- `GET /{id}` - Get invoice
- `GET /by-order/{order_id}` - Get invoices by order
- `POST /{id}/issue` - Issue invoice
- `POST /{id}/mark-paid` - Mark invoice paid
- `PATCH /{id}` - Update invoice
- `DELETE /{id}` - Delete invoice

### Payments (`/api/v1/payments`)
- `POST /` - Record payment (Step 4)
- `GET /` - List payments
- `GET /{id}` - Get payment
- `GET /by-order/{order_id}` - Get payments by order
- `POST /{id}/verify` - Verify payment (Step 5)
- `PATCH /{id}` - Update payment
- `DELETE /{id}` - Delete payment

### Health
- `GET /health` - Health check

## Complete 7-Step Workflow

```
1. POST /api/v1/orders/              (Customer places order)
2. POST /api/v1/orders/{id}/accept   (Order Staff accepts)
3. POST /api/v1/invoices/            (Accountant creates invoice)
4. POST /api/v1/payments/            (Customer pays)
5. POST /api/v1/payments/{id}/verify (Accountant verifies)
6. POST /api/v1/orders/{id}/ship     (Order Staff ships)
7. POST /api/v1/orders/{id}/close    (Order Staff closes)
```

## Key Design Decisions

### Immutable Terminal States
Orders in CLOSED or CANCELLED status are fully immutable — no field modifications are allowed. This ensures financial data integrity and prevents accounting discrepancies.

### Duplicate Prevention
- **Invoices:** Only one invoice can be created per order. Attempting to create a second invoice returns a clear error.
- **Payments:** Only one pending payment is allowed per order. Duplicate payment submissions are rejected.

### Status Transition Validation
All order status transitions are validated against a defined state machine. Invalid transitions (e.g., SHIPPED -> PENDING) are rejected with a clear error message.

## Local Deployment Guide

### Prerequisites
- Python 3.12+
- uv (Python package manager)

### Quick Start

```bash
# 1. Clone and enter the project
cd oms

# 2. Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync

# 3. Run the application
uv run uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

### Using Docker

```bash
docker compose up --build
```

### Database Migrations

```bash
# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## NFR Verification

### NFR 1.1 - Response Time
- Run: `httpx` load test against `/api/v1/products?search=test`
- Verify: Response times < 200ms under 100 concurrent requests
- Tool: `uv run python -c "import httpx; ..."` or use `locust`

### NFR 1.2 - Concurrency & Resource Utilization
- Run: `uvicorn` with 4 workers (matches 98GB RAM class)
- Verify: CPU utilization stays below 70% under load
- Tool: `htop` or `docker stats`

### NFR 1.3 - Queue Management
- Run: Flood the background queue with 2000+ tasks
- Verify: Queue rejects tasks at capacity (maxsize=1000) instead of crashing
- Tool: Check logs for "Background queue full" messages

## ADR Summary

| Decision | Context | Alternatives Rejected |
|----------|---------|----------------------|
| FastAPI (async) | NFR 1.1, 1.2 | Flask (sync), Django (heavy) |
| SQLAlchemy 2.0 | NFR 1.2 | Tortoise-ORM (immature), raw SQL (no ORM) |
| asyncio Queue | NFR 1.3 | Celery (overhead for dev), Redis Queue (extra dep) |
| SQLite (dev) | Local deploy | PostgreSQL (heavy for dev), MySQL (complex setup) |
| Pydantic v2 | Validation | Marshmallow (slower), attrs (less features) |
| Workflow Layer | Orchestration | Fat controllers, Saga pattern |
| Immutable Terminal States | Data integrity | Audit log, Soft delete |
| Duplicate Prevention | Financial consistency | DB constraints only, Idempotency keys |
