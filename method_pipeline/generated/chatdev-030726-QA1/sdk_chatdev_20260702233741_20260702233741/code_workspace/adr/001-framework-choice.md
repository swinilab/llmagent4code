# ADR 001 – Framework Choice

**Decision**: Use Python FastAPI as the primary backend framework.

**Context**: NFR 1.1 (Response Time), NFR 1.2 (Concurrency & Resource Utilization).

**Alternatives considered**:
1. **Node.js with Express** – Rejected due to less mature ecosystem for data modeling and limited built‑in async task handling compared to Celery.
2. **Java Spring Boot** – Rejected because the project specifications now target a Python stack and FastAPI offers lower latency and simpler deployment.

**Consequences**:
- Gains: Lightweight runtime, fast startup, async support via `async` endpoints, easy integration with Celery and Redis.
- Trade‑offs: Requires external task queue for heavy workloads, less out‑of‑the‑box ORM features (SQLAlchemy used).
