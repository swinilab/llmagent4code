# NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|------------------|---------------------|
| NFR 1.1 Limit Event Response | Token bucket rate limiter with sliding window | `src/services/services.py::RateLimiter` | Call rate limiter 100+ times within 60s window; verify 101st request is rejected |
| NFR 1.2 Maintain Multiple copies of Data | SQLite database persistence + in-memory caching | `src/repositories/repositories.py::BaseRepository` | Verify data persists after restart; check both memory and DB have same data |
| NFR 2.1 Exception detection | Async timeout middleware with configurable threshold | `src/main.py::timeout_middleware` | Induce slow response (>30s); verify 504 timeout returned |
| NFR 2.2 Graceful Degradation | Exception handlers returning appropriate HTTP status codes | `src/main.py::value_error_handler`, `key_error_handler` | Send invalid request; verify 400/404 returned instead of 500 crash |
| NFR 2.3 State Resynchronization | Database ACID transactions with thread-safe locking | `src/repositories/repositories.py::BaseRepository._lock` | Simulate concurrent writes; verify no data corruption |
| NFR 2.4 Transactions | SQLite transactional operations with commit/rollback | `src/repositories/repositories.py::BaseRepository.save`, `src/services/services.py::InvoiceService.create_invoice` | Verify invoice creation updates both invoice and order atomically |

---

# Architectural Decision Records (ADRs)

## ADR-001: SQLite for Data Persistence

**Decision:** Use SQLite as the primary data store for the OMS backend.

**Context:** Addresses NFR 1.2 (Maintain Multiple copies of Data), NFR 2.3 (State Resynchronization), NFR 2.4 (Transactions). The system needs reliable persistence with ACID properties for local deployment.

**Alternatives considered:**
1. **PostgreSQL:** Rejected because it requires external service setup, increasing deployment complexity for local development. PostgreSQL is better suited for high-concurrency production environments.
2. **In-memory only:** Rejected because it doesn't satisfy NFR 1.2 (data persistence across restarts) and NFR 2.3 (state resynchronization after failures).

**Consequences:** 
- Pros: Zero configuration, file-based persistence, ACID transactions, thread-safe with proper locking.
- Cons: Limited concurrency compared to client-server databases, not suitable for distributed deployments.

---

## ADR-002: Token Bucket Rate Limiter

**Decision:** Implement a sliding window token bucket rate limiter in the service layer.

**Context:** Addresses NFR 1.1 (Limit Event Response). The system must handle non-trivial traffic and prevent overload.

**Alternatives considered:**
1. **Redis-based rate limiting:** Rejected because it requires external dependency and adds complexity for local deployment.
2. **Nginx rate limiting:** Rejected because it requires infrastructure configuration and doesn't provide application-level visibility.

**Consequences:**
- Pros: Simple implementation, no external dependencies, application-level control.
- Cons: Not distributed-safe (each instance has its own limiter), memory-based tracking lost on restart.

---

## ADR-003: Async Timeout Middleware

**Decision:** Implement FastAPI middleware with `asyncio.wait_for` for request timeout detection.

**Context:** Addresses NFR 2.1 (Exception detection - Timeout). The system must detect and handle slow or hanging requests.

**Alternatives considered:**
1. **Gunicorn worker timeout:** Rejected because it kills the entire worker, not individual requests.
2. **Client-side timeout only:** Rejected because server resources remain consumed even if client gives up.

**Consequences:**
- Pros: Per-request timeout control, graceful handling with 504 response.
- Cons: Requires async-compatible code throughout the stack, timeout value must be tuned.

---

## ADR-004: Exception Handlers for Graceful Degradation

**Decision:** Implement global exception handlers for ValueError and KeyError returning appropriate HTTP status codes.

**Context:** Addresses NFR 2.2 (Graceful Degradation). The system must maintain critical functions while dropping less critical ones on errors.

**Alternatives considered:**
1. **Try-catch in every endpoint:** Rejected because it leads to code duplication and inconsistent error handling.
2. **Custom exception hierarchy:** Rejected as over-engineering for this scope; simple handlers suffice.

**Consequences:**
- Pros: Centralized error handling, consistent API responses, prevents 500 crashes.
- Cons: May mask underlying bugs if overused; requires careful exception classification.

---

## ADR-005: Thread-Safe Repository Pattern

**Decision:** Use threading.Lock in repository layer for concurrent access control.

**Context:** Addresses NFR 2.3 (State Resynchronization) and NFR 2.4 (Transactions). Multiple concurrent requests must not corrupt data.

**Alternatives considered:**
1. **Async locks (asyncio.Lock):** Rejected because SQLite connections are thread-local and blocking locks are appropriate.
2. **Optimistic locking with version numbers:** Rejected as over-engineering for single-instance deployment.

**Consequences:**
- Pros: Simple, effective for single-instance deployments, prevents race conditions.
- Cons: Can become bottleneck under high concurrency, not suitable for distributed systems.

---

## ADR-006: Pydantic for Validation

**Decision:** Use Pydantic models for all entity validation with field validators.

**Context:** Addresses all field constraints in the Field Constraint Table. Provides automatic validation on deserialization.

**Alternatives considered:**
1. **Manual validation in services:** Rejected because it leads to duplicated validation logic and inconsistent enforcement.
2. **Database-level constraints only:** Rejected because validation must occur before database operations to provide meaningful error messages.

**Consequences:**
- Pros: Declarative validation, automatic type coercion, consistent error messages.
- Cons: Validation logic coupled to model definitions, may require model updates for constraint changes.
