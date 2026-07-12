# OMS Backend - NFR Verification Guide

This document shows how to verify each NFR is satisfied through observation.

## NFR 2.1 Graceful Degradation

**Requirement:** Under extreme resource contention, the system must degrade non-essential features to ensure core checkout functionality remains available.

### Verification Method:

1. **Start the server:**
```bash
python -m src.main
```

2. **Check current feature flags:**
```bash
curl http://localhost:8000/api/v1/health/features
```

Expected response:
```json
{
  "analytics_enabled": true,
  "notifications_enabled": true,
  "audit_log_enabled": true,
  "extended_logging_enabled": true
}
```

3. **Disable non-essential features (simulating resource contention):**
```bash
curl -X POST http://localhost:8000/api/v1/health/features/disable-non-essential
```

Expected response:
```json
{
  "status": "non-essential features disabled"
}
```

4. **Verify flags are disabled:**
```bash
curl http://localhost:8000/api/v1/health/features
```

Expected response:
```json
{
  "analytics_enabled": false,
  "notifications_enabled": false,
  "audit_log_enabled": false,
  "extended_logging_enabled": true
}
```

5. **Verify core checkout still works:**
```bash
# Place and process an order
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{...}'
```

Core checkout endpoints remain functional:
- `POST /api/v1/orders` - Place order
- `POST /api/v1/invoices` - Create invoice
- `POST /api/v1/payments` - Create payment
- `PATCH /api/v1/orders/{id}/ship` - Ship order

6. **Circuit breaker verification:**
```bash
curl http://localhost:8000/api/v1/health/nfr-verification
```

Look for `nfr_2_1_graceful_degradation.circuit_breakers` section.

## NFR 2.2 Fault Detection and Recovery

**Requirement:** The application must detect internal component failures and automatically attempt to recover or reconnect, minimizing user-facing errors.

### Verification Method:

1. **Check overall system health:**
```bash
curl http://localhost:8000/api/v1/health
```

Expected response includes:
```json
{
  "status": "healthy",
  "components": {
    "database": {"status": "healthy", ...},
    "api": {"status": "healthy", ...}
  }
}
```

2. **Check database health specifically:**
```bash
curl http://localhost:8000/api/v1/health/db
```

Expected response:
```json
{
  "status": "healthy",
  "wal_mode": "wal",
  "sync_mode": "normal",
  "integrity": "ok"
}
```

3. **Verify readiness probe:**
```bash
curl http://localhost:8000/api/v1/health/ready
```

4. **NFR verification endpoint:**
```bash
curl http://localhost:8000/api/v1/health/nfr-verification
```

Expected response:
```json
{
  "nfr_2_2_fault_detection": {
    "overall_status": "healthy",
    "component_health": {...},
    "database_health": {...},
    "recovery_available": true
  }
}
```

5. **Simulate fault detection:**
The health checker monitors all registered components. If a component fails:
- The component status changes to "unhealthy"
- The overall status changes to "degraded"
- Recovery is attempted automatically

## NFR 2.3 State Preservation

**Requirement:** In the event of an unexpected application process crash, the system must be able to restore its operational state and resume processing pending orders upon restart with minimal data loss.

### Verification Method:

1. **Verify WAL mode is enabled:**
```bash
curl http://localhost:8000/api/v1/health/db
```

Look for `"wal_mode": "wal"` in the response.

2. **Create an order with idempotency key:**
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "...",
    "line_items": [...],
    "shipping_address": {...},
    "idempotency_key": "unique-key-123"
  }'
```

3. **Repeat the request with same idempotency key:**
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "...",
    "line_items": [...],
    "shipping_address": {...},
    "idempotency_key": "unique-key-123"
  }'
```

The same order should be returned (no duplicate created).

4. **Check state snapshots:**
```bash
curl http://localhost:8000/api/v1/health/nfr-verification
```

Expected response:
```json
{
  "nfr_2_3_state_preservation": {
    "wal_mode_enabled": true,
    "database_integrity": "ok",
    "pending_recoveries": [...],
    "snapshot_count": 0
  }
}
```

5. **Crash recovery test:**
- Start the server
- Create an order
- **Kill the server process** (simulating crash)
- **Restart the server**
- Check the recovery endpoint:
```bash
curl http://localhost:8000/api/v1/orders/recovery/pending
```

If there were pending orders, they will be recovered.

6. **Verify data integrity after restart:**
```bash
curl http://localhost:8000/api/v1/health/db
curl http://localhost:8000/api/v1/orders/<order_id>
```

The order should exist with its state preserved.

## Running All NFR Verification Tests

```bash
# Start the server
python -m src.main &

# Run NFR verification
curl http://localhost:8000/api/v1/health/nfr-verification | jq

# Test graceful degradation
curl -X POST http://localhost:8000/api/v1/health/features/disable-non-essential
curl http://localhost:8000/api/v1/health/features

# Verify core functionality still works
curl http://localhost:8000/api/v1/health/live

# Check database state preservation
curl http://localhost:8000/api/v1/health/db
```

## Summary

| NFR | Verification Endpoint | Key Indicators |
|-----|----------------------|----------------|
| NFR 2.1 | `/api/v1/health/features` | Feature flags disabled, core endpoints still work |
| NFR 2.2 | `/api/v1/health/nfr-verification` | Component health, recovery_available: true |
| NFR 2.3 | `/api/v1/health/nfr-verification` | wal_mode: wal, pending_recoveries tracked |
