# Overview
Design and implement a production-grade, full-stack e-commerce Order Management System (OMS).
Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building a comprehensive OMS that handles the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must be designed as if it will be deployed to a Kubernetes cluster handling non-trivial traffic. No authentication is required.

---

# Tech Stack (Fixed — do not substitute)
- **Frontend:** ReactJS (functional components, hooks, Context API or lightweight state management)
- **Backend:** Spring Boot 3.x (Java 17+, records where appropriate)
- **Containerization:** Docker (multi-stage builds)
- **Orchestration:** Kubernetes (raw manifests or Helm — your choice, justify)
- **Local runtime:** docker-compose for dev, minikube/kind for K8s

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
- The **architectural mechanism** you will use to satisfy it (e.g., a caching layer, an async queue, a circuit breaker, a specific DB engine, a K8s resource)
- The **module/component** where it lives
- A one-line **verification method** (how a reviewer would confirm it works)

Non-Functional Requirements to satisfy:
- **NFR 1.1 Response Time:** core journeys (product search, cart, checkout) must minimize round-trip latency under load.
- **NFR 1.2 Concurrency & Resource Utilization:** system must exploit available server resources (up to 98GB RAM class) with minimal queuing.
- **NFR 1.3 Queue Management:** sudden spikes must not crash the system — bound inbound queues, apply back-pressure, reject/delay excess gracefully.
- **NFR 2.1 Localization of Changes:** business rules (tax, discount, shipping) must be changeable without touching the core order engine.
- **NFR 2.2 Interface Stability:** frontend evolution must never force backend API recompilation or contract breakage.
- **NFR 2.3 Deferred Binding:** feature flags, cache TTLs, pool sizes, and similar parameters must be changeable at runtime or via external config without restart.
- **NFR 3.1 Graceful Degradation:** under CPU/RAM saturation, non-essential features (recommendations, analytics) must shed load while checkout stays alive.
- **NFR 3.2 Fault Detection & Recovery:** transient failures (DB drops, downstream hiccups) must auto-recover with minimal user-visible errors.
- **NFR 3.3 State Preservation:** process crash → restart must resume pending orders with minimal data loss.

## 3. Cross-Cutting Concerns (must be designed, not bolted on)
Address each of the following explicitly. Do NOT just name a library — explain the **pattern**, the **scope**, and the **failure behavior**:
- **Caching strategy:** which data is cached, where (in-process vs. distributed), invalidation policy, cache-aside vs. write-through, stampede protection.
- **Asynchronous messaging / queuing:** which flows are sync vs. async, ordering guarantees, dead-letter handling, consumer concurrency.
- **Resilience patterns:** retries (with backoff & jitter), circuit breakers, bulkheads, timeouts — applied to which call paths.
- **Connection & thread pool tuning:** how pool sizes are derived and exposed as deferred-binding parameters (NFR 2.3).
- **Back-pressure & load shedding:** how the system signals overload and what gets dropped first (NFR 1.3, 3.1).
- **Observability:** structured logging, metrics endpoints, distributed trace propagation, K8s liveness/readiness probes.
- **Externalized configuration:** how runtime parameters are injected (ConfigMaps, env vars, config server) to satisfy NFR 2.3.

## 4. Data Architecture
- Choose and **justify** the persistence store(s) per entity (polyglot persistence encouraged where it earns its keep).
- Explain read vs. write path separation if used.
- Explain how NFR 3.3 (state preservation) is guaranteed at the storage/transaction layer.
- Provide the schema (DDL or equivalent) — complete, not abbreviated.

## 5. Scalability & Statelessness
- Demonstrate that backend services are horizontally scalable (stateless request handling, externalized session/state).
- Explain how K8s will scale the workload (HPA triggers, resource requests/limits) and how this addresses NFR 1.2.

## 6. Module Structure
Follow RESTful, module-based Domain-Driven Design:
- Three layers: **UI (React)**, **Server (Spring Boot)**, **Shared Domain Models** (used by both sides via REST contracts).
- Each bounded context (Customer, Order, Product, Payment, Invoice) owns its own slice in all three layers.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum with full lifecycle), timestamps, invoice ref.
- **Product:** id, description, pricing (base + currency).
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

---

# User Workflow (must be implemented end-to-end)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

---

# Frontend Requirements (ReactJS)
Per entity produce three **complete** components:
- **Overview** (entry/dashboard)
- **List** (paginated, filterable collection)
- **Form** (create/edit with validation)

Use idiomatic React: hooks, composition, a shared API client, and error/loading states.

---

# Backend Requirements (Spring Boot)
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths to satisfy NFR 2.2)

---

# Infrastructure Requirements
Provide complete, runnable artifacts:
- **Dockerfiles** (multi-stage, minimal final images) for frontend and backend.
- **docker-compose.yml** for one-command local dev (all services + chosen data stores).
- **Kubernetes manifests** (or Helm chart): Deployments, Services, ConfigMaps, Secrets, HPA, liveness/readiness probes, and any StatefulSets/Jobs required by your chosen data stores.
- **Deployment guide** for local execution on minikube or kind, step-by-step, including how to verify each NFR is active.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** use Java records, Lombok where appropriate, Spring Data repository derivation, and React hook composition. Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.
- **Show the actual wiring** of cross-cutting concerns (e.g., the `@Cacheable` / cache manager config, the retry/circuit-breaker config, the queue listener) — not just the business methods.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix.
2. ADRs for major decisions.
3. Data architecture narrative + complete schema.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config (cache, queues, resilience, externalized config), OpenAPI spec.
6. Complete frontend code: API client, all Overview/List/Form components per entity, routing.
7. Dockerfiles + docker-compose.yml.
8. Kubernetes manifests (or Helm chart) with HPA, probes, ConfigMaps.
9. Local deployment guide (docker-compose path AND minikube/kind path).
10. Verification steps showing how to observe each NFR being satisfied.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.