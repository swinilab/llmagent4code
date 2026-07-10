# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), meeting explicit, quantified performance targets. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building an OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must handle non-trivial traffic on a single-node deployment target with up to 98GB RAM and multi-core CPU. No authentication is required. You may select and justify any backend language/framework, database, and messaging technology — none is mandated, but every choice must be defended against the NFRs below.

---

# Architectural Design Requirements

## 1. Architectural Decision Records (ADR)
For every major architectural choice you MUST provide a short ADR entry containing:
- **Decision:** what you chose
- **Context:** which NFR(s) it addresses
- **Alternatives considered:** at least 2 other options and why they were rejected
- **Consequences:** trade-offs accepted

## 2. NFR Traceability Matrix (MANDATORY)
Before writing any code, produce a table mapping every NFR below to:
- The **architectural mechanism** you will use to satisfy it.
- The **module/component** where it lives.
- A **quantitative verification method** (the specific measurement, tool, and pass/fail threshold a reviewer would use).

Non-Functional Requirements to satisfy:
- **NFR 1.1 Response Time:** the checkout journey (cart → order submission) must meet p95 latency ≤ 300ms and product search/browse must meet p95 latency ≤ 150ms, measured at 2,000 concurrent virtual users with a realistic think-time distribution.
- **NFR 1.2 Concurrency & Resource Utilization:** the system must sustain 5,000 concurrent active sessions on the target hardware class with average request queueing time < 50ms; you must state and justify your thread/worker pool sizing and connection pool sizing relative to available cores and RAM. Consider concrete mechanisms such as a bounded, sized DB connection pool (e.g., a HikariCP-style pool), a non-blocking/async I/O or event-loop execution model on the checkout path, and an in-memory or Redis-backed cache for hot read paths to offload the database.
- **NFR 1.3 Queue Management:** the system must absorb a traffic spike of 3x baseline load arriving within a 60-second ramp without process crashes, unbounded memory growth, or silent request loss; you must define an explicit admission-control / backpressure policy and the client-visible behavior when capacity is exceeded (e.g., HTTP status, retry guidance). Consider decoupling spike-prone work (e.g., invoice generation, notifications) from the request thread using a message broker/task-queue pattern (e.g., RabbitMQ or Kafka feeding a worker pool, Celery-style), and a rate-limiter (e.g., token-bucket, optionally Redis-backed if shared across instances) at the admission layer.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum with full lifecycle: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED as a terminal exception state from any pre-SHIPPED state), timestamps, invoice ref, version/optimistic-lock field.
- **Product:** id, description, pricing (base + currency), stock/availability indicator.
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

State transitions must be enforced by the domain layer (not just by controller-level checks), and illegal transitions must be rejected with a clear error.

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

Each transition is a candidate hot path for NFR 1.1 — identify which steps are on the critical path for the checkout journey specifically (order placement, payment) versus back-office steps that have relaxed latency budgets.

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths)

Additionally:
- Implement or configure a caching strategy for read-heavy, latency-sensitive endpoints (e.g., product search/browse) and state the invalidation policy. A dedicated cache store (e.g., Redis) is a reasonable default if it simplifies invalidation and TTL control across instances.
- Implement connection pooling and, where relevant, asynchronous/non-blocking I/O for the checkout path, with the sizing rationale from NFR 1.2 made visible in configuration.
- Implement the admission-control/backpressure mechanism from NFR 1.3 as real, runnable code (not just described) — e.g., a rate limiter guarding the checkout endpoint plus a broker-backed worker queue for deferrable work.

---

# Performance Verification Requirements
- Provide a load-test plan (tool of your choice — e.g., a scripting-based load generator) covering: baseline load, sustained load at the target concurrency, and the 3x spike scenario.
- Specify the exact metrics to capture (p50/p95/p99 latency, throughput, error rate, CPU/memory utilization, queue depth) and the pass/fail thresholds tied to NFR 1.1–1.3.
- Provide instrumentation (metrics endpoint, structured logs with request correlation) sufficient to observe these metrics at runtime.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on a local machine as a production-representative environment, with resource limits (CPU/memory) configured to reflect the target hardware class and justified in relation to NFR 1.2.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix with quantitative thresholds.
2. ADRs for major decisions.
3. Data architecture narrative + complete schema.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, OpenAPI spec.
6. IaC config and documents, with resource limits stated.
7. Local deployment guide.
8. Load-test plan and instrumentation showing how each performance NFR is measured and verified.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
