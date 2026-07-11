# Local Deployment Guide

## Prerequisites

- **Python 3.12+** (check with `python --version`)
- **uv** (Python package manager, install with `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Docker** (optional, for containerized deployment)
- **Redis** (optional, only needed for Celery in production mode)

## Quick Start (No Docker)

### 1. Clone and enter the project

```bash
cd oms
```

### 2. Create virtual environment and install dependencies

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
uv sync
```

### 3. Seed the database with sample data

```bash
uv run python scripts/seed_data.py
```

### 4. Run the application

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access the API

- API: http://localhost:8000
- Interactive docs (Swagger UI): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI spec: http://localhost:8000/openapi.json
- Health check: http://localhost:8000/health

## Docker Deployment

### 1. Build and start all services

```bash
docker compose up --build
```

This starts:
- **oms-api**: FastAPI application on port 8000
- **oms-redis**: Redis for Celery broker on port 6379
- **oms-celery-worker**: Celery worker for background tasks

### 2. Seed data (if needed)

```bash
docker exec -it oms-api python scripts/seed_data.py
```

## Running the Complete 7-Step Workflow

### Using the test script

```bash
# Ensure the server is running first, then:
uv run python scripts/test_workflow.py
```

### Manual workflow via curl

```bash
# 1. Create a customer
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers/ \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","address":"123 Main St","phone":"+1-555-0000","role":"CUSTOMER"}')
CUSTOMER_ID=$(echo $CUSTOMER | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Create a product
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{"description":"Widget","pricing":{"base_price":49.99,"currency":"USD"}}')
PRODUCT_ID=$(echo $PRODUCT | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Place an order (Step 1)
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"line_items\":[{\"product_id\":\"$PRODUCT_ID\",\"product_description\":\"Widget\",\"quantity\":2,\"unit_price\":49.99}]}")
ORDER_ID=$(echo $ORDER | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order: $ORDER_ID"

# 4. Review and accept order (Step 2)
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/review" | python -m json.tool
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/accept" | python -m json.tool

# 5. Create invoice (Step 3) — automatically issues the invoice and updates order to INVOICED
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices/ \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"billing_info\":{\"name\":\"John Doe\"},\"issue_date\":\"$(date +%Y-%m-%d)\",\"due_date\":\"$(date -d '+30 days' +%Y-%m-%d)\"}")
INVOICE_ID=$(echo $INVOICE | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Invoice: $INVOICE_ID (status: ISSUED)"

# 6. Record payment (Step 4)
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments/ \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"amount\":118.95,\"method\":\"CREDIT_CARD\",\"transaction_ref\":\"TXN001\"}")
PAYMENT_ID=$(echo $PAYMENT | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 7. Verify payment (Step 5) — also updates order to PAID and marks invoice as paid
curl -s -X POST "http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify" | python -m json.tool

# 8. Ship order (Step 6)
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/ship" | python -m json.tool

# 9. Close order (Step 7)
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/close" | python -m json.tool
```

## Database Migrations

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Configuration

All configuration is managed via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./oms.db` | Database connection string |
| `DATABASE_ECHO` | `false` | Log SQL queries |
| `DATABASE_POOL_SIZE` | `20` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Max overflow connections |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `4` | Number of uvicorn workers |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window (seconds) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery result backend |
| `BACKGROUND_QUEUE_MAXSIZE` | `1000` | Max background queue size |
| `BACKGROUND_WORKERS` | `4` | Background worker count |

## Production Deployment

For production, update the `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/oms
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW_SECONDS=60
```

Then deploy using Docker Compose or Kubernetes.
