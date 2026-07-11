# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), fully specified for reliability: explicit graceful degradation, automated fault recovery, and crash-safe state preservation, with all technical choices justified by specific libraries and patterns. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building an OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must run on a single-node deployment target. No authentication is required. You may select and justify any backend language/framework, database, and messaging technology — none is mandated, but every choice must be defended against the NFRs below, and any tension between reliability and latency must be reconciled explicitly.

---

# Architectural Design Requirements

## 1. Architectural Decision Records (ADR)
For every major architectural choice you MUST provide a short ADR entry containing:
- **Decision:** what you chose
- **Context:** which NFR(s) it addresses
- **Alternatives considered:** at least 2 other options and why they were rejected
- **Consequences:** trade-offs accepted, with numeric costs where relevant and any reliability/latency tension explicitly noted

## 2. NFR Traceability Matrix (MANDATORY)
Before writing any code, produce a table mapping every NFR below to:
- The **architectural mechanism** you will use to satisfy it.
- The **module/component** where it lives.
- A **precise verification method** — exact failure injection steps and expected system behavior.

Non-Functional Requirements to satisfy:

**Reliability**
- **NFR 2.1 Graceful Degradation:** Under extreme resource contention (e.g., CPU or RAM saturation), the system must gracefully degrade non-essential features (e.g., personalized product recommendations, heavy analytics logging) to ensure core checkout functionality remains available with minimum downtime. **Implementation:** Use a Circuit Breaker pattern (e.g., Resilience4j/Polly) on non-essential calls; implement a fallback response (cached/default) when the breaker opens.
- **NFR 2.2 Fault Detection and Recovery:** The application must detect internal component failures (e.g., temporary database connection drops or GPU driver hiccups) and automatically attempt to recover or reconnect within the shortest possible time, minimizing user-facing errors. **Implementation:** Use Health Check endpoints (e.g., Spring Actuator /custom `/health`) and Retry patterns with exponential backoff (e.g., Spring Retry) for transient DB errors.
- **NFR 2.3 State Preservation:** In the event of an unexpected application process crash, the system must be able to restore its operational state and resume processing pending orders upon restart with minimal data loss. **Implementation:** Use a Transactional Outbox pattern or durable message queue (e.g., RabbitMQ/Kafka with acknowledgments) for state transitions; ensure process management (e.g., systemd) auto-restarts the service.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED as a terminal exception state), timestamps per transition, invoice ref, optimistic-lock version field.
- **Product:** id, description, pricing (base + currency), stock/availability indicator.
- **Payment:** id, order ref, amount, timestamp, status, method, idempotency key.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

Provide the explicit Order state-transition table (from-state, event, to-state, guard) enforced in the domain layer. For each state transition, specify if it is persisted synchronously (critical) or asynchronously (degradable).

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

For each step: (a) classify its criticality (Core vs. Non-Essential per NFR 2.1), and (b) specify the recovery mechanism if it fails (Retry vs. Manual Intervention per NFR 2.2).

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths)

Additionally, implement as real, runnable code:
- A circuit breaker configuration for non-essential services (e.g., Recommendation API) with a defined fallback method, sized connection pools, and the full retry/backpressure chain from NFR 2.2 (e.g., Spring Retry + HikariCP validation query).
- State preservation logic from NFR 2.3: ensure order state changes are written to a durable store (DB or Queue) before responding; include a startup routine that checks for "in-flight" orders and resumes them.
- Process management configuration (e.g., a `systemd` unit file or Docker restart policy) to ensure automatic restart upon crash.

---

# Verification Requirements
**Reliability:**
- **Degradation Test:** Load-test plan (tool named, e.g., JMeter) inducing severe load while disabling a non-essential service; pass if core checkout API returns success while non-essential API returns fallback.
- **Recovery Test:** Script that temporarily blocks network traffic to the DB port; pass if errors spike briefly then auto-recover without manual restart.
- **State Test:** Script that force-terminates (`kill -9`) the Orderman process during order creation; pass if DB reflects all committed transactions up to failure upon restart.

**Cross-cutting:** explicitly state where a reliability mechanism interacts with latency (e.g., does retry logic increase checkout time?) and how the design resolves it.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on a local machine as a production-representative environment. Resource limits must numerically reflect the target hardware class. The runtime-configuration and process-management mechanism must be present.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix (failure scenarios + expected behavior).
2. ADRs for major decisions, including numeric trade-offs and reliability/latency tension notes.
3. Data architecture narrative + complete schema, including the Order state-transition table and durability annotations.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, OpenAPI spec(s), circuit breaker/retry implementation, state recovery logic.
6. IaC config and documents, with process-management config (systemd/Docker).
7. Local deployment guide.
8. Reliability test plan/instrumentation evidence (degradation, recovery, state preservation scripts).

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
