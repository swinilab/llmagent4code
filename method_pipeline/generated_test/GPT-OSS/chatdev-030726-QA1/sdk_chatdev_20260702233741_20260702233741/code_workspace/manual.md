# Order Management System (OMS) – User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [Key Features](#key-features)
3. [System Architecture Overview](#system-architecture-overview)
4. [Prerequisites](#prerequisites)
5. [Installation \& Setup](#installation--setup)
   - [Option A: Docker Compose (Recommended)](#option-a-docker-compose-recommended)
   - [Option B: Local Python Environment](#option-b-local-python-environment)
6. [Running the Application](#running-the-application)
   - [Starting Services with Docker](#starting-services-with-docker)
   - [Running FastAPI Directly](#running-fastapi-directly)
   - [Starting Celery Workers](#starting-celery-workers)
7. [API Reference](#api-reference)
   - [Versioning](#versioning)
   - [Endpoints Overview](#endpoints-overview)
   - [Example Requests (cURL)](#example-requests-curl)
8. [Testing \& Verification](#testing--verification)
   - [Functional Tests](#functional-tests)
   - [Non‑Functional Requirements Validation](#non‑functional-requirements-validation)
9. [Database Initialization](#database-initialization)
10. [Troubleshooting](#troubleshooting)
11. [Further Development](#further-development)

---

## Introduction
The **Order Management System (OMS)** is a production‑grade, backend‑only e‑commerce service that manages the complete order lifecycle:
1. Customer places an order
2. Order staff reviews \& accepts the order
3. Accountant creates an invoice
4. Customer pays the invoice
5. Accountant verifies the payment
6. Order staff ships the order
7. Order staff closes the completed order

The system is built with **FastAPI**, **SQLAlchemy**, **PostgreSQL**, and **Celery + Redis** for asynchronous processing. No authentication is required, matching the original specification.

## Key Features
- Fully asynchronous HTTP endpoints for low latency (NFR 1.1).
- Robust transaction handling with PostgreSQL (NFR 1.2).
- Scalable task queue (Celery + Redis) to absorb traffic spikes (NFR 1.3).
- OpenAPI documentation automatically generated at `/api/v1/docs`.
- Docker‑Compose based production‑like environment for easy local deployment.

## System Architecture Overview
```
+----------------+      +----------------+      +----------------+
|   FastAPI      | <--- | PostgreSQL DB  | <--- | SQLAlchemy ORM |
| (Uvicorn ASGI) |      | (Transactional)|      +----------------+
+----------------+      +----------------+                |
        |                     ^                       |
        |                     |                       |
        v                     |                       v
+----------------+      +----------------+      +----------------+
|   Redis        | <---| Celery Workers | ---> | Async Tasks    |
+----------------+      +----------------+      +----------------+
```
- **FastAPI** serves versioned REST APIs under `/api/v1`.
- **SQLAlchemy** maps the domain models (`Customer`, `Product`, `Order`, `Invoice`, `Payment`, `OrderLineItem`).
- **Celery** processes heavy/slow operations such as payment verification and shipping notifications, buffering spikes.
- **Docker Compose** orchestrates all containers (`api`, `db`, `redis`, `worker`).

## Prerequisites
| Tool | Minimum Version |
|------|-----------------|
| Docker \& Docker‑Compose | 20.10 |
| Python | 3.11 (only required for **Option B**) |
| Git (optional) | any |

## Installation \& Setup
### Option A: Docker Compose (Recommended)
1. Clone the repository (already present in the workspace).
2. Build and start the stack:
   ```bash
   docker-compose up --build -d
   ```
   This will launch:
   - `api` – FastAPI application (exposed on port **8000**)
   - `db` – PostgreSQL (default port **5432**, user `postgres`, password `postgres`)
   - `redis` – Redis broker for Celery (port **6379**)
   - `worker` – Celery worker processing background tasks
3. Verify containers are healthy:
   ```bash
   docker ps
   ```
### Option B: Local Python Environment
If you prefer to run without Docker:
1. **Create a virtual environment** (using `uv` which is already vendored):
   ```bash
   uv venv
   source .venv/bin/activate
   ```
2. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```
3. **Start supporting services** (PostgreSQL \& Redis) – you can use local installations or Docker for just those two services.
4. **Run the API** (hot‑reload):
   ```bash
   uvicorn app.main:app --reload
   ```
5. **Start a Celery worker** in another terminal:
   ```bash
   celery -A app.queue.celery_app worker --loglevel=info
   ```

## Running the Application
### Starting Services with Docker
```bash
# Build and start all services in detached mode
docker-compose up --build -d

# Tail logs (optional)
docker-compose logs -f api worker
```
### Running FastAPI Directly (local dev)
```bash
uvicorn app.main:app --reload
```
The API will be reachable at `http://localhost:8000`.
### Starting Celery Workers
```bash
# In the project root (same virtual env as the API)
celery -A app.queue.celery_app worker --loglevel=info
```
You can scale workers by launching additional processes or using `docker-compose up --scale worker=3`.

## API Reference
### Versioning
All endpoints are prefixed with **`/api/v1`**. Future versions can be added as `/api/v2`, etc.
### Endpoints Overview
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/customers` | Create a new customer |
| `GET`  | `/api/v1/customers/{id}` | Retrieve a customer |
| `POST` | `/api/v1/products` | Add a product |
| `GET`  | `/api/v1/products` | List all products |
| `POST` | `/api/v1/orders` | Place a new order |
| `POST` | `/api/v1/orders/{order_id}/accept` | Staff accepts order |
| `POST` | `/api/v1/orders/{order_id}/invoice` | Accountant creates invoice |
| `POST` | `/api/v1/payments` | Record a payment |
| `POST` | `/api/v1/payments/{payment_id}/verify` | Verify payment (async) |
| `POST` | `/api/v1/orders/{order_id}/ship` | Ship the order |
| `POST` | `/api/v1/orders/{order_id}/close` | Close the order |

The OpenAPI UI is available at `http://localhost:8000/api/v1/docs`.
### Example Requests (cURL)
```bash
# 1️⃣ Create a customer
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","address":"123 Main St","phone":"555-1234","banking_details":"DE89 3704 0044 0532 0130 00"}'

# 2️⃣ Add a product
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"description":"Widget","price":19.99,"currency":"USD"}'

# 3️⃣ Place an order (using IDs from previous steps)
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id":1,"line_items":[{"product_id":1,"quantity":2}]}'

# 4️⃣ Accept the order (order staff)
curl -X POST http://localhost:8000/api/v1/orders/1/accept

# 5️⃣ Create invoice (accountant)
curl -X POST http://localhost:8000/api/v1/orders/1/invoice

# 6️⃣ Record payment (customer)
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{"order_id":1,"amount":39.98,"method":"credit_card"}'

# 7️⃣ Verify payment (async task)
curl -X POST http://localhost:8000/api/v1/payments/1/verify

# 8️⃣ Ship order (order staff)
curl -X POST http://localhost:8000/api/v1/orders/1/ship

# 9️⃣ Close order (order staff)
curl -X POST http://localhost:8000/api/v1/orders/1/close
```
All responses are JSON objects matching the Pydantic schemas defined in `app/schemas.py`.

## Testing \& Verification
### Functional Tests
The repository contains a **pytest** suite under `tests/` (if not present, you can add one). Run:
```bash
pytest -q
```
All CRUD operations and workflow transitions should pass.
### Non‑Functional Requirements Validation
- **Response Time (NFR 1.1)** – Use a load‑testing tool such as `hey`:
  ```bash
  hey -n 1000 -c 50 http://localhost:8000/api/v1/products
  ```
  Verify the 95th‑percentile latency is below **200 ms** (see `NFR_TRACEABILITY.md`).
- **Concurrency \& Resource Utilization (NFR 1.2)** – Scale the API container:
  ```bash
  docker-compose up --scale api=4 -d
  ```
  Monitor CPU/RAM with `docker stats`. The system should keep CPU < 80 % under load.
- **Queue Management (NFR 1.3)** – Simulate a spike of verification tasks:
  ```bash
  for i in {1..10000}; do curl -s -X POST http://localhost:8000/api/v1/payments/$i/verify & done
  ```
  Observe Redis queue length (`redis-cli LLEN celery`) and ensure the API does not return 5xx errors.

## Database Initialization
After the containers are up, create the schema:
```bash
docker-compose exec api python init_db.py
```
`init_db.py` uses SQLAlchemy metadata to create tables in PostgreSQL.

## Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|---------------|-----|
| `Connection refused` on port 8000 | API container not running | `docker-compose up api` |
| `psycopg2.OperationalError` | DB not ready yet | Wait a few seconds or run `docker-compose exec db pg_isready` |
| Celery task never runs | Redis not reachable or worker not started | Ensure `redis` container is up and `celery -A app.queue.celery_app worker` is running |
| 500 errors on `/orders/{id}/accept` | Order status invalid | Check order lifecycle; use GET `/orders/{id}` to view current status |

## Further Development
- Add **authentication/authorization** (JWT) for production security.
- Implement **event sourcing** for audit logs.
- Replace **Redis** with a more robust broker (e.g., RabbitMQ) for larger scale.
- Add **Docker Swarm/Kubernetes** manifests for cloud deployment.
- Expand **OpenAPI** docs with examples and response models.

---
*This manual was generated by the ChatDev Chief Product Officer for the OMS backend.*