# ADR 003 – In‑process Async Queue for Task Offloading

**Decision:** Use a bounded ``asyncio.Queue`` (max size 5000) to decouple heavy operations (invoice creation, payment processing) from the request thread.

**Context:** Directly addresses NFR 1.3 (queue management) and contributes to NFR 2.1 (graceful degradation) by allowing workers to be paused.

**Alternatives considered:**
1. **External RabbitMQ / Kafka** – rejected because it adds external infrastructure and complexity for a prototype.
2. **Redis List with RQ** – rejected as it would require a Redis server, increasing deployment footprint.

**Consequences:**
- Keeps the system self‑contained; no external broker needed.
- Queue depth is bounded, preventing unbounded memory growth under spikes.
- If the worker crashes, the queue remains in memory; combined with WAL entries, pending tasks can be recovered on restart.
