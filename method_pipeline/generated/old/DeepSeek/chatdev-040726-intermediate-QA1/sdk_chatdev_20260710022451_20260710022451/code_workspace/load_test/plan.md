# Load-Test Plan — OMS Backend

## 1. Objectives

| NFR | Metric | Threshold | Tool |
|-----|--------|-----------|------|
| NFR 1.1 (checkout) | p95 latency for `POST /api/v1/orders` | ≤ 300 ms | Locust |
| NFR 1.1 (search) | p95 latency for `GET /api/v1/products` | ≤ 150 ms | Locust |
| NFR 1.2 | Sustained 2 000 concurrent users, avg queueing < 50 ms | < 50 ms | /metrics endpoint |
| NFR 1.3 | 3x spike (6 000 users in 60 s) — no crashes, no silent loss | 0% error rate (excluding 429) | Locust + /metrics |

## 2. Scenarios

### Baseline (200 users)
- 200 concurrent virtual users
- Spawn rate: 10 users/s
- Duration: 5 minutes
- Expected: all NFRs pass comfortably

### Sustained Load (2 000 users)
- 2 000 concurrent virtual users (target concurrency)
- Spawn rate: 50 users/s
- Duration: 10 minutes
- Expected: p95 checkout ≤ 300 ms, p95 search ≤ 150 ms, queueing < 50 ms

### Spike (6 000 users)
- Ramp from 0 to 6 000 users in 60 seconds (3x baseline)
- Spawn rate: 100 users/s
- Duration: 5 minutes total
- Expected: rate limiter returns 429 for excess requests, no crashes, no unbounded memory

## 3. Metrics to Capture

| Metric | Source | Pass/Fail |
|--------|--------|-----------|
| p50/p95/p99 latency (checkout) | Locust stats | p95 ≤ 300 ms |
| p50/p95/p99 latency (search) | Locust stats | p95 ≤ 150 ms |
| Throughput (RPS) | Locust stats | ≥ 500 RPS at sustained load |
| Error rate (non-429) | Locust stats | < 1% |
| CPU usage | `docker stats` / `psutil` | < 80% |
| Memory usage | `docker stats` / `psutil` | < 4 GB (container limit) |
| Rate limiter queue depth | GET /metrics | Available tokens > 0 at steady state |
| Request queueing time | /metrics latency histograms | p95 < 50 ms |

## 4. Running the Tests

```bash
# Start the stack
docker compose up -d

# Run migrations
alembic upgrade head

# Baseline
locust -f load_test/locustfile.py --scenario baseline --host http://localhost:8000 --headless --csv=results/baseline

# Sustained
locust -f load_test/locustfile.py --scenario sustained --host http://localhost:8000 --headless --csv=results/sustained

# Spike
locust -f load_test/locustfile.py --scenario spike --host http://localhost:8000 --headless --csv=results/spike
```

## 5. Instrumentation

- **/metrics** endpoint exposes real-time latency histograms, request counts, and rate-limiter state.
- **Structured JSON logs** with correlation IDs enable end-to-end tracing.
- **Locust CSV output** provides detailed percentiles and throughput data.
