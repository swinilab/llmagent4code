# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), fully specified for both quantified performance/resilience and demonstrable modifiability, with all sizing and boundary decisions justified by explicit formulas, scenarios, and evidence. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building an OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must run on a single-node deployment target with up to 98GB RAM and a multi-core CPU (state the core count you assume and justify it). No authentication is required. You may select and justify any backend language/framework, database, cache, and messaging technology — none is mandated, but every choice must be defended against the NFRs below, and any tension between performance and modifiability mechanisms must be reconciled explicitly (e.g., caching vs. contract freshness, async event boundaries vs. checkout latency).

---

# Architectural Design Requirements

## 1. Architectural Decision Records (ADR)
For every major architectural choice you MUST provide a short ADR entry containing:
- **Decision:** what you chose
- **Context:** which NFR(s) it addresses
- **Alternatives considered:** at least 2 other options and why they were rejected
- **Consequences:** trade-offs accepted, with numeric costs where relevant and any performance/modifiability tension explicitly noted

## 2. NFR Traceability Matrix (MANDATORY)
Before writing any code, produce a table mapping every NFR below to:
- The **architectural mechanism** you will use to satisfy it.
- The **module/component** where it lives.
- A **precise verification method** — quantitative thresholds for performance NFRs; exact change scenarios with expected diff scope for modifiability NFRs.

Non-Functional Requirements to satisfy:

**Performance**
- **NFR 1.1 Response Time:** checkout journey p95 latency ≤ 300ms, p99 ≤ 600ms; product search/browse p95 latency ≤ 150ms; measured at 2,000 concurrent virtual users, 10-minute steady-state window.
- **NFR 1.2 Concurrency & Resource Utilization:** sustain 5,000 concurrent active sessions with average queueing time < 50ms and CPU utilization 60–85% at peak. State the exact pool-sizing formulas used (worker/thread pool and a HikariCP-style DB connection pool) and the inputs assumed. Name the concrete execution model (e.g., reactive/non-blocking stack vs. a sized platform-thread pool) and the concrete cache technology for hot reads (e.g., Redis, with eviction policy stated).
- **NFR 1.3 Queue Management:** absorb a 3x baseline spike ramping over 60 seconds without crashes, unbounded memory growth, or silent request loss. Specify the admission-control algorithm (e.g., token bucket, optionally Redis-backed if shared across instances), the concrete decoupling mechanism for deferrable work (e.g., a message broker such as RabbitMQ or Kafka feeding a Celery-style worker pool), the bounded queue capacity and rejection policy, client-visible rejection behavior, and a circuit-breaker policy for downstream dependencies naming the pattern/library family (e.g., Resilience4j/Polly/Hystrix-style).

**Modifiability**
- **NFR 2.1 Localization of Changes:** define explicit bounded contexts (at minimum Ordering, Catalog, Payment, Invoicing, Shipping), each owning its own module, persistence, and domain model; state the inter-context communication mechanism per pair (synchronous REST/gRPC vs. asynchronous events on the same broker used for NFR 1.3) and any anti-corruption translation. A confined business-rule change in one context must not touch another context's files.
- **NFR 2.2 Interface Stability:** URI-versioned APIs with a written compatibility policy (additive vs. breaking changes, minimum 2 concurrently supported versions, deprecation header with ≥90-day sunset). A versioned OpenAPI document per version, plus a consumer-driven contract test using a concrete tool/pattern (e.g., Pact-style).
- **NFR 2.3 Deferred Binding:** externalized, runtime-reloadable configuration (infrastructure- and business-rule-level), naming a concrete mechanism (e.g., a config service such as Spring Cloud Config/Consul/etcd, or env-vars with a refresh endpoint), with a stated propagation delay bound, an audit trail (who/what/when/old/new), and a rollback mechanism.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED as a terminal exception state), timestamps per transition, invoice ref, optimistic-lock version field.
- **Product:** id, description, pricing (base + currency), stock/availability indicator, last-modified timestamp (for cache invalidation).
- **Payment:** id, order ref, amount, timestamp, status, method, idempotency key.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

Provide the explicit Order state-transition table (from-state, event, to-state, guard) enforced in the domain layer. For each bounded context, list owned entities, published domain events (with schema and versioning approach), and consumed events/APIs.

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

For each step: (a) classify its latency budget (checkout-critical vs. relaxed back-office, per NFR 1.1), and (b) name its owning bounded context and the exact contract used to hand off to the next context (per NFR 2.1/2.2).

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths)

Additionally, implement as real, runnable code:
- A cache-aside layer for latency-sensitive read paths (e.g., Redis-backed, TTL and invalidation trigger stated), sized connection pools/async I/O per NFR 1.2's formulas, and the full admission-control/backpressure/circuit-breaker chain from NFR 1.3 (e.g., rate limiter + RabbitMQ/Kafka-backed worker queue + a Resilience4j/Polly-style breaker), including idempotency handling for payment submission.
- Bounded-context module boundaries with no shared entity classes or cross-context direct DB access, cross-context calls via REST/gRPC or broker-published events, the versioning/deprecation mechanism from NFR 2.2 (including one deprecated-but-served endpoint and a Pact-style contract test), and the externalized runtime-reloadable configuration mechanism from NFR 2.3 (e.g., a config service or refreshable env vars, with audit log and rollback), applied to at least one infrastructure and one business-rule value.

---

# Verification Requirements
**Performance:**
- Load-test plan (tool named) with baseline, sustained 5,000-session, and 3x-spike scenarios; exact metrics (p50/p95/p99 latency, throughput, error rate, resource utilization, queue depth, circuit-breaker transitions) with pass/fail thresholds tied to NFR 1.1–1.3; runtime instrumentation (metrics endpoint, correlated structured logs).

**Modifiability:**
- A worked example changing a business rule inside one bounded context with the full diff shown, confirming no other context's files change; a consumer-driven contract test proving an existing API version is unaffected; a runtime reconfiguration demonstration (one infra value, one business-rule value) with audit-log evidence; a brief impact-analysis note for a second hypothetical change.

**Cross-cutting:** explicitly state where a performance mechanism and a modifiability mechanism interact (e.g., does caching reduce contract-test coverage freshness; does an added bounded-context hop add latency against the 300ms budget) and how the design resolves it.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on a local machine as a production-representative environment. Resource limits must numerically reflect the target hardware class and match the pool-sizing formulas (show the arithmetic). Each bounded context's data store must be independently provisioned, and the runtime-configuration delivery mechanism must be present.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix (quantitative thresholds + precise change scenarios).
2. ADRs for major decisions, including numeric trade-offs and performance/modifiability tension notes.
3. Data architecture narrative + complete schema, including the Order state-transition table and bounded-context ownership annotations.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, versioned OpenAPI spec(s), cache layer, backpressure/circuit-breaker implementation, idempotency handling, contract tests.
6. IaC config and documents, with resource-limit derivations shown.
7. Local deployment guide.
8. Load-test plan/instrumentation evidence, and change-isolation diff / contract-test / runtime-reconfiguration+audit-log / impact-analysis evidence.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
