# ADR-001: SQLite with WAL Mode as the Primary Database

**Date:** 2025-01-01
**Status:** Accepted

## Decision

Use SQLite in WAL (Write-Ahead Logging) mode as the primary database for the
OMS backend, accessed via the `aiosqlite` async driver through SQLAlchemy 2.0.

## Context

**NFRs addressed:** NFR 2.3 (State Preservation), NFR 1.1 (Response Time),
NFR 1.2 (Concurrency & Resource Utilization).

The system must preserve operational state across unexpected process crashes
with minimal data loss, while keeping round-trip latency low for core journeys.
The deployment target is a local machine running a production environment, so
operational simplicity (no separate database server to install/manage) is a
strong constraint.

## Alternatives Considered

1. **PostgreSQL with asyncpg** — Full-featured RDBMS with MVCC, streaming
   replication, and excellent concurrent write performance. Rejected because it
   requires a separate server process, additional infrastructure setup, and
   configuration that contradicts the "install and deploy on local machine"
   requirement. The OMS traffic profile (moderate, not extreme write-heavy) does
   not demand PostgreSQL's advanced features.

2. **SQLite in default rollback-journal mode** — Simpler than WAL but locks the
   entire database file during writes, serialising all readers and writers. This
   would cause significant latency spikes under concurrent load, violating NFR
   1.1 and NFR 1.2. WAL mode allows concurrent readers alongside a single writer,
   which is the dominant access pattern for an OMS (many product searches, fewer
   order writes).

3. **In-memory store (e.g. Redis)** — Ultra-low latency but no built-in durable
   persistence to disk by default, violating NFR 2.3 (State Preservation). Would
   require a separate persistence layer, adding complexity.

## Consequences

- **Accepted:** SQLite WAL provides crash-safe durability with
  `synchronous=NORMAL` (each transaction is durable across application crashes
  but not across power loss). `busy_timeout=5000` prevents "database is locked"
  errors under concurrent write contention.
- **Accepted:** Single-writer limitation means very high write throughput is not
  achievable; acceptable for the OMS traffic profile.
- **Accepted:** No built-in replication; horizontal scaling would require
  migrating to PostgreSQL. This is documented as a future growth path.
- **Benefit:** Zero-infrastructure deployment — the database is a single file
  (`oms.db`) that can be backed up by copying.