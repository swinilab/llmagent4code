# NFR Traceability Matrix

## Overview

This document maps each Non-Functional Requirement to its architectural mechanism, component location, and verification method.

## Requirements Matrix

| NFR ID | Requirement | Architectural Mechanism | Component | Verification Method |
|--------|-------------|------------------------|-----------|---------------------|
| **NFR 2.1** | Graceful Degradation | CircuitBreaker | `src/utils/resilience.py` | Disable non-essential features, observe core checkout continues |
| **NFR 2.1** | Graceful Degradation | FeatureFlags | `src/utils/resilience.py` | `GET /api/v1/health/features` returns all flags |
| **NFR 2.1** | Graceful Degradation | Feature disable endpoint | `src/controllers/health_controller.py` | `POST /api/v1/health/features/disable-non-essential` |
| **NFR 2.2** | Fault Detection | HealthChecker | `src/utils/resilience.py` | `GET /api/v1/health` shows component status |
| **NFR 2.2** | Fault Detection | Component registration | `src/controllers/health_controller.py` | Components appear in health response |
| **NFR 2.2** | Fault Detection | Circuit breaker state | `src/utils/resilience.py` | `nfr_2_2_fault_detection.recovery_available: true` |
| **NFR 2.2** | Fault Detection | Database health check | `src/infrastructure/database.py` | `GET /api/v1/health/db` shows WAL mode |
| **NFR 2.3** | State Preservation | WAL journal mode | `src/infrastructure/database.py` | `wal_mode: wal` in db health check |
| **NFR 2.3** | State Preservation | Idempotency keys | `src/infrastructure/repositories.py` | Duplicate requests return same order |
| **NFR 2.3** | State Preservation | State snapshots | `src/utils/resilience.py` | `snapshot_count` in NFR verification |
| **NFR 2.3** | State Preservation | StateManager | `src/utils/resilience.py` | Snapshots saved to disk on operations |
| **NFR 2.3** | State Preservation | Recovery on startup | `src/main.py` | `recover_pending_orders()` called on startup |

## NFR 2.1: Graceful Degradation

### Description
Under extreme resource contention, the system must degrade non-essential features to ensure core checkout functionality remains available.

### Mechanisms

1. **CircuitBreaker** (`src/utils/resilience.py`)
   - Opens circuit after configurable failure threshold
   - Transitions to half-open to test recovery
   - Prevents cascade failures

2. **FeatureFlags** (`src/utils/resilience.py`)
   - Toggle non-essential features at runtime
   - `analytics_enabled` - Analytics processing
   - `notifications_enabled` - Email/push notifications
   - `audit_log_enabled` - Detailed audit logging

### Verification
```bash
# Check feature flags
curl http://localhost:8000/api/v1/health/features

# Disable non-essential features
curl -X POST http://localhost:8000/api/v1/health/features/disable-non-essential

# Verify core endpoints still work
curl http://localhost:8000/api/v1/health/live
curl -X POST http://localhost:8000/api/v1/orders  # Should work
```

## NFR 2.2: Fault Detection and Recovery

### Description
The application must detect internal component failures and automatically attempt to recover or reconnect, minimizing user-facing errors.

### Mechanisms

1. **HealthChecker** (`src/utils/resilience.py`)
   - Registers components with health check functions
   - Periodic health monitoring
   - Tracks failure counts

2. **CircuitBreaker Integration** (`src/utils/resilience.py`)
   - Circuit breaker per component
   - Automatic recovery attempts
   - State transitions: CLOSED → OPEN → HALF_OPEN → CLOSED

3. **Database Health Check** (`src/infrastructure/database.py`)
   - Checks WAL mode
   - Verifies sync mode
   - Runs integrity check

### Verification
```bash
# Overall health
curl http://localhost:8000/api/v1/health

# Component health
curl http://localhost:8000/api/v1/health/nfr-verification

# Database health
curl http://localhost:8000/api/v1/health/db

# Readiness probe
curl http://localhost:8000/api/v1/health/ready
```

## NFR 2.3: State Preservation

### Description
In the event of an unexpected application process crash, the system must be able to restore its operational state and resume processing pending orders upon restart with minimal data loss.

### Mechanisms

1. **WAL Journal Mode** (`src/infrastructure/database.py`)
   - Enabled via `PRAGMA journal_mode=WAL`
   - Provides ACID durability
   - Crash-safe writes

2. **Idempotency Keys** (`src/infrastructure/repositories.py`)
   - Unique key per order/invoice/payment
   - Prevents duplicate creation
   - Client-provided or auto-generated

3. **State Snapshots** (`src/utils/resilience.py`)
   - Periodic snapshots to disk
   - Recoverable on restart
   - JSON format

4. **StateManager** (`src/utils/resilience.py`)
   - Manages snapshot lifecycle
   - Tracks pending operations
   - Recovery point identification

### Verification
```bash
# Check WAL mode
curl http://localhost:8000/api/v1/health/db | grep wal_mode

# Create order with idempotency key
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key": "test-key-123", ...}'

# Repeat request - should return same order
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key": "test-key-123", ...}'

# Check pending recoveries
curl http://localhost:8000/api/v1/health/nfr-verification | jq .nfr_2_3_state_preservation

# Check recovery pending orders
curl http://localhost:8000/api/v1/orders/recovery/pending
```

## Component Responsibilities

| Component | NFR Responsibilities |
|-----------|---------------------|
| `src/utils/resilience.py` | CircuitBreaker, FeatureFlags, StateManager, HealthChecker |
| `src/infrastructure/database.py` | WAL mode, health checks |
| `src/infrastructure/repositories.py` | Idempotency key enforcement |
| `src/controllers/health_controller.py` | Health API endpoints, feature flag API |
| `src/main.py` | Recovery on startup |
| `src/services/*.py` | State snapshots on operations |

## Traceability Verification Checklist

- [ ] CircuitBreaker implemented and used in services
- [ ] FeatureFlags disable_non_essential() works
- [ ] HealthChecker registers all components
- [ ] Database WAL mode confirmed
- [ ] Idempotency keys prevent duplicates
- [ ] State snapshots are created on order operations
- [ ] Recovery on startup calls recover_pending_orders()
- [ ] NFR verification endpoint returns all mechanisms
