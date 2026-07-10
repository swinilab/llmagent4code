# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), meeting fully specified, quantified performance and resilience targets, with all sizing decisions justified by explicit formulas and load-test evidence. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building an OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must run on a single-node deployment target with up to 98GB RAM and a multi-core CPU (state the core count you assume and justify it). No authentication is required. You may select and justify any backend language/framework, database, cache, and messaging technology — none is mandated, but every choice must be defended quantitatively against the NFRs below.

---

# Architectural Design Requirements

## 1. Architectural Decision Records (ADR)
For every major architectural choice you MUST provide a short ADR entry containing:
- **Decision:** what you chose
- **Context:** which NFR(s) it addresses
- **Alternatives considered:** at least 2 other options and why they were rejected
- **Consequences:** trade-offs accepted, with any numeric cost (e.g., added latency, memory overhead) estimated

## 2. NFR Traceability Matrix (MANDATORY)
Before writing any code, produce a table mapping every NFR below to:
- The **architectural mechanism** you will use to satisfy it.
- The **module/component** where it lives.
- A **quantitative verification method**, including the exact tool, test scenario, and numeric pass/fail threshold.

Non-Functional Requirements to satisfy:
- **NFR 1.1 Response Time:** checkout journey (cart → order submission) p95 latency ≤ 300ms and p99 ≤ 600ms; product search/browse p95 latency ≤ 150ms; measured at 2,000 concurrent virtual users with a think-time distribution of 1–5s, over a 10-minute steady-state window.
- **NFR 1.2 Concurrency & Resource Utilization:** sustain 5,000 concurrent active sessions with average request queueing time < 50ms and CPU utilization between 60–85% at peak (headroom retained for spikes). You must state the exact formula used to size your worker/thread pool (e.g., `pool_size = cores × (1 + wait_time/compute_time)`) and your DB connection pool (e.g., a HikariCP-style pool sized via `connections = cores × 2` as a starting heuristic, adjusted per measured wait ratio), with the inputs you assumed. Name and justify the concrete execution model (e.g., a reactive/non-blocking stack, or a platform-thread pool sized by the formula above) and the concrete cache technology chosen for hot read paths (e.g., Redis with a stated eviction policy) rather than describing caching only in the abstract.
- **NFR 1.3 Queue Management:** absorb a 3x baseline traffic spike arriving within a 60-second linear ramp without process crashes, unbounded memory growth (define a hard memory ceiling and OOM-avoidance strategy), or silent request loss. Specify: (a) the admission-control algorithm (e.g., token bucket or leaky bucket, with capacity and refill rate — implemented in-process or via a shared store such as Redis if state must be shared across instances), (b) the bounded queue capacity and rejection policy once full — name the concrete mechanism (e.g., a message broker such as RabbitMQ or Kafka feeding a Celery-style/consumer worker pool for deferrable work like invoice generation or notifications, versus an in-process bounded queue for work that must stay synchronous), (c) the exact client-visible behavior on rejection (HTTP status code, `Retry-After` header or equivalent), and (d) a circuit-breaker policy for any downstream dependency, naming the pattern/library family you'd use (e.g., a Resilience4j/Polly/Hystrix-style breaker) with failure-rate threshold, open-state duration, and half-open trial count.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED as a terminal exception state reachable from any pre-SHIPPED state), timestamps (created/updated/each transition), invoice ref, optimistic-lock version field.
- **Product:** id, description, pricing (base + currency), stock/availability indicator, cache-relevant last-modified timestamp.
- **Payment:** id, order ref, amount, timestamp, status, method, idempotency key.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

Provide the explicit state-transition table (from-state, event, to-state, guard condition) for Order status, enforced in the domain layer with illegal transitions rejected before any persistence write.

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

Classify each step by latency budget: checkout-critical (order placement, payment submission — subject to NFR 1.1's 300ms target) versus back-office (accept, invoice, verify, ship, close — state your relaxed target, e.g., p95 ≤ 1s, and justify why relaxation is acceptable here).

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths)

Additionally, implement as real, runnable code:
- A cache-aside layer for product search/browse (e.g., backed by Redis) with a stated TTL and an explicit invalidation trigger on price/stock updates (state the max staleness window this allows and confirm it is acceptable).
- Sized connection pools and, for the checkout path specifically, non-blocking/async I/O or an equivalent concurrency model, with the sizing formula from NFR 1.2 encoded in configuration and commented with its derivation.
- The full admission-control/backpressure/circuit-breaker chain from NFR 1.3, wired into the checkout path — e.g., a rate limiter guarding the checkout endpoint, a broker-backed worker queue (RabbitMQ/Kafka + a Celery-style consumer pool) absorbing deferrable spike work, and a Resilience4j/Polly-style circuit breaker wrapping calls to any downstream dependency.
- Idempotency handling for payment submission (using the idempotency key, e.g., persisted or cached in Redis with a TTL) to make retries under spike conditions safe.

---

# Performance Verification Requirements
- A load-test plan (specify the tool) with three scenarios: (1) baseline steady load, (2) sustained load at 5,000 concurrent sessions for ≥10 minutes, (3) a 3x spike scenario ramping over 60 seconds and held for ≥5 minutes.
- Exact metrics captured per scenario: p50/p95/p99 latency per endpoint class, throughput (req/s), error rate (%), CPU/memory utilization over time, queue depth over time, circuit-breaker state transitions.
- Explicit pass/fail thresholds tied one-to-one to NFR 1.1–1.3, and a description of what output artifact (e.g., a report or dashboard) presents these results.
- Runtime instrumentation: a metrics endpoint (state the format, e.g., a standard metrics exposition format), structured logs with request correlation IDs, and at least one dashboard/query example showing how a reviewer reads p95 latency and queue depth live.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on a local machine as a production-representative environment. Container/process resource limits (CPU cores, memory) must numerically reflect the target hardware class and must match the pool-sizing formulas above — show the arithmetic.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix with quantitative thresholds and derivation formulas.
2. ADRs for major decisions, with numeric trade-off estimates.
3. Data architecture narrative + complete schema, including the Order state-transition table.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, OpenAPI spec, cache layer, backpressure/circuit-breaker implementation, idempotency handling.
6. IaC config and documents with resource limits and their derivation shown.
7. Local deployment guide.
8. Load-test plan, executed-or-executable scripts, and instrumentation showing measured (or expected) values against each threshold.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
