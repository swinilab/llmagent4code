# ADR 002 – In‑memory AsyncIO Queue for background tasks

**Decision**: Use a bounded ``asyncio.Queue`` to decouple request handling from background processing (notifications, inventory updates).

**Context**: Addresses NFR 1.3 (Queue Management) and NFR 2.1 (Graceful Degradation) by bounding the queue size and allowing the system to reject overloads early.

**Alternatives considered**:
- External message broker (RabbitMQ, Kafka) – adds operational complexity, not needed for a local production‑grade demo.
- ThreadPoolExecutor – would block the event loop for I/O‑bound work.

**Consequences**: Simple to implement and works within a single process; however, it does not survive process crashes – mitigated by WAL persistence (see ADR 004).
