# ADR 002: Asynchronous SQLAlchemy with SQLite (aiosqlite)

**Decision:** Use SQLAlchemy 2.x async engine with aiosqlite for the database.

**Context (NFRs addressed):**
- NFR 1.1 Response Time – Non‑blocking DB calls keep request latency low.
- NFR 1.2 Concurrency – Async engine allows many concurrent DB interactions without thread pool exhaustion.
- NFR 1.3 Queue Management – Async I/O reduces thread count, helping the system handle spikes.

**Alternatives considered:**
1. Synchronous SQLAlchemy with PostgreSQL – Would require a thread pool; higher memory usage under load.
2. NoSQL (MongoDB) – Would lose relational integrity needed for order‑line items and transactions.

**Consequences:**
- Gains: Simpler deployment (SQLite file), async throughout stack, easy for local development.
- Trade‑offs: SQLite may not scale to massive production; for real deployment replace DATABASE_URL with PostgreSQL.
