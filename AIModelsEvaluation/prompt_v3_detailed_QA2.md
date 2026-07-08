# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS), fully specified for modifiability: explicit bounded contexts, a versioning/deprecation policy, a change-impact contract, and an auditable runtime-configuration mechanism. Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

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
- A **precise verification method**: the exact change scenario applied, the files/modules expected to change, and the files/modules expected to remain untouched.

Non-Functional Requirements to satisfy:
- **NFR 2.1 Localization of Changes:** define explicit bounded contexts — at minimum Ordering, Catalog, Payment, Invoicing, and Shipping — each with its own module/package, its own persistence (own tables/schema or own database), and its own domain model that is not shared by reference with other contexts. State the inter-context communication mechanism per pair of contexts (synchronous request/response, e.g., REST/gRPC, vs. asynchronous domain event, e.g., published to a broker such as RabbitMQ or Kafka and consumed by subscribing contexts) and, for each, whether it uses an anti-corruption layer / translation at the boundary. Name the concrete event schema/serialization approach (e.g., versioned JSON schema or a schema-registry-backed format) if events are used. A change to an internal business rule in one context (e.g., adding a new invoice field, changing an invoicing calculation) must touch only that context's module — enumerate what "touching" excludes (no shared entity classes, no shared migration files, no controller changes in other contexts).
- **NFR 2.2 Interface Stability:** every API is versioned in the URI (e.g., `/v1/...`) with a written compatibility policy: (a) additive changes (new optional fields, new endpoints) do not require a version bump; (b) any removal, renaming, or semantic change of an existing field/endpoint requires a new version; (c) at least 2 versions are supported concurrently in production; (d) deprecated versions carry a `Deprecation`/`Sunset` response header (or documented equivalent) with a stated sunset date at least 90 days out. Provide a distinct, versioned OpenAPI document per supported API version, and a consumer-driven contract test using a concrete tool/pattern (e.g., a Pact-style contract test) that fails the build if a response shape changes incompatibly within a version.
- **NFR 2.3 Deferred Binding:** all environment-specific or tunable values (DB connection info, timeouts, retry counts, feature toggles, business thresholds such as invoice due-date offsets) are externalized from compiled artifacts. Specify the exact mechanism and name a concrete technology choice (e.g., environment variables re-read via a refresh endpoint/signal, a config service such as Spring Cloud Config/Consul/etcd, or a feature-flag service/library) and: (a) the propagation delay bound (state and justify a number, e.g., ≤30 seconds), (b) the audit record captured per change (who/what/when/old-value/new-value, and where it is stored — e.g., an append-only audit table or the config service's own change history), and (c) the rollback mechanism if a bad config value is pushed.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum: CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED, plus CANCELLED as a terminal exception state), timestamps, invoice ref.
- **Product:** id, description, pricing (base + currency).
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

For each bounded context, list: the entities it owns, the domain events it publishes (name, payload schema, versioning approach for the event schema itself), and the events/APIs it consumes from other contexts.

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

For each step, name the owning bounded context and the exact contract (endpoint or event name + schema) used to hand off to the next step's context.

---

# Backend Requirements
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths satisfying NFR 2.2)

Additionally, implement as real, runnable code:
- Bounded-context boundaries as separate modules/packages/projects with no shared entity classes or cross-context direct database access; all cross-context interaction goes through the declared APIs/events (e.g., REST/gRPC calls, or events published to and consumed from a broker such as RabbitMQ or Kafka), including any anti-corruption translation.
- The versioning and deprecation mechanism from NFR 2.2, including at least one deprecated-but-still-served endpoint demonstrating the sunset header/policy, and a contract test (e.g., Pact-style) wired into the build.
- The externalized, runtime-reloadable configuration mechanism from NFR 2.3 (e.g., a config service such as Spring Cloud Config/Consul/etcd, or an env-var-plus-refresh-endpoint approach), including the audit log and rollback path, applied to at least two real configuration values (one infrastructure-level, one business-rule-level).

---

# Change-Isolation Verification Requirements
- A worked example: add a new field or status to Invoice and show the complete diff — confirm no file outside the Invoicing module changes, and that the Order/Payment modules' code and contracts are untouched.
- A consumer-driven contract test (or equivalent) proving an existing API version's request/response shape is unaffected by that change, with the test shown passing before and (hypothetically) failing if the contract were broken.
- A runtime demonstration (script or documented steps) that changes one business-rule config value and one infrastructure config value without restarting the service, with the audit log entry shown for each.
- A brief impact-analysis note estimating, for a second hypothetical change (e.g., adding a new Shipping carrier integration), which modules would change and which would not, based on the boundaries defined.

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on local machine as a production environment, including the concrete delivery mechanism for runtime configuration (e.g., mounted file, config service, feature-flag backend) and how each bounded context's data store is provisioned independently.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix with precise change scenarios and expected diffs.
2. ADRs for major decisions.
3. Data architecture narrative + complete schema, partitioned and annotated by bounded context ownership.
4. Shared domain models (used by both FE and BE).
5. Complete backend code: entities, repositories, services, controllers, config, versioned OpenAPI spec(s), contract tests.
6. IaC config and documents.
7. Local deployment guide.
8. Worked change-isolation diff, contract test evidence, runtime reconfiguration + audit-log demonstration, and the impact-analysis note.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- Do not mandate a specific programming language up front; select and justify one against the NFRs.
