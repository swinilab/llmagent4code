# ADR 003 – Tenacity for retry & backoff on external calls

**Decision**: Use the ``tenacity`` library to wrap calls to external services (e.g., payment gateway) with retry and exponential backoff.

**Context**: Satisfies NFR 2.2 (Fault Detection and Recovery) by automatically retrying transient failures.

**Alternatives considered**:
- Custom retry loops – more error‑prone, duplicate code.
- ``retrying`` library – less maintained than tenacity.

**Consequences**: Adds a dependency but provides robust, configurable retry semantics. Retries are limited to avoid indefinite hanging.
