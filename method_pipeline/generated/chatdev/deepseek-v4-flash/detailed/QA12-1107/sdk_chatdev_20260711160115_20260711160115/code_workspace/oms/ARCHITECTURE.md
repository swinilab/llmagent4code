# Order Management System (OMS) — Architecture Document

## 1. NFR Traceability Matrix

| NFR | Requirement | Architectural Mechanism | Module/Component | Verification Method |
|-----|-------------|------------------------|-----------------|---------------------|
| **1.1** | Checkout p95 ≤ 300ms, p99 ≤ 600ms; Search p95 ≤ 150ms | Cache-aside (Redis, allkeys-lru), async I/O (uvloop + httptools), connection pooling | `infrastructure/cache.py`, `services/order_service.py` (cache-aside reads), `api/controllers.py` | Locust load test: 2,000 concurrent VUs, 10-min steady state; measure p50/p95/p99 via `/metrics` and structured logs |
| **1.2** | 5,000 concurrent sessions, avg queueing < 50ms, CPU 60–85% | Sized worker pool (8 uvicorn async workers = 16 cores × 0.5), HikariCP-style DB pool (20 + 10 overflow = 30 max), Redis pool (16 conns), token-bucket rate limiter (5,000/s refill, 10,000 burst) | `config.py`, `infrastructure/database.py`, `infrastructure/cache.py`, `infrastructure/rate_limiter.py` | Locust sustained 5,000-session test; monitor CPU via `top`/`docker stats`, queue depth via `/metrics` (rate_limiter.available_tokens) |
| **1.3** | Absorb 3x spike over 60s without crashes/memory growth/request loss | Token-bucket admission control (Redis-backed Lua script), RabbitMQ decoupling for deferrable work, bounded queue (10,000), circuit breaker (Resilience4j-style) for downstream deps | `infrastructure/rate_limiter.py`, `infrastructure/message_queue.py`, `infrastructure/circuit_breaker.py`, `api/middleware.py` | Locust spike test: ramp 1,500→4,500 users over 60s; verify zero 5xx, zero OOM, queue depth < 10,000, circuit-breaker transitions logged |
| **2.1** | Graceful degradation under resource contention | Circuit breaker on non-essential calls (recommendations) with fallback to cached/generic responses; core checkout path isolated | `infrastructure/circuit_breaker.py`, `services/order_service.py` (RecommendationService) | Degradation test: disable recommendation service, send high load; verify core checkout returns 200, recommendations return fallback (generic "Popular Item") |
| **2.2** | Fault detection and auto-recovery | Health check endpoints (`/health`, `/health/ready`, `/health/live`), retry with exponential backoff (tenacity) for transient DB errors, connection pool pre-ping | `infrastructure/health.py`, `infrastructure/retry.py`, `infrastructure/database.py` (pool_pre_ping=True) | Recovery test: block DB port temporarily; verify errors spike then auto-recover without restart; health endpoint correctly reports degraded→up |
| **2.3** | State preservation on crash | Transactional Outbox pattern (order_outbox table, same DB transaction), background outbox processor, startup recovery routine, systemd auto-restart | `infrastructure/state_recovery.py`, `main.py` (lifespan + outbox task), `deploy/oms.service` | State test: `kill -9` during order creation; verify all committed transactions survive restart; outbox entries re-published |

## 2. Architectural Decision Records (ADRs)

### ADR-001: Programming Language & Framework

**Decision:** Python 3.12 with FastAPI (async)

**Context:** NFR 1.1 (response time), NFR 1.2 (concurrency)

**Alternatives considered:**
- **Go + Gin:** Superior raw throughput (~2x Python), but smaller ecosystem for async DB/queue libraries; longer development time for complex state machines.
- **Java + Spring Boot:** Mature ecosystem, excellent circuit-breaker support (Resilience4j), but heavier memory footprint (~500MB baseline vs ~100MB for Python); slower cold start.
- **Node.js + Express:** Good async I/O, but weaker type safety; callback-heavy patterns increase bug risk in complex state transitions.

**Consequences:**
- Python's GIL limits CPU-bound parallelism, but the workload is I/O-bound (DB, cache, queue). Uvicorn with 8 async workers handles 5,000 concurrent sessions via cooperative multitasking.
- FastAPI's automatic OpenAPI generation satisfies the API definition requirement.
- **Performance/Reliability tension:** Python's async model means a single slow DB query blocks the event loop for that worker. Mitigated by connection pooling (pool_timeout=5s) and circuit breakers on downstream calls.

### ADR-002: Database

**Decision:** PostgreSQL 16 with SQLAlchemy 2.0 (async) + asyncpg

**Context:** NFR 1.2 (concurrency), NFR 2.3 (state preservation)

**Alternatives considered:**
- **MySQL 8:** Similar ACID compliance, but weaker support for advisory locks and JSON operations; async driver (aiomysql) less mature than asyncpg.
- **SQLite:** Zero-config, but no concurrent write support; unsuitable for 5,000 concurrent sessions.

**Consequences:**
- PostgreSQL's `SELECT ... FOR UPDATE` enables pessimistic locking for stock decrement and payment idempotency (eliminates TOCTOU races).
- Connection pool sized at 20 (base) + 10 (overflow) = 30 max connections. Formula: `Pool = Tn × (Cm - 1) + 1 = 8 × (2 - 1) + 1 = 9`, rounded to 20 for headroom.
- **Performance/Reliability tension:** Optimistic locking (version field) adds a retry cost on conflict (~50ms per retry). Resolved by using pessimistic locking (`FOR UPDATE`) for high-contention paths (payment, stock decrement), keeping optimistic locking for low-contention paths (accept, ship, close).

### ADR-003: Cache

**Decision:** Redis 7 with allkeys-lru eviction

**Context:** NFR 1.1 (response time), NFR 1.2 (concurrency)

**Alternatives considered:**
- **Memcached:** Simpler, lower memory overhead, but no built-in data structures for rate limiter state; no persistence.
- **Local in-memory cache (dict):** Zero network latency, but not shared across workers; cache inconsistency under 8 workers.

**Consequences:**
- Redis connection pool: 16 connections (8 workers × 2). Async I/O via `redis.asyncio`.
- Cache-aside pattern: read from cache, miss → read DB → write cache with TTL (products: 60s, orders: 30s). Invalidation on write (stock change, order status change).
- Redis also serves as shared state for rate limiter (token bucket Lua script) and circuit breakers.
- **Performance/Reliability tension:** Redis is a single point of failure. If Redis goes down, rate limiter falls back to per-worker in-memory mode (less accurate but still functional), and circuit breakers fall back to per-worker state. Cache misses increase DB load but don't cause failures.

### ADR-004: Message Queue

**Decision:** RabbitMQ with aio-pika

**Context:** NFR 1.3 (queue management), NFR 2.3 (state preservation)

**Alternatives considered:**
- **Apache Kafka:** Higher throughput (millions of msg/s), but heavier operational overhead; overkill for OMS's moderate throughput (~5,000 orders/s peak).
- **Redis Streams:** Simpler deployment (no separate service), but weaker durability guarantees; no dead-letter exchange built-in.

**Consequences:**
- RabbitMQ queues: `oms.orders`, `oms.invoices`, `oms.shipping`, `oms.dead-letter`. All durable with persistent messages.
- Transactional Outbox: events written to `order_outbox` table in same DB transaction as order update. Background processor polls and forwards to RabbitMQ.
- **Performance/Reliability tension:** The outbox pattern adds ~5ms latency to order writes (DB write + outbox insert). This is acceptable for checkout-critical paths (budget: 300ms p95). The background processor runs every 5 seconds, so events may be delayed up to 5s in failure scenarios.

### ADR-005: Rate Limiting (Admission Control)

**Decision:** Token bucket with Redis-backed Lua script

**Context:** NFR 1.3 (spike absorption)

**Alternatives considered:**
- **Leaky bucket:** Simpler, but less flexible for burst absorption; harder to tune for 3x spike.
- **Fixed window counter:** Prone to thundering herd at window boundaries; less accurate for sub-second control.

**Consequences:**
- Refill rate: 5,000 tokens/s (sustained throughput for 5,000 sessions). Burst: 10,000 tokens (absorb 3x spike over ~2s).
- Redis Lua script ensures atomic token consumption across all 8 workers.
- Rejection: HTTP 429 with `Retry-After: 1` header.
- **Performance/Reliability tension:** Redis-backed rate limiting adds ~1ms per request. If Redis is unavailable, falls back to per-worker in-memory mode (each worker independently allows up to burst, giving 8x effective limit). This is acceptable for graceful degradation.

### ADR-006: Circuit Breaker

**Decision:** Resilience4j-style circuit breaker with Redis-backed state

**Context:** NFR 2.1 (graceful degradation)

**Alternatives considered:**
- **Hystrix-style (Netflix):** Proven in production, but Java-only; no native Python port.
- **Polly (.NET):** Feature-rich, but .NET-only.

**Consequences:**
- States: CLOSED → OPEN (after 5 failures) → HALF_OPEN (after 30s) → CLOSED (after 3 successes).
- Timeout: 5s on protected calls to prevent hanging requests from keeping circuit closed.
- Fallback: passed as parameter to `call()` to avoid race conditions on shared instance state.
- **Performance/Reliability tension:** Circuit breaker adds ~0.5ms overhead per call (state check + Redis round-trip). This is negligible for non-essential features. The 5s timeout prevents resource exhaustion from hung downstream calls.

### ADR-007: Execution Model

**Decision:** Async/non-blocking stack (uvicorn + uvloop + httptools)

**Context:** NFR 1.2 (concurrency)

**Alternatives considered:**
- **Gunicorn + sync workers:** Each worker handles one request at a time; would need 500+ workers for 5,000 concurrent sessions, consuming excessive RAM.
- **Thread pool (ThreadPoolExecutor):** Python GIL limits CPU-bound parallelism; thread overhead for 5,000 sessions would be prohibitive.

**Consequences:**
- 8 uvicorn workers (16 cores × 0.5). Each worker runs an async event loop handling many concurrent requests via cooperative multitasking.
- uvloop provides ~2x throughput improvement over asyncio's default event loop.
- httptools provides faster HTTP parsing.
- **Performance/Reliability tension:** A single slow coroutine can block the event loop for that worker. Mitigated by: (a) connection timeouts on all external calls, (b) circuit breakers on downstream deps, (c) rate limiting to prevent overload.

## 3. Data Architecture Narrative

### Entity-Relationship Overview

```
Customer 1───N Order 1───1 Invoice
                │
                1
                │
                1
              Payment
```

### Order State-Transition Table

| From | Event | To | Guard | Persistence |
|------|-------|----|-------|-------------|
| CREATED | accept | ACCEPTED | role=ORDER_STAFF or ACCOUNTANT | synchronous (DB write before response) |
| ACCEPTED | invoice | INVOICED | role=ACCOUNTANT | synchronous |
| INVOICED | pay | PAID | payment verified, idempotent | synchronous (with FOR UPDATE lock) |
| PAID | ship | SHIPPED | role=ORDER_STAFF, payment=PAID | synchronous |
| SHIPPED | close | CLOSED | role=ORDER_STAFF | synchronous |
| CREATED | cancel | CANCELLED | not CLOSED or SHIPPED | synchronous |
| ACCEPTED | cancel | CANCELLED | not CLOSED or SHIPPED | synchronous |
| INVOICED | cancel | CANCELLED | not CLOSED or SHIPPED | synchronous |
| PAID | cancel | CANCELLED | not CLOSED or SHIPPED | synchronous |

**Durability annotations:**
- All critical transitions are persisted synchronously (DB write before HTTP response).
- Outbox events are written in the same DB transaction (transactional outbox).
- CANCELLED restores product stock (synchronous, in same transaction).

### Schema (DDL)

```sql
-- Customers
CREATE TABLE customers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(32) NOT NULL,
    banking_details TEXT NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'CUSTOMER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Products
CREATE TABLE products (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    base_price NUMERIC(12,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    stock_available INTEGER NOT NULL DEFAULT 0,
    last_modified TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Orders
CREATE TABLE orders (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL REFERENCES customers(id),
    line_items TEXT NOT NULL DEFAULT '[]',  -- JSON array
    total_amount NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(16) NOT NULL DEFAULT 'CREATED',
    invoice_ref VARCHAR(36),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    invoiced_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- Payments
CREATE TABLE payments (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES orders(id),
    amount NUMERIC(12,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    method VARCHAR(32) NOT NULL DEFAULT 'CREDIT_CARD',
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Invoices
CREATE TABLE invoices (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES orders(id),
    customer_id VARCHAR(36) NOT NULL REFERENCES customers(id),
    billing_address TEXT NOT NULL,
    total_amount NUMERIC(14,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    issue_date TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Outbox (transactional outbox pattern)
CREATE TABLE order_outbox (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload TEXT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);
CREATE INDEX idx_outbox_status ON order_outbox(status);
CREATE INDEX idx_outbox_order ON order_outbox(order_id);
```

## 4. Workflow Latency & Criticality Classification

| Step | Action | Latency Budget | Criticality | Recovery Mechanism |
|------|--------|---------------|-------------|-------------------|
| 1 | Customer places order | Checkout-critical (p95 ≤ 300ms) | Core | Retry (exponential backoff, 3 attempts) |
| 2 | Order Staff reviews & accepts | Relaxed back-office | Core | Retry (exponential backoff) |
| 3 | Accountant creates invoice | Relaxed back-office | Core | Retry (exponential backoff) |
| 4 | Customer pays invoice | Checkout-critical (p95 ≤ 300ms) | Core | Retry + idempotency key (deduplication) |
| 5 | Accountant verifies payment | Relaxed back-office | Core | Retry (exponential backoff) |
| 6 | Order Staff ships paid order | Relaxed back-office | Core | Retry (exponential backoff) |
| 7 | Order Staff closes completed order | Relaxed back-office | Core | Retry (exponential backoff) |

## 5. Cross-cutting Performance/Reliability Tension Resolution

| Tension | Resolution |
|---------|-----------|
| **Retry logic increases checkout time** | Retry only for transient DB errors (connection drops, deadlocks). Max 3 attempts with exponential backoff (100ms base, 5s max). Expected added latency: ~200ms in worst case (still within 300ms p95 budget). |
| **Circuit breaker timeout vs. response time** | Circuit breaker timeout (5s) is longer than p95 checkout budget (300ms). The breaker only protects non-essential features; core checkout has no circuit breaker on its own path. |
| **Pessimistic locking vs. throughput** | `FOR UPDATE` locks are held for < 50ms (single row update). Lock contention is low because payments are serialized per-order (different orders have different rows). |
| **Outbox pattern adds write latency** | Outbox insert is in the same DB transaction as the order update (no extra round-trip). Added latency: ~2ms per write. |
| **Rate limiting adds latency** | Redis-backed token check adds ~1ms per request. In-memory fallback adds ~0.01ms. Both well within budget. |
