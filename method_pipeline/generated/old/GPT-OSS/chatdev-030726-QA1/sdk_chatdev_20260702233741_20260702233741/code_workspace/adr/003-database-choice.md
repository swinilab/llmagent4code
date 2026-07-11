# ADR 003 – Database Choice

**Decision**: Use PostgreSQL as the primary database for both development and production. For local quickstart, SQLite can be used as an in‑memory fallback.

**Context**: Supports NFR 1.1 (low latency) and NFR 1.2 (efficient resource utilization) by providing a robust relational store with proven performance.

**Alternatives considered**:
1. **MySQL** – Rejected due to similar capabilities but less seamless integration with SQLAlchemy's PostgreSQL‑specific features.
2. **SQLite only** – Rejected for production because it does not handle concurrent writes and scaling as well as PostgreSQL.

**Consequences**:
- Requires a PostgreSQL server (Docker Compose provided) for full functionality.
- Development can start quickly with SQLite, but migration scripts (Alembic) should be added for production readiness.
