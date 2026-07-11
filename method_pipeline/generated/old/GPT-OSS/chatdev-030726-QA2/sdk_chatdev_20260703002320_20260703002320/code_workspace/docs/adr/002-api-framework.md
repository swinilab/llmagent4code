# ADR 002 – API Framework Choice

**Decision:** Use FastAPI as the web framework.

**Context (NFRs addressed):**
- **NFR 2.2 Interface Stability:** FastAPI automatically generates OpenAPI specifications, ensuring contract stability for front‑ends.
- **NFR 2.3 Deferred Binding:** Configuration via Pydantic Settings can be changed at runtime.
- **NFR 2.1 Localization of Changes:** Routers are modular per domain, keeping endpoints isolated.

**Alternatives considered:**
1. **Django Rest Framework** – Rejected due to heavier weight and tighter coupling between models and views.
2. **Flask + Flask‑RESTful** – Rejected because manual OpenAPI generation would increase risk of contract drift.

**Consequences:**
- Fast development with type‑hints and automatic docs.
- Requires Python 3.7+ (satisfied).
