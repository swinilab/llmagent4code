# OMS Backend — Order Management System

A production-grade, backend-only e-commerce Order Management System built with
FastAPI, SQLAlchemy (async), and SQLite (WAL mode).

Serves the complete workflow: **customer ordering → payment processing →
invoicing → shipping → closure** for three roles (Customer, Order Staff,
Accountant).

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (dependency manager)

### Local Development

```bash
# 1. Install dependencies
uv sync

# 2. (Optional) Configure environment
cp .env.example .env
# Edit .env as needed

# 3. Run the server
uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Verify
curl http://localhost:8000/health
curl http://localhost:8000/api/docs   # Swagger UI
```

### Docker Deployment

```bash
# Build and run
docker compose up --build -d

# Verify
curl http://localhost:8000/health
curl http://localhost:8000/api/docs

# View logs
docker compose logs -f oms

# Stop
docker compose down
```

## API Overview

All endpoints are versioned under `/api/v1/`. Interactive docs available at
`/api/docs` (Swagger) and `/api/redoc` (ReDoc).

| Entity | Base Path | Key Endpoints |
|--------|-----------|---------------|
| Customers | `/api/v1/customers` | CRUD + order history |
| Products | `/api/v1/products` | CRUD + search (`/search?q=...`) |
| Orders | `/api/v1/orders` | Create, list, get, update items, transition status, cancel, delete |
| Payments | `/api/v1/payments` | Create, verify, list, get by order |
| Invoices | `/api/v1/invoices` | Create, list, get, update status, mark overdue |

### Health Endpoints

- `GET /health` — Liveness probe (always 200 if process is alive)
- `GET /health/ready` — Readiness probe (checks DB, circuit breakers, queue)

## Workflow

1. **Customer places order** — `POST /api/v1/orders/` (status: PENDING)
2. **Order Staff accepts** — `POST /api/v1/orders/{id}/transition` (→ ACCEPTED)
3. **Accountant creates invoice** — `POST /api/v1/invoices/` (→ INVOICED)
4. **Customer pays invoice** — `POST /api/v1/payments/` (payment: PENDING)
5. **Accountant verifies payment** — `POST /api/v1/payments/{id}/verify` (→ PAID)
6. **Order Staff ships** — `POST /api/v1/orders/{id}/transition` (→ SHIPPED)
7. **Order Staff closes** — `POST /api/v1/orders/{id}/transition` (→ CLOSED)

## Testing

```bash
uv run pytest tests/ -v --asyncio-mode=auto
```

## Documentation

- [NFR Traceability Matrix](docs/nfr_traceability_matrix.md)
- [Architecture Decision Records](docs/adrs/)
- [Data Architecture](docs/data_architecture.md)
- [Deployment Guide](docs/deployment_guide.md)
- [NFR Verification Steps](docs/verification_steps.md)

## Configuration

All settings are environment-variable driven with the `OMS_` prefix. See
[`.env.example`](.env.example) for the full list.