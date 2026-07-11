# Reliability Test Plan

## 1. Degradation Test (NFR 2.1)

**Tool:** Custom Python script using `httpx` (see `tests/test_degradation.py`)

**Objective:** Verify that under severe load, core checkout remains available while non-essential services return fallback.

### Test Setup
1. Start OMS API on `localhost:8000`
2. Start PostgreSQL on `localhost:5432`
3. Do NOT start the recommendation service (port 9001)
4. Run: `python tests/test_degradation.py`

### Test Steps
1. Create test customer and product
2. Send 20 concurrent POST `/api/v1/orders` requests (core checkout)
3. Simultaneously send 20 concurrent GET `/api/v1/recommendations/{id}` requests (non-essential)
4. Measure success rates and response times

### Pass Criteria
- Core checkout: ≥90% success rate (201 Created)
- Non-essential: ≥1 response with `{"fallback": true}` (circuit breaker opened)
- No cascading failures: core checkout errors must not increase when recommendations fail

### Failure Injection
- The recommendation service is simply not started
- After 3 failed calls, the circuit breaker transitions to OPEN
- Subsequent calls return fallback immediately (no HTTP timeout)

### Expected Log Output
```
WARNING  Circuit breaker 'recommendation' OPEN (failures=3/3)
WARNING  Recommendation circuit breaker open or service unavailable for customer X. Returning fallback (empty recommendations).
```

---

## 2. Recovery Test (NFR 2.2)

**Tool:** Custom Python script using `httpx` + `iptables` (see `tests/test_recovery.py`)

**Objective:** Verify that the system detects DB failures and auto-recovers without manual restart.

### Test Setup
1. Start OMS API on `localhost:8000`
2. Start PostgreSQL on `localhost:5432`
3. Run with sudo: `sudo python tests/test_recovery.py`

### Test Steps
1. Verify initial health: `GET /api/v1/health` → healthy
2. Block DB port: `sudo iptables -A INPUT -p tcp --dport 5432 -j DROP`
3. Send 5 health check requests during block → expect degraded/errors
4. Unblock DB port: `sudo iptables -D INPUT -p tcp --dport 5432 -j DROP`
5. Wait 10 seconds for recovery
6. Send health check requests → expect healthy

### Pass Criteria
- During block: health endpoint returns `{"status": "degraded", "database": "disconnected"}` or connection errors
- After unblock: health endpoint returns `{"status": "healthy", "database": "connected"}` within 10 seconds
- No manual restart required

### Failure Injection
- iptables DROP rule simulates network partition to PostgreSQL
- Connection pool detects broken connections via `pool_pre_ping=True`
- After unblock, new connections are established automatically

### Expected Log Output
```
ERROR    Database health check failed: could not connect to server
WARNING  Retrying DB operation (attempt 2/3)...
INFO     Database connection verified.
```

---

## 3. State Preservation Test (NFR 2.3)

**Tool:** Custom Python script using `httpx` + `os.kill` (see `tests/test_state.py`)

**Objective:** Verify that committed transactions survive a process crash and that in-flight orders are detected on restart.

### Test Setup
1. Start OMS API on `localhost:8000`
2. Start PostgreSQL on `localhost:5432`
3. Run: `python tests/test_state.py`

### Test Steps
1. Create test customer and product
2. Place 3 orders (committed to DB)
3. Find OMS PID via `pgrep -f "uvicorn app.main:app"`
4. Force-kill: `os.kill(pid, signal.SIGKILL)`
5. Verify process is dead
6. Restart OMS process
7. Wait for health check to pass
8. Verify all 3 committed orders are retrievable via `GET /api/v1/orders/{id}`
9. Check startup logs for in-flight order detection

### Pass Criteria
- All 3 committed orders are present in DB after restart
- Startup logs show: "In-flight order detected on startup: {id} (status=CREATED)"
- Health endpoint returns healthy after restart

### Failure Injection
- `SIGKILL` (kill -9) simulates an abrupt process crash
- No graceful shutdown — the process has zero time to flush buffers
- PostgreSQL's WAL ensures all committed transactions are durable

### Expected Log Output
```
WARNING  In-flight order detected on startup: <uuid> (status=CREATED)
INFO     Found 3 in-flight order(s) requiring attention.
INFO     Order Management System started successfully.
```

---

## 4. Load Test (Performance Baseline)

**Tool:** `locust` or `wrk`

**Objective:** Establish performance baseline and verify resource limits.

### Test Commands
```bash
# Install locust
pip install locust

# Run load test
locust --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=5m
```

### Test Scenarios
1. **Checkout flow:** POST /api/v1/orders (50% of requests)
2. **Order lookup:** GET /api/v1/orders/{id} (30% of requests)
3. **Health check:** GET /api/v1/health (20% of requests)

### Pass Criteria
- P95 latency < 500ms for all endpoints
- Error rate < 1%
- CPU usage < 80% (2 vCPUs)
- Memory usage < 3.5 GB (4 GB limit)

---

## 5. Optimistic Locking Test

**Objective:** Verify that concurrent state transitions don't cause lost updates.

### Test Steps
1. Create an order (status=CREATED, version=1)
2. Send 10 concurrent POST `/api/v1/orders/{id}/transition` with event `review_accept`
3. Exactly 1 request succeeds (status=ACCEPTED, version=2)
4. 9 requests fail with 409 Conflict

### Pass Criteria
- Exactly 1 success, 9 failures
- Order version is exactly 2 after test
- No duplicate state transitions

---

## 6. Idempotency Test

**Objective:** Verify that duplicate payment requests don't cause duplicate charges.

### Test Steps
1. Create order, accept it, create invoice
2. Send POST `/api/v1/payments` with idempotency_key="test-key-1"
3. Send same request again with same idempotency_key
4. Both return 201, but only 1 payment record exists in DB

### Pass Criteria
- Second request returns existing payment (same ID)
- Only 1 payment record with idempotency_key="test-key-1"
- Order transitions to PAID only once
