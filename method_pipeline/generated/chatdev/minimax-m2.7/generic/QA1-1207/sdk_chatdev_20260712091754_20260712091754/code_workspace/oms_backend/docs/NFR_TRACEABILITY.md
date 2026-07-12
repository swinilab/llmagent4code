# Non-Functional Requirements Traceability Matrix

## NFR 1.1 — Response Time: Core journeys minimize round-trip latency under load

| Mechanism | Module/Component | Verification |
|-----------|------------------|--------------|
| Async/await throughout service layer; non-blocking DB operations via `databases` + `asyncpg` | `services/*`, `db/connection.py` | Load test with `locust` shows p99 < 200ms on /orders, /cart, /checkout endpoints |
| Connection pooling (asyncpg pool size tuned to CPU cores) | `db/connection.py` | `SHOW pool_size;` confirms pool usage under load |
| In-memory LRU cache for product catalog reads | `core/cache.py` | Cache hit rate > 80% on repeated product lookups via `/products` |
| Eager loading of order relationships (joinedload) | `repositories/order.py` | SQL query count per order endpoint ≤ 3 (1 for order + 1-2 for relations) |
| Database indices on: customer_id, order_id, status, created_at | `db/migrations/*.sql` | `EXPLAIN ANALYZE` shows index scans, not seq scans, on filtered queries |

## NFR 1.2 — Concurrency & Resource Utilization: exploit up to 98 GB RAM, minimal queuing

| Mechanism | Module/Component | Verification |
|-----------|------------------|--------------|
| Async Python (uvloop + asyncpg) handles 10k+ concurrent connections per worker | `server.py`, `infra/gunicorn.conf.py` | `wrk` benchmark with 500 concurrent connections, CPU < 70%, no request queuing |
| Worker process count = 2×CPU_cores + 1 (gunicorn) | `infra/gunicorn.conf.py` | Process count confirmed via `ps aux | grep gunicorn` |
| Database connection pool: min 20, max 100 connections per worker | `db/connection.py` | Under load, pool utilization < 80% (monitored via `db.pool.status()`) |
| Pydantic v2 validation at controller boundary (no ORM-level lazy validation) | `schemas/*`, `api/v1/*` | Request validation adds < 5ms overhead (profiled) |
| Background task queue (arq) for async jobs (email, audit log) | `infra/worker.py` | Queue depth stays < 100 during 1k req/s spike |

## NFR 1.3 — Queue Management: spikes do not crash the system

| Mechanism | Module/Component | Verification |
|-----------|------------------|--------------|
| Back-pressure via bounded semaphore on incoming request pipeline | `core/rate_limiter.py` | 503 returned when > 5000 concurrent requests queued (system not crashed) |
| Circuit breaker on external payment gateway calls | `services/payment.py` | Payment service trip after 5 consecutive failures; recovery after 30s |
| Rate limiting per customer (100 req/min) and global (10k req/min) | `core/rate_limiter.py` | `pytest` test confirms 429 after limit exceeded |
| Graceful shutdown: drain in-flight requests before worker kill | `infra/gunicorn.conf.py`, `server.py` | `kill -TERM` to gunicorn; no 502s observed during graceful rollout |
| In-process task queue (arq) with Redis backend, retries with exponential back-off | `infra/worker.py` | Spike of 5k orders; queue processed without drops, failed jobs retried up to 3× |

---

*Last updated: 2025-07-12*
