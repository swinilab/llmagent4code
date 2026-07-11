# NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|-----------------|--------------------|
| **2.1 Localization of Changes** | Domain‑driven design with separate SQLAlchemy models, repositories, services, and routers per entity. | `app/models/*`, `app/repositories/*`, `app/services/*`, `app/controllers/*` | Reviewer checks that each business concept (Customer, Order, etc.) resides in its own package and that cross‑cutting concerns (DB session, config) are injected, not hard‑coded.
| **2.2 Interface Stability** | FastAPI auto‑generates OpenAPI spec; versioned path prefix `/api/v1`. | `app/api/v1/router.py`, `app/main.py` | Run `GET /openapi.json` and confirm schema matches Pydantic models; ensure no breaking changes in path signatures.
| **2.3 Deferred Binding** | Runtime configuration via Pydantic `BaseSettings` reading env vars (`DATABASE_URL`, `DEBUG`, etc.). | `app/config/settings.py` (used in `app/db.py`, `app/main.py`) | Change an env var (e.g., `DEBUG=True`) and observe behaviour without restarting the process (FastAPI reload mode can be used).
