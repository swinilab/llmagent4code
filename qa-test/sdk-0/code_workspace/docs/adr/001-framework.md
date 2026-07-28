# ADR 001 – Choose FastAPI as web framework

**Decision**: Use FastAPI for the HTTP API layer.

**Context**: Need high performance, async support, automatic OpenAPI generation, and type‑hinted validation to satisfy NFR 1.1 (Response Time) and NFR 1.2 (Concurrency).

**Alternatives considered**:
- Django REST Framework – heavier, synchronous by default, slower start‑up latency.
- Flask with extensions – lacks built‑in async support and OpenAPI generation, would require extra libraries.

**Consequences**: FastAPI gives us native async endpoints, low overhead, and auto‑docs, but requires Python 3.7+ and developers familiar with Pydantic.
