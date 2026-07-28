# ADR 002: Use asyncio.Queue for internal task buffering

**Decision:** Introduce an in‑process bounded ``asyncio.Queue`` for order‑related background tasks.

**Context:** Satisfies NFR 1.3 (Queue Management) and contributes to NFR 2.1 (Graceful Degradation) by limiting resource demand.

**Alternatives considered:**
- External message broker (RabbitMQ, Kafka) – rejected for production complexity and external dependency in this prototype.
- Celery – rejected because it introduces separate worker processes and requires a broker/backend.

**Consequences:** Queue is limited to 1000 items; excess requests will await, preventing OOM. However, queue is in‑process, so a process crash loses pending tasks – mitigated by WAL (NFR 2.3).
