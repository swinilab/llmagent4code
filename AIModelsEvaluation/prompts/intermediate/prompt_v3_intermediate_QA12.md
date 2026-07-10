# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), meeting explicit, quantified performance targets **and** demonstrable reliability/fault-tolerance. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building an OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must handle non-trivial traffic on a single-node deployment target with up to 98GB RAM and multi-core CPU. No authentication is required. You may select and justify any backend language/framework, database, and messaging technology — none is mandated, but every choice must be defended against the NFRs below, including where performance and reliability goals trade off against each other.

---

# Architectural Design Requirements

## 1. Architectural Decision Records (ADR)
For every major architectural choice you MUST provide a short ADR entry containing:
- **Decision:** what you chose
- **Context:** which NFR(s) it addresses
- **Alternatives considered:** at least 2 other options and why they were rejected
- **Consequences:** trade-offs accepted (explicitly note any performance/reliability tension)

## 2. NFR Traceability Matrix (MANDATORY)
Before writing any code, produce a table mapping every NFR below to:
- The **architectural mechanism** you will use to satisfy it.
- The **module/component** where it lives.
- A **concrete verification method** — quantitative for performance NFRs, scenario-based for reliability NFRs.

Non-Functional Requirements to satisfy:
- **NFR 1.1 Response Time:** checkout journey p95 latency ≤ 300ms; product search/browse p95 latency ≤ 150ms, measured at 2,000 concurrent virtual users.
- **NFR 1.2 Concurrency & Resource Utilization:** sustain 5,000 concurrent active sessions on the target hardware class, average queueing time < 50ms; justify thread/worker and connection pool sizing against available cores/RAM. **Hint:** Consider a sized DB connection pool (e.g., HikariCP-style) and a Redis-backed cache for hot reads.
- **NFR 1.3 Queue Management:** absorb a 3x baseline traffic spike arriving within 60 seconds without crashes, unbounded memory growth, or silent request loss; define an explicit admission-control/backpressure policy. **Hint:** Consider a message broker/task-queue pattern (e.g., RabbitMQ or Kafka feeding a worker pool) to decouple spike-prone work.
- **NFR 2.1 Graceful Degradation:** Under extreme resource contention, non-essential features must degrade to ensure core checkout remains available. **Hint:** Consider using a circuit breaker pattern to disable non-critical paths dynamically.
- **NFR 2.2 Fault Detection and Recovery:** The application must detect internal component failures and automatically attempt to recover/reconnect. **Hint:** Consider implementing health check endpoints and retry policies with exponential backoff.
- **NFR 2.3 State Preservation:** In the event of an unexpected process crash, the system must restore operational state and resume processing pending orders upon restart. **Hint:** Consider using durable message queues or transactional outbox patterns to ensure no order state is lost.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED), timestamps, invoice ref, version/optimistic-lock field.
- **Product:** id, description, pricing (base + currency), stock/availability indicator.
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

State transitions enforced in the domain layer. Ensure critical state transitions are persisted before acknowledging external requests.

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

Identify which steps sit on the latency-critical path (NFR 1.1) versus which operations can degrade (NFR 2.1), and how state is preserved across process boundaries (NFR 2.3).

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths)

Additionally:
- Implement caching for latency-sensitive read paths (e.g., Redis-backed cache-aside), connection pooling/async I/O sized per NFR 1.2, and the admission-control mechanism from NFR 1.3 as runnable code.
- Implement the fault tolerance mechanisms from NFR 2.1 & 2.2 as real, runnable code (e.g., retry logic, circuit breakers, health endpoints).
- Implement the state preservation mechanism from NFR 2.3 as real, runnable code (e.g., durable queue for async steps).

---

# Verification Requirements
**Performance:**
- Load-test plan covering baseline, sustained target concurrency, and 3x spike scenarios, with metrics (p50/p95/p99 latency, throughput, error rate, resource utilization) and pass/fail thresholds tied to NFR 1.1–1.3.

**Reliability:**
- **Degradation Test:** Describe how to simulate load and verify non-essential features turn off while checkout stays up.
- **Recovery Test:** Describe how to simulate a DB disconnect and verify automatic reconnection without manual restart.
- **State Test:** Describe how to simulate a process kill and verify pending orders are recovered upon restart.

Where performance and reliability mechanisms interact (e.g., does retry logic increase latency?), state the trade-off explicitly.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on a local machine as a production-representative environment, with resource limits reflecting the target hardware class and the process-management mechanism in place.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix (quantitative + scenario-based).
2. ADRs for major decisions, including trade-off notes.
3. Data architecture narrative + complete schema, annotated for durability.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, OpenAPI spec(s), cache layer, fault-tolerance logic.
6. IaC config and documents.
7. Local deployment guide.
8. Load-test plan/instrumentation and reliability verification evidence.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
