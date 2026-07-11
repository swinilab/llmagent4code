# OMS — Order Management System

Production-grade, backend-only e-commerce Order Management System built with Python + FastAPI.

---

## 1. NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|-----------------|-------------------|
| **NFR 2.1 — Localization of Changes** | Domain-driven package structure with bounded contexts (domain, service, repository, api) | `oms/domain/`, `oms/service/`, `oms/repository/`, `oms/api/` | Change a domain model field; only the owning service and its controller need updates — no cascading changes across unrelated modules. |
| **NFR 2.2 — Interface Stability** | Versioned API paths (`/api/v1/...`), OpenAPI spec, Pydantic response models decoupled from internal entities | `oms/api/v1/` routers, `openapi.yaml` | Add a new field to an internal entity; the API response schema stays unchanged unless explicitly version-bumped. The OpenAPI spec is the contract. |
| **NFR 2.3 — Deferred Binding** | Pydantic-Settings reads from `.env` / environment variables at startup; config is a single `Settings` object | `oms/config.py`, `.env` | Change `PORT=8001` in `.env` and restart; the server binds to the new port without code changes. |

---

## 2. Architectural Decision Records (ADRs)

### ADR-1: Python + FastAPI over Spring Boot

- **Decision:** Use Python with FastAPI instead of Spring Boot (Java).
- **Context:** NFR 2.1 (Localization of Changes) — Python's dynamic typing and FastAPI's dependency injection allow rapid iteration with minimal boilerplate. The task explicitly states "Programming Language: Python".
- **Alternatives considered:**
  1. *Spring Boot (Java)* — Rejected because the task mandates Python. Spring Boot would also require significantly more boilerplate (XML configs, annotations, Maven/Gradle).
  2. *Flask* — Rejected because it lacks native OpenAPI support, async capabilities, and built-in validation (Pydantic integration).
- **Consequences:** FastAPI provides automatic OpenAPI generation, async support, and Pydantic validation out of the box. Trade-off: Python's runtime performance is lower than Java, but for an OMS backend this is acceptable.

### ADR-2: In-Memory Repositories over SQL Database

- **Decision:** Use thread-safe in-memory dictionaries as the persistence layer.
- **Context:** NFR 2.1 — The focus is on domain logic and API design, not database setup. In-memory storage allows zero-config local deployment.
- **Alternatives considered:**
  1. *PostgreSQL with SQLAlchemy* — Rejected because it adds deployment complexity (requires a running DB) and obscures the domain logic with ORM mapping.
  2. *SQLite* — Rejected because it requires file-system persistence and migration management, which is unnecessary for demonstrating the architecture.
- **Consequences:** Data is lost on restart. This is acceptable for a demo/prototype. The repository interface is cleanly abstracted, so swapping to a real DB requires only implementing the same interface.

### ADR-3: Versioned API Paths (`/api/v1/`)

- **Decision:** All REST endpoints are prefixed with `/api/v1/`.
- **Context:** NFR 2.2 (Interface Stability) — Versioned paths prevent breaking changes from affecting existing clients.
- **Alternatives considered:**
  1. *Header-based versioning (Accept: application/vnd.oms.v1+json)* — Rejected because it's less discoverable and harder to test with simple HTTP clients.
  2. *No versioning* — Rejected because any future change to request/response schemas would break existing clients.
- **Consequences:** URL paths are longer. A new version (v2) can be added alongside v1 without breaking existing integrations.

### ADR-4: Domain Events over Direct Service Calls

- **Decision:** Use an in-process event bus (`EventBus`) to decouple services.
- **Context:** NFR 2.1 — When an order is accepted, the invoice service should know about it without the order service calling invoice service directly.
- **Alternatives considered:**
  1. *Direct service-to-service calls* — Rejected because it creates tight coupling between services; changing one service may force changes in others.
  2. *Message queue (RabbitMQ / Redis)* — Rejected because it adds infrastructure complexity beyond what is needed for this scope.
- **Consequences:** Events are delivered synchronously in-process. If the system grows, the event bus can be replaced with a real message broker without changing the event definitions.

### ADR-5: Pydantic-Settings for Configuration

- **Decision:** Use `pydantic-settings` to load configuration from `.env` files and environment variables.
- **Context:** NFR 2.3 (Deferred Binding) — Configuration must be changeable without code changes.
- **Alternatives considered:**
  1. *Hardcoded constants* — Rejected because they violate NFR 2.3.
  2. *Python `configparser`* — Rejected because it lacks type coercion, validation, and environment variable override support.
- **Consequences:** Configuration is validated at startup. Environment variables override `.env` values, which is standard 12-factor app behavior.

### ADR-6: Payment Amount Validation

- **Decision:** Validate that payment amount exactly matches invoice total before accepting a payment.
- **Context:** Critical business logic — without this validation, a customer could underpay and still receive goods.
- **Alternatives considered:**
  1. *Allow any amount and track over/under payments* — Rejected because it adds complexity (partial payments, credit notes) beyond the current scope.
  2. *No validation* — Rejected because it breaks financial integrity.
- **Consequences:** Payments must match invoice totals exactly. Partial payments are not supported.

### ADR-7: Request Body for Staff/Accountant IDs

- **Decision:** Use request body (JSON) for `staff_id` and `accountant_id` on PATCH endpoints instead of query parameters.
- **Context:** REST semantics — query parameters are for filtering/identifying resources, not for passing action-specific data.
- **Alternatives considered:**
  1. *Query parameters* — Rejected because they violate REST conventions; IDs are action data, not resource identifiers.
  2. *Path parameters* — Rejected because they would make URLs less readable and harder to version.
- **Consequences:** Clients must send a JSON body with `{\"staff_id\": \"...\"}` or `{\"accountant_id\": \"...\"}` on PATCH operations.

### ADR-8: Catalog Price Validation on Order Placement

- **Decision:** Validate that line item unit prices match the product catalog prices when placing an order.
- **Context:** Financial integrity — without this validation, a customer could place an order with arbitrary prices that differ from the catalog.
- **Alternatives considered:**
  1. *Allow any price and rely on invoice correction* — Rejected because it introduces financial risk and requires manual correction workflows.
  2. *No validation* — Rejected because it breaks pricing integrity.
- **Consequences:** Orders must use catalog prices. Discounts or negotiated pricing would require a separate discount mechanism.

### ADR-9: Timezone-Aware UTC Datetimes

- **Decision:** Use `datetime.now(timezone.utc)` instead of the deprecated `datetime.utcnow()`.
- **Context:** Python 3.12+ deprecates `datetime.utcnow()`; it will be removed in Python 3.14. All timestamps must be timezone-aware to avoid subtle comparison bugs.
- **Alternatives considered:**
  1. *Keep using `datetime.utcnow()`* — Rejected because it emits `DeprecationWarning` in Python 3.12 and will break in Python 3.14.
  2. *Use `datetime.now(datetime.UTC)`* — Equivalent alternative; `timezone.utc` is used for consistency with the `timezone` import.
- **Consequences:** All timestamps are timezone-aware UTC, which is the modern Python standard. No behavioral change for consumers.

### ADR-10: OrderCancelled Domain Event

- **Decision:** Publish an `OrderCancelled` domain event when an order is cancelled.
- **Context:** Consistency — all other order state transitions publish domain events. The cancellation transition was missing its event, which could break event-driven workflows.
- **Alternatives considered:**
  1. *No event for cancellation* — Rejected because it creates an inconsistency in the event model; downstream systems would not know about cancellations.
  2. *Reuse `OrderCompleted` with a flag* — Rejected because it conflates two distinct states.
- **Consequences:** The event model is now consistent: every state transition publishes a corresponding event.

---

## 3. Data Architecture Narrative

### Domain Model Overview

The system is built around five core entities, each with a clear bounded context:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Customer │────▶│  Order   │────▶│ Invoice  │────▶│ Payment  │     │ Product  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                                                │
                      │ line_items[]                                  │ referenced by
                      ▼                                                ▼
                  LineItem ────────────────────────────────────── Product
```

### Entity Relationships

- **Customer** has a 1:N relationship with **Order** (order_history contains order IDs).
- **Order** contains 1:N **LineItem** references, each pointing to a **Product**.
- **Order** has a 0:1 relationship with **Invoice** (invoice_ref).
- **Invoice** has a 1:N relationship with **Payment** (via order_id).
- **Order** follows a strict state machine: `pending → accepted → invoiced → paid → shipped → completed`.

### Schema (SQL DDL equivalent)

```sql
-- Customers
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    address JSONB NOT NULL,       -- Address value object
    phone TEXT NOT NULL,
    banking_details JSONB NOT NULL, -- BankingDetails value object
    order_history UUID[],
    role TEXT NOT NULL DEFAULT 'customer',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY,
    description TEXT NOT NULL,
    base_price JSONB NOT NULL,     -- Money value object
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Orders
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(id),
    line_items JSONB NOT NULL,     -- Array of LineItem value objects
    total JSONB NOT NULL,           -- Money value object
    status TEXT NOT NULL CHECK (status IN ('pending','accepted','invoiced','paid','shipped','completed','cancelled')),
    invoice_ref UUID REFERENCES invoices(id),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Invoices
CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    billing_address JSONB NOT NULL,
    line_items JSONB NOT NULL,
    subtotal JSONB NOT NULL,
    tax JSONB NOT NULL,
    total JSONB NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft','issued','paid','overdue','cancelled')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Payments
CREATE TABLE payments (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    amount JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','verified','failed')),
    method TEXT NOT NULL CHECK (method IN ('credit_card','debit_card','bank_transfer','digital_wallet')),
    verified_by UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

---

## 4. Shared Domain Models

All domain models are defined in `oms/domain/models.py` using Pydantic. These are used by both the backend services and exposed via the API as response models. Key models:

- **Value Objects:** `Money`, `Address`, `BankingDetails`, `LineItem`
- **Entities:** `Customer`, `Product`, `Order`, `Payment`, `Invoice`
- **Request DTOs:** `CreateCustomerRequest`, `CreateProductRequest`, `CreateOrderRequest`, `CreateInvoiceRequest`, `CreatePaymentRequest`, `StaffActionRequest`, `AccountantActionRequest`, `CancelOrderRequest`

---

## 5. Complete Backend Code

### Project Structure

```
oms/
├── __init__.py
├── main.py                  # FastAPI app creation and entry point
├── config.py                # Pydantic-settings configuration
├── domain/
│   ├── __init__.py
│   ├── enums.py             # OrderStatus, PaymentStatus, etc.
│   ├── models.py            # All domain entities and DTOs
│   └── events.py            # Domain events (including OrderCancelled)
├── repository/
│   ├── __init__.py
│   └── in_memory.py         # Thread-safe in-memory repositories
├── service/
│   ├── __init__.py
│   ├── event_bus.py         # In-process event bus
│   ├── customer_service.py
│   ├── product_service.py
│   ├── order_service.py
│   ├── invoice_service.py
│   └── payment_service.py
├── api/
│   ├── __init__.py
│   ├── deps.py              # Dependency injection
│   └── v1/
│       ├── __init__.py
│       ├── customers.py
│       ├── products.py
│       ├── orders.py
│       ├── invoices.py
│       └── payments.py
└── middleware/
    ├── __init__.py
    └── error_handler.py     # Global exception handlers
```

### API Endpoints Summary

| Method | Path | Step | Description |
|--------|------|------|-------------|
| POST | `/api/v1/customers` | — | Register a customer |
| GET | `/api/v1/customers` | — | List customers |
| GET | `/api/v1/customers/{id}` | — | Get customer |
| POST | `/api/v1/products` | — | Create a product |
| GET | `/api/v1/products` | — | List products |
| GET | `/api/v1/products/{id}` | — | Get product |
| POST | `/api/v1/orders` | 1 | Place order |
| PATCH | `/api/v1/orders/{id}/accept` | 2 | Accept order |
| POST | `/api/v1/invoices` | 3 | Create invoice |
| POST | `/api/v1/payments` | 4 | Make payment |
| PATCH | `/api/v1/payments/{id}/verify` | 5 | Verify payment |
| PATCH | `/api/v1/orders/{id}/ship` | 6 | Ship order |
| PATCH | `/api/v1/orders/{id}/close` | 7 | Close order |
| PATCH | `/api/v1/orders/{id}/cancel` | — | Cancel order |
| PATCH | `/api/v1/invoices/{id}/mark-overdue` | — | Mark invoice overdue |
| GET | `/api/v1/orders` | — | List orders |
| GET | `/api/v1/orders/{id}` | — | Get order |
| GET | `/api/v1/invoices` | — | List invoices |
| GET | `/api/v1/invoices/{id}` | — | Get invoice |
| GET | `/api/v1/payments` | — | List payments |
| GET | `/api/v1/payments/{id}` | — | Get payment |
| GET | `/health` | — | Health check |

---

## 6. IaC Config and Documents

### Docker

- **Dockerfile** — Multi-stage build using `python:3.12-slim` with `uv` for fast dependency installation.
- **docker-compose.yml** — Single service (`oms-api`) with health check, port mapping, and environment variable passthrough.

### Environment

- **`.env`** — All configurable parameters with sensible defaults.

---

## 7. Local Deployment Guide

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (or pip)
- Docker (optional, for containerized deployment)

### Option A: Run Locally (uv)

```bash
# 1. Clone / navigate to the project
cd oms-backend

# 2. Create virtual environment and install dependencies
uv sync

# 3. Run the application
uv run python -m oms.main
```

The server starts at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

### Option B: Run Locally (pip)

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# 2. Install dependencies
pip install fastapi uvicorn[standard] pydantic pydantic-settings pyyaml httpx

# 3. Run the application
python -m oms.main
```

### Option C: Run with Docker

```bash
# Build and start
docker compose up --build -d

# Check logs
docker compose logs -f

# Stop
docker compose down
```

### Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Should return: {"status":"ok"}
```

---

## 8. Verification Steps for NFRs

### NFR 2.1 — Localization of Changes

**Test:** Add a new field to the `Customer` domain model (e.g., `email: str`).

1. Edit `oms/domain/models.py` — add `email: str` to the `Customer` class.
2. Edit `oms/domain/models.py` — add `email: str` to `CreateCustomerRequest`.
3. Edit `oms/api/v1/customers.py` — no changes needed (Pydantic auto-serializes).
4. **Result:** Only the domain model and its request DTO changed. No other files required modification.

### NFR 2.2 — Interface Stability

**Test:** Add an internal field to `Order` that should not appear in the API response.

1. Edit `oms/domain/models.py` — add `internal_notes: str = \"\"` to `Order`.
2. Restart the server.
3. `curl http://localhost:8000/api/v1/orders/{id}` — the response does NOT include `internal_notes`.
4. **Result:** The API contract (defined by Pydantic response models) remains stable. Internal entity changes do not leak to clients.

### NFR 2.3 — Deferred Binding

**Test:** Change the server port without modifying code.

1. Edit `.env` — change `PORT=8001`.
2. Restart the server: `uv run python -m oms.main`.
3. `curl http://localhost:8001/health` — returns `{\"status\":\"ok\"}`.
4. **Result:** Configuration changed at runtime via external file, no code changes needed.

### Code Quality Verification

**Test:** Verify no deprecated `datetime.utcnow()` calls exist.

```bash
grep -r "datetime\.utcnow" oms/
# Should return no matches
```

**Test:** Verify `OrderCancelled` event is published on cancellation.

```bash
# Run the integration test
uv run python test_workflow.py
# Look for "[PASS] Order cancellation works" in output
```

**Test:** Verify catalog price validation on order placement.

```bash
# Attempt to place an order with a mismatched unit price
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "<valid-uuid>", "line_items": [{"product_id": "<valid-uuid>", "product_description": "Test", "quantity": 1, "unit_price": {"amount": 999.99, "currency": "USD"}}]}'
# Should return 400 with "does not match catalog price"
```

---

## Full Workflow Test (curl)

```bash
# 1. Register a customer
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": {"street": "123 Main St", "city": "Springfield", "state": "IL", "zip_code": "62701", "country": "USA"},
    "phone": "+1-555-0100",
    "banking_details": {"bank_name": "First National", "account_number": "123456789", "routing_number": "021000021"}
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Customer ID: $CUSTOMER"

# 2. Create a product
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description": "Widget A", "base_price": {"amount": 29.99, "currency": "USD"}}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PRODUCT"

# 3. Place an order (Step 1)
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"$CUSTOMER\",
    \"line_items\": [{\"product_id\": \"$PRODUCT\", \"product_description\": \"Widget A\", \"quantity\": 2, \"unit_price\": {\"amount\": 29.99, \"currency\": \"USD\"}}]
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order ID: $ORDER"

# 4. Accept order (Step 2) — staff_id in request body
STAFF="00000000-0000-0000-0000-000000000001"
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/accept" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool

# 5. Create invoice (Step 3)
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER\",
    \"customer_id\": \"$CUSTOMER\",
    \"billing_address\": {\"street\": \"123 Main St\", \"city\": \"Springfield\", \"state\": \"IL\", \"zip_code\": \"62701\", \"country\": \"USA\"},
    \"tax\": {\"amount\": 5.00, \"currency\": \"USD\"},
    \"due_date\": \"2025-08-01\"
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Invoice ID: $INVOICE"

# 6. Make payment (Step 4) — amount must match invoice total (59.98 + 5.00 = 64.98)
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER\",
    \"invoice_id\": \"$INVOICE\",
    \"amount\": {\"amount\": 64.98, \"currency\": \"USD\"},
    \"method\": \"credit_card\"
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Payment ID: $PAYMENT"

# 7. Verify payment (Step 5) — accountant_id in request body
ACCOUNTANT="00000000-0000-0000-0000-000000000002"
curl -s -X PATCH "http://localhost:8000/api/v1/payments/$PAYMENT/verify" \
  -H "Content-Type: application/json" \
  -d "{\"accountant_id\": \"$ACCOUNTANT\"}" | python -m json.tool

# 8. Ship order (Step 6) — staff_id in request body
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/ship" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool

# 9. Close order (Step 7) — staff_id in request body
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/close" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool

# 10. Verify final state
curl -s "http://localhost:8000/api/v1/orders/$ORDER" | python -m json.tool
```

Production-grade, backend-only e-commerce Order Management System built with Python + FastAPI.

---

## 1. NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|-----------------|-------------------|
| **NFR 2.1 — Localization of Changes** | Domain-driven package structure with bounded contexts (domain, service, repository, api) | `oms/domain/`, `oms/service/`, `oms/repository/`, `oms/api/` | Change a domain model field; only the owning service and its controller need updates — no cascading changes across unrelated modules. |
| **NFR 2.2 — Interface Stability** | Versioned API paths (`/api/v1/...`), OpenAPI spec, Pydantic response models decoupled from internal entities | `oms/api/v1/` routers, `openapi.yaml` | Add a new field to an internal entity; the API response schema stays unchanged unless explicitly version-bumped. The OpenAPI spec is the contract. |
| **NFR 2.3 — Deferred Binding** | Pydantic-Settings reads from `.env` / environment variables at startup; config is a single `Settings` object | `oms/config.py`, `.env` | Change `PORT=8001` in `.env` and restart; the server binds to the new port without code changes. |

---

## 2. Architectural Decision Records (ADRs)

### ADR-1: Python + FastAPI over Spring Boot

- **Decision:** Use Python with FastAPI instead of Spring Boot (Java).
- **Context:** NFR 2.1 (Localization of Changes) — Python's dynamic typing and FastAPI's dependency injection allow rapid iteration with minimal boilerplate. The task explicitly states "Programming Language: Python".
- **Alternatives considered:**
  1. *Spring Boot (Java)* — Rejected because the task mandates Python. Spring Boot would also require significantly more boilerplate (XML configs, annotations, Maven/Gradle).
  2. *Flask* — Rejected because it lacks native OpenAPI support, async capabilities, and built-in validation (Pydantic integration).
- **Consequences:** FastAPI provides automatic OpenAPI generation, async support, and Pydantic validation out of the box. Trade-off: Python's runtime performance is lower than Java, but for an OMS backend this is acceptable.

### ADR-2: In-Memory Repositories over SQL Database

- **Decision:** Use thread-safe in-memory dictionaries as the persistence layer.
- **Context:** NFR 2.1 — The focus is on domain logic and API design, not database setup. In-memory storage allows zero-config local deployment.
- **Alternatives considered:**
  1. *PostgreSQL with SQLAlchemy* — Rejected because it adds deployment complexity (requires a running DB) and obscures the domain logic with ORM mapping.
  2. *SQLite* — Rejected because it requires file-system persistence and migration management, which is unnecessary for demonstrating the architecture.
- **Consequences:** Data is lost on restart. This is acceptable for a demo/prototype. The repository interface is cleanly abstracted, so swapping to a real DB requires only implementing the same interface.

### ADR-3: Versioned API Paths (`/api/v1/`)

- **Decision:** All REST endpoints are prefixed with `/api/v1/`.
- **Context:** NFR 2.2 (Interface Stability) — Versioned paths prevent breaking changes from affecting existing clients.
- **Alternatives considered:**
  1. *Header-based versioning (Accept: application/vnd.oms.v1+json)* — Rejected because it's less discoverable and harder to test with simple HTTP clients.
  2. *No versioning* — Rejected because any future change to request/response schemas would break existing clients.
- **Consequences:** URL paths are longer. A new version (v2) can be added alongside v1 without breaking existing integrations.

### ADR-4: Domain Events over Direct Service Calls

- **Decision:** Use an in-process event bus (`EventBus`) to decouple services.
- **Context:** NFR 2.1 — When an order is accepted, the invoice service should know about it without the order service calling invoice service directly.
- **Alternatives considered:**
  1. *Direct service-to-service calls* — Rejected because it creates tight coupling between services; changing one service may force changes in others.
  2. *Message queue (RabbitMQ / Redis)* — Rejected because it adds infrastructure complexity beyond what is needed for this scope.
- **Consequences:** Events are delivered synchronously in-process. If the system grows, the event bus can be replaced with a real message broker without changing the event definitions.

### ADR-5: Pydantic-Settings for Configuration

- **Decision:** Use `pydantic-settings` to load configuration from `.env` files and environment variables.
- **Context:** NFR 2.3 (Deferred Binding) — Configuration must be changeable without code changes.
- **Alternatives considered:**
  1. *Hardcoded constants* — Rejected because they violate NFR 2.3.
  2. *Python `configparser`* — Rejected because it lacks type coercion, validation, and environment variable override support.
- **Consequences:** Configuration is validated at startup. Environment variables override `.env` values, which is standard 12-factor app behavior.

### ADR-6: Payment Amount Validation

- **Decision:** Validate that payment amount exactly matches invoice total before accepting a payment.
- **Context:** Critical business logic — without this validation, a customer could underpay and still receive goods.
- **Alternatives considered:**
  1. *Allow any amount and track over/under payments* — Rejected because it adds complexity (partial payments, credit notes) beyond the current scope.
  2. *No validation* — Rejected because it breaks financial integrity.
- **Consequences:** Payments must match invoice totals exactly. Partial payments are not supported.

### ADR-7: Request Body for Staff/Accountant IDs

- **Decision:** Use request body (JSON) for `staff_id` and `accountant_id` on PATCH endpoints instead of query parameters.
- **Context:** REST semantics — query parameters are for filtering/identifying resources, not for passing action-specific data.
- **Alternatives considered:**
  1. *Query parameters* — Rejected because they violate REST conventions; IDs are action data, not resource identifiers.
  2. *Path parameters* — Rejected because they would make URLs less readable and harder to version.
- **Consequences:** Clients must send a JSON body with `{"staff_id": "..."}` or `{"accountant_id": "..."}` on PATCH operations.

---

## 3. Data Architecture Narrative

### Domain Model Overview

The system is built around five core entities, each with a clear bounded context:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Customer │────▶│  Order   │────▶│ Invoice  │────▶│ Payment  │     │ Product  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                                                │
                      │ line_items[]                                  │ referenced by
                      ▼                                                ▼
                  LineItem ────────────────────────────────────── Product
```

### Entity Relationships

- **Customer** has a 1:N relationship with **Order** (order_history contains order IDs).
- **Order** contains 1:N **LineItem** references, each pointing to a **Product**.
- **Order** has a 0:1 relationship with **Invoice** (invoice_ref).
- **Invoice** has a 1:N relationship with **Payment** (via order_id).
- **Order** follows a strict state machine: `pending → accepted → invoiced → paid → shipped → completed`.

### Schema (SQL DDL equivalent)

```sql
-- Customers
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    address JSONB NOT NULL,       -- Address value object
    phone TEXT NOT NULL,
    banking_details JSONB NOT NULL, -- BankingDetails value object
    order_history UUID[],
    role TEXT NOT NULL DEFAULT 'customer',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY,
    description TEXT NOT NULL,
    base_price JSONB NOT NULL,     -- Money value object
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Orders
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(id),
    line_items JSONB NOT NULL,     -- Array of LineItem value objects
    total JSONB NOT NULL,           -- Money value object
    status TEXT NOT NULL CHECK (status IN ('pending','accepted','invoiced','paid','shipped','completed','cancelled')),
    invoice_ref UUID REFERENCES invoices(id),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Invoices
CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    billing_address JSONB NOT NULL,
    line_items JSONB NOT NULL,
    subtotal JSONB NOT NULL,
    tax JSONB NOT NULL,
    total JSONB NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft','issued','paid','overdue','cancelled')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Payments
CREATE TABLE payments (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    amount JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','verified','failed')),
    method TEXT NOT NULL CHECK (method IN ('credit_card','debit_card','bank_transfer','digital_wallet')),
    verified_by UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

---

## 4. Shared Domain Models

All domain models are defined in `oms/domain/models.py` using Pydantic. These are used by both the backend services and exposed via the API as response models. Key models:

- **Value Objects:** `Money`, `Address`, `BankingDetails`, `LineItem`
- **Entities:** `Customer`, `Product`, `Order`, `Payment`, `Invoice`
- **Request DTOs:** `CreateCustomerRequest`, `CreateProductRequest`, `CreateOrderRequest`, `CreateInvoiceRequest`, `CreatePaymentRequest`, `StaffActionRequest`, `AccountantActionRequest`, `CancelOrderRequest`

---

## 5. Complete Backend Code

### Project Structure

```
oms/
├── __init__.py
├── main.py                  # FastAPI app creation and entry point
├── config.py                # Pydantic-settings configuration
├── domain/
│   ├── __init__.py
│   ├── enums.py             # OrderStatus, PaymentStatus, etc.
│   ├── models.py            # All domain entities and DTOs
│   └── events.py            # Domain events
├── repository/
│   ├── __init__.py
│   └── in_memory.py         # Thread-safe in-memory repositories
├── service/
│   ├── __init__.py
│   ├── event_bus.py         # In-process event bus
│   ├── customer_service.py
│   ├── product_service.py
│   ├── order_service.py
│   ├── invoice_service.py
│   └── payment_service.py
├── api/
│   ├── __init__.py
│   ├── deps.py              # Dependency injection
│   └── v1/
│       ├── __init__.py
│       ├── customers.py
│       ├── products.py
│       ├── orders.py
│       ├── invoices.py
│       └── payments.py
└── middleware/
    ├── __init__.py
    └── error_handler.py     # Global exception handlers
```

### API Endpoints Summary

| Method | Path | Step | Description |
|--------|------|------|-------------|
| POST | `/api/v1/customers` | — | Register a customer |
| GET | `/api/v1/customers` | — | List customers |
| GET | `/api/v1/customers/{id}` | — | Get customer |
| POST | `/api/v1/products` | — | Create a product |
| GET | `/api/v1/products` | — | List products |
| GET | `/api/v1/products/{id}` | — | Get product |
| POST | `/api/v1/orders` | 1 | Place order |
| PATCH | `/api/v1/orders/{id}/accept` | 2 | Accept order |
| POST | `/api/v1/invoices` | 3 | Create invoice |
| POST | `/api/v1/payments` | 4 | Make payment |
| PATCH | `/api/v1/payments/{id}/verify` | 5 | Verify payment |
| PATCH | `/api/v1/orders/{id}/ship` | 6 | Ship order |
| PATCH | `/api/v1/orders/{id}/close` | 7 | Close order |
| PATCH | `/api/v1/orders/{id}/cancel` | — | Cancel order |
| PATCH | `/api/v1/invoices/{id}/mark-overdue` | — | Mark invoice overdue |
| GET | `/api/v1/orders` | — | List orders |
| GET | `/api/v1/orders/{id}` | — | Get order |
| GET | `/api/v1/invoices` | — | List invoices |
| GET | `/api/v1/invoices/{id}` | — | Get invoice |
| GET | `/api/v1/payments` | — | List payments |
| GET | `/api/v1/payments/{id}` | — | Get payment |
| GET | `/health` | — | Health check |

---

## 6. IaC Config and Documents

### Docker

- **Dockerfile** — Multi-stage build using `python:3.12-slim` with `uv` for fast dependency installation.
- **docker-compose.yml** — Single service (`oms-api`) with health check, port mapping, and environment variable passthrough.

### Environment

- **`.env`** — All configurable parameters with sensible defaults.

---

## 7. Local Deployment Guide

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (or pip)
- Docker (optional, for containerized deployment)

### Option A: Run Locally (uv)

```bash
# 1. Clone / navigate to the project
cd oms-backend

# 2. Create virtual environment and install dependencies
uv sync

# 3. Run the application
uv run python -m oms.main
```

The server starts at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

### Option B: Run Locally (pip)

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install fastapi uvicorn[standard] pydantic pydantic-settings pyyaml httpx

# 3. Run the application
python -m oms.main
```

### Option C: Run with Docker

```bash
# Build and start
docker compose up --build -d

# Check logs
docker compose logs -f

# Stop
docker compose down
```

### Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Should return: {"status":"ok"}
```

---

## 8. Verification Steps for NFRs

### NFR 2.1 — Localization of Changes

**Test:** Add a new field to the `Customer` domain model (e.g., `email: str`).

1. Edit `oms/domain/models.py` — add `email: str` to the `Customer` class.
2. Edit `oms/domain/models.py` — add `email: str` to `CreateCustomerRequest`.
3. Edit `oms/api/v1/customers.py` — no changes needed (Pydantic auto-serializes).
4. **Result:** Only the domain model and its request DTO changed. No other files required modification.

### NFR 2.2 — Interface Stability

**Test:** Add an internal field to `Order` that should not appear in the API response.

1. Edit `oms/domain/models.py` — add `internal_notes: str = ""` to `Order`.
2. Restart the server.
3. `curl http://localhost:8000/api/v1/orders/{id}` — the response does NOT include `internal_notes`.
4. **Result:** The API contract (defined by Pydantic response models) remains stable. Internal entity changes do not leak to clients.

### NFR 2.3 — Deferred Binding

**Test:** Change the server port without modifying code.

1. Edit `.env` — change `PORT=8001`.
2. Restart the server: `uv run python -m oms.main`.
3. `curl http://localhost:8001/health` — returns `{"status":"ok"}`.
4. **Result:** Configuration changed at runtime via external file, no code changes needed.

---

## Full Workflow Test (curl)

```bash
# 1. Register a customer
CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": {"street": "123 Main St", "city": "Springfield", "state": "IL", "zip_code": "62701", "country": "USA"},
    "phone": "+1-555-0100",
    "banking_details": {"bank_name": "First National", "account_number": "123456789", "routing_number": "021000021"}
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Customer ID: $CUSTOMER"

# 2. Create a product
PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description": "Widget A", "base_price": {"amount": 29.99, "currency": "USD"}}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PRODUCT"

# 3. Place an order (Step 1)
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"$CUSTOMER\",
    \"line_items\": [{\"product_id\": \"$PRODUCT\", \"product_description\": \"Widget A\", \"quantity\": 2, \"unit_price\": {\"amount\": 29.99, \"currency\": \"USD\"}}]
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order ID: $ORDER"

# 4. Accept order (Step 2) — staff_id in request body
STAFF="00000000-0000-0000-0000-000000000001"
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/accept" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool

# 5. Create invoice (Step 3)
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER\",
    \"customer_id\": \"$CUSTOMER\",
    \"billing_address\": {\"street\": \"123 Main St\", \"city\": \"Springfield\", \"state\": \"IL\", \"zip_code\": \"62701\", \"country\": \"USA\"},
    \"tax\": {\"amount\": 5.00, \"currency\": \"USD\"},
    \"due_date\": \"2025-08-01\"
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Invoice ID: $INVOICE"

# 6. Make payment (Step 4) — amount must match invoice total (59.98 + 5.00 = 64.98)
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$ORDER\",
    \"invoice_id\": \"$INVOICE\",
    \"amount\": {\"amount\": 64.98, \"currency\": \"USD\"},
    \"method\": \"credit_card\"
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Payment ID: $PAYMENT"

# 7. Verify payment (Step 5) — accountant_id in request body
ACCOUNTANT="00000000-0000-0000-0000-000000000002"
curl -s -X PATCH "http://localhost:8000/api/v1/payments/$PAYMENT/verify" \
  -H "Content-Type: application/json" \
  -d "{\"accountant_id\": \"$ACCOUNTANT\"}" | python -m json.tool

# 8. Ship order (Step 6) — staff_id in request body
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/ship" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool

# 9. Close order (Step 7) — staff_id in request body
curl -s -X PATCH "http://localhost:8000/api/v1/orders/$ORDER/close" \
  -H "Content-Type: application/json" \
  -d "{\"staff_id\": \"$STAFF\"}" | python -m json.tool

# 10. Verify final state
curl -s "http://localhost:8000/api/v1/orders/$ORDER" | python -m json.tool
```
