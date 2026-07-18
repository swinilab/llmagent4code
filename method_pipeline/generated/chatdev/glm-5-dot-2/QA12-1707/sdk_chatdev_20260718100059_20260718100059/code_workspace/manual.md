# OMS Backend — User Manual

**Order Management System (OMS)** is a production-grade, backend-only
e-commerce service built with FastAPI, async SQLAlchemy, and SQLite (WAL
mode). It exposes a versioned REST API that drives the complete order
lifecycle — *customer ordering → payment processing → invoicing → shipping →
closure* — for three roles: **Customer**, **Order Staff**, and **Accountant**.

This manual explains the main functions of the software, how to install the
environment dependencies, and how to run and use the system end-to-end.

---

## Table of Contents

1. [Main Functions](#1-main-functions)
2. [System Requirements](#2-system-requirements)
3. [Installing Environment Dependencies](#3-installing-environment-dependencies)
4. [Running the Server](#4-running-the-server)
5. [Configuration](#5-configuration)
6. [API Reference](#6-api-reference)
7. [End-to-End Workflow Walkthrough](#7-end-to-end-workflow-walkthrough)
8. [Health, Observability & NFR Features](#8-health-observability--nfr-features)
9. [Testing](#9-testing)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Main Functions

The OMS backend is organized around five domain entities, each exposing a
complete three-layer stack (Service → Controller → Routing):

| Entity | Purpose | Roles involved |
|--------|---------|----------------|
| **Customer** | Manage customer profiles, banking details, and order history. | Customer |
| **Product** | Manage the product catalog (CRUD) plus keyword/price search. | Customer (search) |
| **Order** | Create orders with line items, transition status across the full lifecycle, cancel, and delete. | Customer, Order Staff |
| **Payment** | Create payments against an order's invoice and verify/reject them. | Customer, Accountant |
| **Invoice** | Create invoices for accepted orders, list/get, update status, mark overdue. | Accountant |

### Order Lifecycle

The order status enum drives the entire workflow:

```
PENDING → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED
                       ↘ CANCELLED (terminal, reachable from PENDING/ACCEPTED/INVOICED)
```

Allowed transitions are enforced in the service layer via an
`ORDER_TRANSITIONS` map (see `oms/enums.py`).

### Cross-Cutting Concerns (visible in code)

- **Request timing** — every response carries an `X-Response-Time-ms` header
  (`oms/core/middleware.py`, `RequestTimingMiddleware`).
- **Graceful degradation** — under high CPU/memory pressure, non-essential
  endpoints (currently `/api/v1/products/search`) return `503` while core
  checkout endpoints stay available (`GracefulDegradationMiddleware`, NFR 2.1).
- **Health checks** — liveness (`/health`) and readiness (`/health/ready`)
  probes (`HealthCheckMiddleware`, NFR 2.2).
- **Bounded queue** — background `QueueManager` with configurable size and
  worker count; overflow is rejected rather than crashing (NFR 1.3).
- **Circuit breaker** — protects downstream calls from cascading failure
  (`oms/core/resilience.py`, NFR 2.2).
- **State recovery** — on startup, `RecoveryService` scans for orders left in
  non-terminal states from a previous crash and resumes them (NFR 2.3).
- **Atomic multi-entity transactions** — order/invoice/payment state changes
  are committed in a single DB transaction (NFR 2.3, ADR-005).

---

## 2. System Requirements

- **Python 3.12** or later
- **[uv](https://docs.astral.sh/uv/)** dependency manager
  (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Docker** + **Docker Compose** (only if using the containerized deployment)
- ~200 MB free disk for dependencies and the SQLite database

---

## 3. Installing Environment Dependencies

### Option A — Local (uv)

From the project root (the `code_workspace` directory):

```bash
# 1. Install all dependencies into a managed virtual environment
uv sync
```

`uv sync` reads `pyproject.toml` / `uv.lock`, creates a `.venv/`, and installs
the full dependency set:

- `fastapi`, `uvicorn[standard]` — web framework & ASGI server
- `sqlalchemy[asyncio]`, `aiosqlite` — async ORM + SQLite driver
- `pydantic`, `pydantic-settings` — validation & configuration
- `psutil` — resource monitoring for graceful degradation
- `httpx`, `pytest`, `pytest-asyncio` — testing

### Option B — Docker

```bash
docker compose up --build -d
```

The `Dockerfile` installs `uv`, runs `uv sync --frozen --no-dev`, copies the
`oms/` source, and starts uvicorn. The SQLite database is persisted in the
`oms-data` named volume (mounted at `/app/data`) so it survives container
recreation.

### Option C — Make targets

The provided `Makefile` wraps the common commands:

```bash
make install      # uv sync
make dev          # server with auto-reload
make run          # server (production mode)
make test         # full pytest suite
make test-smoke   # quick import smoke test
make docker-up    # docker compose up --build -d
make docker-down  # docker compose down
make docker-logs  # docker compose logs -f oms
make clean        # remove oms.db* and test_oms.db*
```

---

## 4. Running the Server

### Local (development, auto-reload)

```bash
uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000 --reload
```

or

```bash
make dev
```

### Local (production-style)

```bash
uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000
```

or

```bash
make run
```

> For multi-worker write concurrency, switch `OMS_DATABASE_URL` to a shared
> database such as PostgreSQL and run with `--workers N`. SQLite is single-writer;
> the default config uses one worker.

### Docker

```bash
docker compose up --build -d
docker compose logs -f oms      # follow logs
docker compose down             # stop
```

### Verify it is running

```bash
# Liveness probe
curl http://localhost:8000/health
# {"status":"alive","service":"OMS Backend"}

# Readiness probe (DB, circuit breakers, queue)
curl http://localhost:8000/health/ready

# Interactive API docs
open http://localhost:8000/api/docs    # Swagger UI
open http://localhost:8000/api/redoc   # ReDoc
```

On startup the server logs:

1. `Database initialised (WAL mode enabled)`
2. `Recovery summary: ...` (NFR 2.3 — resumes pending orders from a prior crash)
3. `Queue workers started`
4. `OMS Backend ready — serving on 0.0.0.0:8000`

---

## 5. Configuration

All settings are environment-variable driven with the `OMS_` prefix (loaded via
`pydantic-settings` from a `.env` file if present). Defaults are production-safe.

| Variable | Default | Description |
|----------|---------|-------------|
| `OMS_APP_NAME` | `OMS Backend` | Application title |
| `OMS_APP_VERSION` | `1.0.0` | Application version |
| `OMS_DEBUG` | `false` | Debug flag |
| `OMS_HOST` | `0.0.0.0` | Bind host |
| `OMS_PORT` | `8000` | Bind port |
| `OMS_DATABASE_URL` | `sqlite+aiosqlite:///./oms.db` | Async DB URL |
| `OMS_DB_ECHO` | `false` | Echo SQL statements |
| `OMS_DB_POOL_SIZE` | `10` | Connection pool size |
| `OMS_DB_MAX_OVERFLOW` | `20` | Pool overflow |
| `OMS_QUEUE_MAX_SIZE` | `500` | Bounded queue capacity (NFR 1.3) |
| `OMS_QUEUE_WORKER_COUNT` | `4` | Background queue workers |
| `OMS_QUEUE_TIMEOUT_SECONDS` | `5.0` | Queue enqueue timeout |
| `OMS_CB_FAILURE_THRESHOLD` | `5` | Circuit-breaker failure threshold |
| `OMS_CB_RECOVERY_TIMEOUT` | `30.0` | Circuit-breaker recovery seconds |
| `OMS_CB_HALF_OPEN_MAX_CALLS` | `3` | Half-open probe calls |
| `OMS_DEGRADATION_CHECK_INTERVAL` | `10.0` | Seconds between resource checks |
| `OMS_DEFAULT_TAX_RATE` | `0.20` | Default tax rate (20 %) |
| `OMS_DEFAULT_CURRENCY` | `USD` | Default currency code |
| `OMS_DEGRADATION_MEMORY_THRESHOLD` | `85.0` | Memory % triggering degradation |
| `OMS_DEGRADATION_CHECK_INTERVAL` | *(see config)* | Seconds between resource checks |

To customize, create a `.env` file (the project ships a `.env.example`):

```bash
cp .env.example .env
# edit .env
```

---

## 6. API Reference

All endpoints are versioned under `/api/v1/`. OpenAPI spec is served at
`/api/openapi.json`, with Swagger at `/api/docs` and ReDoc at `/api/redoc`.

### Customers — `/api/v1/customers`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/` | Create a customer |
| `GET` | `/` | List customers (paginated: `?page=&page_size=`) |
| `GET` | `/{customer_id}` | Get customer **with order history** |
| `PUT` | `/{customer_id}` | Update customer |
| `DELETE` | `/{customer_id}` | Delete customer |

**Create customer body:**
```json
{
  "name": "Alice",
  "address": "123 Market St, San Francisco",
  "phone": "+14155551234",
  "banking_details": {"iban": "US12...", "bank_name": "Acme Bank"},
  "role": "customer"
}
```
`role` is one of `customer`, `order_staff`, `accountant`.

### Products — `/api/v1/products`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/` | Create product |
| `GET` | `/` | List products (paginated) |
| `GET` | `/search` | Search by `q`, `min_price`, `max_price`, `currency` (core journey, NFR 1.1) |
| `GET` | `/{product_id}` | Get product |
| `PUT` | `/{product_id}` | Update product |
| `DELETE` | `/{product_id}` | Delete product |

**Create product body:**
```json
{"description": "Mechanical Keyboard", "base_price": 79.99, "currency": "USD"}
```

### Orders — `/api/v1/orders`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/` | Create order with line items (step 1) |
| `GET` | `/` | List orders (`?status=&page=&page_size=`) |
| `GET` | `/customer/{customer_id}` | List a customer's orders |
| `GET` | `/{order_id}` | Get order with line items, invoice, payments |
| `PUT` | `/{order_id}/items` | Replace line items (only when `PENDING`) |
| `POST` | `/{order_id}/transition` | Transition status (steps 2, 6, 7) |
| `POST` | `/{order_id}/cancel` | Cancel order (from `PENDING`/`ACCEPTED`/`INVOICED`) |
| `DELETE` | `/{order_id}` | Delete order |

**Create order body:**
```json
{
  "customer_id": "<customer uuid>",
  "items": [{"product_id": "<product uuid>", "quantity": 2}]
}
```
Duplicate `product_id`s within one order are rejected by schema validation.

**Transition body:**
```json
{"status": "accepted", "reason": "stock confirmed"}
```

### Payments — `/api/v1/payments`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/` | Create payment against an order's invoice (step 4) |
| `GET` | `/` | List payments (paginated) |
| `GET` | `/{payment_id}` | Get payment |
| `POST` | `/{payment_id}/verify` | Verify or reject payment (step 5) |
| `GET` | `/order/{order_id}` | List payments for an order |

**Create payment body:**
```json
{"order_id": "<order uuid>", "amount": 159.98, "method": "credit_card"}
```
`method` is one of `credit_card`, `bank_transfer`, `paypal`.

**Verify body:**
```json
{"verified": true}
```
`true` → payment `verified` + order → `PAID`; `false` → payment `failed`.

### Invoices — `/api/v1/invoices`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/` | Create invoice for an accepted order (step 3) |
| `GET` | `/` | List invoices (paginated) |
| `GET` | `/{invoice_id}` | Get invoice |
| `GET` | `/order/{order_id}` | Get invoice for an order |
| `PUT` | `/{invoice_id}/status` | Update invoice status |
| `POST` | `/overdue` | Mark past-due issued invoices as `OVERDUE` |

**Create invoice body:**
```json
{
  "order_id": "<order uuid>",
  "billing_info": {"company": "Acme Inc.", "vat": "US123"},
  "issue_date": null,
  "due_date": null
}
```
`issue_date` defaults to today; `due_date` defaults to +30 days. Creating an
invoice transitions the order to `INVOICED`.

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe (always 200 if process alive) |
| `GET` | `/health/ready` | Readiness probe (DB, circuit breakers, queue) |

---

## 7. End-to-End Workflow Walkthrough

This is the canonical 7-step user workflow. Run the server first (see
[Section 4](#4-running-the-server)), then follow each step. Replace
`<...>` placeholders with the IDs returned by previous calls.

### Step 1 — Customer places an order

First, create the customer and a product:

```bash
# Create a customer
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","address":"123 Market St","phone":"+14155551234","banking_details":{},"role":"customer"}')
CUSTOMER_ID=$(echo $CUSTOMER | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Customer: $CUSTOMER_ID"

# Create a product
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{"description":"Mechanical Keyboard","base_price":79.99,"currency":"USD"}')
PRODUCT_ID=$(echo $PRODUCT | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Product: $PRODUCT_ID"

# Place the order (status: PENDING)
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":2}]}")
ORDER_ID=$(echo $ORDER | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Order: $ORDER_ID  status: $(echo $ORDER | python -c "import sys,json;print(json.load(sys.stdin)['status'])")"
```

### Step 2 — Order Staff reviews & accepts

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/transition \
  -H "Content-Type: application/json" \
  -d '{"status":"accepted","reason":"stock confirmed"}' | python -m json.tool
```
Order status becomes `accepted` and `accepted_at` is set.

### Step 3 — Accountant creates the invoice

```bash
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices/ \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"billing_info\":{\"company\":\"Acme Inc.\"}}")
INVOICE_ID=$(echo $INVOICE | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Invoice: $INVOICE_ID"
```
The order automatically transitions to `invoiced`.

### Step 4 — Customer pays the invoice

```bash
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments/ \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"amount\":159.98,\"method\":\"credit_card\"}")
PAYMENT_ID=$(echo $PAYMENT | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Payment: $PAYMENT_ID  status: $(echo $PAYMENT | python -c "import sys,json;print(json.load(sys.stdin)['status'])")"
```
Payment is created with status `pending`.

### Step 5 — Accountant verifies the payment

```bash
curl -s -X POST http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify \
  -H "Content-Type: application/json" \
  -d '{"verified":true}' | python -m json.tool
```
Payment becomes `verified`; the order transitions to `paid`.

### Step 6 — Order Staff ships the paid order

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/transition \
  -H "Content-Type: application/json" \
  -d '{"status":"shipped"}' | python -m json.tool
```
Order becomes `shipped`; `shipped_at` is set.

### Step 7 — Order Staff closes the completed order

```bash
curl -s -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/transition \
  -H "Content-Type: application/json" \
  -d '{"status":"closed"}' | python -m json.tool
```
Order becomes `closed`; `closed_at` is set. The lifecycle is complete.

### Inspecting the result

```bash
# Full order with line items, invoice, and payments
curl -s http://localhost:8000/api/v1/orders/$ORDER_ID | python -m json.tool

# Customer with their full order history
curl -s http://localhost:8000/api/v1/customers/$CUSTOMER_ID | python -m json.tool
```

### Cancelling an order

```bash
curl -s -X POST "http://localhost:8000/api/v1/orders/$ORDER_ID/cancel?reason=changed+mind" | python -m json.tool
```
Only allowed from `pending`, `accepted`, or `invoiced`.

---

## 8. Health, Observability & NFR Features

The backend implements all six non-functional requirements visibly in code.
Here is how to observe each one against a running instance.

### NFR 1.1 — Response Time

```bash
# X-Response-Time-ms header on every response
curl -s -o /dev/null -D - "http://localhost:8000/api/v1/products/search?q=keyboard"
```
Look for `X-Response-Time-ms: <value>` (well under 500 ms). Orders eagerly
load line items/invoice/payments via `selectin` to avoid N+1 queries.

### NFR 1.2 — Concurrency & Resource Utilization

```bash
# Readiness confirms async DB pool is active
curl -s http://localhost:8000/health/ready | python -m json.tool

# Fire 50 concurrent requests
for i in $(seq 1 50); do
  curl -s -o /dev/null -w "%{http_code} %{time_total}\n" \
    "http://localhost:8000/api/v1/products/search?q=keyboard" &
done
wait
```
All should return `200` with low latency — the async event loop handles them
concurrently without serial blocking.

### NFR 1.3 — Queue Management

```bash
curl -s http://localhost:8000/health/ready | python -c "
import sys, json
print(json.dumps(json.load(sys.stdin)['checks']['queue'], indent=2))"
```
Expect `running: true`, `max_size` = `OMS_QUEUE_MAX_SIZE` (default 500),
`worker_count` = `OMS_QUEUE_WORKER_COUNT` (default 4). On graceful shutdown
(`kill -TERM`), logs show `QueueManager stopped (processed=N, failed=M)` —
in-flight tasks drain before exit.

### NFR 2.1 — Graceful Degradation

Under high CPU/memory pressure (thresholds `OMS_DEGRADATION_CPU_THRESHOLD`
and `OMS_DEGRADATION_MEMORY_THRESHOLD`, default 85%), non-essential endpoints
return `503` while core checkout endpoints remain available.

```bash
# Normal: product search returns 200
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/products/search?q=keyboard"
# Expected: 200

# Simulate contention (e.g. stress CPU), then re-check:
#   product search -> 503 (degraded)
#   POST /api/v1/orders -> still 201 (core journey preserved)
```
Server logs print `Graceful degradation ACTIVE (cpu=..%, mem=..%)` when it
engages and `Graceful degradation cleared` when resources recover.

### NFR 2.2 — Fault Detection and Recovery

- Readiness probe reports circuit-breaker and DB state:
  ```bash
  curl -s http://localhost:8000/health/ready | python -m json.tool
  ```
- The circuit breaker (`oms/core/resilience.py`) opens after
  `OMS_CB_FAILURE_THRESHOLD` failures, half-opens after
  `OMS_CB_RECOVERY_TIMEOUT`, and auto-recovers.

### NFR 2.3 — State Preservation

On every startup, `RecoveryService` scans for orders left in non-terminal
states from a prior crash and resumes them. To observe:

```bash
# 1. Start the server, create an order (leave it PENDING), then kill the process:
kill -9 $(pgrep -f uvicorn)

# 2. Restart:
uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000

# 3. Check startup logs for:
#    Recovery summary: {...}
```
The SQLite WAL file (`oms.db-wal`) ensures committed transactions survive
abrupt process termination with minimal data loss.

---

## 9. Testing

### Full automated test suite

```bash
uv run pytest tests/ -v --asyncio-mode=auto
```
or

```bash
make test
```

The suite (`tests/test_workflow.py`) exercises the complete 7-step workflow
end-to-end against an in-memory/test SQLite database, including status
transitions, invoice creation, payment verification, and cancellation paths.

### Smoke test (import check)

```bash
uv run python test_smoke.py
```
or

```bash
make test-smoke
```
Confirms the app imports, creates, and lists its routes.

### Manual exploration

Open the interactive docs in a browser:

```
http://localhost:8000/api/docs    # Swagger UI — try every endpoint live
http://localhost:8000/api/redoc   # ReDoc — browsable reference
```

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `uv: command not found` | uv not installed | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `database is locked` | Multiple writer workers on SQLite | Use a single worker, or switch `OMS_DATABASE_URL` to PostgreSQL |
| `503` on `/api/v1/products/search` | Graceful degradation active (high CPU/mem) | Wait for resources to recover, or raise `OMS_DEGRADATION_*_THRESHOLD` |
| Order transition returns `409` / `400` | Invalid transition for current status | Check the `ORDER_TRANSITIONS` map in `oms/enums.py` |
| `404` on `/api/docs` | Server not started, or wrong port | Confirm `curl http://localhost:8000/health` returns `alive` |
| Stale data after schema change | Old SQLite file | `make clean` (removes `oms.db*`), then restart |
| Payments/invoice not linked to order | Wrong `order_id` | Use the `id` returned by `POST /api/v1/orders/` |
| Docker container unhealthy | Healthcheck failing | `docker compose logs oms` and check startup errors |

### Resetting the database

```bash
make clean
# or manually:
rm -f oms.db oms.db-wal oms.db-shm test_oms.db test_oms.db-wal test_oms.db-shm
```
The database is recreated automatically on next startup with WAL mode enabled.

---

## Further Reading

The `docs/` directory contains the full architectural documentation:

- `docs/nfr_traceability_matrix.md` — NFR → mechanism → component → verification
- `docs/adrs/` — Architectural Decision Records (SQLite WAL, circuit breaker,
  bounded queue, graceful degradation, atomic transactions)
- `docs/data_architecture.md` — schema narrative and complete table definitions
- `docs/deployment_guide.md` — detailed local and Docker deployment
- `docs/verification_steps.md` — concrete commands to observe each NFR

---

*OMS Backend — ChatDev. Changing the digital world through programming.*