# NFR Traceability Matrix

This document maps each Non-Functional Requirement (NFR) to the architectural mechanisms, components, and verification methods used to satisfy them.

## NFR 1.1 - Limit Event Response

| Aspect | Details |
|--------|---------|
| **NFR** | Process events only up to a set maximum rate |
| **Architectural Mechanism** | Token bucket rate limiter |
| **Module/Component** | `oms_backend/infrastructure/rate_limiter.py`, `oms_backend/server.py` (middleware) |
| **Implementation** | `RateLimiter.allow_request()`, HTTP middleware checking rate before processing |
| **Verification Method** | Send burst of 150+ requests; verify 429 responses for excess requests |
| **Tactic** | Performance > Limit Event Response |

## NFR 1.2 - Maintain Multiple copies of Data

| Aspect | Details |
|--------|---------|
| **NFR** | Two common examples: data replication and caching |
| **Architectural Mechanism** | In-memory caching layer with TTL |
| **Module/Component** | `oms_backend/repository/base.py` (Database class), Service layer |
| **Implementation** | `Database.get_cached()`, `Database.set_cached()`, cache checks in service methods |
| **Verification Method** | Measure response times: subsequent requests to same resource should be faster |
| **Tactic** | Performance > Maintain Multiple Copies of Data > Caching |

## NFR 2.1 - Exception Detection

| Aspect | Details |
|--------|---------|
| **NFR** | Detect a system condition that alters the normal flow of execution (System exceptions and timeout) |
| **Architectural Mechanism** | Tenacity retry decorator with timeout detection |
| **Module/Component** | `oms_backend/repository/base.py`, `oms_backend/infrastructure/fault_injection.py` |
| **Implementation** | `Database.get_session()` with `@retry` decorator, `FaultInjector` class |
| **Verification Method** | Verify requests timeout within configured limit (35s), no hanging requests |
| **Tactic** | Availability > Detect Faults > Timeout |

## NFR 2.2 - Graceful Degradation

| Aspect | Details |
|--------|---------|
| **NFR** | Maintain the most critical system functions in the presence of component failures, while dropping less critical functions |
| **Architectural Mechanism** | Retry with exponential backoff, fault isolation |
| **Module/Component** | `oms_backend/service/payment_service.py`, `oms_backend/repository/base.py` |
| **Implementation** | `PaymentService.create_payment()` with `@retry`, session rollback on failure |
| **Verification Method** | System maintains >90% availability under transient fault conditions |
| **Tactic** | Availability > Recover from Faults > Graceful Degradation |

## NFR 2.3 - State Resynchronization

| Aspect | Details |
|--------|---------|
| **NFR** | States of active and standby components are periodically compared to ensure synchronization |
| **Architectural Mechanism** | Background state synchronization task |
| **Module/Component** | `oms_backend/infrastructure/state_sync.py`, `oms_backend/server.py` |
| **Implementation** | `StateSynchronizer._sync_loop()`, `StateSynchronizer._sync_once()` |
| **Verification Method** | Query `/nfr-stats` endpoint; verify sync mechanism is running and components registered |
| **Tactic** | Availability > Detect Faults > State Resynchronization |

## NFR 2.4 - Transactions

| Aspect | Details |
|--------|---------|
| **NFR** | Leverage transactional semantics to ensure ACID properties for asynchronous messages |
| **Architectural Mechanism** | SQLAlchemy async sessions with commit/rollback |
| **Module/Component** | `oms_backend/repository/base.py`, Service layer (`order_service.py`, `invoice_service.py`, `payment_service.py`) |
| **Implementation** | `Database.get_session()` with async context manager, session.commit()/rollback() |
| **Verification Method** | Create related entities; verify referential integrity and atomic operations |
| **Tactic** | Data Integrity > Maintain Integrity > Transactions |

---

## Summary Table

| NFR | Mechanism | Component | Tactic | Verification |
|-----|-----------|-----------|--------|--------------|
| 1.1 | Token bucket rate limiter | rate_limiter.py, server.py | Limit Event Response | 429 on burst |
| 1.2 | In-memory cache | base.py, services | Caching | Faster 2nd request |
| 2.1 | Retry + timeout | base.py, fault_injection.py | Timeout | No hanging requests |
| 2.2 | Retry with backoff | payment_service.py | Graceful Degradation | >90% availability |
| 2.3 | Background sync task | state_sync.py | State Resynchronization | Sync running |
| 2.4 | Async transactions | base.py, services | Transactions | Referential integrity |
