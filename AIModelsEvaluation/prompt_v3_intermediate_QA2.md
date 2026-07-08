# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), optimized for demonstrable modifiability and explicit change-isolation. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building an OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must handle non-trivial traffic. No authentication is required. You may select and justify any backend language/framework, database, and messaging technology — none is mandated, but every choice must be defended against the NFRs below.

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
- A **concrete verification method** (a specific change scenario a reviewer could apply and the expected blast radius / non-effect).

Non-Functional Requirements to satisfy:
- **NFR 2.1 Localization of Changes:** define explicit bounded contexts — at minimum Ordering, Catalog, Payment, Invoicing, and Shipping — each owning its own module/package boundary and its own data. A change to invoicing rules (e.g., adding a new invoice status or billing field) must be confined to the Invoicing module and must not require modifying or redeploying the Order or Payment modules. Where contexts must react to each other's state changes (e.g., Invoicing reacting to Order acceptance), consider an asynchronous domain-event mechanism (e.g., a message broker such as RabbitMQ or Kafka) instead of direct synchronous coupling, so each context can evolve and scale independently.
- **NFR 2.2 Interface Stability:** all APIs must be explicitly versioned (e.g., URI-based, `/v1/...`), with a stated backward-compatibility policy: existing endpoints/fields must not change meaning or shape within a version; breaking changes require a new version, with old versions kept available for a defined deprecation window (state the window, e.g., minimum 2 releases). Provide a versioned OpenAPI contract per version, and consider a consumer-driven contract-testing tool (e.g., Pact) to automatically catch breaking changes.
- **NFR 2.3 Deferred Binding:** all environment-specific or tunable values (DB connection info, timeouts, rate limits, feature toggles) must be externalized from compiled code and changeable at runtime without a restart or redeploy — via environment variables re-read on a refresh signal, a dedicated config service (e.g., Spring Cloud Config, Consul, or etcd), or a feature-flag mechanism. State the propagation delay bound (e.g., changes take effect within 30 seconds) and how a change is audited (who/what/when).

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum with full lifecycle: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED as a terminal exception state from any pre-SHIPPED state), timestamps, invoice ref.
- **Product:** id, description, pricing (base + currency).
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

Each bounded context must own only the data it is authoritative for; cross-context references must go through a stable, explicit interface (not shared database tables/direct entity access).

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

Identify, per step, which bounded context owns it and what stable contract (event or API) is used to hand off to the next context.

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths to satisfy NFR 2.2)

Additionally:
- Implement the module/bounded-context boundaries as real package/project structure, not just naming convention — cross-context calls must go through defined interfaces (synchronous REST/gRPC calls, or published domain events via a broker), never direct repository/entity access across contexts.
- Implement the externalized configuration mechanism from NFR 2.3 as real, runnable code (e.g., env vars combined with a lightweight config-refresh endpoint, or a config/feature-flag service), including at least one value that can be changed and observed to take effect without restarting the application.

---

# Change-Isolation Verification Requirements
- Provide at least one worked example changing a business rule inside a single bounded context (e.g., adding a new invoice field or a new status value) and show which files change — confirm no other module's code or contract changes as a result.
- Provide a contract test (or equivalent) demonstrating that an existing API version's request/response shape is unaffected by that change.
- Provide a runtime demonstration (script or documented steps) of reconfiguring one externalized value without restarting the service.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on local machine as a production environment, including the mechanism used to deliver runtime configuration (e.g., mounted config file, env var injection, config service).

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix with concrete change scenarios.
2. ADRs for major decisions.
3. Data architecture narrative + complete schema, annotated by bounded context ownership.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, versioned OpenAPI spec(s).
6. IaC config and documents.
7. Local deployment guide.
8. Worked change-isolation example, contract test, and runtime reconfiguration demonstration.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
