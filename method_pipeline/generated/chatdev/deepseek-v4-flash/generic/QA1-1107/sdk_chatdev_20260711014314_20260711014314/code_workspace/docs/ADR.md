# Architectural Decision Records (ADR)

## ADR 1: Web Framework — FastAPI (async)

**Decision:** Use FastAPI with async support.

**Context:** NFR 1.1 (Response Time) and NFR 1.2 (Concurrency). Core journeys (product search, cart, checkout) must minimize round-trip latency under load. The system must exploit up to 98GB RAM with minimal queuing.

**Alternatives considered:**
1. **Flask (sync):** Rejected because synchronous I/O blocks worker processes under concurrent load, increasing latency and reducing throughput. Would require additional async wrappers.
2. **Django + Django REST Framework:** Rejected because it is heavier, has more overhead per request, and its synchronous ORM would negate async benefits. Overkill for a focused OMS backend.

**Consequences:**
- Automatic OpenAPI docs generation at `/docs` and `/redoc`.
- Native async support enables high concurrency with fewer workers.
- Smaller community than Django but sufficient for this scope.

---

## ADR 2: ORM — SQLAlchemy 2.0 (async)

**Decision:** Use SQLAlchemy 2.0 with async session support.

**Context:** NFR 1.2 (Concurrency & Resource Utilization). The ORM must support async database access to avoid blocking the event loop.

**Alternatives considered:**
1. **Tortoise-ORM:** Rejected because it is less mature, has fewer integrations, and limited support for complex queries and migrations.
2. **Raw SQL / asyncpg directly:** Rejected because it would require manual migration management, no model validation, and increased development time.

**Consequences:**
- Full type hints with Mapped annotations.
- Alembic for migrations.
- Slightly more verbose than Tortoise but production-proven.

---

## ADR 3: Task Queue — asyncio.Queue (dev) / Celery + Redis (prod)

**Decision:** Use an in-process asyncio.Queue for development and Celery + Redis for production.

**Context:** NFR 1.3 (Queue Management). Sudden traffic spikes must not crash the system. Background tasks (notifications, reports) must be processed asynchronously.

**Alternatives considered:**
1. **Celery only:** Rejected for development because it requires a running Redis/RabbitMQ broker, adding complexity for local setup.
2. **Redis Queue (RQ):** Rejected because it adds an extra dependency (Redis) even for development, and has fewer features than Celery.

**Consequences:**
- Development: lightweight, no external dependencies.
- Production: swap to Celery for persistence, retries, and monitoring.
- Dual implementation requires maintaining two code paths.

---

## ADR 4: Database — SQLite (dev) / PostgreSQL (prod)

**Decision:** Use SQLite with aiosqlite for development, with easy swap to PostgreSQL for production.

**Context:** Local deployment must be simple with zero external dependencies. Production requires ACID compliance and concurrent write support.

**Alternatives considered:**
1. **PostgreSQL for dev:** Rejected because it requires installing and running a database server, increasing setup friction.
2. **MySQL:** Rejected because it has weaker async support in SQLAlchemy and is less common in Python ecosystems.

**Consequences:**
- SQLite has limited concurrency (single writer), but sufficient for dev.
- Connection string change in config enables production swap.
- Alembic migrations work with both.

---

## ADR 5: Validation — Pydantic v2

**Decision:** Use Pydantic v2 for request/response validation.

**Context:** All entities require strict input validation, serialization, and OpenAPI schema generation.

**Alternatives considered:**
1. **Marshmallow:** Rejected because it is slower than Pydantic v2 and requires separate schema definitions.
2. **attrs / dataclasses:** Rejected because they lack built-in validation and OpenAPI integration.

**Consequences:**
- Tight integration with FastAPI for automatic validation and docs.
- Faster than Pydantic v1 and Marshmallow.
- Model config with `from_attributes=True` enables ORM integration.

---

## ADR 6: Rate Limiting — In-Memory Sliding Window

**Decision:** Implement rate limiting via an in-memory sliding window middleware.

**Context:** NFR 1.1 (Response Time) and NFR 1.3 (Queue Management). Must prevent abuse and shed excess load before it reaches the application.

**Alternatives considered:**
1. **Redis-based rate limiter:** Rejected because it adds a dependency for a feature that works in-memory for single-server deployments.
2. **Nginx rate limiting:** Rejected because it shifts the responsibility outside the application and makes testing harder.

**Consequences:**
- Simple, no external dependencies.
- Not shared across multiple server instances (use Redis in multi-instance prod).
- Memory usage scales with number of unique clients.

---

## ADR 7: Layered Architecture — Controller → Service → Repository/ORM

**Decision:** Use a three-layer architecture (Controller, Service, Data) with clear separation of concerns.

**Context:** The system must be maintainable, testable, and allow independent evolution of each layer.

**Alternatives considered:**
1. **Fat controllers (logic in routes):** Rejected because it leads to untestable code and violates Single Responsibility Principle.
2. **Hexagonal architecture (ports/adapters):** Rejected because it adds unnecessary abstraction for this scope.

**Consequences:**
- Controllers handle HTTP concerns only.
- Services contain business logic and transaction boundaries.
- ORM models handle data persistence.
- Easy to unit test services by mocking the database session.

---

## ADR 8: Workflow Orchestration — Dedicated Workflow Layer

**Decision:** Extract cross-service orchestration into a dedicated `OrderWorkflow` class.

**Context:** The 7-step order lifecycle requires coordinated operations across multiple services (Order, Payment, Invoice). Without a dedicated orchestrator, business logic would leak into controllers or services.

**Alternatives considered:**
1. **Orchestration in controllers:** Rejected because it would couple HTTP concerns with business logic, making testing and reuse impossible.
2. **Saga pattern with event bus:** Rejected because it adds infrastructure complexity (message broker) that is unnecessary for a single-service deployment.

**Consequences:**
- Clear separation: controllers handle HTTP, services handle single-entity logic, workflows handle multi-entity orchestration.
- Workflow methods are independently testable.
- Easy to add compensating transactions (rollback logic) in the future.

---

## ADR 9: Immutable Terminal States

**Decision:** Orders in CLOSED or CANCELLED status are immutable — no field modifications allowed.

**Context:** Financial data integrity requires that once an order reaches a terminal state, its data cannot be altered. This prevents accounting discrepancies and audit trail corruption.

**Alternatives considered:**
1. **Allow modifications with audit log:** Rejected because it complicates the data model and still allows data corruption.
2. **Soft delete with versioning:** Rejected because it adds complexity without clear benefit for this domain.

**Consequences:**
- Strong data integrity guarantees for financial records.
- Controllers return 400 Bad Request if a terminal-state update is attempted.
- Future enhancement: add a "reopen" workflow with explicit authorization.

---

## ADR 10: Duplicate Prevention at Service Layer

**Decision:** Prevent duplicate invoices and duplicate payment submissions at the service layer.

**Context:** The 7-step workflow must enforce that each order has exactly one invoice and one payment flow. Duplicate invoices or payments would cause financial inconsistencies.

**Alternatives considered:**
1. **Database unique constraints:** Rejected because they are database-specific and harder to provide clear error messages.
2. **Application-level idempotency keys:** Rejected because they add client-side complexity and are unnecessary for this scope.

**Consequences:**
- `InvoiceService.create` checks for existing invoices before creating.
- `OrderWorkflow.pay_invoice` checks for pending payments before creating.
- Clear error messages returned to the client.
- Additional database-level unique constraints can be added for defense in depth.
