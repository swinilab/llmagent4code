# NFR Verification Steps

## NFR 1.1 Response Time

**Verification Method:** Load test with k6 shows p95 latency < 200ms for checkout endpoint

**Steps:**
1. Start the application: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Install k6: `brew install k6` or download from https://k6.io
3. Create load test script:
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 50,
  duration: '30s',
};

export default function () {
  const res = http.post('http://localhost:8000/api/v1/orders', {
    customerRef: 'test-customer-id',
    lineItems: [{ productRef: 'test-product-id', quantity: 1 }]
  }, {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, {
    'status is 202': (r) => r.status === 202,
    'latency < 200ms': (r) => r.timings.duration < 200,
  });
  sleep(0.1);
}
```
4. Run: `k6 run loadtest.js`
5. Verify p95 latency < 200ms in output

---

## NFR 1.2 Concurrency & Resource Utilization

**Verification Method:** ab -c 100 shows throughput scales near-linearly up to worker count

**Steps:**
1. Start the application
2. Install Apache Bench: `sudo apt-get install apache2-utils`
3. Run concurrent test: `ab -c 100 -n 1000 http://localhost:8000/api/v1/products`
4. Observe throughput in requests/second
5. Compare with single-threaded: `ab -c 1 -n 1000 http://localhost:8000/api/v1/products`
6. Verify near-linear scaling (throughput should increase ~4x with 4 workers)

---

## NFR 1.3 Queue Management

**Verification Method:** Burst of 1000 requests returns 503 without dropped connections; queue_size bounded per /health/queue

**Steps:**
1. Start the application
2. Send burst of requests:
```bash
for i in {1..1000}; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/orders \
    -H "Content-Type: application/json" \
    -d '{"customerRef":"test","lineItems":[{"productRef":"test","quantity":1}]}' &
done
wait
```
3. Check queue status: `curl http://localhost:8000/api/v1/health/queue`
4. Verify:
   - Some requests return 503 (queue full)
   - No connection drops (all return valid HTTP status)
   - queue_size never exceeds max_size (1000)

---

## NFR 2.1 Graceful Degradation

**Verification Method:** Kill background worker under load; checkout endpoint still returns 2xx while non-essential endpoints return 503

**Steps:**
1. Start the application
2. Generate load: `while true; do curl -s http://localhost:8000/api/v1/health/queue; sleep 0.1; done &`
3. Check degradation status: `curl http://localhost:8000/api/v1/health/degradation`
4. Verify core endpoint (orders) still works:
   ```bash
   curl -X POST http://localhost:8000/api/v1/orders \
     -H "Content-Type: application/json" \
     -d '{"customerRef":"test","lineItems":[{"productRef":"test","quantity":1}]}'
   ```
5. Under high load, verify non-essential endpoints may return degraded response

---

## NFR 2.2 Fault Detection and Recovery

**Verification Method:** Kill DB connection mid-request; observe automatic reconnect within N seconds via /health/ready

**Steps:**
1. Start the application
2. Monitor health: `watch -n 1 'curl -s http://localhost:8000/api/v1/health/ready'`
3. Simulate DB failure (for SQLite, delete the file):
   ```bash
   rm -f oms.db
   ```
4. Observe health endpoint shows "unhealthy"
5. Application should auto-reconnect on next request
6. Verify health returns to "ready" after reconnection
7. Check logs for retry attempts using tenacity

---

## NFR 2.3 State Preservation

**Verification Method:** Kill process mid-queue-processing, restart, confirm pending orders resume from persisted state with no loss

**Steps:**
1. Start the application
2. Create several orders rapidly:
```bash
for i in {1..10}; do
  curl -s -X POST http://localhost:8000/api/v1/orders \
    -H "Content-Type: application/json" \
    -d "{\"customerRef\":\"test\",\"lineItems\":[{\"productRef\":\"test\",\"quantity\":$i}]}" &
done
```
3. Immediately kill the process: `pkill -f uvicorn`
4. Check WAL file exists: `ls -la oms_wal.db`
5. Restart the application
6. Check pending operations were recovered:
   ```bash
   curl http://localhost:8000/api/v1/orders/recent
   ```
7. Verify orders are present (may need to wait for async processing)
8. Check WAL entries: pending should be 0 after recovery

---

## Automated Verification Script

Create `verify_nfrs.sh`:

```bash
#!/bin/bash
set -e

echo "Starting NFR verification..."

# Start server in background
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 5

# Test health
echo "Testing health endpoints..."
curl -f http://localhost:8000/api/v1/health/live || exit 1
curl -f http://localhost:8000/api/v1/health/ready || exit 1

# Test queue management
echo "Testing queue management..."
QUEUE_STATUS=$(curl -s http://localhost:8000/api/v1/health/queue)
echo "Queue status: $QUEUE_STATUS"

# Test degradation
echo "Testing degradation..."
DEGRADE_STATUS=$(curl -s http://localhost:8000/api/v1/health/degradation)
echo "Degradation status: $DEGRADE_STATUS"

# Cleanup
kill $SERVER_PID 2>/dev/null || true
echo "NFR verification complete!"
```

Run: `chmod +x verify_nfrs.sh && ./verify_nfrs.sh`
