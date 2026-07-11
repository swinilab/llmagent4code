# NFR Traceability Matrix

## NFR 2.1 — Graceful Degradation

| Mechanism | Module/Component | Verification Method | Expected Behavior |
|-----------|-----------------|---------------------|-------------------|
| Circuit Breaker (AsyncCircuitBreaker) | `app/infrastructure/circuit_breaker.py` | 1. Start OMS API and PostgreSQL<br>2. Do NOT start recommendation service on port 9001<br>3. Send 20 concurrent POST /api/v1/orders (core checkout)<br>4. Send 20 concurrent GET /api/v1/recommendations/{id} (non-essential) | Core checkout: ≥90% success rate (201 Created)<br>Non-essential: 100% return `{"recommendations": [], "fallback": true}` after 3 failures trigger circuit breaker OPEN |
| Fallback response | `app/infrastructure/circuit_breaker.py` line 140-158 (`get_recommendations_with_fallback`) | Same as above — inspect response body | Response contains `"fallback": true` and empty recommendations list |
| Connection pool sizing (10 pool, 20 overflow) | `app/infrastructure/database.py` | JMeter: 200 concurrent users, ramp-up 10s, loop 5 times | Active connections ≤30 (pool+overflow). Requests queue with <5s wait. No connection timeouts. |
| Request timeout (30s) | `app/config.py` `REQUEST_TIMEOUT` | JMeter: send request with 60s delay | Server closes connection at 30s. Returns 503. Frees worker for next request. |

## NFR 2.2 — Fault Detection and Recovery

| Mechanism | Module/Component | Verification Method | Expected Behavior |
|-----------|-----------------|---------------------|-------------------|
| Health check endpoint | `app/api/health.py` + `app/services/health_service.py` | `curl http://localhost:8000/api/v1/health` | Returns `{"status": "healthy", "database": "connected", "uptime_seconds": N}` |
| Database health probe | `app/infrastructure/lifecycle.py` `check_database_health()` | Block DB port: `sudo iptables -A INPUT -p tcp --dport 5432 -j DROP` | Health endpoint returns `{"status": "degraded", "database": "disconnected"}` |
| Retry with exponential backoff | `app/infrastructure/retry.py` `db_retry` decorator | 1. Block DB port<br>2. Send POST /api/v1/orders<br>3. Unblock DB port after 3s<br>4. Retry happens automatically | First 1-2 requests fail (503/500). After unblock, request succeeds. Logs show retry attempts with increasing wait times. |
| Session rollback before retry | `app/infrastructure/retry.py` `_rollback_session_before_retry` | Inject DBAPIError in repository method | Session is rolled back before each retry. No "nested transaction" errors in logs. |
| Connection validation (pool_pre_ping) | `app/infrastructure/database.py` | Restart PostgreSQL while OMS is running | Next DB query detects broken connection, acquires new one. No 500 errors after PostgreSQL restart. |
| Startup DB check | `app/infrastructure/lifecycle.py` `startup_routine()` | Start OMS without PostgreSQL running | Logs: "Database is unreachable. Application will start but may fail." Health endpoint returns degraded. |

## NFR 2.3 — State Preservation

| Mechanism | Module/Component | Verification Method | Expected Behavior |
|-----------|-----------------|---------------------|-------------------|
| Transactional Outbox | `app/adapters/outbox.py` | 1. Create order<br>2. Kill OMS with `kill -9` during order creation<br>3. Restart OMS<br>4. Check outbox_messages table | All committed orders have corresponding outbox_messages rows. Unprocessed messages are re-delivered on restart. |
| Optimistic locking (version field) | `app/adapters/repositories.py` `update_status()` | 1. Load order (version=1)<br>2. Send two concurrent transition requests<br>3. One succeeds (version→2), one fails with "Optimistic lock conflict" | No lost updates. Conflicting request gets 409 Conflict response. |
| State recovery on startup | `app/infrastructure/lifecycle.py` `recover_in_flight_orders()` | 1. Create order (status=CREATED)<br>2. Kill OMS with `kill -9`<br>3. Restart OMS<br>4. Check logs | Logs: "In-flight order detected on startup: {id} (status=CREATED)". Order is listed in recovery summary. |
| Auto-restart on crash | `deploy/systemd/oms.service` (Restart=always) | `kill -9 <oms_pid>` | systemd restarts OMS within 5 seconds. Health endpoint becomes healthy within 15s. |
| Docker restart policy | `deploy/docker-compose.yml` (restart: unless-stopped) | `docker kill oms-api` | Docker restarts container. Health check passes within 30s. |
| Atomic status + invoice_ref update | `app/adapters/repositories.py` `update_status()` | 1. Create invoice for order<br>2. Check order.invoice_ref and order.status | Both updated in single SQL UPDATE. No race condition where status changes but invoice_ref doesn't. |
| Idempotency key (payments) | `app/domain/models.py` Payment.idempotency_key (unique) | 1. Process payment with key="test-1"<br>2. Process same payment again with same key | Second request returns existing payment. No duplicate charge. |
