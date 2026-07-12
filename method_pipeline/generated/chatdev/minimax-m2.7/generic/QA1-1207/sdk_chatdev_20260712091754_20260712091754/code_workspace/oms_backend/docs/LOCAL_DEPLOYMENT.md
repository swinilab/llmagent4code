# Local Deployment Guide

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15 client (psql)
- `curl` or `httpie` for API testing

---

## Step 1 — Clone and Configure

```bash
git clone <repo-url>
cd oms_backend
```

Edit `config.yaml` to set your PostgreSQL and Redis host/port. The default assumes Docker Compose services.

---

## Step 2 — Install Python Dependencies

We use `uv` for fast, reproducible installs.

```bash
pip install uv
uv sync
```

Or via pip:
```bash
pip install -e .
```

---

## Step 3 — Start Infrastructure (PostgreSQL + Redis)

```bash
docker compose up -d postgres redis
```

Wait for health checks:
```bash
docker compose ps
# Both postgres and redis should show (healthy)
```

---

## Step 4 — Initialize the Database

```bash
psql -h localhost -U postgres -d oms_db -f db/schema.sql
```

Expected output: CREATE TABLE / CREATE INDEX messages with no errors.

---

## Step 5 — Run the Backend

### Option A — Uvicorn (development)

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8000 --reload --loop uvloop
```

### Option B — Gunicorn (production simulation)

```bash
uv run gunicorn -c infra/gunicorn.conf.py server:app
```

### Option C — Docker Compose (full stack)

```bash
docker compose up --build
```

All services start: postgres, redis, oms-backend, oms-worker.

---

## Step 6 — Verify the API is Running

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/ready
# {"status":"ready"}

# OpenAPI docs
open http://localhost:8000/docs
```

---

## Step 7 — Start the Background Worker (optional)

```bash
uv run python -m infra.worker
```

---

## Step 8 — Run End-to-End Workflow Test

```bash
./scripts/workflow_test.sh
```

Or manually:

```bash
# 1. Create customer
CUST=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com","phone":"+1234"}')
CUST_ID=$(echo $CUST | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Customer ID: $CUST_ID"

# 2. Create product
PROD=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"sku":"WIDGET-01","name":"Widget","description":"A test widget","base_price":"29.99","stock_qty":100}')
PROD_ID=$(echo $PROD | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PROD_ID"

# 3. Place order
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUST_ID\",\"line_items\":[{\"product_id\":\"$PROD_ID\",\"quantity\":2,\"unit_price\":\"29.99\",\"tax_rate\":\"0.0825\"}]}")
ORDER_ID=$(echo $ORDER | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order ID: $ORDER_ID"

# 4. Accept order
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/accept"

# 5. Create invoice
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"issue_date\":\"2025-07-12\",\"due_date\":\"2025-07-19\"}")
echo $INVOICE

# 6. Issue invoice
INV_ID=$(echo $INVOICE | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST "http://localhost:8000/api/v1/invoices/$INV_ID/issue" \
  -H "Content-Type: application/json" \
  -d '{"issue_date":"2025-07-12","due_date":"2025-07-19"}'

# 7. Pay invoice
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"invoice_id\":\"$INV_ID\",\"amount\":\"64.97\",\"method\":\"bank_transfer\"}")
echo $PAYMENT

# 8. Mark invoice paid
curl -s -X POST "http://localhost:8000/api/v1/invoices/$INV_ID/pay"

# 9. Ship order
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/ship" \
  -H "Content-Type: application/json" \
  -d '{"tracking_number":"1Z999AA10123456784"}'

# 10. Close order
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/close"
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `psql: could not connect to server` | Ensure postgres container is running: `docker compose ps` |
| `Connection refused` on port 8000 | Check if app is listening: `docker compose logs oms-backend` |
| `database "oms_db" does not exist` | Run `psql ... -f db/schema.sql` with `-c "CREATE DATABASE oms_db;"` first |
| Worker not processing jobs | Ensure Redis is up: `docker compose ps redis` |
