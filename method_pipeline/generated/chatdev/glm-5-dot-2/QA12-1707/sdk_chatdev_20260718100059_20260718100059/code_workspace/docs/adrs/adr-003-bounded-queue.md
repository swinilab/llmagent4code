# ADR-003: Bounded Async Queue for Spike Protection

**Date:** 2025-01-01
**Status:** Accepted

## Decision

Implement a bounded `asyncio.Queue` (`QueueManager`) with N worker coroutines
for background task processing. When the queue reaches its maximum size, new
tasks are rejected with `QueueFullError` so the HTTP layer can return 503
Service Unavailable instead of accumulating unbounded work and crashing.

## Context

**NFRs addressed:** NFR 1.3 (Queue Management), NFR 1.2 (Concurrency & Resource
Utilization).

Sudden traffic spikes (e.g. flash sale, marketing campaign) can generate far
more background work than the system can process. Without a bound, the queue
grows until memory is exhausted and the process crashes. The system must
degrade gracefully under spikes, not crash.

## Alternatives Considered

1. **Unbounded queue (accept everything)** — Rejected because memory usage
   grows without limit under sustained spikes, eventually causing OOM and
   process termination — directly violating NFR 1.3.

2. **Synchronous inline processing (no queue)** — Process every task inline in
   the request handler. Rejected because it couples task execution latency to
   request latency, violating NFR 1.1. A spike would cause all requests to block
   on task completion, stalling the event loop.

3. **External message broker (RabbitMQ / Redis Streams)** — Provides durable,
   horizontally scalable queuing. Rejected for the local-machine deployment
   target because it adds infrastructure complexity (a separate broker process
   to install and manage). The in-process bounded queue is sufficient for the
   OMS traffic profile and keeps deployment simple.

## Consequences

- **Accepted:** When the queue is full, tasks are rejected with
  `QueueFullError`. The HTTP layer translates this to 503, signalling the client
  to retry later. This is intentional backpressure.
- **Accepted:** Background tasks are not durable — if the process crashes while
  tasks are queued, they are lost. This is mitigated by NFR 2.3 state recovery
  (orders in non-terminal states are scanned on restart). For truly durable
  background processing, an external broker would be needed (future growth).
- **Benefit:** Multiple workers drain the queue concurrently, exploiting
  available CPU cores. The `/health/ready` endpoint exposes queue metrics
  (`max_size`, `current_size`, `processed`, `failed`) for observability.