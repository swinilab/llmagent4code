"""
Local deployment guide for the OMS backend.
"""
# Order Management System — Local Deployment Guide

## Prerequisites

- Docker & Docker Compose (for containerized deployment)
- OR Python 3.12+ with `uv` (for bare-metal deployment)
- At least 8 GB RAM, 4 CPU cores recommended

## Quick Start (Docker Compose)

```bash
# 1. Clone and enter the project
cd oms

# 2. Start all services
docker compose up --build -d

# 3. Verify health
curl http://localhost:8000/health

# 4. View metrics
curl http://localhost:8000/metrics

# 5. OpenAPI docs
open http://localhost:8000/docs
```

## Bare-Metal Deployment

```bash
# 1. Start dependencies
docker run -d --name oms-postgres -e POSTGRES_USER=oms -e POSTGRES_PASSWORD=oms -e POSTGRES_DB=oms -p 5432:5432 postgres:16-alpine
docker run -d --name oms-redis -p 6379:6379 redis:7-alpine
docker run -d --name oms-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management-alpine

# 2. Install Python deps
uv sync

# 3. Run the app
uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Running Tests

```bash
uv run pytest oms/tests/ -v
```

## Running Load Tests

```bash
# Scenario 1: Baseline (2,000 users, 10 min)
uv run locust -f oms/load_test/locustfile.py --host http://localhost:8000 --users 2000 --spawn-rate 50 --run-time 10m --headless --csv=baseline

# Scenario 2: Sustained (5,000 users, 10 min)
uv run locust -f oms/load_test/locustfile.py --host http://localhost:8000 --users 5000 --spawn-rate 100 --run-time 10m --headless --csv=sustained

# Scenario 3: Spike (6,000 users, ramp 60s, hold 5 min)
uv run locust -f oms/load_test/locustfile.py --host http://localhost:8000 --users 6000 --spawn-rate 100 --run-time 6m --headless --csv=spike
```

## Viewing Metrics

- Prometheus metrics: `http://localhost:8000/metrics`
- Example PromQL queries:
  - p95 latency: `histogram_quantile(0.95, sum(rate(oms_http_request_duration_seconds_bucket[5m])) by (le, endpoint))`
  - Queue depth: `oms_queue_depth`
  - Rate limiter tokens: `oms_rate_limiter_tokens`
  - Circuit breaker state: `oms_circuit_breaker_state`

## Resource Limits (Derivation)

| Component | CPU | Memory | Formula |
|-----------|-----|--------|---------|
| App       | 4   | 4 GB   | 50% of 8 cores, 4% of 98 GB |
| PostgreSQL| 2   | 2 GB   | 25% of 8 cores |
| Redis     | 1   | 1 GB   | 12.5% of 8 cores |
| RabbitMQ  | 1   | 1 GB   | 12.5% of 8 cores |
| **Total** | **8** | **8 GB** | Within target (98 GB RAM, 8 cores) |

## Pool Sizing Formulas

### DB Connection Pool
```
pool_size = cores × 2 = 8 × 2 = 16
max_overflow = 8 (50% headroom for bursts)
```
Derivation: HikariCP-style heuristic. With async I/O, connections spend most time waiting on DB,
so `wait_time/compute_time` ratio is high. 16 connections per 8 cores is conservative.

### Worker Pool (Uvicorn workers)
```
workers = cores = 8 (but limited to 4 in container for headroom)
```
Derivation: For async workers, `workers = cores` is standard. We use 4 in container
to leave 4 cores for OS and other services.

### Rate Limiter (Token Bucket)
```
capacity = 5000 (burst)
refill_rate = 1000/s (sustained)
```
Derivation: At 2,000 concurrent users with 1-5s think time, peak throughput ≈ 2,000/1 = 2,000 req/s.
Capacity of 5,000 allows 2.5x burst. Refill of 1,000/s sustains normal load with headroom.

### Consumer Pool (RabbitMQ)
```
concurrency = cores = 8
```
Derivation: One consumer per core for CPU-bound task processing.
