# ADR 003: Use Tenacity for retry logic

**Decision:** Apply the ``tenacity`` library to wrap DB connection acquisition and external payment gateway calls.

**Context:** Meets NFR 2.2 (Fault Detection and Recovery) by automatically retrying transient failures.

**Alternatives considered:**
- Custom exponential backoff – rejected because it would duplicate well‑tested logic and increase maintenance.
- CircuitBreaker library – rejected as we need simple retry rather than circuit breaking for this scope.

**Consequences:** Adds a third‑party dependency; retries are limited to three attempts to avoid long hangs.
