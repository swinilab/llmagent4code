# ADR 002 – Persistence with SQLite (WAL)

**Decision:** Use an embedded SQLite database with Write‑Ahead Logging (WAL) mode.

**Context:** Satisfies NFR 2.3 (state preservation) and NFR 2.2 (fault detection/recovery) without external dependencies.

**Alternatives considered:**
1. **PostgreSQL** – rejected for the prototype because it adds operational overhead and external service management.
2. **MongoDB** – rejected because document stores make enforcing strict relational constraints (FKs, enums) harder.

**Consequences:**
- Simple deployment (single file) and fast read/write for moderate traffic.
- WAL provides durability and allows crash recovery with minimal data loss.
- Limited scalability compared to a client‑server RDBMS; acceptable for the current load expectations.
