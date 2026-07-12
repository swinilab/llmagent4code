# Architecture Decision Records (ADR)

## ADR-001: Async Python Stack (FastAPI + asyncpg + uvloop)

**Decision:** Use FastAPI with asyncpg for database access and uvloop as the event loop, replacing the synchronous Django/Flask pattern.

**Context (NFRs addressed):**
- NFR 1.1 (Response Time): Async DB queries eliminate I/O blocking, reducing latency under concurrent load.
- NFR 1.2 (Concurrency): Async I/O enables handling 10k+ concurrent connections per worker without thread overhead.

**Alternatives considered:**
1. **Django + Gunicorn (sync workers)** — Rejected because each request occupies a thread/process during DB I/O, limiting concurrency to ~200-500 concurrent users.
2. **Node.js + Express** — Rejected because Python's ecosystem (pydantic, SQLAlchemy, arq) better fits our type-heavy, domain-rich OMS workload and team familiarity.

**Consequences:**
- All DB calls must be `await`-annotated; no sync ORM calls in the hot path.
- Developer discipline required to never mix sync blocking calls (e.g., `time.sleep`, sync `requests`) in service layer.

---

## ADR-002: PostgreSQL as Primary Database

**Decision:** PostgreSQL 15+ with asyncpg driver; Redis for cache + queue backend.

**Context (NFRs addressed):**
- NFR 1.2 (Concurrency): PostgreSQL's MVCC + connection pooling supports high concurrency with ACID guarantees.
- NFR 1.3 (Queue Management): Redis STREAMS provide a durable, ordered queue with consumer-group semantics for background job processing.

**Alternatives considered:**
1. **MySQL 8** — Rejected: lacks JSONb, advanced indexing (GIN), and lateral join performance for complex order analytics.
2. **MongoDB** — Rejected: weak multi-document transaction support makes cross-entity operations (order+invoice+payment) fragile without a two-phase commit workaround.

**Consequences:**
- Must maintain migration discipline (Alembic) across schema evolutions.
- Redis is a single point of failure for queue; requires Redis Sentinel or Cluster for HA (acceptable trade-off for local dev simplicity).

---

## ADR-003: Pydantic v2 for Schema Validation and Serialization

**Decision:** Pydantic v2 BaseModel for all request/response schemas, domain models, and cross-layer data transfer objects (DTOs).

**Context (NFRs addressed):**
- NFR 1.1 (Response Time): Pydantic v2's Rust-based validator runs 50× faster than v1; validation overhead < 2ms per request.
- NFR 1.2 (Concurrency): Immutable models (frozen=True where appropriate) are safe to share across async tasks without locking.

**Alternatives considered:**
1. **attrs + cattrs** — Rejected: smaller ecosystem; FastAPI native integration is stronger with Pydantic.
2. **Marshmallow** — Rejected: declarative-only, not type-guided; more boilerplate for complex nested domain objects.

**Consequences:**
- All domain models are co-located with validation logic; no separate schema files needed.
- Serialization of complex nested objects (Order → LineItems → Product) requires careful exclude_unset / exclude_defaults configuration.

---

## ADR-004: Gunicorn with Uvicorn Workers + uvloop

**Decision:** Deploy via Gunicorn with `uvicorn.workers.UvicornWorker`, each worker running uvloop as the event loop.

**Context (NFRs addressed):**
- NFR 1.2 (Resource Utilization): Multi-worker bypasses Python GIL, utilizing all CPU cores (up to 98 GB RAM class machines).
- NFR 1.3 (Queue Management): Gunicorn's master process handles SIGTERM gracefully, draining in-flight requests before worker replacement.

**Alternatives considered:**
1. **Uvicorn standalone (no Gunicorn)** — Rejected: no process management, no worker graceful restart, no systemd integration clarity.
2. **Daphne (Twisted-based)** — Rejected: larger memory footprint; less tuning community compared to Gunicorn+uvicorn.

**Consequences:**
- Worker count must be tuned per machine (2×cores + 1 is a starting point).
- Shared state across workers (in-memory cache) requires external store (Redis); local cache is worker-local only.

---

## ADR-005: Arq for Background Task Processing

**Decision:** Arq (async Redis queue) for all async jobs: invoice PDF generation, audit logging, payment gateway webhooks, and email notifications.

**Context (NFRs addressed):**
- NFR 1.3 (Queue Management): Arq's bounded queue with retries prevents job loss during spikes; dead-letter queue captures permanently failed jobs.
- NFR 1.1 (Response Time): Moves heavy I/O (PDF rendering, email) off the request path.

**Alternatives considered:**
1. **Celery + Redis** — Rejected: heavier weight, requires separate `celery` process, less async-native; Celery tasks are not true coroutines.
2. **RQ (Redis Queue)** — Rejected: no built-in retry with backoff or dead-letter queue; less active maintenance.

**Consequences:**
- Job definitions live in `infra/worker.py`; service layer enqueues via `await enqueue_job()`.
- Redis must be available for background jobs; graceful degradation if Redis is down (log + skip non-critical jobs).

---

*Last updated: 2025-07-12*
