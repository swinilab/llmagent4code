# Architectural Decision Records (ADRs)

## ADR 001 – Choose FastAPI + Uvicorn for the web framework
**Decision:** Use FastAPI with Uvicorn as the HTTP server.
**Context:** Need low latency (NFR 1.1) and high concurrency (NFR 1.2). FastAPI provides async support, automatic OpenAPI generation, and excellent performance.
**Alternatives considered:**
- **Spring Boot (Java):** Rejected due to language mismatch with the Python execution environment and longer startup time.
- **Django REST Framework:** Rejected because its synchronous view handling adds overhead and less fine‑grained async control.
**Consequences:** Faster response times, easier integration with async Celery tasks, but requires developers to be comfortable with async Python.

## ADR 002 – Data Persistence with PostgreSQL via SQLAlchemy
**Decision:** Use PostgreSQL as the relational store and SQLAlchemy ORM.
**Context:** Strong consistency, ACID transactions needed for order lifecycle (NFR 1.2).
**Alternatives considered:**
- **MySQL:** Similar capabilities but PostgreSQL offers richer JSON and indexing features useful for future extensions.
- **NoSQL (MongoDB):** Rejected because transactional guarantees across multiple documents are weaker.
**Consequences:** Need to manage migrations (handled via Alembic if extended) and connection pooling; provides reliable durability.

## ADR 003 – Asynchronous processing with Celery + Redis
**Decision:** Introduce Celery workers backed by Redis for queue management.
**Context:** Sudden traffic spikes (NFR 1.3) must not crash the system; heavy tasks like payment verification and shipping notifications should be offloaded.
**Alternatives considered:**
- **RQ (Redis Queue):** Simpler but lacks advanced routing and monitoring features.
- **Kafka + Faust:** Overkill for the current scope and adds operational complexity.
**Consequences:** Additional Redis dependency, but provides robust task queue, retries, and scaling.

## ADR 004 – API Versioning via URL path (`/api/v1`)
**Decision:** Prefix all endpoints with `/api/v1`.
**Context:** Future evolution of the API without breaking existing clients.
**Alternatives considered:**
- **Header‑based versioning:** More complex for clients and tooling.
- **Sub‑domain versioning:** Requires DNS changes and extra infra.
**Consequences:** Simple, explicit versioning; easy to route via FastAPI routers.

## ADR 005 – Containerised deployment with Docker Compose
**Decision:** Package the application, PostgreSQL, and Redis in Docker Compose.
**Context:** Provide a reproducible production‑like environment for local development and CI.
**Alternatives considered:**
- **Kubernetes manifests:** Too heavyweight for local setup.
- **Bare‑metal install scripts:** Harder to guarantee identical environments.
**Consequences:** Requires Docker; simplifies scaling and isolation.
