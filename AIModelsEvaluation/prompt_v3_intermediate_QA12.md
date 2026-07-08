# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), meeting explicit, quantified performance targets **and** demonstrable modifiability/change-isolation. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building an OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must handle non-trivial traffic on a single-node deployment target with up to 98GB RAM and multi-core CPU. No authentication is required. You may select and justify any backend language/framework, database, and messaging technology — none is mandated, but every choice must be defended against the NFRs below, including where performance and modifiability goals trade off against each other.

---

# Architectural Design Requirements

## 1. Architectural Decision Records (ADR)
For every major architectural choice you MUST provide a short ADR entry containing:
- **Decision:** what you chose
- **Context:** which NFR(s) it addresses
- **Alternatives considered:** at least 2 other options and why they were rejected
- **Consequences:** trade-offs accepted (explicitly note any performance/modifiability tension)

## 2. NFR Traceability Matrix (MANDATORY)
Before writing any code, produce a table mapping every NFR below to:
- The **architectural mechanism** you will use to satisfy it.
- The **module/component** where it lives.
- A **concrete verification method** — quantitative for performance NFRs, scenario-based for modifiability NFRs.

Non-Functional Requirements to satisfy:
- **NFR 1.1 Response Time:** checkout journey p95 latency ≤ 300ms; product search/browse p95 latency ≤ 150ms, measured at 2,000 concurrent virtual users.
- **NFR 1.2 Concurrency & Resource Utilization:** sustain 5,000 concurrent active sessions on the target hardware class, average queueing time < 50ms; justify thread/worker and connection pool sizing against available cores/RAM. Consider a sized DB connection pool (e.g., HikariCP-style), a non-blocking/async I/O or event-loop model on the checkout path, and a Redis-backed cache for hot reads.
- **NFR 1.3 Queue Management:** absorb a 3x baseline traffic spike arriving within 60 seconds without crashes, unbounded memory growth, or silent request loss; define an explicit admission-control/backpressure policy. Consider a message broker/task-queue pattern (e.g., RabbitMQ or Kafka feeding a worker pool, Celery-style) to decouple spike-prone work, and a token-bucket rate limiter (optionally Redis-backed) at the admission layer.
- **NFR 2.1 Localization of Changes:** define explicit bounded contexts (at minimum Ordering, Catalog, Payment, Invoicing, Shipping), each owning its own module and data; a change confined to one context's business rules must not require modifying or redeploying other contexts. Consider using the same broker from NFR 1.3 for cross-context domain events, keeping contexts decoupled both operationally and architecturally.
- **NFR 2.2 Interface Stability:** all APIs explicitly versioned (e.g., `/v1/...`) with a stated backward-compatibility policy and deprecation window; provide a versioned OpenAPI contract per version, and consider a consumer-driven contract-testing tool (e.g., Pact) to catch breaking changes automatically.
- **NFR 2.3 Deferred Binding:** environment-specific/tunable values externalized and changeable at runtime without restart, with a stated propagation delay bound and an audit trail of changes. Consider a config/feature-flag service (e.g., Spring Cloud Config, Consul, etcd) or an env-var-plus-refresh-endpoint approach.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED as a terminal exception state), timestamps, invoice ref, version/optimistic-lock field.
- **Product:** id, description, pricing (base + currency), stock/availability indicator.
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

State transitions enforced in the domain layer. Each bounded context owns only the data it is authoritative for; cross-context access goes through a stable interface (API call or domain event), never shared tables.

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

Identify which steps sit on the latency-critical path (NFR 1.1) versus which bounded context owns each step and what stable contract hands off between them (NFR 2.1/2.2).

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths)

Additionally:
- Implement caching for latency-sensitive read paths (e.g., Redis-backed cache-aside), connection pooling/async I/O sized per NFR 1.2, and the admission-control mechanism from NFR 1.3 as runnable code (e.g., rate limiter + broker-backed worker queue for deferrable work).
- Implement bounded-context boundaries as real project/package structure with explicit cross-context interfaces (sync calls or broker-published domain events), and the runtime-configurable mechanism from NFR 2.3 as runnable code (e.g., config service or refreshable env vars).

---

# Verification Requirements
**Performance:**
- Load-test plan covering baseline, sustained target concurrency, and 3x spike scenarios, with metrics (p50/p95/p99 latency, throughput, error rate, resource utilization) and pass/fail thresholds tied to NFR 1.1–1.3.
- Runtime instrumentation (metrics endpoint, structured/correlated logs).

**Modifiability:**
- One worked example changing a business rule inside a single bounded context, showing the confined blast radius.
- A contract test showing an existing API version's shape is unaffected by that change.
- A runtime demonstration of reconfiguring one externalized value without restart.

Where performance and modifiability mechanisms interact (e.g., caching vs. contract stability, async messaging vs. latency budget), state the trade-off explicitly.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on a local machine as a production-representative environment, with resource limits reflecting the target hardware class and the runtime-configuration delivery mechanism in place.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix (quantitative + scenario-based).
2. ADRs for major decisions, including trade-off notes.
3. Data architecture narrative + complete schema, annotated by bounded context ownership.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, versioned OpenAPI spec(s).
6. IaC config and documents.
7. Local deployment guide.
8. Load-test plan/instrumentation and change-isolation/contract-test/runtime-reconfiguration demonstrations.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
