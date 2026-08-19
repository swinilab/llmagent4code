# Architectural Decision Records (ADRs)

This document contains ADRs for all major architectural decisions in the OMS backend.

---

## ADR 001: Async-First Architecture with FastAPI

### Decision
Use FastAPI with async/await pattern for all I/O operations.

### Context
- **NFR Addressed:** NFR 1.1 (Performance), NFR 2.1 (Exception Detection), NFR 2.2 (Graceful Degradation)
- System must handle non-trivial traffic
- Need efficient resource utilization under load
- Require built-in async support for timeout handling

### Alternatives Considered

1. **Synchronous Flask/Django**
   - Rejected because: Blocking I/O would limit concurrency, requiring more threads/processes
   - Would need additional infrastructure (gunicorn workers) for concurrent requests
   - Harder to implement timeout detection without blocking threads

2. **Tornado**
   - Rejected because: Less mature ecosystem, fewer built-in features
   - FastAPI provides automatic OpenAPI docs and better type hints
   - Smaller community and fewer third-party integrations

### Consequences
- **Positive:** High concurrency with fewer resources, native async timeout handling
- **Negative:** Steeper learning curve for developers unfamiliar with async
- **Trade-off:** Async complexity in exchange for performance and scalability

---

## ADR 002: SQLite with Async Driver for Data Persistence

### Decision
Use SQLite with aiosqlite async driver for data persistence.

### Context
- **NFR Addressed:** NFR 1.2 (Multiple Data Copies), NFR 2.4 (Transactions)
- Must support ACID transactions
- Need to run locally without complex infrastructure
- Require async database operations

### Alternatives Considered

1. **PostgreSQL with asyncpg**
   - Rejected because: Requires external database server, complex local setup
   - Overkill for development and local deployment
   - Adds infrastructure dependency for simple use case

2. **In-memory storage**
   - Rejected because: No persistence across restarts
   - Cannot satisfy NFR 2.4 (durability requirement)
   - No transaction support

### Consequences
- **Positive:** Zero-config deployment, file-based persistence, async support
- **Negative:** Limited concurrent write throughput compared to PostgreSQL
- **Trade-off:** Simplicity and deployability vs. enterprise-scale performance

---

## ADR 003: Token Bucket Rate Limiting

### Decision
Implement token bucket algorithm for rate limiting at middleware level.

### Context
- **NFR Addressed:** NFR 1.1 (Limit Event Response)
- Must process events only up to maximum rate
- Need per-client rate limiting
- Simple implementation preferred

### Alternatives Considered

1. **Fixed Window Rate Limiting**
   - Rejected because: Allows burst at window boundaries
   - Less smooth rate limiting behavior
   - Can allow 2x rate at window edges

2. **Redis-based Rate Limiting**
   - Rejected because: Requires external Redis server
   - Adds infrastructure complexity
   - Overkill for single-instance deployment

### Consequences
- **Positive:** Smooth rate limiting, no external dependencies, per-client tracking
- **Negative:** In-memory state lost on restart, not distributed-aware
- **Trade-off:** Simplicity vs. distributed scalability

---

## ADR 004: In-Memory Caching Layer

### Decision
Implement simple in-memory caching with TTL in the repository layer.

### Context
- **NFR Addressed:** NFR 1.2 (Maintain Multiple Copies of Data)
- Need to reduce database load for repeated reads
- Cache frequently accessed entities (customers, products, orders)
- Simple cache invalidation strategy

### Alternatives Considered

1. **Redis Caching**
   - Rejected because: Requires external Redis server
   - Adds deployment complexity
   - Network latency for cache access

2. **No Caching**
   - Rejected because: Every read hits database
   - Cannot satisfy NFR 1.2 requirement
   - Poor performance for repeated reads

### Consequences
- **Positive:** Zero dependencies, fast access, simple implementation
- **Negative:** Cache lost on restart, memory-bounded, single-process only
- **Trade-off:** Simplicity vs. distributed cache consistency

---

## ADR 005: Tenacity for Retry Logic

### Decision
Use tenacity library for retry logic with exponential backoff.

### Context
- **NFR Addressed:** NFR 2.1 (Exception Detection), NFR 2.2 (Graceful Degradation)
- Must detect and handle transient failures
- Need automatic retry with backoff
- Graceful degradation under fault conditions

### Alternatives Considered

1. **Custom Retry Implementation**
   - Rejected because: Reinventing well-tested library
   - More code to maintain
   - Tenacity provides battle-tested patterns

2. **No Retry Logic**
   - Rejected because: Transient failures would cause immediate errors
   - Cannot satisfy NFR 2.2 (graceful degradation)
   - Poor user experience under temporary faults

### Consequences
- **Positive:** Battle-tested library, declarative decorators, exponential backoff
- **Negative:** Additional dependency, learning curve for configuration
- **Trade-off:** External dependency vs. robust fault handling

---

## ADR 006: Background State Synchronization Task

### Decision
Implement asyncio background task for periodic state synchronization.

### Context
- **NFR Addressed:** NFR 2.3 (State Resynchronization)
- Must periodically compare active and standby states
- Need automatic detection of state drift
- Simple implementation for single-instance

### Alternatives Considered

1. **Celery Periodic Tasks**
   - Rejected because: Requires Redis/RabbitMQ broker
   - Complex setup for simple periodic task
   - Overkill for single-instance state sync

2. **Cron-based External Script**
   - Rejected because: External to application
   - Harder to monitor and manage
   - No visibility into sync status

### Consequences
- **Positive:** Built-in to application, no external dependencies, observable
- **Negative:** Runs in same process, single-instance only
- **Trade-off:** Simplicity vs. distributed state management

---

## ADR 007: SQLAlchemy ORM with Async Sessions

### Decision
Use SQLAlchemy 2.0 ORM with async sessions for transaction management.

### Context
- **NFR Addressed:** NFR 2.4 (Transactions)
- Must ensure ACID properties
- Need async database operations
- Type-safe ORM preferred

### Alternatives Considered

1. **Raw SQL with asyncpg**
   - Rejected because: No ORM benefits, more error-prone
   - Manual query building and result mapping
   - Harder to maintain referential integrity

2. **SQLAlchemy Sync Sessions**
   - Rejected because: Blocking I/O in async application
   - Would need run_in_executor for all DB operations
   - Defeats purpose of async architecture

### Consequences
- **Positive:** Type-safe ORM, async support, automatic transaction management
- **Negative:** SQLAlchemy learning curve, migration complexity
- **Trade-off:** ORM abstraction vs. raw SQL flexibility

---

## ADR 008: Layered Architecture (Controller-Service-Repository)

### Decision
Implement three-layer architecture: Controller, Service, Repository.

### Context
- **NFR Addressed:** All NFRs (separation of concerns)
- Clear separation of responsibilities
- Testability and maintainability
- Reusable business logic

### Alternatives Considered

1. **Fat Controller Pattern**
   - Rejected because: Business logic mixed with HTTP handling
   - Harder to test business logic in isolation
   - Violates single responsibility principle

2. **Domain-Driven Design (Full DDD)**
   - Rejected because: Overly complex for this scope
   - Requires significant upfront design
   - More boilerplate code

### Consequences
- **Positive:** Clear separation, testable layers, maintainable codebase
- **Negative:** More files and boilerplate
- **Trade-off:** Structure vs. minimalism
