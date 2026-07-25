# NFR Traceability Matrix

| NFR ID | NFR Name | Architectural Mechanism | Module/Component | Verification Method |
|--------|----------|------------------------|------------------|---------------------|
| NFR 1.1 | Response Time | Async I/O with FastAPI, connection pooling, response caching | `app/main.py`, `app/db/connection_pool.py` | Load test with k6 shows p95 latency < 200ms for checkout endpoint |
| NFR 1.2 | Concurrency & Resource Utilization | Asyncio concurrency, worker pool for queue processing | `app/main.py`, `app/queue/queue_manager.py` | ab -c 100 shows throughput scales near-linearly up to worker count |
| NFR 1.3 | Queue Management | Bounded asyncio.Queue with max size, graceful rejection | `app/queue/queue_manager.py` | Burst of 1000 requests returns 503 without dropped connections; queue_size bounded per /health/queue |
| NFR 2.1 | Graceful Degradation | DegradationManager disables non-essential endpoints under load | `app/degradation/degradation_manager.py` | Kill background worker under load; checkout endpoint still returns 2xx while non-essential endpoints return 503 |
| NFR 2.2 | Fault Detection and Recovery | Tenacity retry with exponential backoff, database ping/echo | `app/db/connection_pool.py`, `app/health/liveness.py` | Kill DB connection mid-request; observe automatic reconnect within N seconds via /health/ready |
| NFR 2.3 | State Preservation | Write-Ahead Log (WAL) for pending operations, state snapshots | `app/persistence/wal.py` | Kill process mid-queue-processing, restart, confirm pending orders resume from persisted state with no loss |

---

# Architectural Decision Records (ADRs)

## ADR 1: Async I/O with FastAPI

**Decision:** Use FastAPI with async/await for all I/O operations.

**Context:** Addresses NFR 1.1 (Response Time) and NFR 1.2 (Concurrency & Resource Utilization).

**Alternatives considered:**
1. **Flask with threading:** Rejected due to GIL limitations and lower throughput under concurrent load.
2. **Django with async views:** Rejected due to heavier framework overhead and less mature async support.

**Consequences:** 
- Pros: High concurrency with minimal threads, excellent performance under load.
- Cons: Requires async-compatible libraries, steeper learning curve for developers unfamiliar with async.

---

## ADR 2: SQLite with Async Connection Pool

**Decision:** Use SQLite with aiosqlite and connection pooling for data persistence.

**Context:** Addresses NFR 2.2 (Fault Detection and Recovery) and NFR 2.3 (State Preservation).

**Alternatives considered:**
1. **PostgreSQL with asyncpg:** Rejected for local deployment simplicity; adds operational complexity.
2. **In-memory storage:** Rejected due to lack of persistence across restarts.

**Consequences:**
- Pros: Zero configuration, file-based persistence, easy recovery.
- Cons: Limited write concurrency compared to PostgreSQL; acceptable for moderate traffic.

---

## ADR 3: Bounded Queue with Graceful Rejection

**Decision:** Implement bounded queue with max size and return 503 when full.

**Context:** Addresses NFR 1.3 (Queue Management) and NFR 2.1 (Graceful Degradation).

**Alternatives considered:**
1. **Unbounded queue:** Rejected due to risk of OOM under sustained load.
2. **Blocking enqueue:** Rejected due to potential request timeouts and poor user experience.

**Consequences:**
- Pros: System remains stable under load spikes, predictable resource usage.
- Cons: Some requests rejected during extreme load; clients must retry.

---

## ADR 4: Write-Ahead Log for State Recovery

**Decision:** Implement WAL pattern to persist operations before execution.

**Context:** Addresses NFR 2.3 (State Preservation).

**Alternatives considered:**
1. **Transaction log from database:** Rejected due to SQLite limitations and complexity.
2. **Periodic snapshots only:** Rejected due to potential data loss between snapshots.

**Consequences:**
- Pros: Can recover pending operations after crash, minimal data loss.
- Cons: Additional I/O overhead per operation; acceptable trade-off for reliability.

---

## ADR 5: Degradation Manager for Load Shedding

**Decision:** Implement DegradationManager to disable non-essential endpoints under high load.

**Context:** Addresses NFR 2.1 (Graceful Degradation).

**Alternatives considered:**
1. **Rate limiting only:** Rejected as it doesn't prioritize core functionality.
2. **Circuit breaker pattern:** Rejected as it focuses on external dependencies, not internal load.

**Consequences:**
- Pros: Core checkout remains available during overload.
- Cons: Non-essential features unavailable during degradation; acceptable for business continuity.

---

## ADR 6: Tenacity for Retry Logic

**Decision:** Use tenacity library for automatic retry with exponential backoff.

**Context:** Addresses NFR 2.2 (Fault Detection and Recovery).

**Alternatives considered:**
1. **Custom retry logic:** Rejected due to reinventing the wheel and potential bugs.
2. **No retry:** Rejected as transient failures would cause unnecessary errors.

**Consequences:**
- Pros: Robust fault recovery, configurable retry behavior.
- Cons: Additional dependency; minor latency increase during retries.
