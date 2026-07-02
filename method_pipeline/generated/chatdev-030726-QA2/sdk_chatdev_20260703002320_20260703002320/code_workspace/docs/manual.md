# OMS Backend Manual

## Overview
This repository implements a production‑grade **Order Management System (OMS)** backend using **Python**, **FastAPI**, and **SQLModel** (SQLite). It provides REST APIs for the complete order lifecycle:
1. Customer places an order.
2. Order staff reviews \u0026 accepts the order.
3. Accountant creates an invoice.
4. Customer pays the invoice.
5. Accountant verifies the payment.
6. Order staff ships the order.
7. Order staff closes the order.

The system is designed with domain‑driven boundaries, stable OpenAPI contracts, and runtime‑configurable settings.

---

## Repository Structure
```
.
├─ app/                     # Application package
│   ├─ __init__.py
│   ├─ main.py              # FastAPI entry point
│   ├─ db.py                # Database (SQLModel + SQLite)
│   ├─ config/              # Configuration handling
│   │   └─ settings.py
│   ├─ models/              # Domain models (SQLModel)
│   ├─ schemas/             # Pydantic request/response schemas
│   ├─ repositories/        # Data‑access layer (CRUD helpers)
│   ├─ services/            # Business logic (transaction boundaries)
│   └─ controllers/         # REST controllers (FastAPI routers)
├─ docs/                    # Documentation
│   ├─ adr/                 # Architectural Decision Records
│   ├─ nfr_traceability.md  # NFR traceability matrix
│   └─ manual.md            # **THIS FILE**
├─ Dockerfile                # Container image definition
├─ docker-compose.yml        # Local multi‑container dev (optional)
├─ pom.xml                   # Legacy placeholder (unused)
├─ pyproject.toml            # Poetry/uv project definition
└─ run.py                    # Helper script to start the server with uv
```

---

## Prerequisites
- **Python 3.12+** (the project uses `uv` for dependency management).
- **Git** (to clone the repo).
- **Docker** (optional, for containerised deployment).

---

## Installation \u0026 Development Setup
### 1. Clone the repository
```bash
git clone <repository-url>
cd <repo-directory>
```
### 2. Initialise the Python environment (using `uv`)
```bash
uv venv          # creates a virtual environment in .venv
source .venv/bin/activate
uv sync          # installs exact versions from uv.lock
```
> **Tip:** The `uv.lock` file guarantees reproducible builds.

### 3. Database migration (first run only)
The application uses SQLite (`oms.db`). The schema is auto‑created on first start. If you need to reset:
```bash
rm oms.db   # delete the file
```
The next launch will recreate the tables.

### 4. Run the server locally
```bash
uv run python -m app.main
```
The API will be available at **http://127.0.0.1:8000**.

### 5. (Optional) Run via Docker
```bash
docker build -t oms-backend .
docker run -p 8000:8000 oms-backend
```
---

## Configuration (NFR 2.3 – Deferred Binding)
All runtime options live in **`app/config/settings.py`** and can be overridden via environment variables:
| Variable | Description | Default |
|---|---|---|
| `APP_HOST` | Host address for FastAPI | `0.0.0.0` |
| `APP_PORT` | Port number | `8000` |
| `DATABASE_URL` | SQLite DSN (e.g., `sqlite:///oms.db`) | `sqlite:///oms.db` |
| `LOG_LEVEL` | Logging verbosity (`debug`, `info`, `warning`, `error`) | `info` |

Example override:
```bash
export APP_PORT=8080
uv run python -m app.main
```
---

## API Overview (Stable Contracts – NFR 2.2)
The OpenAPI spec is generated automatically and served at **`/docs`** (Swagger UI) and **`/redoc`**.
All endpoints are versioned under **`/api/v1`**.

### 1. Customer
- `POST /api/v1/customers/` – Create a new customer.
- `GET /api/v1/customers/{customer_id}` – Retrieve a customer.
- `GET /api/v1/customers/` – List customers.

### 2. Product
- `POST /api/v1/products/` – Add a product.
- `GET /api/v1/products/{product_id}` – Get product details.
- `GET /api/v1/products/` – List products.

### 3. Order
- `POST /api/v1/orders/` – Place a new order (customer only).
- `PATCH /api/v1/orders/{order_id}/status` – Update order status (staff).
- `GET /api/v1/orders/{order_id}` – Retrieve order with line items.
- `GET /api/v1/orders/` – List orders (filterable by status).

### 4. Invoice
- `POST /api/v1/invoices/` – Create invoice for an accepted order (accountant).
- `GET /api/v1/invoices/{invoice_id}` – Retrieve invoice.
- `PATCH /api/v1/invoices/{invoice_id}/status` – Mark invoice as paid/verified.

### 5. Payment
- `POST /api/v1/payments/` – Record a payment against an invoice.
- `GET /api/v1/payments/{payment_id}` – Get payment details.

All request/response bodies are defined in **`app/schemas/`** and are version‑stable; adding new fields is done with `Optional` types to avoid breaking existing clients.
---

## Running Tests (Optional)
The project ships with a small test suite using **pytest**.
```bash
pip install pytest
pytest
```
---

## Deployment Guide (Production)
1. **Containerise** – Build the Docker image (see Dockerfile). Push to your registry.
2. **Configure** – Provide environment variables via your orchestrator (K8s, Docker‑Compose, etc.).
3. **Scale** – The service is stateless aside from the SQLite file; for horizontal scaling use a shared DB (PostgreSQL) – update `DATABASE_URL` accordingly.
4. **Monitoring** – Logs are emitted in JSON format; integrate with your log aggregator.
5. **Health Checks** – FastAPI automatically exposes `/health` (returns `200 OK`). Configure your platform to poll this endpoint.
---

## Verifying Non‑Functional Requirements
| NFR | Mechanism | Module | Verification |
|-----|-----------|--------|--------------|
| **2.1 Localization of Changes** | Domain‑driven package layout (`models`, `schemas`, `services`, `controllers`) with clear boundaries. | Entire `app/` package | Add a new domain entity (e.g., `Shipment`) – only new files under its own sub‑package should be required.
| **2.2 Interface Stability** | Versioned OpenAPI (`/api/v1`) and Pydantic schemas with optional fields. | `app/controllers/*`, `app/schemas/*` | Generate the OpenAPI spec (`curl http://localhost:8000/openapi.json`) and diff against a previously stored version – no breaking changes.
| **2.3 Deferred Binding** | Config via `app/config/settings.py` with environment variable overrides; no code restart needed for env changes. | `app/config/settings.py` | Change `LOG_LEVEL` at runtime (`export LOG_LEVEL=debug`) and observe log verbosity without recompiling.
---

## Frequently Asked Questions
**Q:** *Can I switch to PostgreSQL?*  
**A:** Yes. Set `DATABASE_URL=postgresql+psycopg2://user:pass@host/dbname` and ensure the driver is installed (`uv add psycopg2-binary`). The rest of the code works unchanged because it uses SQLModel’s generic engine.

**Q:** *How do I add a new role?*  
**A:** Extend the `role` field in `app/models/customer.py` (enum) and update any role‑based checks in services. No controller changes are required.
---

## Contact \u0026 Support
For issues, open a GitHub issue or contact the development team at **dev@chatdev.io**.

*End of manual.*