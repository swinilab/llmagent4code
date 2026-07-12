# NFR Verification Steps

This document provides reproducible steps for a reviewer to confirm each NFR is satisfied.

---

## NFR 1.1 — Response Time: Core journeys minimize round-trip latency under load

### V1.1.1 — Verify async I/O (no blocking DB calls in request path)

**Method:** Add a breakpoint or log in `db/connection.py` to confirm queries are awaited.

```bash
# Confirm asyncpg is used (not psycopg2 sync)
grep -r "asyncpg" oms_backend/db/connection.py
# Expected: imports `asyncpg` via `databases` / SQLAlchemy async engine
```

### V1.1.2 — Verify connection pooling

```python
# In db/connection.py:
# pool_size=20, max_overflow=80 (total 100 connections per worker)
# Run:
curl http://localhost:8000/ready
# Check pool status:
# psql -c "SELECT * FROM pg_stat_activity WHERE datname='oms_db';" | wc -l
# Should show multiple idle connections warming up.
```

### V1.1.3 — Verify GIN index on product search

```sql
psql -d oms_db -c "\d products"
-- Should show: idx_products_name_gin USING gin(to_tsvector(...))
```

### V1.1.4 — Load test with locust (target: p99 < 200ms)

```bash
# Install locust
uv add locust

# Create locustfile.py (provided in tests/)
# Run load test:
locust --host=http://localhost:8000 --users=500 --spawn-rate=50 --run-time=60s --headless
# Verify p99 < 200ms for /api/v1/products/search and /api/v1/orders
```

---

## NFR 1.2 — Concurrency & Resource Utilization: exploit available server resources

### V1.2.1 — Verify multiple gunicorn workers

```bash
# Start via gunicorn
uv run gunicorn -c infra/gunicorn.conf.py server:app &

# Count worker processes
ps aux | grep "uvicorn.workers.UvicornWorker" | grep -v grep | wc -l
# Expected: 2 * CPU_cores + 1 (e.g., 9 on a 4-core machine)
```

### V1.2.2 — Verify asyncpg connection pool settings

```bash
# Check logs on startup:
grep "pool" <(uv run gunicorn -c infra/gunicorn.conf.py server:app 2>&1)
# Should show pool_size=20, max_overflow=80
```

### V1.2.3 — Verify uvloop is the event loop

```python
# In server.py, run() uses loop="uvloop"
# Confirm:
uv run python -c "import uvloop; print(uvloop.__version__)"
```

---

## NFR 1.3 — Queue Management: sudden spikes do not crash the system

### V1.3.1 — Verify rate limiting is active

```bash
# Make 100+ requests per minute per customer
for i in {1..110}; do
  curl -s http://localhost:8000/api/v1/products > /dev/null
done
# 101st request should return 429:
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/products
# Expected: 429
```

### V1.3.2 — Verify circuit breaker on payment service

```python
# In tests/test_payment.py:
# Mock gateway to fail 6 times consecutively
# 6th request should get 503 from circuit breaker
# 7th request after 30s should succeed (half-open recovery)
```

### V1.3.3 — Verify graceful shutdown

```bash
# Start gunicorn in background
uv run gunicorn -c infra/gunicorn.conf.py server:app &
PID=$!

# Send SIGTERM
kill -TERM $PID

# Verify no 502s: check that in-flight requests complete
# Gunicorn log should show: "Graceful worker shutdown completed"
```

### V1.3.4 — Verify background queue handles spike

```bash
# Start worker
uv run python -m infra.worker &

# Spike: create 100 orders rapidly
# Jobs should be queued in Redis, not dropped
redis-cli LLEN arq:queue

# Verify no job loss:
# Jobs should be processed sequentially, failed ones retried 3×
```

---

## Verification Checklist

| # | NFR | Verification | Pass/Fail |
|---|-----|-------------|-----------|
| 1.1.1 | Async I/O | `asyncpg` in db/connection.py | ☐ |
| 1.1.2 | Connection pool | Pool size 20–100 per worker | ☐ |
| 1.1.3 | GIN index | `idx_products_name_gin` exists | ☐ |
| 1.1.4 | Load test | p99 < 200ms on /products, /orders | ☐ |
| 1.2.1 | Workers = 2×CPU+1 | `ps aux \| grep UvicornWorker` | ☐ |
| 1.2.2 | Pool settings | Log shows pool_size/max_overflow | ☐ |
| 1.2.3 | uvloop | `import uvloop` succeeds | ☐ |
| 1.3.1 | Rate limiting | 429 returned after 100+ req/min | ☐ |
| 1.3.2 | Circuit breaker | 503 after 5 gateway failures | ☐ |
| 1.3.3 | Graceful shutdown | SIGTERM drains, no 502 | ☐ |
| 1.3.4 | Queue handles spike | 100 jobs queued, none dropped | ☐ |
