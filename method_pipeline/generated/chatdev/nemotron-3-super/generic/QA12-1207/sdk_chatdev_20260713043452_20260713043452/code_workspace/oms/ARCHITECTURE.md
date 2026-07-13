# Architecture Documentation

## Architectural Decision Records (ADRs)

### ADR 1: Choice of Framework
**Decision:** Use FastAPI for the web framework.
**Context:** Need for high performance, async support, and automatic API documentation.
**Alternatives Considered:** 
- Django REST Framework: Rejected due to synchronous nature and heavier weight.
- Flask: Rejected due to lack of built-in async support and automatic validation.
**Consequences:** 
- Pros: High performance, automatic OpenAPI docs, dependency injection.
- Cons: Smaller community than Django, newer ecosystem.

### ADR 2: Database Choice
**Decision:** Use SQLite with aiosqlite for development, PostgreSQL for production.
**Context:** Need for a simple setup for local development and a robust production database.
**Alternatives Considered:** 
- MongoDB: Rejected because relational model fits the domain better.
- MySQL: Rejected due to slightly higher complexity than PostgreSQL for our needs.
**Consequences:** 
- Pros: SQLite is file-based and zero-config for dev; PostgreSQL is robust and feature-rich for prod.
- Cons: Need to manage two different environments; asyncpg driver for PostgreSQL adds complexity.

### ADR 3: Architecture Pattern
**Decision:** Use a layered architecture with separation of concerns: API, Service, Repository, Model.
**Context:** Need for maintainability, testability, and clear separation of business logic.
**Alternatives Considered:** 
- MVC: Rejected because it mixes controller and view logic, which is not ideal for APIs.
- Hexagonal Architecture: Rejected as overkill for this service's size.
**Consequences:** 
- Pros: Clear separation, easy to test, swap implementations.
- Cons: Slightly more indirection.

## NFR Traceability Matrix

| NFR | Architectural Mechanism | Component | Verification Method |
|-----|-------------------------|-----------|---------------------|
| NFR 1.1: Response Time | Async request handling, connection pooling, efficient DB queries | API layer, Service layer, Database layer | Load testing with tools like Locust or k6; monitor response times under load |
| NFR 1.2: Concurrency & Resource Utilization | Async/await throughout, async database driver, connection pooling | All layers | Stress test to verify high concurrency with low resource saturation |
| NFR 1.3: Queue Management | Use of async queues (e.g., Redis) for background tasks (not implemented in MVP but designed for extension) | Service layer | Simulate traffic spikes and verify system remains responsive |
| NFR 2.1: Graceful Degradation | Feature toggles, circuit breakers (planned for payment/gateway integration) | Service layer | Simulate failure of external services (e.g., payment gateway) and verify core ordering still works |
| NFR 2.2: Fault Detection & Recovery | Database connection retries, health checks, logging | Database layer, API layer | Kill database connection and verify reconnection; check logs for retry attempts |
| NFR 2.3: State Preservation | ACID transactions, database persistence, idempotent operations | Repository layer, Service layer | Crash simulator (e.g., kill -9) and restart; verify no data loss and pending orders can be resumed |

## Data Architecture

### Domain Model

- **Customer:** id, name, address, phone, banking_details, role, created_at, updated_at, orders (one-to-many)
- **Product:** id, description, base_price, currency, created_at, updated_at
- **Order:** id, customer_id, status (enum), total_amount, created_at, updated_at, items (one-to-many), payment (one-to-one), invoice (one-to-one)
- **OrderItem:** id, order_id, product_id, quantity, unit_price, total_price, created_at
- **Payment:** id, order_id, amount, method (enum), status (enum), transaction_id, created_at, updated_at
- **Invoice:** id, order_id, billing_name, billing_address, billing_email, billing_phone, amount, issue_date, due_date, status (enum), created_at, updated_at

### Database Schema

See the SQLAlchemy models in `app/models/` for the exact schema.

## API Design

RESTful API with versioning (`/api/v1/*`). 
Endpoints:
- Customers: POST/GET/PUT/DELETE /customers, GET /customers/{id}
- Products: POST/GET/PUT/DELETE /products, GET /products/{id}
- Orders: POST/GET/PUT/DELETE /orders, GET /orders/{id}
- Payments: POST/GET/PUT/DELETE /payments, GET /payments/{id}
- Invoices: POST/GET/PUT/DELETE /invoices, GET /invoices/{id}

## Deployment

The application is containerized using Docker and can be orchestrated with Docker Compose.
See DEPLOYMENT.md for details.

## Technology Stack

- Language: Python 3.9+
- Web Framework: FastAPI
- ORM: SQLAlchemy 2.0 with async support
- Database: SQLite (dev), PostgreSQL (prod)
- Server: Uvicorn (ASGI)
- API Documentation: Swagger UI (via FastAPI)
- Containerization: Docker, Docker Compose
