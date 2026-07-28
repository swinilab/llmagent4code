# ADR 001 – Async API with FastAPI & Uvicorn

**Decision:** Use FastAPI (async) as the web framework and run it with Uvicorn workers.

**Context:** Addresses NFR 1.1 (low latency), 1.2 (concurrency), 2.2 (fault detection via async retries).

**Alternatives considered:**
1. **Django REST Framework (sync)** – rejected because synchronous request handling would increase latency and limit concurrency.
2. **Flask + Gunicorn** – rejected due to lack of native async support; would require additional libraries for async DB access.

**Consequences:**
- Gains high throughput and low per‑request latency.
- Requires all services to be written async, increasing code complexity.
- Worker processes are isolated; a crash in one does not affect others, aiding graceful degradation.
