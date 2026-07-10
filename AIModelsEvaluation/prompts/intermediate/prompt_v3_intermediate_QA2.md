# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), optimized for demonstrable reliability and fault tolerance. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building a OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must handle non-trivial traffic. No authentication is required. You may select and justify any backend language/framework, database, and messaging technology — none is mandated, but every choice must be defended against the NFRs below.

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
- A **concrete verification method** (a specific failure scenario a reviewer could apply and the expected system behavior).

Non-Functional Requirements to satisfy:
- **NFR 2.1 Graceful Degradation:** Under extreme resource contention (e.g., CPU/RAM saturation), non-essential features (e.g., recommendations, heavy logging) must degrade to ensure core checkout remains available. **Hint:** Consider using a circuit breaker pattern or feature flags to disable non-critical paths dynamically.
- **NFR 2.2 Fault Detection and Recovery:** The application must detect internal component failures (e.g., DB connection drops) and automatically attempt to recover/reconnect within the shortest possible time. **Hint:** Consider implementing health check endpoints (Ping/Echo) and retry policies with exponential backoff.
- **NFR 2.3 State Preservation:** In the event of an unexpected process crash, the system must restore operational state and resume processing pending orders upon restart with minimal data loss. **Hint:** Consider using durable message queues or transactional outbox patterns to ensure no order state is lost during a crash.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum with full lifecycle: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED), timestamps, invoice ref.
- **Product:** id, description, pricing (base + currency).
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

Each entity must support state recovery; ensure critical state transitions are persisted before acknowledging external requests.

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

Identify, per step, which operations are critical (must not fail) vs. non-essential (can degrade), and how state is preserved across process boundaries.

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths)

Additionally:
- Implement the fault tolerance mechanisms from NFR 2.1 & 2.2 as real, runnable code (e.g., retry logic, circuit breakers, health endpoints).
- Implement the state preservation mechanism from NFR 2.3 as real, runnable code (e.g., ensuring transactions are committed before response, or using a durable queue for async steps).

---

# Reliability Verification Requirements
- **Degradation Test:** Describe how to simulate load and verify non-essential features turn off while checkout stays up.
- **Recovery Test:** Describe how to simulate a DB disconnect and verify automatic reconnection without manual restart.
- **State Test:** Describe how to simulate a process kill (e.g., `kill -9`) and verify pending orders are recovered upon restart.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on local machine as a production environment, including the mechanism used to ensure process restarts (e.g., systemd, Docker restart policies).

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix with concrete failure scenarios.
2. ADRs for major decisions.
3. Data architecture narrative + complete schema, annotated for durability.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, OpenAPI spec, fault-tolerance logic.
6. IaC config and documents.
7. Local deployment guide.
8. Reliability verification evidence (degradation, recovery, state preservation steps).

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
