# Architectural Decision Records (ADRs)

## ADR-001: SQLite with WAL Mode for Persistence

### Status
Accepted

### Context
NFR 2.3 requires State Preservation: the system must restore operational state after unexpected crashes with minimal data loss.

### Decision
Use SQLite database with WAL (Write-Ahead Logging) journal mode enabled.

### Alternatives Considered

**1. PostgreSQL**
- Pros: Full ACID compliance, excellent concurrency, production-proven
- Cons: Requires separate database server, complex local setup, overkill for single-instance OMS
- Rejected because: Local development would require Docker/compose setup; production deployment complexity increased significantly

**2. Flat File Storage (JSON/CSV)**
- Pros: Simple, no dependencies
- Cons: No transaction support, no crash recovery, data corruption risk, no query capability
- Rejected because: Cannot satisfy NFR 2.3 ACID requirements, no crash safety

**3. In-Memory Only**
- Pros: Fast, simple
- Cons: Data lost on restart, no persistence
- Rejected because: Directly violates NFR 2.3 State Preservation

### Consequences
- **Accepted Trade-off**: Limited write concurrency (SQLite allows one writer at a time)
- **Accepted Trade-off**: Not suitable for multi-instance deployment without additional coordination
- **Benefit**: Full ACID compliance with crash-safe WAL mode
- **Benefit**: Simple local development and deployment
- **Benefit**: Zero-configuration persistence (no database server needed)

---

## ADR-002: Circuit Breaker Pattern for Graceful Degradation

### Status
Accepted

### Context
NFR 2.1 Graceful Degradation requires core checkout functionality to remain available under extreme resource contention. NFR 2.2 Fault Detection requires automatic recovery from component failures.

### Decision
Implement Circuit Breaker pattern as a resilience mechanism for all external service calls and critical internal operations.

### Alternatives Considered

**1. Simple Try-Catch with Global Flag**
- Pros: Simple to implement
- Cons: No state awareness, no automatic recovery, all-or-nothing approach
- Rejected because: Cannot satisfy NFR 2.2 automatic recovery requirement

**2. Rate Limiter**
- Pros: Prevents overload, simple concept
- Cons: No failure detection, no recovery mechanism, doesn't degrade gracefully
- Rejected because: Does not address fault detection and recovery (NFR 2.2)

**3. Bulkhead Pattern**
- Pros: Isolates failures, maintains partial availability
- Cons: Complex implementation, resource-intensive
- Rejected because: Overkill for single-instance OMS, circuit breaker provides similar benefits with less complexity

### Consequences
- **Accepted Trade-off**: Added latency on circuit state transitions
- **Accepted Trade-off**: Configuration complexity (failure threshold, recovery timeout)
- **Benefit**: Prevents cascade failures
- **Benefit**: Automatic recovery after timeout
- **Benefit**: Observable state (OPEN/HALF_OPEN/CLOSED)
- **Benefit**: Enables graceful degradation by failing fast when system is unhealthy

---

## ADR-003: State Snapshot Pattern for Crash Recovery

### Status
Accepted

### Context
NFR 2.3 State Preservation requires restoring operational state after unexpected process crashes with minimal data loss.

### Decision
Implement periodic state snapshots saved to disk, combined with idempotency keys for operation deduplication.

### Alternatives Considered

**1. Full Transaction Log (Write-Ahead Log)**
- Pros: Complete audit trail, point-in-time recovery
- Cons: Complex implementation, storage overhead, parsing complexity
- Rejected because: SQLite WAL provides similar benefits natively; overhead not justified for OMS

**2. Database Backup on Interval**
- Pros: Simple concept, guaranteed consistency
- Cons: Potential data loss between backups, storage overhead, complexity for automation
- Rejected because: Does not provide continuous recovery capability; snapshots provide finer granularity

**3. Event Sourcing**
- Pros: Complete history, replay capability, excellent for auditing
- Cons: Significant architectural complexity, eventual consistency challenges, overkill for OMS
- Rejected because: Architecture mismatch with current design; would require complete redesign

### Consequences
- **Accepted Trade-off**: Small disk overhead for snapshot files
- **Accepted Trade-off**: Snapshot frequency vs crash recovery point tradeoff
- **Benefit**: Fast restart recovery (seconds, not minutes)
- **Benefit**: Idempotency ensures no duplicate operations on retry
- **Benefit**: Simple implementation using JSON files
- **Benefit**: Minimal performance impact (snapshots are async to main flow)

---

## ADR-004: Feature Flags for Runtime Graceful Degradation

### Status
Accepted

### Context
NFR 2.1 Graceful Degradation requires disabling non-essential features under resource contention while keeping core checkout available.

### Decision
Implement runtime feature flags that can toggle non-essential features (analytics, notifications, audit logging) without restart.

### Alternatives Considered

**1. Environment Variables**
- Pros: Simple, standard approach
- Cons: Requires restart to change, no runtime toggle
- Rejected because: Cannot dynamically degrade under load (NFR 2.1 requirement)

**2. Separate Microservices for Non-Essential Features**
- Pros: Complete isolation, independent scaling
- Cons: Architecture complexity, inter-service communication, deployment complexity
- Rejected because: Overkill for non-essential feature isolation; adds significant complexity

**3. Feature Branches / Dark Launches**
- Pros: Complete control, gradual rollout
- Cons: Code complexity, testing overhead, still requires full feature execution
- Rejected because: Does not address runtime degradation under load

### Consequences
- **Accepted Trade-off**: Additional configuration to manage
- **Accepted Trade-off**: Testing complexity for flag combinations
- **Benefit**: Zero-downtime feature toggling
- **Benefit**: Enables graceful degradation under load
- **Benefit**: Simple to understand and operate
- **Benefit**: Supports A/B testing in future

---

## ADR-005: Layered Architecture (Controller → Service → Repository)

### Status
Accepted

### Context
Backend requires clear separation of concerns: REST handling, business logic, and data access.

### Decision
Use three-layer architecture with Service layer managing transaction boundaries and orchestrating cross-cutting concerns.

### Alternatives Considered

**1. Direct Controller → Repository**
- Pros: Simple, fewer files
- Cons: Business logic in controllers, hard to test, transaction boundaries unclear
- Rejected because: Violates single responsibility principle, difficult to maintain

**2. Domain-Driven Design (DDD)**
- Pros: Rich domain model, bounded contexts, excellent for complex domains
- Cons: Significant learning curve, complexity overhead for OMS size
- Rejected because: Overkill for order management domain; could be evolution path

**3. Transaction Script**
- Pros: Very simple, straightforward
- Cons: Doesn't scale with domain complexity, no reuse of domain logic
- Rejected because: Order workflow has enough complexity to benefit from service layer

### Consequences
- **Accepted Trade-off**: More files to navigate
- **Accepted Trade-off**: Indirection for simple operations
- **Benefit**: Clear separation of concerns
- **Benefit**: Business logic is testable in isolation
- **Benefit**: Transaction boundaries clearly in service layer
- **Benefit**: Easy to add caching, auditing, etc. in service layer

---

## ADR-006: Pydantic for Request/Response Validation

### Status
Accepted

### Context
REST API requires validation of incoming requests and consistent response formatting.

### Decision
Use Pydantic models for all request/response DTOs with FastAPI's automatic validation.

### Alternatives Considered

**1. Marshmallow**
- Pros: Mature, feature-rich
- Cons: Separate schema from model, more verbose
- Rejected because: Pydantic integrates better with FastAPI, less boilerplate

**2. attrs + cattrs**
- Pros: Lightweight, good performance
- Cons: Less ecosystem integration with FastAPI
- Rejected because: Pydantic is the de facto standard for FastAPI

**3. Custom Validation Functions**
- Pros: Full control
- Cons: Manual, error-prone, no schema reuse
- Rejected because: Doesn't scale, no automatic OpenAPI generation

### Consequences
- **Accepted Trade-off**: Runtime overhead for validation (minimal with Pydantic V2)
- **Accepted Trade-off**: Learning curve for Pydantic features
- **Benefit**: Automatic OpenAPI schema generation
- **Benefit**: Type hints throughout
- **Benefit**: Consistent validation error format
