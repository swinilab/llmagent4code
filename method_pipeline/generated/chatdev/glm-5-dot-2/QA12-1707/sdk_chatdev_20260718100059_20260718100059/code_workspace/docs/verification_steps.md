# NFR Verification Steps

Concrete commands and observations to verify each Non-Functional Requirement
is satisfied. Run these against a running instance of the OMS backend
(`uv run uvicorn oms.main:app --port 8000` or `docker compose up`).

---

## NFR 1.1 — Response Time

**Goal:** Core journeys (product search, cart, checkout) must minimize
round-trip latency under load.

### Verification

1. **Check the `X-Response-Time-ms` header on a core journey:**
   ```bash
   curl -s -o /dev/null -D - "http://localhost:8000/api/v1/products/search?q=laptop"
   ```
   **Expected:** Response header `X-Response-Time-ms: <value>` where value is
   well under 500 ms. The `RequestTimingMiddleware` adds this header to every
   response.

2. **Verify eager loading avoids N+1 queries (order with relationships):**
   ```bash
   # Create a customer, product, and order first (see workflow in README)
   curl -s "http://localhost:8000/api/v1/orders/{order_id}" | python -m json.tool
   ```
   **Expected:** Single response containing customer, line_items (with
   products), invoice, and payments — all loaded in a bounded number of
   `selectin` queries, not N+1. Check server logs for query count.

3. **Load test with wrk:**
   ```bash
   wrk -t4 -c100 -d10s "http://localhost:8000/api/v1/products/search?q=laptop"
   ```
   **Expected:** High throughput with p99 latency < 500 ms.

---

## NFR 1.2 — Concurrency & Resource Utilization

**Goal:** System must exploit available server resources with minimal queuing.

### Verification

1. **Confirm async I/O and connection pool:**
   ```bash
   curl -s "http://localhost:8000/health/ready" | python -m json.tool
   ```
   **Expected:** `checks.database` is `"ok"`, confirming the async engine and
   connection pool are active (`pool_pre_ping` prevents stale connections).

2. **Concurrent request test:**
   ```bash
   # Fire 50 concurrent requests
   for i in $(seq 1 50); do
     curl -s -o /dev/null -w "%{http_code} %{time_total}\n" \
       "http://localhost:8000/api/v1/products/search?q=laptop" &
   done
   wait
   ```
   **Expected:** All return 200 with low individual latency. The async event
   loop handles all 50 concurrently without serial blocking.

3. **Check queue workers are running:**
   ```bash
   curl -s "http://localhost:8000/health/ready" | python -m json.tool
   # Look for: checks.queue.running == true, worker_count > 0
   ```

---

## NFR 1.3 — Queue Management

**Goal:** Sudden spikes must not crash the system.

### Verification

1. **Inspect queue configuration and metrics:**
   ```bash
   curl -s "http://localhost:8000/health/ready" | python -c "
   import sys, json
   data = json.load(sys.stdin)
   print(json.dumps(data['checks']['queue'], indent=2))
   "
   ```
   **Expected:** `max_size` matches `OMS_QUEUE_MAX_SIZE` (default 500),
   `worker_count` matches `OMS_QUEUE_WORKER_COUNT` (default 4),
   `running` is `true`.

2. **Verify bounded queue rejects overflow:**
   The `QueueManager.enqueue` raises `QueueFullError` when the queue is full.
   Inspect the source in `oms/core/queue_manager.py` — the `try_enqueue` method
   returns `False` on `asyncio.QueueFull`, and `enqueue` raises
   `QueueFullError`. The HTTP layer can translate this to 503.

3. **Graceful shutdown drains the queue:**
   ```bash
   # Start server, enqueue tasks, then send SIGTERM
   kill -TERM $(pgrep -f uvicorn)
   ```
   **Expected:** Logs show `QueueManager stopped (processed=N, failed=M)` —
   workers finish in-flight tasks before exiting.

---

## NFR 2.1 — Graceful Degradation

**Goal:** Under extreme resource contention, degrade non-essential features to
keep core checkout available.

### Verification

1. **Normal operation — all endpoints available:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/products/search?q=laptop"
   # Expected: 200
   ```

2. **Stress CPU above threshold (default 85%):**
   ```bash
   # In a separate terminal, saturate CPU
   stress -c 4 &  # or: yes > /dev/null & (repeat 4 times)
   sleep 12       # wait for degradation check interval (10s)

   # Non-essential endpoint should be degraded
   curl -s -w "\n%{http_code}\n" "http://localhost:8000/api/v1/products/search?q=laptop"
   # Expected: 503 with {"detail":"Service temporarily degraded...","degraded":true}

   # Core endpoint should still work
   curl -s -w "\n%{http_code}\n" -X POST "http://localhost:8000/api/v1/orders/" \
     -H "Content-Type: application/json" \
     -d '{"customer_id":"<existing-id>","items":[{"product_id":"<existing-id>","quantity":1}]}'
   # Expected: 201 (order created successfully)

   # Stop the stress
   killall stress  # or: killall yes
   sleep 12        # wait for degradation to lift

   # Non-essential endpoint should be restored
   curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/products/search?q=laptop"
   # Expected: 200
   ```

3. **Check server logs for degradation state changes:**
   ```bash
   docker compose logs oms | grep -i "degradation"
   # Expected: "Graceful degradation ACTIVE ..." and later "Graceful degradation LIFTED ..."
   ```

---

## NFR 2.2 — Fault Detection and Recovery

**Goal:** Detect internal component failures and automatically attempt to
recover or reconnect.

### Verification

1. **Circuit breaker is CLOSED under normal conditions:**
   ```bash
   curl -s "http://localhost:8000/health/ready" | python -c "
   import sys, json
   data = json.load(sys.stdin)
   print(json.dumps(data['checks']['circuit_breakers'], indent=2))
   "
   # Expected: open_count == 0, all breakers state == "closed"
   ```

2. **Circuit breaker opens on repeated failures:**
   The payment gateway call in `PaymentService.create_payment` is wrapped with
   `@with_circuit_breaker("payment_gateway")`. After `cb_failure_threshold`
   (default 5) consecutive failures, the breaker opens.

   Inspect the code in `oms/core/resilience.py` — the `CircuitBreaker.call`
   method records failures via `_on_failure()` and transitions to OPEN when
   `failure_count >= failure_threshold`.

3. **Automatic recovery (OPEN → HALF_OPEN → CLOSED):**
   After `cb_recovery_timeout` (default 30s), the breaker enters HALF_OPEN and
   allows `cb_half_open_max_calls` (default 3) probe calls. If they succeed,
   the circuit closes automatically.

   ```bash
   # Wait 30s after the breaker opened, then check state
   curl -s "http://localhost:8000/health/ready" | python -c "
   import sys, json
   data = json.load(sys.stdin)
   for b in data['checks']['circuit_breakers']['details']:
       print(f\"{b['name']}: {b['state']}\")
   "
   # Expected: state transitions from "open" → "half_open" → "closed"
   ```

4. **DB auto-reconnect:**
   The engine is created with `pool_pre_ping=True` in `oms/database.py`. This
   pings each connection before use and replaces stale ones automatically.

---

## NFR 2.3 — State Preservation

**Goal:** On unexpected process crash, restore operational state and resume
processing pending orders with minimal data loss.

### Verification

1. **Create an order (PENDING state):**
   ```bash
   # Create customer and product first, then:
   curl -s -X POST "http://localhost:8000/api/v1/orders/" \
     -H "Content-Type: application/json" \
     -d '{"customer_id":"<id>","items":[{"product_id":"<id>","quantity":1}]}'
   # Save the order_id
   ```

2. **Kill the process unexpectedly (simulate crash):**
   ```bash
   # Find the process
   pgrep -f "uvicorn oms.main"
   # Kill it abruptly
   kill -9 <pid>
   ```

3. **Restart the server and verify recovery:**
   ```bash
   uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000
   ```
   **Expected in logs:**
   ```
   Recovery: found 1 order(s) in state pending — resuming processing
   Recovery: order <id> is in state pending (created <ts>, updated <ts>)
   Recovery scan complete: 1 order(s) in non-terminal states
   ```

4. **Verify the order persisted (no data loss):**
   ```bash
   curl -s "http://localhost:8000/api/v1/orders/<order_id>" | python -m json.tool
   # Expected: 200 with the order in "pending" status — data survived the crash
   ```

5. **Verify WAL files exist (durability mechanism):**
5. **Verify WAL files exist (durability mechanism):**
   ```bash
   # Local (default path):
   ls -la oms.db*
   # Docker (persisted inside the volume):
   docker compose exec oms ls -la /app/data/oms.db*
   # Expected: oms.db, oms.db-wal, oms.db-shm all present
   The `-wal` file contains write-ahead log entries that are checkpointed
   into the main `oms.db` file. `synchronous=NORMAL` ensures transactions
   are durable across process crashes. Under Docker the file lives at
   `/app/data/oms.db` inside the `oms-data` volume (NFR 2.3).

6. **Verify persistence across container recreation (Docker, NFR 2.3):**
   ```bash
   docker compose up -d
   # Create a customer + order via the API
   curl -s -X POST http://localhost:8000/api/v1/customers/ -H 'Content-Type: application/json' \
     -d '{"name":"Persist Test","address":"1 St","phone":"+15550000000","role":"customer"}'
   docker compose down
   docker compose up -d
   curl -s http://localhost:8000/api/v1/customers/ | python -m json.tool
   # Expected: the previously created customer is still present — the
   # oms-data volume at /app/data preserved /app/data/oms.db.
   ```