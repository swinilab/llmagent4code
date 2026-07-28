# manual.md

---

## Table of Contents
1. [Project Overview](#project-overview)  
2. [Prerequisites](#prerequisites)  
3. [Environment Setup](#environment-setup)  
4. [Running the Application](#running-the-application)  
5. [API Overview](#api-overview)  
   - 5.1 [Versioning & Base URL](#versioning--base-url)  
   - 5.2 [Authentication & Authorization](#authentication--authorization)  
   - 5.3 [Endpoints by Role](#endpoints-by-role)  
6. [Data Model & Validation Rules](#data-model--validation-rules)  
7. [Testing the Service](#testing-the-service)  
8. [Observability & NFR Verification](#observability--nfr-verification)  
9. [Troubleshooting & Common Issues](#troubleshooting--common-issues)  
10. [Appendix](#appendix)  

---

## 1. Project Overview
The **Order Management System (OMS)** is a production‑grade, backend‑only service that implements the complete e‑commerce order lifecycle:

1. **Customer** places an order.  
2. **Order Staff** reviews and accepts the order.  
3. **Accountant** creates an invoice.  
4. **Customer** pays the invoice.  
5. **Accountant** verifies the payment.  
6. **Order Staff** ships the order.  
7. **Order Staff** closes the order.

All operations are exposed via a **RESTful JSON API** built with **FastAPI** and run on **Uvicorn**. The system is deliberately stateless at the API layer, persisting state in an embedded **SQLite** database with write‑ahead logging (WAL) to meet the required non‑functional guarantees.

---

## 2. Prerequisites
| Item | Minimum Version | Why Needed |
|------|------------------|------------|
| **Python** | 3.11 | Required for `uv`‑based environment and type‑hinted code. |
| **uv** (Python package manager) | latest | Fast, deterministic dependency resolution. |
| **Docker** (optional) | 24.x | For containerised deployment (recommended for production‑like testing). |
| **git** | any | To clone the repository. |
| **curl / HTTPie / Postman** | any | To invoke the API endpoints. |
| **jq** (optional) | any | Pretty‑print JSON responses in the terminal. |

> **Note:** The project does **not** require any external services (e.g., Redis, RabbitMQ). All required components are bundled.

---

## 3. Environment Setup
The repository ships with a **UV‑managed virtual environment**. Follow the steps below:

```bash
# 1️⃣ Clone the repo
git clone https://github.com/your-org/oms-backend.git
cd oms-backend

# 2️⃣ Initialise the Python environment (creates .venv)
uv venv .venv --python 3.11

# 3️⃣ Activate the environment
source .venv/bin/activate   # Bash/Zsh
# or
.venv\Scripts\activate     # PowerShell (Windows)

# 4️⃣ Install dependencies (fastapi, uvicorn, pydantic, sqlalchemy, tenacity, etc.)
uv pip install -r requirements.txt

# 5️⃣ Apply database migrations (creates SQLite DB with WAL mode)
python -m app.db.migrations  # idempotent – safe to run multiple times
```
All commands above are **cross‑platform**; the `uv` tool automatically resolves the correct interpreter.

---

## 4. Running the Application
A single command starts the entire service (API + background workers). The command is stored in `start_command.txt` for convenience.

```bash
# Option A – Use the helper file (recommended)
cat start_command.txt | bash   # Unix/macOS
type start_command.txt | powershell -Command -  # Windows

# Option B – Run manually
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### What the command does
| Component | Description |
|-----------|-------------|
| **Uvicorn** | ASGI server with 4 worker processes (concurrency & resource utilization). |
| **FastAPI** | Auto‑generates OpenAPI docs at `http://localhost:8000/docs`. |
| **Background Workers** (started by the same process) | Consume tasks from an internal `asyncio.Queue` for payment processing, invoicing, and shipping. |
| **SQLite (WAL mode)** | Guarantees durability and state preservation after crashes. |

The service will be reachable at **`http://localhost:8000`**.

---

## 5. API Overview

### 5.1 Versioning & Base URL
All endpoints are prefixed with **`/api/v1`**. Example:

```
GET http://localhost:8000/api/v1/products
```

### 5.2 Authentication & Authorization
*The current prototype does **not** implement authentication* (as per the specification). Role‑based access is enforced by a simple query‑parameter `role` (e.g., `?role=CUSTOMER`). In production you would replace this with proper JWT/OAuth2.

### 5.3 Endpoints by Role
| Role | Endpoint | Method | Description | Request Body | Response |
|------|----------|--------|-------------|--------------|----------|
| **Customer** | `/orders` | `POST` | Place a new order | `OrderCreateDTO` | `OrderResponseDTO` |
| | `/orders/{order_id}/pay` | `POST` | Pay an invoice (after it exists) | `PaymentCreateDTO` | `PaymentResponseDTO` |
| **Order Staff** | `/orders/{order_id}/accept` | `POST` | Accept a placed order | – | `OrderResponseDTO` |
| | `/orders/{order_id}/ship` | `POST` | Mark order as shipped (requires payment verified) | – | `OrderResponseDTO` |
| | `/orders/{order_id}/close` | `POST` | Close a shipped order | – | `OrderResponseDTO` |
| **Accountant** | `/orders/{order_id}/invoice` | `POST` | Issue an invoice for an accepted order | `InvoiceCreateDTO` | `InvoiceResponseDTO` |
| | `/payments/{payment_id}/verify` | `POST` | Verify a pending payment | – | `PaymentResponseDTO` |
| **Common** | `/products` | `GET` | Search / list products (read‑only) | Query params: `search`, `page`, `size` | Paginated `ProductDTO` list |
| | `/healthz` | `GET` | Liveness probe (always 200) | – | `{ "status": "alive" }` |
| | `/readyz` | `GET` | Readiness probe (checks DB, queue) | – | `{ "status": "ready" }` |

All request/response payloads strictly follow the **Field Constraint Table** (see Section 6). Validation errors are returned as **HTTP 422** with a detailed Pydantic error list.

---

## 6. Data Model & Validation Rules
The service uses **Pydantic v2** models for input validation and **SQLAlchemy** for persistence. Validation mirrors the **Field Constraint Table** word‑for‑word:

| Entity | Key Validation Highlights |
|--------|---------------------------|
| **Customer** | `id` auto‑generated UUID v4, `name` matches `^[\p{L} .'-]+$` (2‑100 chars), `phone` matches E.164 regex, `bankingDetails.accountNumber` numeric 6‑20 digits, `role` must be one of `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT`. |
| **Product** | `price.amount` must be a decimal with exactly two digits after the point (`0.01`‑`999999.99`), `price.currency` limited to `USD`, `VND`, `EUR`. |
| **Order** | `lineItems` array 1‑100 items, each `quantity` 1‑1000, `unitPriceSnapshot` computed from current product price (immutable), `totalAmount` computed server‑side, `status` follows the defined state machine, `invoiceRef` may be null. |
| **Invoice** | `issueDate` & `dueDate` validated against `dd/MM/yyyy` regex **and** calendar correctness, `dueDate` ≥ `issueDate` (default +7 days). |
| **Payment** | `amount` must equal the related invoice total, `status` defaults to `PENDING`, `method` limited to `CREDIT_CARD`, `BANK_TRANSFER`, `E_WALLET`. |

All validation errors are surfaced in the API response, enabling client‑side correction.

---

## 7. Testing the Service
### 7.1 Unit & Integration Tests
Run the test suite (pytest) inside the virtual environment:

```bash
uv run pytest -q
```

Tests cover:
- Field‑level validation (regex, range, enum).
- State‑machine transitions for `Order`, `Invoice`, `Payment`.
- Queue back‑pressure handling and graceful degradation.
- Fault‑injection scenarios (DB disconnect, worker crash).

### 7.2 Load / Stress Testing (NFR 1.1, 1.2, 1.3)
A sample **k6** script is provided under `tests/load/k6_test.js`. Execute:

```bash
k6 run tests/load/k6_test.js
```

Key metrics to verify:
- **p95 latency** for `/checkout` < 200 ms under 100 concurrent users.
- **Throughput** scales linearly up to the number of Uvicorn workers (default 4).
- **Queue depth** never exceeds the configured bound (`MAX_QUEUE_SIZE = 5000`).  

### 7.3 Fault‑Recovery Tests (NFR 2.1‑2.3)
Use the helper script `scripts/fault_inject.sh` to:
- Kill a background worker while the queue is saturated (verifies graceful degradation).
- Corrupt the SQLite WAL file and restart (verifies state restoration).

---

## 8. Observability & NFR Verification
| NFR | Mechanism (code location) | How to Observe |
|-----|--------------------------|----------------|
| **1.1 Response Time** | `app/cache/response_cache.py` (caches product list) & FastAPI’s built‑in `TimingMiddleware` | Check `/metrics` (Prometheus) for `http_request_duration_seconds` p95 < 200 ms. |
| **1.2 Concurrency** | `uvicorn` workers (`app/main.py::create_app`) & `asyncio` tasks in services | `ab -n 1000 -c 100 http://localhost:8000/api/v1/products` – throughput should increase proportionally to workers. |
| **1.3 Queue Management** | `app/queue/queue_manager.py` (bounded `asyncio.Queue`) | `/health/queue` returns current depth; spikes of 1000 requests still return `202 Accepted`. |
| **2.1 Graceful Degradation** | `app/degradation/degradation_manager.py` (feature‑flag checks) | Simulate worker crash; non‑essential endpoints (`/products/search`) return `503` while `/orders/{id}/pay` stays `2xx`. |
| **2.2 Fault Detection & Recovery** | `app/health/liveness.py`, `app/db/connection_pool.py` (retry with `tenacity`) | Stop the SQLite file temporarily; health endpoint `/readyz` flips to `unready` then back to `ready` after auto‑reconnect. |
| **2.3 State Preservation** | `app/persistence/wal.py` (write‑ahead log) | Kill the process mid‑order processing; on restart, pending orders are replayed from WAL and no order is lost. |

All metrics are exposed via **Prometheus** format at `/metrics`. Grafana dashboards are included in `infra/grafana/` for visual verification.

---

## 9. Troubleshooting & Common Issues
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `422 Unprocessable Entity` on order creation | Input fails regex/length constraints (e.g., whitespace‑only name) | Ensure request body conforms to the Field Constraint Table. |
| `404 Not Found` for `/orders/{id}` after creation | Database transaction not committed (rare) | Verify that the SQLite file is writable and that the `order_service` completed without exception. |
| High latency > 500 ms under load | Worker count too low or CPU throttling (Docker) | Increase `--workers` flag in the start command or allocate more CPU cores. |
| Queue depth stuck at max, new requests get `429` | Background worker crashed | Check logs (`logs/worker.log`) and restart the service; the health endpoint `/readyz` will indicate “unready”. |
| Database lock errors (`SQLITE_BUSY`) | SQLite WAL not enabled | Ensure `app/db/migrations.py` runs; it sets `PRAGMA journal_mode=WAL`. |
| Missing OpenAPI docs | FastAPI not started (wrong import) | Run the command from the project root; ensure `app.main:app` is the entry point. |

Log files are written to `logs/` with rotating file handlers (size 10 MiB, keep 5). Use `tail -f logs/app.log` to watch live activity.

---

## 10. Appendix

### 10.1 Directory Layout (high‑level)
```
/ (project root)
│
├─ app/
│   ├─ main.py                 # FastAPI app & worker startup
│   ├─ api/
│   │   ├─ v1/
│   │   │   ├─ routers/
│   │   │   │   ├─ product.py
│   │   │   │   ├─ order.py
│   │   │   │   ├─ invoice.py
│   │   │   │   └─ payment.py
│   │   │   └─ dtos/
│   │   │       ├─ product_dto.py
│   │   │       ├─ order_dto.py
│   │   │       ├─ invoice_dto.py
│   │   │       └─ payment_dto.py
│   ├─ services/
│   │   ├─ order_service.py
│   │   ├─ payment_service.py
│   │   ├─ invoice_service.py
│   │   └─ product_service.py
│   ├─ repositories/
│   │   ├─ order_repo.py
│   │   └─ ... (SQLAlchemy CRUD)
│   ├─ queue/
│   │   └─ queue_manager.py
│   ├─ degradation/
│   │   └─ degradation_manager.py
│   ├─ health/
│   │   ├─ liveness.py
│   │   └─ readiness.py
│   ├─ persistence/
│   │   └─ wal.py
│   ├─ db/
│   │   ├─ models.py
│   │   ├─ connection_pool.py
│   │   └─ migrations.py
│   └─ cache/
│       └─ response_cache.py
│
├─ infra/
│   ├─ docker-compose.yml
│   ├─ grafana/
│   └─ prometheus/
│
├─ tests/
│   ├─ unit/
│   ├─ integration/
│   └─ load/
│
├─ requirements.txt
├─ start_command.txt           # `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
├─ nfr-trace.json              # machine‑readable NFR traceability matrix
└─ manual.md                   # (this file)
```

### 10.2 Sample `curl` Calls
```bash
# 1️⃣ List products (available to every role)
curl -s http://localhost:8000/api/v1/products | jq .

# 2️⃣ Place an order (Customer role)
curl -X POST http://localhost:8000/api/v1/orders?role=CUSTOMER \
  -H "Content-Type: application/json" \
  -d '{
        "customerRef": "c1f5a2b0-1234-4d5e-8f9a-abcdef012345",
        "lineItems": [
          { "productRef": "e2d8c3f9-1111-4a2b-9c3d-456789abcdef", "quantity": 2 }
        ]
      }' | jq .

# 3️⃣ Accept order (Order Staff)
curl -X POST http://localhost:8000/api/v1/orders/abcd1234-ef56-7890-abcd-1234567890ab/accept?role=ORDER_STAFF

# 4️⃣ Issue invoice (Accountant)
curl -X POST http://localhost:8000/api/v1/orders/abcd1234-ef56-7890-abcd-1234567890ab/invoice?role=ACCOUNTANT \
  -H "Content-Type: application/json" \
  -d '{}' | jq .

# 5️⃣ Pay invoice (Customer)
curl -X POST http://localhost:8000/api/v1/orders/abcd1234-ef56-7890-abcd-1234567890ab/pay?role=CUSTOMER \
  -H "Content-Type: application/json" \
  -d '{ "method": "CREDIT_CARD" }' | jq .
```
Replace the UUIDs with values returned from previous calls.

### 10.3 Generating OpenAPI Spec
The spec is automatically generated at **`/openapi.json`**. To export it:

```bash
curl http://localhost:8000/openapi.json -o oms_openapi.json
```
You can import `oms_openapi.json` into tools like **Postman**, **Insomnia**, or **Swagger UI**.

---

*Prepared by the Chief Product Officer – ChatDev*  
*Last updated: 2026‑07‑27*