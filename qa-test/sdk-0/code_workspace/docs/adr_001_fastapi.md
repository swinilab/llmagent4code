# ADR 001: Use FastAPI with async endpoints

**Decision:** Adopt FastAPI with asynchronous request handling.

**Context:** Addresses NFR 1.1 (Response Time) and NFR 1.2 (Concurrency & Resource Utilization) by providing non‑blocking I/O and easy integration with uvicorn workers.

**Alternatives considered:**
- Django REST Framework – rejected due to heavier synchronous request handling and slower startup.
- Flask + gevent – rejected because less native async support and additional complexity for type‑safe validation.

**Consequences:** FastAPI requires Python 3.7+ and pydantic models; developers must write async code, but we gain lower latency and better concurrency.
