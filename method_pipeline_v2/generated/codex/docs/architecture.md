# Context

The Order Management System (OMS) is a backend-only service for the complete customer ordering, payment, invoicing, shipping, and closure workflow. It supports Customer, Order Staff, and Accountant domain roles without authentication. PostgreSQL is the system of record; Redis is a disposable secondary copy for caching and is also the event transport. Critical REST operations remain synchronous and return the created resource.

# Architecture

## NFR traceability matrix

This matrix was established before implementation. The paths and symbols below are the implementation contract used by `nfr-trace.json`.

| NFR | Architectural mechanism | Module/component | Verification method |
|---|---|---|---|
| NFR 1.1 Limit Event Response | A configured `AsyncLimiter` gates each transactional-outbox event before Redis publication and each polling pass claims only a bounded batch. | `app/workers/outbox.py::OutboxDispatcher.dispatch_pending_events` | Set `EVENT_MAX_RATE=2`, enqueue at least four events, and verify the publish timestamps span at least one second. |
| NFR 1.2 Maintain Multiple copies of Data | PostgreSQL remains canonical while versioned JSON snapshots are written to and read from Redis as a read-through secondary copy. | `app/infrastructure/cache.py::EntityCache.get_json`, `app/infrastructure/cache.py::EntityCache.set_json` | Create an entity, inspect its `oms:entity:*` Redis key, delete the key, GET the entity, and confirm the key is repopulated from PostgreSQL. |
| NFR 2.1 Exception detection | Dependency calls have explicit timeouts; system/database/validation exceptions are translated by centralized handlers; health probes expose failed/degraded dependencies. | `app/core/resilience.py::run_with_timeout`, `app/core/errors.py::install_exception_handlers`, `app/services/health_service.py::HealthService.check` | Stop Redis and call `/health/ready` to observe `degraded`; inject a slow probe to verify a detected timeout and bounded response. |
| NFR 2.2 Graceful Degradation | Redis operations fail open, database reads replace cache misses/failures, and unpublished outbox rows remain durable for later retry. | `app/infrastructure/cache.py::EntityCache.get_json`, `app/infrastructure/cache.py::EntityCache.set_json`, `app/workers/outbox.py::OutboxDispatcher.dispatch_pending_events` | Stop Redis, then create and fetch an entity successfully from PostgreSQL while readiness reports `degraded`; restart Redis and observe pending events publish. |
| NFR 2.3 State Resynchronization | A periodic reconciler compares canonical PostgreSQL entity versions and payload hashes with the Redis secondary snapshots, repairing missing or stale copies. | `app/workers/state_sync.py::StateSynchronizer.resynchronize_once`, `app/workers/state_sync.py::StateSynchronizer.run_forever` | Corrupt a Redis entity envelope, trigger `/internal/resynchronize`, and verify the repaired payload/hash plus mismatch counter. |
| NFR 2.4 Transactions | SQLAlchemy transaction boundaries atomically persist each state change and its idempotently identified outbox event; rows are claimed with `FOR UPDATE SKIP LOCKED`. | `app/infrastructure/unit_of_work.py::SqlAlchemyUnitOfWork.transaction`, `app/repositories/outbox_repository.py::OutboxRepository.add`, `app/repositories/outbox_repository.py::OutboxRepository.claim_batch` | Force outbox insertion to fail and verify the entity mutation rolls back; run two dispatchers and verify each event is claimed/published once. |

The tactic names used by the machine-readable trace are the Bass/Clements/Kazman tactics `Performance / Control Resource Demand / Limit Event Response`, `Performance / Manage Resources / Maintain Multiple Copies of Data`, `Availability / Detect Faults / Exception Detection`, `Availability / Recover from Faults / Preparation and Repair / Degradation`, `Availability / Recover from Faults / Reintroduction / State Resynchronization`, and `Availability / Prevent Faults / Transactions`.

## Runtime topology

```text
HTTP client
    |
FastAPI routes -> controllers -> services -> repositories -> PostgreSQL
                                      |             |
                                      |             +-- domain rows + outbox (one transaction)
                                      +-- best-effort versioned Redis entity cache

background outbox dispatcher -> rate limiter -> Redis Stream
background state synchronizer <-> PostgreSQL canonical rows / Redis secondary copies
```

The application is a modular monolith: domain boundaries are explicit in schemas, repositories, services, controllers, and routes, while one deployment preserves simple ACID workflow transitions. All money uses `Decimal`; external amounts use strings with exactly two fractional digits. Dates are `dd/MM/yyyy` at the API boundary and real date types internally. UUIDs are generated server-side.

## Architectural decision records

### ADR-001: Modular monolith with explicit layers

- **Decision:** Deploy one asynchronous FastAPI service, separated into domain, repository, service, controller, route, infrastructure, and worker modules.
- **Context:** Non-trivial traffic, synchronous creation contracts, transactional workflow invariants, operational simplicity, and NFR 2.4.
- **Alternatives considered:** Microservices were rejected because distributed workflow transactions and five independently operated services add failure modes without a stated independent-scaling need. Serverless functions were rejected because background outbox/reconciliation loops and predictable connection pooling fit a continuously running service better.
- **Consequences:** The service can scale horizontally and is easy to run locally, but modules share a release cadence and very high future hotspots may need extraction.

### ADR-002: PostgreSQL as the canonical relational store

- **Decision:** Use PostgreSQL through SQLAlchemy 2 asynchronous sessions, relational foreign keys, unique constraints, checks, and row locks.
- **Context:** Strict relationships, money precision, workflow consistency, concurrent transitions, and NFRs 2.1 and 2.4.
- **Alternatives considered:** MongoDB was rejected because cross-aggregate referential and transactional rules are central. SQLite was rejected for production because its concurrency model and lack of PostgreSQL `SKIP LOCKED` do not fit multiple dispatchers.
- **Consequences:** Strong integrity and mature operations are gained at the cost of running a database service and managing schema migrations.

### ADR-003: Transactional outbox for asynchronous events

- **Decision:** Write domain changes and event rows in the same database transaction; publish committed events asynchronously with idempotent event IDs.
- **Context:** NFR 1.1, NFR 2.2, and NFR 2.4 require bounded event processing without losing a domain change when the event transport fails.
- **Alternatives considered:** Direct Redis publication inside request handlers was rejected because a crash can split the domain commit from publication. Distributed two-phase commit was rejected because Redis does not participate and the operational cost is disproportionate.
- **Consequences:** Requests do not depend on Redis and events are durable, but delivery is at least once and consumers must deduplicate by event ID.

### ADR-004: Redis for disposable data copies and event transport

- **Decision:** Store versioned entity snapshots in Redis and publish outbox events to a Redis Stream.
- **Context:** NFR 1.2, NFR 2.2, read latency, and simple local production deployment.
- **Alternatives considered:** Process-local caching was rejected because replicas would have divergent copies and no shared inspection point. Kafka was rejected because its operational footprint is excessive for the stated local deployment and traffic requirements.
- **Consequences:** Read load and event transport latency improve; Redis is explicitly non-canonical, so failures reduce performance/async freshness rather than correctness.

### ADR-005: Explicit state machines in services

- **Decision:** Central transition maps and locked database rows enforce the Order, Payment, and Invoice lifecycles.
- **Context:** The seven-step behavior workflow, prevention of illegal transitions, and concurrent staff/accountant actions.
- **Alternatives considered:** Unrestricted CRUD status updates were rejected because they cannot preserve lifecycle invariants. A separate workflow engine was rejected because the workflow is small, deterministic, and has no long-running human task scheduler requirement.
- **Consequences:** Valid transitions are easy to audit and test, but new lifecycle branches require a code/schema migration.

### ADR-006: Strict boundary validation with Pydantic and domain checks

- **Decision:** Pydantic validates lexical shape and exact boundaries; services validate foreign-key existence, snapshots, totals, and current state. Invalid format/value is HTTP 400, a missing well-formed reference is 404, and a state conflict is 409.
- **Context:** The authoritative field constraint table and automated BVA/EP compatibility requirements.
- **Alternatives considered:** Database-only validation was rejected because it gives poor client errors and cannot express all lexical rules. Permissive coercion was rejected because it silently rounds money and accepts malformed types.
- **Consequences:** The API is predictable and preserves exact values, but clients must send decimal amounts as two-decimal JSON strings and case-sensitive enums.

# Tasks

1. Implement strict shared request/response schemas and relational persistence.
2. Implement per-entity repositories, services, controllers, and versioned routes.
3. Implement workflow transitions, transactional outbox, bounded dispatch, cache degradation, health checks, and state reconciliation.
4. Provide OpenAPI, manifests, containers, schema documentation, tests, and NFR verification instructions.

# Deliverables

The completed repository will include `nfr-trace.json`, `create_apis.json`, `start_command.txt`, `openapi.yaml`, application source, automated tests, Docker infrastructure, a complete schema, and local deployment/verification documentation.

# Output

The API listens on port 8000, exposes `/api/v1` resources, `/health/live`, `/health/ready`, `/metrics`, and an explicit reconciliation trigger. `docker compose up --build -d` is the one-command local production start path.
