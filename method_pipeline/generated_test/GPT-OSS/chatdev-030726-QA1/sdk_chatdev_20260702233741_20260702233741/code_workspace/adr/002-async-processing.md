# ADR 002 – Asynchronous Processing & Queue Management

**Decision**: Use Celery with Redis as the message broker and result backend for all long‑running steps (invoice generation, payment verification, shipping notification).

**Context**: Addresses NFR 1.3 (Queue Management) and helps NFR 1.2 by off‑loading work from request threads.

**Alternatives considered**:
1. **In‑memory Python `queue.Queue`** – Rejected because it does not survive process restarts and cannot handle spikes beyond a single worker process.
2. **Kafka** – Rejected due to higher operational complexity for a relatively simple OMS; Celery+Redis provides sufficient throughput and easier setup.

**Consequences**:
- Adds a Redis dependency and requires Docker Compose configuration.
- Guarantees at‑least‑once delivery; idempotency must be handled in services (currently simple and safe).
- Enables horizontal scaling of Celery worker instances.
