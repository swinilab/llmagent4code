# Order Management System (OMS) — User Manual

> **Product:** OMS Backend (v1.0.0)  
> **Tech Stack:** FastAPI (Python) · SQLAlchemy · Alembic · PostgreSQL/SQLite · Docker  
> **Roles:** Customer · Order Staff · Accountant  
> **Workflow:** Place → Accept → Invoice → Pay → Verify → Ship → Close

---

## Table of Contents

1. [Overview & System Architecture](#1-overview--system-architecture)
2. [NFR Traceability Matrix](#2-nfr-traceability-matrix)
3. [Architectural Decision Records (ADRs)](#3-architectural-decision-records-adrs)
4. [Data Architecture](#4-data-architecture)
5. [Domain Model](#5-domain-model)
6. [API Reference](#6-api-reference)
7. [Installation & Environment Setup](#7-installation--environment-setup)
8. [Local Development Guide](#8-local-development-guide)
9. [Deployment Guide (Docker / Production)](#9-deployment-guide-docker--production)
10. [Running Tests](#10-running-tests)
11. [Verification Steps (NFR Observability)](#11-verification-steps-nfr-observability)
12. [Configuration Reference](#12-configuration-reference)

---

## 1. Overview & System Architecture

The **Order Management System (OMS)** is a production-grade, backend-only e-commerce platform that manages the complete order lifecycle from placement through closure. It serves three distinct roles:

| Role | Responsibilities |
|---|---|
| **Customer** | Places orders, makes payments |
| **Order Staff** | Reviews/accepts orders, ships and closes completed orders |
| **Accountant** | Creates invoices, verifies payments |

### Architecture Diagram (Logical)

```
┌──────────────────────────────────────────────────────────────┐
│                       FastAPI Application                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Routers  │→ │ Services │→ │ Repos    │→ │   Database   │ │
│  │ (v1/*)   │  │ (domain) │  │ (data)   │  │ (SQLite/PG)  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
│       │                                                    │
│  ┌────┴─────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Rate     │  │ Queue Manager    │  │ Workflow        │  │
│  │ Limiter  │  │ (Background)     │  │ Orchestrator    │  │
│  └──────────┘  └──────────────────┘  └─────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Domain Models (Pydantic) ←→ ORM Entities (SQLAlch.)│    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions (see Section 3 for ADRs)

- **Async-first** using FastAPI + asyncpg/aiosqlite for maximum throughput
- **Domain-Driven Design** with clear boundaries between models, services, and repositories
- **Versioned API** under `/v1/` prefix to guarantee interface stability
- **Bounded async queue** for traffic spike absorption
- **Sliding-window rate limiter** for fair resource usage
- **Environment-driven configuration** via `.env` / environment variables

---

## 2. NFR Traceability Matrix

| NFR | Description | Architectural Mechanism | Module/Component | Verification Method |
|---|---|---|---|---|
| **NFR 1.1** | Response Time — core journeys must minimize latency under load | Sliding-window rate limiter (200 req/min per IP); async I/O with connection pooling; eager-loaded relationships via `selectinload` to prevent N+1 queries | `app/middleware/rate_limiter.py`, `app/database.py`, all repositories with `selectinload` | Observe 429 responses when exceeding 200 req/min; use `httpx` client to measure sub-100ms latencies for GET endpoints under moderate load |
| **NFR 1.2** | Concurrency & Resource Utilization — exploit up to 98GB RAM | Configurable connection pool (`pool_size=20`, `max_overflow=10`); SQLite WAL mode for concurrent reads; async engine with `pool_pre_ping`; PostgreSQL multi-worker support | `app/database.py` (engine & session factory), `app/config.py` | Set `DATABASE_POOL_SIZE=50` and observe connection count via `SELECT * FROM pg_stat_activity` (PG) or `PRAGMA database_list` (SQLite) |
| **NFR 1.3** | Queue Management — sudden spikes must not crash the system | Bounded in-process `asyncio.Queue` with configurable `maxsize` (default 10,000); background drain worker processes batches; returns 503 when queue full | `app/middleware/queue_manager.py` | Submit >10,000 rapid requests; observe queue overflow logged as WARNING and requests rejected with `{"detail": "Queue full"}` |
| **NFR 2.1** | Localization of Changes — domain-driven component boundaries | DDD package structure: `domain/` (models), `services/` (business logic), `repositories/` (data access), `routers/` (presentation) | Entire `app/` package tree | Modify a domain model field and verify only its repository and service files change; no cross-boundary ripple |
| **NFR 2.2** | Interface Stability — backend changes never force frontend redesign | Versioned API prefix `/v1/` on all routers; OpenAPI schema auto-generated; backward-compatible response models via Pydantic | `app/routers/v1/*.py`, OpenAPI at `/openapi.json` | Add a new optional field to a domain model; verify existing API consumers still get valid JSON responses |
| **NFR 2.3** | Deferred Binding — config changeable without restart | All parameters from `.env` / environment variables via Pydantic `BaseSettings`; hot-reload in development via `uvicorn --reload` | `app/config.py` (Settings class), `.env` file | Change `DATABASE_URL` or `QUEUE_MAX_SIZE` in `.env`, restart the process, observe new values in `/health` or logs |

---

## 3. Architectural Decision Records (ADRs)

### ADR-001: Async Python (FastAPI) Instead of Spring Boot

| Field | Value |
|---|---|
| **Decision** | Use FastAPI (Python) with async SQLAlchemy |
| **Context** | NFR 1.1 (Response Time), NFR 1.2 (Concurrency) |
| **Alternatives** | 1) **Spring Boot (Java)** — rejected because the team specified Python; heavier resource footprint per instance; longer startup time. 2) **Node.js Express** — rejected because the team's domain expertise is in Python; lack of mature ORM comparable to SQLAlchemy. |
| **Consequences** | + Native async/await support; + Automatic OpenAPI docs; + Lightweight (<100MB container). — GIL-bound CPU work must be offloaded to async patterns. |

### ADR-002: Domain-Driven Package Structure

| Field | Value |
|---|---|
| **Decision** | Separate packages for `domain/`, `services/`, `repositories/`, `routers/` |
| **Context** | NFR 2.1 (Localization of Changes) |
| **Alternatives** | 1) **Flat structure** — rejected because changes would ripple across files. 2) **Layered (controller/service/dao)** — rejected because it doesn't enforce domain boundaries, only technical layers. |
| **Consequences** | + Clear separation of concerns; + Each domain concept is a cohesive unit. — More files to navigate. |

### ADR-003: Versioned API Prefix `/v1/`

| Field | Value |
|---|---|
| **Decision** | All routers mounted under `/v1/` prefix |
| **Context** | NFR 2.2 (Interface Stability) |
| **Alternatives** | 1) **No versioning** — rejected because any contract change would break existing consumers. 2) **Header-based versioning** — rejected because URL-based is more discoverable and cache-friendly. |
| **Consequences** | + Backward incompatible changes can be introduced as `/v2/` without breaking `/v1/` consumers. — URL paths are slightly longer. |

### ADR-004: Bounded In-Process Async Queue

| Field | Value |
|---|---|
| **Decision** | Use `asyncio.Queue` with configurable `maxsize` for background task offloading |
| **Context** | NFR 1.3 (Queue Management) |
| **Alternatives** | 1) **Redis Queue (RQ/Celery)** — rejected because adds infrastructure dependency; overkill for notification-style tasks. 2) **Direct processing** — rejected because synchronous processing would block the request thread under spikes. |
| **Consequences** | + Zero external dependencies for queueing; + Configurable capacity prevents OOM. — Queue state is lost on process restart (acceptable for notifications). |

### ADR-005: Environment-Driven Configuration via Pydantic Settings

| Field | Value |
|---|---|
| **Decision** | All config loaded from `.env` / environment variables through `pydantic-settings` |
| **Context** | NFR 2.3 (Deferred Binding) |
| **Alternatives** | 1) **Hard-coded constants** — rejected because requires code changes for environment differences. 2) **YAML config files** — rejected because environment variables are the 12-factor standard and natively supported by Docker/K8s. |
| **Consequences** | + Works out-of-the-box with Docker, Kubernetes, CI/CD pipelines; + `.env` file provides local development defaults. — No dynamic runtime reload (requires restart). |

### ADR-006: String-Based Enum Storage in Database

| Field | Value |
|---|---|
| **Decision** | Store enum values as strings (`String(20)` columns) rather than native DB enums |
| **Context** | NFR 2.2 (Interface Stability), portability across SQLite and PostgreSQL |
| **Alternatives** | 1) **Database-native ENUM types** — rejected because SQLite doesn't support them; migration harder between DB backends. 2) **Integer codes** — rejected because less readable in DB queries and debugging. |
| **Consequences** | + Full portability between SQLite (dev) and PostgreSQL (prod); + Human-readable in raw SQL queries. — Slightly larger storage; requires application-level validation. |

### ADR-007: Eager Loading via `selectinload` for Async ORM

| Field | Value |
|---|---|
| **Decision** | Use `selectinload` on all repository queries that return relationships |
| **Context** | NFR 1.1 (Response Time), NFR 1.2 (Concurrency) |
| **Alternatives** | 1) **Lazy loading (default)** — rejected because async SQLAlchemy throws `MissingGreenletError` when lazy-loading outside a sync context. 2) **Joined loading (`joinedload`)** — rejected because can cause cartesian product explosions with multiple to-many relationships. |
| **Consequences** | + Eliminates N+1 query problem; + Works correctly in async context. — Slightly more verbose repository queries. |

---

## 4. Data Architecture

### Entity-Relationship Diagram (Logical)

```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│   Customer   │1──N→   │    Order     │1──N→   │  LineItem    │
├──────────────┤        ├──────────────┤        ├──────────────┤
│ id (PK)      │        │ id (PK)      │        │ id (PK)      │
│ name         │        │ customer_id  │        │ order_id(FK) │
│ address      │        │ total_amount │        │ product_id   │
│ phone        │        │ status       │        │ quantity     │
│ banking_     │        │ invoice_id   │        │ unit_price   │
│   details    │        │ created_at   │        │ subtotal     │
│ role         │        │ updated_at   │        └──────────────┘
└──────────────┘        └──────┬───────┘
       1│                      │1                   1│
        │                      │                     │
        │1                     │N                    │1
┌──────────────┐        ┌──────┴───────┐        ┌──────────────┐
│   Invoice    │N──────→│   Payment    │        │   Product    │
├──────────────┤        ├──────────────┤        ├──────────────┤
│ id (PK)      │        │ id (PK)      │        │ id (PK)      │
│ order_id(FK) │        │ order_id(FK) │        │ description  │
│ customer_id  │        │ invoice_id   │        │ base_price   │
│ billing_name │        │ amount       │        │ currency     │
│ billing_addr │        │ method       │        └──────────────┘
│ total_amount │        │ status       │
│ issue_date   │        │ timestamp    │
│ due_date     │        └──────────────┘
│ status       │
└──────────────┘
```

### Schema DDL (PostgreSQL-compatible)

The full schema is defined via SQLAlchemy ORM in `app/entities.py` and the Alembic migration in `migrations/versions/0001_initial.py`. Key design decisions:

| Table | Key Columns | Notes |
|---|---|---|
| `customers` | `id VARCHAR(36) PK`, `name`, `address`, `phone`, `banking_details`, `role VARCHAR(20)` | Role is one of `customer`, `order_staff`, `accountant` |
| `products` | `id VARCHAR(36) PK`, `description TEXT`, `base_price NUMERIC(12,2)`, `currency VARCHAR(3)` | Currency default is `USD` |
| `orders` | `id VARCHAR(36) PK`, `customer_id FK`, `total_amount NUMERIC(12,2)`, `status VARCHAR(20)`, `invoice_id VARCHAR(36)`, `created_at`, `updated_at` | Status lifecycle: `pending → accepted → invoiced → paid → verified → shipped → completed` |
| `line_items` | `id INTEGER PK AUTO`, `order_id FK`, `product_id FK`, `quantity INT`, `unit_price NUMERIC(12,2)`, `subtotal NUMERIC(12,2)` | Line items are always loaded eager with orders |
| `invoices` | `id VARCHAR(36) PK`, `order_id FK`, `customer_id FK`, `billing_name`, `billing_address TEXT`, `total_amount NUMERIC(12,2)`, `issue_date`, `due_date`, `status VARCHAR(20)` | Status: `draft → issued → paid → overdue → cancelled` |
| `payments` | `id VARCHAR(36) PK`, `order_id FK`, `invoice_id FK`, `amount NUMERIC(12,2)`, `method VARCHAR(20)`, `status VARCHAR(20)`, `timestamp` | Status: `pending → completed → failed → refunded` |

### Concurrency & Isolation

- SQLite uses **WAL (Write-Ahead Logging)** mode for concurrent reads with single-writer access
- PostgreSQL supports **full MVCC** with configurable pool sizes (default 20 connections)
- All status transitions are **atomic** within a single database transaction
- The `get_db()` dependency ensures **commit-or-rollback** semantics for every request

---

## 5. Domain Model

The shared domain models live in `app/domain/models.py` and are used by both the API layer (request/response schemas) and internal service logic. They are pure Pydantic models with no ORM dependencies.

### Enums

```python
class OrderStatus(str, enum.Enum):
    PENDING = "pending"     # Customer placed
    ACCEPTED = "accepted"   # Order staff reviewed & accepted
    INVOICED = "invoiced"   # Accountant created invoice
    PAID = "paid"           # Customer paid
    VERIFIED = "verified"   # Accountant verified payment
    SHIPPED = "shipped"     # Order staff shipped
    COMPLETED = "completed" # Order staff closed

class PaymentMethod(str, enum.Enum):
    CREDIT_CARD, DEBIT_CARD, BANK_TRANSFER, DIGITAL_WALLET

class PaymentStatus(str, enum.Enum):
    PENDING, COMPLETED, FAILED, REFUNDED

class InvoiceStatus(str, enum.Enum):
    DRAFT, ISSUED, PAID, OVERDUE, CANCELLED

class UserRole(str, enum.Enum):
    CUSTOMER, ORDER_STAFF, ACCOUNTANT
```

### Core Models

| Model | Key Fields | Description |
|---|---|---|
| `Customer` | `id`, `name`, `address`, `phone`, `banking_details`, `order_history`, `role` | Represents any user in the system |
| `Product` | `id`, `description`, `base_price`, `currency` | A sellable item |
| `LineItem` | `product_id`, `quantity`, `unit_price`, `subtotal` | A single line within an order |
| `Order` | `id`, `customer_id`, `line_items`, `total_amount`, `status`, `invoice_id`, `created_at`, `updated_at` | The core aggregate root |
| `Payment` | `id`, `order_id`, `invoice_id`, `amount`, `method`, `status`, `timestamp` | A payment record |
| `Invoice` | `id`, `order_id`, `customer_id`, `billing_name`, `billing_address`, `total_amount`, `issue_date`, `due_date`, `status` | Billing document |

---

## 6. API Reference

All endpoints are versioned under `/v1/` and produce/consume JSON. The full OpenAPI specification is available at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Raw JSON:** `http://localhost:8000/openapi.json`

### 6.1 Health Check

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns system health, version, and current queue size |

### 6.2 Customers

| Method | Path | Description | Role |
|---|---|---|---|
| `POST` | `/v1/customers` | Create a new customer | Any |
| `GET` | `/v1/customers` | List all customers | Any |
| `GET` | `/v1/customers/{id}` | Get customer by ID | Any |

### 6.3 Products

| Method | Path | Description | Role |
|---|---|---|---|
| `POST` | `/v1/products` | Create a new product | Any |
| `GET` | `/v1/products` | List all products | Any |
| `GET` | `/v1/products/{id}` | Get product by ID | Any |

### 6.4 Orders (Workflow Steps 1→2→6→7)

| Method | Path | Description | Step | Role |
|---|---|---|---|---|
| `POST` | `/v1/orders` | Place a new order | 1 | Customer |
| `GET` | `/v1/orders` | List orders (optional `?status=` filter) | — | Any |
| `GET` | `/v1/orders/{id}` | Get order details with line items | — | Any |
| `POST` | `/v1/orders/{id}/accept` | Order Staff accepts the order | 2 | Order Staff |
| `POST` | `/v1/orders/{id}/ship` | Ship a paid/verified order | 6 | Order Staff |
| `POST` | `/v1/orders/{id}/close` | Close a shipped order | 7 | Order Staff |

### 6.5 Invoices (Workflow Steps 3→4)

| Method | Path | Description | Step | Role |
|---|---|---|---|---|
| `POST` | `/v1/invoices` | Create invoice for accepted order | 3 | Accountant |
| `GET` | `/v1/invoices` | List all invoices | — | Any |
| `GET` | `/v1/invoices/{id}` | Get invoice by ID | — | Any |
| `POST` | `/v1/invoices/{id}/pay` | Pay an invoice | 4 | Customer |

### 6.6 Payments (Workflow Steps 4→5)

| Method | Path | Description | Step | Role |
|---|---|---|---|---|
| `POST` | `/v1/payments` | Create a payment record | 4 | Customer |
| `GET` | `/v1/payments` | List all payments | — | Any |
| `GET` | `/v1/payments/{id}` | Get payment by ID | — | Any |
| `POST` | `/v1/payments/{id}/complete` | Verify and complete a payment | 5 | Accountant |

### Complete Workflow API Flow

```
Step 1:  POST /v1/orders                         → 201 (order: pending)
Step 2:  POST /v1/orders/{id}/accept              → 200 (order: accepted)
Step 3:  POST /v1/invoices                        → 201 (order: invoiced)
Step 4a: POST /v1/payments                        → 201 (payment: pending)
Step 4b: POST /v1/invoices/{id}/pay               → 200 (order: paid)
Step 5:  POST /v1/payments/{id}/complete          → 200 (order: verified)
Step 6:  POST /v1/orders/{id}/ship                → 200 (order: shipped)
Step 7:  POST /v1/orders/{id}/close               → 200 (order: completed)
```

---

## 7. Installation & Environment Setup

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **uv** (fast Python package manager) — install via:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Docker** (optional, for containerized deployment)
- **Make** (optional, for convenience commands)

### Quick Start (Local Development)

```bash
# 1. Clone the repository
git clone <repository-url>
cd oms-backend

# 2. (Optional) Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# 3. Install dependencies using uv
uv sync

# 4. Verify the environment
uv run python -c "import fastapi; print(fastapi.__version__)"

# 5. Run the server (SQLite - single worker)
uv run python -m app

# 6. Open the API docs
# Open http://localhost:8000/docs in your browser
```

### Environment Variables

The application is configured via `.env` file (at project root) or environment variables. A default `.env` is provided:

```ini
# .env — Defaults for local development
DATABASE_URL=sqlite+aiosqlite:///./oms.db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=False
HOST=0.0.0.0
PORT=8000
WORKERS=4
QUEUE_MAX_SIZE=10000
QUEUE_BATCH_SIZE=50
QUEUE_POLL_SECONDS=2.0
LOG_LEVEL=INFO
```

> **Note:** When using SQLite, only 1 worker is used regardless of `WORKERS` setting because SQLite does not support concurrent writes from multiple processes.

---

## 8. Local Development Guide

### 8.1 Starting the Server

```bash
# With default settings (SQLite, single worker)
uv run python -m app

# With custom port
PORT=9000 uv run python -m app

# With PostgreSQL (if running locally)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/oms uv run python -m app

# With hot-reload for development
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8.2 Database Migrations

The project uses **Alembic** for schema migrations.

```bash
# Generate a new migration (after modifying entities.py)
uv run alembic revision --autogenerate -m "description_of_change"

# Apply pending migrations
uv run alembic upgrade head

# Roll back the last migration
uv run alembic downgrade -1

# View migration history
uv run alembic history
```

For development convenience, tables are auto-created on startup via `app/init_db.py`. In production, disable auto-create and rely on Alembic migrations.

### 8.3 Running the Complete Workflow (Manual Test)

Use `curl` or the Swagger UI at `http://localhost:8000/docs`:

```bash
# 1. Create a customer
curl -s -X POST http://localhost:8000/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","address":"123 Elm St","phone":"+1-555-0100","banking_details":"Bank acct 12345","role":"customer"}' | jq .

# 2. Create a product
curl -s -X POST http://localhost:8000/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Widget A","base_price":"29.99","currency":"USD"}' | jq .

# Save returned IDs as CUSTOMER_ID, PRODUCT_ID, etc.

# 3. Place an order
curl -s -X POST http://localhost:8000/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"line_items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":3,\"unit_price\":\"29.99\",\"subtotal\":\"89.97\"}]}" | jq .

# 4. Accept the order
curl -s -X POST http://localhost:8000/v1/orders/$ORDER_ID/accept | jq .

# 5. Create an invoice
curl -s -X POST http://localhost:8000/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"customer_id\":\"$CUSTOMER_ID\",\"billing_name\":\"Alice Johnson\",\"billing_address\":\"123 Elm St\",\"total_amount\":\"89.97\",\"due_days\":30}" | jq .

# 6. Create a payment
curl -s -X POST http://localhost:8000/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"invoice_id\":\"$INVOICE_ID\",\"amount\":\"89.97\",\"method\":\"credit_card\"}" | jq .

# 7. Pay the invoice
curl -s -X POST http://localhost:8000/v1/invoices/$INVOICE_ID/pay | jq .

# 8. Verify payment
curl -s -X POST http://localhost:8000/v1/payments/$PAYMENT_ID/complete | jq .

# 9. Ship the order
curl -s -X POST http://localhost:8000/v1/orders/$ORDER_ID/ship | jq .

# 10. Close the order
curl -s -X POST http://localhost:8000/v1/orders/$ORDER_ID/close | jq .
```

### 8.4 Project Structure

```
oms-backend/
├── app/
│   ├── __init__.py
│   ├── __main__.py          # Entry point (uv run python -m app)
│   ├── main.py              # FastAPI app, middleware, router registration
│   ├── config.py            # Pydantic Settings (NFR 2.3)
│   ├── database.py          # Async engine, session factory, get_db dependency
│   ├── entities.py          # SQLAlchemy ORM entities (CustomerEntity, OrderEntity, etc.)
│   ├── init_db.py           # Auto-create tables (dev convenience)
│   ├── domain/
│   │   ├── __init__.py      # Re-exports all domain models
│   │   └── models.py        # Pydantic domain models + enums (shared FE/BE)
│   ├── repositories/
│   │   ├── base.py          # BaseRepository<T> with generic CRUD
│   │   ├── customer_repo.py
│   │   ├── order_repo.py    # includes update_status, save_line_items
│   │   ├── invoice_repo.py  # selectinload eager loading
│   │   ├── payment_repo.py
│   │   └── product_repo.py
│   ├── services/
│   │   ├── customer_service.py
│   │   ├── order_service.py     # place, accept, ship, close, mark_*
│   │   ├── invoice_service.py   # create, get, mark_paid
│   │   ├── payment_service.py   # create, complete
│   │   └── workflow_service.py  # Orchestrator for the 7-step lifecycle
│   ├── routers/
│   │   └── v1/
│   │       ├── customer_router.py
│   │       ├── order_router.py      # POST /v1/orders, /accept, /ship, /close
│   │       ├── invoice_router.py    # POST /v1/invoices, /pay
│   │       ├── payment_router.py    # POST /v1/payments, /complete
│   │       └── product_router.py
│   └── middleware/
│       ├── queue_manager.py     # Async bounded queue (NFR 1.3)
│       └── rate_limiter.py      # Sliding-window rate limiter (NFR 1.1)
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Fixtures: client, db_session, sample_customer, etc.
│   └── test_workflow.py        # Full 7-step workflow + API unit tests
├── migrations/
│   ├── env.py                  # Alembic async environment
│   ├── script.py.mako          # Migration template
│   └── versions/
│       └── 0001_initial.py     # Initial schema migration
├── deployment/
│   ├── Dockerfile              # Multi-stage Docker build
│   └── docker-compose.yml      # OMS + PostgreSQL
├── .env                        # Environment configuration
├── pyproject.toml              # Project metadata & dependencies
├── alembic.ini                 # Alembic configuration
└── manual.md                   # This document
```

---

## 9. Deployment Guide (Docker / Production)

### 9.1 Docker Compose (Recommended for Production)

The `deployment/docker-compose.yml` runs the OMS backend with PostgreSQL:

```bash
# Start the application stack
cd deployment
docker compose up --build -d

# Check logs
docker compose logs -f oms-backend

# Verify health
curl http://localhost:8000/health

# Apply database migrations
docker compose exec oms-backend alembic upgrade head

# Stop the stack
docker compose down

# Stop and remove volumes (data loss!)
docker compose down -v
```

### 9.2 Docker Compose Configuration

| Service | Image | Ports | Resources |
|---|---|---|---|
| `oms-backend` | Built from `deployment/Dockerfile` | `8000:8000` | CPU: 4 cores, RAM: 4GB |
| `db` | `postgres:16-alpine` | `5432:5432` | CPU: 2 cores, RAM: 2GB |

### 9.3 Manual Docker Build

```bash
# Build the image
docker build -f deployment/Dockerfile -t oms-backend:latest .

# Run with SQLite (single worker)
docker run -p 8000:8000 oms-backend:latest

# Run with PostgreSQL
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://oms:oms_password@host.docker.internal:5432/oms \
  -e WORKERS=4 \
  oms-backend:latest
```

### 9.4 Production Checklist

- [ ] Set `DATABASE_URL` to PostgreSQL (not SQLite)
- [ ] Set `WORKERS=4` or higher (up to `2*CPU_CORES+1`)
- [ ] Configure `DATABASE_POOL_SIZE` based on `WORKERS * 5` (e.g., 20 for 4 workers)
- [ ] Run Alembic migrations on deploy: `alembic upgrade head`
- [ ] Set `DATABASE_ECHO=False` (disable SQL logging in production)
- [ ] Configure reverse proxy (nginx/Caddy) with TLS termination
- [ ] Set up monitoring: health check endpoint at `/health`
- [ ] Adjust `QUEUE_MAX_SIZE` based on expected peak traffic
- [ ] Consider rate limiter tuning: `max_requests` might need adjustment based on expected API usage

---

## 10. Running Tests

### 10.1 Running All Tests

```bash
# Run all tests with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest -v --cov=app --cov-report=term-missing

# Run a specific test class
uv run pytest -v tests/test_workflow.py::TestWorkflow

# Run a specific test
uv run pytest -v tests/test_workflow.py::TestWorkflow::test_full_workflow
```

### 10.2 Test Architecture

Tests use **in-memory SQLite** (WAL mode) for maximum speed and isolation:

- Each test function gets a **fresh database** (tables created before, dropped after)
- The **ASGI transport** (`httpx.AsyncClient`) calls the FastAPI app directly — no network required
- Test fixtures create reusable entities: `sample_customer`, `sample_product`, `sample_order`

### 10.3 Test Coverage

The test suite covers:

| Test | Description |
|---|---|
| `test_full_workflow` | Complete 7-step lifecycle end-to-end |
| `test_health_check` | Health endpoint returns correct status |
| `test_create_customer` | Customer creation with role validation |
| `test_get_customer_not_found` | 404 for non-existent customer |
| `test_create_product` | Product creation with pricing |
| `test_list_products` | Product listing |
| `test_place_order_invalid_customer` | 400 for non-existent customer |
| Additional tests | Order acceptance, payment, invoice workflows |

---

## 11. Verification Steps (NFR Observability)

### 11.1 NFR 1.1 — Response Time Under Load

```bash
# Verify rate limiter is active
for i in $(seq 1 201); do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/v1/products
done
# After ~200 requests, should see 429 responses

# Measure response times
time curl -s http://localhost:8000/v1/orders
# Expect sub-100ms for cached/light endpoints
```

### 11.2 NFR 1.2 — Concurrency & Resource Utilization

```bash
# Configure connection pool
export DATABASE_POOL_SIZE=50
uv run python -m app &

# In another terminal, check connection usage (PostgreSQL)
docker compose exec db psql -U oms -c "SELECT count(*) FROM pg_stat_activity WHERE datname='oms';"

# For SQLite, check WAL mode
sqlite3 oms.db "PRAGMA journal_mode;"
# Should return "wal"
```

### 11.3 NFR 1.3 — Queue Management (Spike Absorption)

```bash
# Send rapid requests to trigger queue overflow
for i in $(seq 1 50); do
  curl -s -X POST http://localhost:8000/v1/orders \
    -H "Content-Type: application/json" \
    -d "{\"customer_id\":\"$CUSTOMER_ID\",\"line_items\":[]}" &
done

# Check logs for queue warnings
# Look for: "Queue full (>10000). Rejecting task" or "Queue size" in logs

# Verify health endpoint shows queue size
curl -s http://localhost:8000/health | jq .queue_size
```

### 11.4 NFR 2.1 — Localization of Changes

```bash
# Demonstrate domain boundaries
# If you add a field to Order domain model:
# 1. Only app/domain/models.py changes (model)
# 2. Only app/entities.py changes (ORM mapping)
# 3. Only app/repositories/order_repo.py might change (if query logic changes)
# 4. No changes needed in customer or payment modules

# Verify with a simple grep
grep -r "domain.models.Order" app/ --include="*.py"
# Should only show: services/order_service.py, services/workflow_service.py, routers/v1/order_router.py
```

### 11.5 NFR 2.2 — Interface Stability

```bash
# Verify versioned paths
curl -s http://localhost:8000/v1/products | jq .
# Old v1 endpoints continue to work even after adding v2

# OpenAPI spec is auto-generated
curl -s http://localhost:8000/openapi.json | jq '.info.version'
# Returns "1.0.0"

# Add a new optional field to a model - existing consumers still work
# (Pydantic's extra="ignore" by default for response models)
```

### 11.6 NFR 2.3 — Deferred Binding

```bash
# Change configuration without code changes
export QUEUE_MAX_SIZE=50000
export LOG_LEVEL=DEBUG
uv run python -m app &

# Verify new values in effect
curl -s http://localhost:8000/health | jq .
# LOG_LEVEL=DEBUG shows detailed SQL queries in console
```

---

## 12. Configuration Reference

### Complete Configuration Options

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./oms.db` | Database connection string. Use `postgresql+asyncpg://user:pass@host:5432/db` for production |
| `DATABASE_POOL_SIZE` | `20` | Maximum persistent connections in pool |
| `DATABASE_MAX_OVERFLOW` | `10` | Extra connections allowed above pool_size during spikes |
| `DATABASE_ECHO` | `False` | If `True`, log all SQL statements |
| `HOST` | `0.0.0.0` | Bind address for uvicorn |
| `PORT` | `8000` | Port for uvicorn |
| `WORKERS` | `4` | Number of uvicorn workers (overridden to 1 for SQLite) |
| `QUEUE_MAX_SIZE` | `10000` | Maximum items in async task queue before rejecting |
| `QUEUE_BATCH_SIZE` | `50` | Number of tasks processed together by background worker |
| `QUEUE_POLL_SECONDS` | `2.0` | Seconds the worker waits when queue is empty |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Rate Limiter Configuration

The rate limiter is configured in `app/main.py`:

```python
app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)
```

- **`max_requests`**: Maximum requests per IP within the window (default: 200)
- **`window_seconds`**: Sliding window duration in seconds (default: 60)

---

## Appendix A: Troubleshooting

| Problem | Solution |
|---|---|
| `sqlite3.OperationalError: database is locked` | Use single worker (`WORKERS=1`) with SQLite, or switch to PostgreSQL |
| `MissingGreenletError` when accessing relationships | Ensure repository queries use `selectinload()` for all relationships |
| Port 8000 already in use | Change port: `PORT=8001 uv run python -m app` |
| `asyncpg.exceptions.InvalidPasswordError` | Check PostgreSQL credentials in `DATABASE_URL` |
| Tests failing with database lock | Tests use in-memory SQLite; ensure no other process locks the test DB |
| Queue tasks not processing | Check logs for queue worker errors; ensure `queue_manager.start()` was called (it is on startup) |

## Appendix B: Quick Reference Commands

```bash
# Start server
uv run python -m app

# Run tests
uv run pytest -v

# Apply migrations
uv run alembic upgrade head

# Create migration
uv run alembic revision --autogenerate -m "description"

# Build Docker
docker compose -f deployment/docker-compose.yml up --build -d

# Health check
curl http://localhost:8000/health
```

---

© 2025 ChatDev — Order Management System v1.0.0