# OMS Backend — Order Management System

Production-grade, backend-only e-commerce Order Management System (OMS) built with Python, FastAPI, and SQLAlchemy.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Controller  │────▶│   Service    │────▶│  Repository  │
│  (REST API)  │     │  (Business)  │     │   (Data)     │
└─────────────┘     └──────────────┘     └──────────────┘
                            │                      │
                            ▼                      ▼
                   ┌──────────────┐     ┌──────────────┐
                   │Infrastructure│     │   Database   │
                   │  (CB/Health) │     │  (SQLite)    │
                   └──────────────┘     └──────────────┘
```

## NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|-----------------|---------------------|
| **NFR 2.1 Graceful Degradation** | Circuit Breaker pattern — non-essential features (invoicing, shipping) use separate breakers with lower thresholds; core checkout uses a higher threshold breaker | `app/infrastructure.py` — `CircuitBreaker` class, `invoice_circuit`, `shipping_circuit`, `checkout_circuit` | Simulate repeated failures on invoice/shipping endpoints; observe `/health` shows those breakers as OPEN while checkout still works |
| **NFR 2.2 Fault Detection and Recovery** | Health check endpoint (`/health`) reports database connectivity and circuit breaker states; automatic retry via circuit breaker half-open recovery | `app/infrastructure.py` — `check_database_health()`, `get_circuit_breaker_states()`; `app/main.py` — `/health` endpoint | Call `/health` after a DB disconnect; observe `database` field shows "unhealthy". After DB recovers, breaker transitions to half-open then closed |
| **NFR 2.3 State Preservation** | Event log table (`event_log`) records every state transition; on startup `recover_pending_orders()` replays non-terminal orders and logs recovery | `app/models.py` — `EventLogModel`; `app/infrastructure.py` — `append_event()`, `recover_pending_orders()`, `rebuild_order_from_events()` | Kill the process mid-workflow, restart; check application logs for "Recovered N pending order(s)" and verify order statuses are intact via API |

## Architectural Decision Records (ADRs)

### ADR-1: Database — SQLite with SQLAlchemy ORM

**Decision:** Use SQLite (file-based) with SQLAlchemy 2.0 ORM.

**Context:** NFR 2.3 (State Preservation) requires durable storage; local deployment must be zero-config.

**Alternatives considered:**
- **PostgreSQL:** More production-realistic but requires external service; violates "local machine" requirement.
- **In-memory dict:** Fast but loses all data on restart; violates NFR 2.3.

**Consequences:** SQLite handles concurrent writes with WAL mode; for high-traffic production, swap `database_url` to PostgreSQL.

### ADR-2: Web Framework — FastAPI

**Decision:** Use FastAPI with automatic OpenAPI generation.

**Context:** All NFRs benefit from async-capable framework; OpenAPI spec is a deliverable.

**Alternatives considered:**
- **Flask:** Mature but lacks native async and auto-generated OpenAPI.
- **Django REST:** Heavy framework with ORM lock-in; overkill for this scope.

**Consequences:** FastAPI's dependency injection integrates cleanly with SQLAlchemy sessions.

### ADR-3: Circuit Breaker for Graceful Degradation

**Decision:** Implement a custom Circuit Breaker with closed/open/half-open states.

**Context:** NFR 2.1 requires non-essential features to degrade while core checkout survives.

**Alternatives considered:**
- **pybreaker library:** External dependency; less control over half-open behavior.
- **Try/except everywhere:** No systematic degradation; violates NFR 2.1.

**Consequences:** Custom implementation adds ~100 LOC but gives full control over thresholds and fallback logic.

### ADR-4: Event Log for State Preservation

**Decision:** Append-only event log table recording every order state transition.

**Context:** NFR 2.3 requires restoring operational state after crash.

**Alternatives considered:**
- **Database snapshots:** Heavy; requires external tooling.
- **Checkpoint files:** Prone to corruption on crash.

**Consequences:** Event log enables full audit trail and future event-sourcing patterns; adds write overhead per transition.

### ADR-5: Layered Architecture (Controller → Service → Repository)

**Decision:** Strict three-layer separation with dependency injection.

**Context:** All NFRs benefit from testability and separation of concerns.

**Alternatives considered:**
- **Fat controllers:** Quick to write but untestable; cross-cutting concerns leak.
- **Single-file monolith:** Violates every NFR.

**Consequences:** More files to maintain; each layer is independently testable and replaceable.

## Data Architecture

### Entity-Relationship

```
Customer 1───* Order 1───* LineItem
                 1───1 Payment
                 1───1 Invoice
```

### Order Status Lifecycle

```
PENDING ──→ ACCEPTED ──→ INVOICED ──→ PAID ──→ SHIPPED ──→ CLOSED
    │            │
    └──CANCELLED─┘
```

### Schema (SQLAlchemy models in `app/models.py`)

- **customers:** id, name, address, phone, banking_details, role
- **products:** id, description, base_price, currency
- **orders:** id, customer_id (FK), status, created_at, updated_at, invoice_id, payment_id
- **line_items:** id, order_id (FK), product_id, quantity, unit_price, currency
- **payments:** id, order_id (FK), amount, currency, method, status, timestamp
- **invoices:** id, order_id (FK), billing_name, billing_address, total_amount, currency, issue_date, due_date, status
- **event_log:** id (auto), aggregate_type, aggregate_id, event_type, payload, created_at

## User Workflow (API Endpoints)

| Step | Action | Endpoint | Role |
|------|--------|----------|------|
| 1 | Place order | `POST /api/v1/orders` | Customer |
| 2 | Accept order | `PATCH /api/v1/orders/{id}/accept` | Order Staff |
| 3 | Create invoice | `POST /api/v1/orders/{id}/invoice` | Accountant |
| 4 | Record payment | `POST /api/v1/orders/{id}/payments` | Customer |
| 5 | Verify payment | `POST /api/v1/orders/payments/{id}/verify` | Accountant |
| 6 | Ship order | `PATCH /api/v1/orders/{id}/ship` | Order Staff |
| 7 | Close order | `PATCH /api/v1/orders/{id}/close` | Order Staff |

## Local Deployment Guide

### Prerequisites
- Python 3.12+
- Docker & Docker Compose (optional, for containerized deployment)

### Option 1: Direct (no Docker)

```bash
cd oms

# Create virtual environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
uv sync

# Run the application
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 2: Docker Compose

```bash
cd oms
docker compose up --build
```

### Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","database":"healthy","circuit_breakers":{"invoice":"CLOSED","shipping":"CLOSED","checkout":"CLOSED"},"version":"1.0.0"}

# OpenAPI docs
open http://localhost:8000/docs
```

## Verification Steps for NFRs

### NFR 2.1 — Graceful Degradation

```bash
# 1. Cause repeated failures on invoice circuit (e.g., by passing invalid order_id)
for i in $(seq 1 6); do
  curl -s -X POST http://localhost:8000/api/v1/orders/00000000-0000-0000-0000-000000000000/invoice \
    -H "Content-Type: application/json" \
    -d '{"billing_name":"Test","billing_address":"Addr","due_days":30}'
done

# 2. Check health — invoice circuit should be OPEN
curl http://localhost:8000/health
# Expected: "invoice": "OPEN"

# 3. Core checkout still works (place a valid order)
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"<valid-customer-id>","line_items":[{"product_id":"<valid-product-id>","quantity":1,"unit_price":10.00}]}'
# Expected: 201 Created (checkout circuit is still CLOSED)
```

### NFR 2.2 — Fault Detection and Recovery

```bash
# 1. Health check shows database healthy
curl http://localhost:8000/health

# 2. Simulate database failure (stop the DB or rename the file)
# The health endpoint will show database: "unhealthy: ..."

# 3. Restore the database file
# The circuit breaker will transition: OPEN → HALF_OPEN → CLOSED
# Health check will show database: "healthy" again
```

### NFR 2.3 — State Preservation

```bash
# 1. Create a full order flow (steps 1-3)
# 2. Kill the process (Ctrl+C or kill)
# 3. Restart the application
# 4. Check logs for: "Recovered N pending order(s) from event log."
# 5. Verify order status via API:
curl http://localhost:8000/api/v1/orders/<order-id>
# Status should be preserved (e.g., INVOICED if that was the last state)
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
