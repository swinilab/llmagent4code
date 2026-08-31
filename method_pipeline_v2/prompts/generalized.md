# Overview

Design and implement a production-grade backend system for the domain described in the Domain Specification section below.

Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

This prompt is domain-independent by construction. Everything before the Domain Specification section applies unchanged to any backend system; the Domain Specification is the only part that changes when the system under construction changes. Nothing outside it names a specific entity, endpoint, or business rule.

---

# How this prompt is organised, and what is expected of you

Two things are asked of you, and they are different in kind.

**The domain is given.** The entities, their field constraints, and the behavioural workflow are specified below and are not yours to change. Implement them exactly.

**The quality attributes are yours to choose.** This prompt does not hand you a list of non-functional requirements to satisfy. You are to decide which quality attributes matter for this system, express them as architecturally significant requirements, select the tactics that address them, implement those tactics, and then prove — by executable measurement, not assertion — that they work.

That second task is the substance of the exercise. A system that implements the domain correctly but whose quality attributes exist only in prose has not completed it.

**What "prove" means here.** An external reviewer will run your system and your verification suite without reading your source code. Everything they need in order to drive, observe, and check your system must therefore be declared in machine-readable manifests that you produce. A mechanism that works but cannot be observed from outside is indistinguishable, to that reviewer, from one that was never built.

---

# Part 1 — Architecture and quality attributes

## 1.1 Choose and justify the quality attributes

Select **at least four** quality attributes this system must exhibit, drawn from recognised quality-attribute taxonomies (availability, performance, security, modifiability, testability, usability, and so on).

Choose them from the domain, not from a checklist. A workflow with irreversible financial steps implies different attributes than a read-heavy catalogue. State, in one or two sentences per attribute, what it is about *this* domain that makes the attribute matter. An attribute you cannot justify from the domain should not be on your list.

Cover at least two distinct quality attributes overall — a list drawn entirely from one attribute does not demonstrate architectural breadth.

## 1.2 Express each as an architecturally significant requirement

For each quality attribute, write one or more ASRs in the six-part scenario form:

```text
Source           — who or what generates the stimulus
Stimulus         — the condition that arrives
Artifact         — the part of the system it arrives at
Environment      — the operating state at that moment (normal, overload, degraded, fault)
Response         — what the system must do
Response measure — the externally observable, quantified criterion
```

The response measure must be a number an outside observer can measure without access to your source code: a latency percentile, a success rate, a count, a status code, a bounded elapsed time. "The system remains responsive" is not a response measure. "p95 latency stays below 500 ms while the dependency is unreachable" is.

Choose the numeric thresholds yourself and justify each one. A threshold you cannot justify is a threshold you have not thought about.

## 1.3 Select tactics

For each ASR, name the architectural tactic that satisfies it, cited **verbatim** from Bass, Clements & Kazman, *Software Architecture in Practice*, with its full category path:

```text
Availability > Detect Faults > Timeout
Performance > Manage Resources > Maintain Multiple Copies of Data
```

Do not paraphrase, abbreviate, or invent tactic names. If no published tactic applies cleanly, write `N/A — <one-line justification>` rather than bending a name to fit.

**Scope.** A tactic is implemented at its natural architectural scope — normally a cross-cutting component applied wherever the concern arises. An ASR names a concrete endpoint or entity so the requirement is observable, but that named element is a **probe, not a boundary**. A retry policy reachable only from the one endpoint your scenario mentions is an implementation defect, not a satisfied requirement.

Where a tactic is deliberately applied to only part of the system — caching some entities and not others, for instance — that narrower scope is a design decision. State it in the ADR and justify it. Note that entities whose state advances through a workflow are usually poor caching candidates: a stale copy makes workflow state externally observable as incorrect.

## 1.4 Architectural Decision Records

For every major architectural choice, provide an ADR containing:

- **Decision** — what you chose
- **Context** — which ASR(s) it addresses
- **Alternatives considered** — at least two other options and why you rejected them
- **Consequences** — the trade-offs you accepted

Where two tactics pull against each other, say so explicitly and record how you resolved the tension. Freshness against availability, retry against latency budget, admission control against throughput: these conflicts are the substance of architectural design, and an ADR set that records none of them has probably not confronted them.

## 1.5 Traceability matrix

Produce a table with one row per ASR:

```text
ASR ID | Quality attribute | Tactic (verbatim) | Mechanism | Component/module |
Files | Functions/configuration | Runtime metrics | Verification scenario
```

It must describe what you actually delivered, not what you planned. Reconcile it after implementation.

---

# Part 2 — Machine-readable declarations

An external reviewer drives your system through these manifests alone. They do not read your source, your OpenAPI document, or your prose. **A capability you do not declare here cannot be exercised, and will be reported as absent.**

All manifests live at the project root and must agree with each other, with the OpenAPI document, and with the running code. Any disagreement is a defect.

## 2.1 `nfr-trace.json` — what you built and where

```json
{
  "nfrTrace": [
    {
      "asrId": "ASR-1",
      "qualityAttribute": "Availability",
      "nfr": "short name for the requirement",
      "tacticUsed": "Availability > Detect Faults > Timeout",
      "responseMeasure": {
        "description": "what an observer measures",
        "metric": "metric_name_as_exposed",
        "operator": "<=",
        "value": 1500,
        "unit": "ms"
      },
      "filesImplemented": ["path/to/file.py"],
      "functionNames": ["path/to/file.py::function_name"],
      "configurationKeys": ["DB_TIMEOUT_MS"],
      "librariesUsed": ["library"],
      "metrics": ["metric_name_as_exposed"],
      "verificationMethod": "verification/asr_1_timeout.py",
      "faultRequired": "database-latency"
    }
  ]
}
```

Rules:

1. One entry per ASR. No omissions, no merging.
2. `filesImplemented` lists files that exist in your deliverable. A path that does not resolve is a defect.
3. `functionNames` lists functions that exist **verbatim** at those paths, in `relative/path::qualified_name` form. Each must be the function that *directly* implements or configures the mechanism — the one that calls into the retry library, not the request handler three layers above it. One function may serve several ASRs; list it under each.
4. `tacticUsed` is verbatim from the published taxonomy, per §1.3.
5. `metrics` names only counters your metrics endpoint actually exposes (§2.3).
6. `verificationMethod` is the runnable path from §3, not a description.
7. `faultRequired` names the fault this ASR needs, matching a key you declare in §2.4, or `null` where the ASR needs no fault.
8. Consistent with the traceability matrix: same ASRs, same tactics, same thresholds.

## 2.2 API manifests — how to reach the domain

**`create_apis.json`** — one entry per entity in the Domain Specification:

```json
{
  "<entity>": {
    "method": "POST",
    "path": "/api/v1/<collection>",
    "readPathTemplate": "/api/v1/<collection>/{id}"
  }
}
```

- Keys are the entity names from the Domain Specification, lowercase and singular. One per entity, no extras.
- `path` is the real registered route including any version prefix. No host, no placeholders.
- `readPathTemplate` is the real single-resource read route, containing `{id}` exactly once. Declare it rather than assuming `/{id}` can be appended; the verb is always `GET`.
- Creation is **synchronous**: `POST` returns `201` with the created resource in the body. A reviewer reads `status_code` and `json()` immediately, with no polling step.

**`workflow_apis.json`** — one entry per state-changing step in the workflow that is not entity creation:

```json
{
  "<stepName>": {
    "method": "POST",
    "pathTemplate": "/api/v1/<collection>/{id}/<action>",
    "entity": "<entity the step acts on>",
    "precondition": "<required status, exact enum value>",
    "postcondition": "<resulting status, exact enum value>"
  }
}
```

- Derive entries from the workflow in the Domain Specification. Do not invent steps it does not describe or omit ones it does.
- `stepName` is a camelCase verb phrase naming the step as the workflow describes it.
- `pathTemplate` contains `{id}` exactly once.
- `precondition` and `postcondition` use exact enum values from the Field Constraint Table. Invoking a step whose precondition does not hold MUST return `409`.

## 2.3 `observability.json` — how to watch the mechanisms

You choose your counter names; the reviewer learns them from this file. Names must describe what is counted, not which scenario reads them.

```json
{
  "metricsEndpoint": "/internal/metrics",
  "healthEndpoints": {
    "liveness": "/health/live",
    "readiness": "/health/ready"
  },
  "resetEndpoint": "/internal/test/reset",
  "metrics": [
    {
      "name": "dependency_timeouts_total",
      "type": "counter",
      "description": "increments where the timeout fires, at the dependency boundary",
      "incrementedAt": "app/db/client.py::execute_with_timeout",
      "scope": "system-wide"
    }
  ],
  "errorCodes": [
    {
      "code": "DEPENDENCY_TIMEOUT",
      "httpStatus": 504,
      "meaning": "a dependency operation exceeded its configured time limit"
    }
  ]
}
```

Requirements on the endpoints:

1. The metrics endpoint returns a flat JSON object of integer-valued counters, monotonic until reset, whose keys are exactly the declared `name` values.
2. Every counter increments **at the point where its mechanism executes** — inside the retry policy, inside the admission decision — never at a request handler that infers it happened.
3. `scope` is `system-wide` or a stated narrower scope. A counter declared system-wide that only ever increments on one endpoint indicates the mechanism was not applied at its declared scope.
4. The reset endpoint clears counters, caches, and injected-fault state, returns `204`, and touches **in-process state only** — it never deletes persisted business data, and it must succeed without a dependency round-trip so it stays callable during an outage.
5. Every controlled failure response carries `{"error": {"code": "...", "message": "..."}}` with a `code` declared in `errorCodes`. Additional keys inside `error` are permitted.
6. Error codes must **distinguish causes that a client would act on differently**. In particular, a dependency that is slow and a dependency that is absent must not report the same code: a reviewer cannot otherwise tell your timeout tactic from your degradation tactic, and neither will be credited.

### Observation paths must survive the conditions you create

Your system is observed *while* it is overloaded and *while* its dependencies are failing. The metrics, health, and reset endpoints are observation infrastructure, not business traffic:

- They MUST NOT pass through admission control, rate limiting, or any load-shedding mechanism. They are never rejected with `429` and never consume an admitted slot.
- They MUST NOT require a dependency round-trip. During a database outage, liveness and metrics must still return `200` with valid bodies.
- Readiness is the sole exception in *content*: it should report not-ready during an outage. It must still **answer** — report the unready state, do not hang or fail to respond.
- They MUST NOT be delayed by test hooks.

An application whose observation paths disappear under fault cannot be evaluated at all. This is a defect in its own right, independent of whether the mechanism behind them works.

## 2.4 `fault-hooks.json` — how to induce the conditions

A tactic that responds to a fault can only be verified if the fault can be induced on demand. Declare every fault your verification suite needs:

```json
{
  "enableFlag": {
    "variable": "ENABLE_TEST_HOOKS",
    "enabledValue": "true",
    "default": "false"
  },
  "faults": [
    {
      "key": "database-latency",
      "description": "delays every database response by a configurable interval",
      "mechanism": "toxiproxy",
      "induce": {
        "type": "http",
        "request": "POST http://localhost:8474/proxies/postgres/toxics",
        "body": { "type": "latency", "attributes": { "latency": 5000 } }
      },
      "remove": {
        "type": "http",
        "request": "DELETE http://localhost:8474/proxies/postgres/toxics/latency"
      },
      "verifyInduced": "GET http://localhost:8474/proxies/postgres — the toxic is listed",
      "affects": "every query issued through the connection pool"
    },
    {
      "key": "transient-dependency-failure",
      "description": "fails the first N attempts at the dependency boundary",
      "mechanism": "request header",
      "induce": {
        "type": "header",
        "name": "X-Test-Fault",
        "value": "transient-db-failures=2"
      },
      "remove": {
        "type": "header",
        "note": "per-request; absent header means no fault"
      },
      "verifyInduced": "attempt counter increases by more than one for a single request",
      "affects": "the dependency read boundary only"
    }
  ]
}
```

Rules:

1. `verifyInduced` must be observable **independently of the application under test** — the proxy's own state, the container's status, a counter the fault injector maintains. "The application returned an error, so the fault must have worked" is circular: a broken application returns errors too.
2. Faults implemented as test hooks are inert unless `enableFlag` is set. When disabled, hook endpoints return `404` and hook headers are ignored with no side effect.
3. An unrecognised, malformed, or out-of-range hook value is **ignored silently** — the request proceeds as if the header were absent. Never return `400` for a bad test header; that turns a harness mistake into an application failure and masks the real result.
4. A hook creates a stimulus; it never bypasses the mechanism it is meant to exercise. A "fault" that skips the retry policy rather than triggering it verifies nothing.
5. Prefer faults injected **outside** the application — a proxy, a stopped container, a severed network path — over in-process hooks. External faults are more convincing evidence because the application cannot fake them. Use in-process hooks where a fault must be deterministic and precisely placed, such as failing exactly the first two attempts, or raising at an exact point inside a transaction.

---

# Part 3 — Executable verification

Every ASR must be observable at runtime. Provide, for each, a runnable script that induces the relevant condition, measures the response, and reports pass or fail — reproducible by a reviewer who has not read your code.

Place them under `verification/`, one entry point per ASR, named so the mapping is unambiguous.

## 3.1 What a verification script must do

1. **Induce the condition the tactic responds to.** A script that calls a healthy endpoint and observes success verifies nothing about an availability or performance tactic. If the ASR concerns behaviour under a slow dependency, the script makes the dependency slow.
2. **Confirm the fault took effect**, by the independent means declared in `verifyInduced`.
3. **Measure a baseline** under healthy conditions, so the effect of the fault is demonstrable rather than asserted.
4. **Measure the response** against the ASR's threshold.
5. **Remove the fault** and confirm the system recovers.
6. **Emit a machine-readable result** and exit non-zero when it fails.

## 3.2 Result format

Each script writes one JSON object to `verification/results/<asr-id>.json`:

```json
{
  "asrId": "ASR-1",
  "nfr": "Dependency timeout detection",
  "tacticUsed": "Availability > Detect Faults > Timeout",
  "faultInduced": {
    "key": "database-latency",
    "description": "5000 ms latency injected via toxiproxy",
    "verified": true,
    "verifiedBy": "toxiproxy API lists the latency toxic as active"
  },
  "baseline": [
    { "metric": "p95_response_ms", "value": 42 }
  ],
  "observed": [
    { "metric": "p95_response_ms", "value": 1180 },
    { "metric": "requests_hanging_beyond_limit", "value": 0 }
  ],
  "threshold": [
    { "metric": "p95_response_ms", "operator": "<=", "value": 1500 },
    { "metric": "requests_hanging_beyond_limit", "operator": "==", "value": 0 }
  ],
  "recovered": true,
  "passed": true
}
```

Rules:

1. Every metric in `threshold` also appears in `observed`.
2. `passed` is **computed** as the conjunction of the threshold comparisons. A hard-coded `passed` is a defect.
3. Values in `observed` come from real measurement, or from counters incremented by the mechanism itself where it executes. Precomputed or constant values are a defect.
4. `faultInduced.verified` reflects the independent check from `verifyInduced`. If the fault could not be confirmed, report `false` and let the script fail — a scenario that did not actually run must not report success.
5. **The suite must stay honest when the mechanism is broken.** For each script, ask: if I deleted the tactic it verifies, would this still pass? If yes, the script tests nothing. This is the single most common way a verification suite becomes decorative, and it is worth checking deliberately for each one rather than assuming.

## 3.3 Interactions between scenarios

Scenarios run against one deployment and can interfere. Two cases arise often enough to name:

**Load-generating scenarios and admission control.** A scenario measuring throughput or cache behaviour must stay within the concurrency your admission control admits. Otherwise your own load shedding rejects the measurement traffic, and the result describes admission control rather than the mechanism under test. Either keep offered concurrency below the limit or exclude shed requests from the measurement — and say which you did.

**Caching and degraded operation.** If one ASR requires cached data to expire so that fresh data is observable, and another requires cached data to survive a dependency outage, these conflict directly. The resolution is a design decision — separate freshness from availability, apply different policies to different data, or something else — and it belongs in the ADR. Do not resolve it by weakening one requirement until both trivially pass.

State any other interference you find, and how your suite avoids it.

## 3.4 Honesty of implemented mechanisms

Every required behaviour must be produced by the real mechanism at runtime:

- No fabricated metrics, precomputed answers, or responses that bypass the mechanism they demonstrate.
- Counters increment where the mechanism executes, and must agree with independently observable evidence — dependency-side query statistics, proxy state, container restart counts, raw HTTP responses.
- Test hooks create stimuli only; they never substitute for the mechanism's behaviour.

A reviewer will cross-check your reported counters against external evidence. Numbers that disagree with what the dependency, the proxy, and the container runtime report are treated as fabricated.

---

# Part 4 — Implementation requirements

## 4.1 Layering

Per entity, deliver three complete layers:

- **Service** — business logic, transaction boundaries, orchestration of cross-cutting concerns
- **Controller** — REST endpoints, request/response mapping, validation
- **Routing / API definition** — OpenAPI-friendly, versioned paths

Cross-cutting mechanisms are **shared components**, not per-entity copies. Prefer composition over inheritance.

## 4.2 Validation and status codes

Uniformly across every endpoint:

- Malformed syntax or a field-constraint violation → `400`
- Well-formed identifier, no such resource → `404`
- Reference exists but is in the wrong workflow state → `409`
- Server-generated, computed, or read-only fields supplied by the client → `400`, never silently ignored

The three-way distinction between `400`, `404`, and `409` must hold for every reference on every endpoint. Collapsing any two is the most common defect in this class of system.

## 4.3 Infrastructure

Provide complete, runnable artifacts to deploy locally as a production-like environment: container definitions, orchestration, schema migrations that run automatically at startup with no manual step.

Pin all direct dependency versions. No manual source or configuration edit may be required after generation.

`start_command.txt` at the project root contains exactly one non-empty line that starts the whole system.

## 4.4 Code quality

- No placeholders, no ellipses, no "repeat this pattern for the other fields". Every file complete and runnable.
- Be concise; do not pad with boilerplate.
- Every cross-cutting concern visible in code, not only described in prose.

---

# Part 5 — Domain Specification

> Everything above this line is domain-independent. This section is the only part that changes
> when the system under construction changes. To retarget this prompt to a different domain,
> replace this section and nothing else.

## 5.1 Context

Build a backend-only e-commerce Order Management System (OMS) serving the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. Three roles participate — Customer, Order Staff, Accountant — as domain data only. No authentication is required. The system must handle non-trivial concurrent traffic.

## 5.2 Domain model

- **Customer** — id, name, address, phone, banking details, order history, role
- **Product** — id, description, pricing (amount + currency)
- **Order** — id, customer ref, line items, amounts, status (enum with full lifecycle), timestamps, invoice ref
- **Invoice** — id, order ref, billing info, amounts, issue/due dates, status
- **Payment** — id, order ref, amount, timestamp, status, method

## 5.3 Field Constraint Table

This table is the authoritative source for all field-level validation. Every constraint MUST be implemented as actual validation logic in the entity/DTO/controller layer — not merely documented. It is also the basis for Boundary Value Analysis and Equivalence Partitioning test design, so exact numeric boundaries and regex patterns must be honoured precisely, with no silent rounding, truncation, or relaxed validation.

Notation: a length written `2–100` means minimum 2 and maximum 100 characters, both inclusive.

### Entity: Customer

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| name | string | Yes | - | - | - | 2–100 | `^[\p{L} .'-]+$` | Must not be blank or whitespace-only | - |
| address | string | Yes | - | - | - | 5–255 | free text | Must not be blank or whitespace-only | - |
| phone | string | Yes | - | - | - | 8–15 digits | `^\+?[1-9]\d{7,14}$` (E.164) | Must not start with 0 after country code | - |
| bankingDetails.accountNumber | string | Yes | - | - | - | 6–20 | `^\d{6,20}$` | - | - |
| bankingDetails.bankName | string | Yes | - | - | - | 2–100 | `^[\p{L}0-9 .&-]+$` | - | - |
| role | enum | Yes | - | - | - | - | - | Fixed at creation | `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT` |
| orderHistory | array\<UUID\> | No (read-only, server-derived) | - | 0 | soft cap 10,000 | - | - | Not settable by client | - |

### Entity: Product

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| description | string | Yes | - | - | - | 3–500 | free text | Must not be blank or whitespace-only | - |
| price.amount | decimal(2dp) | Yes | - | 0.01 | 999999.99 | - | `^\d{1,6}\.\d{2}$` | Must be > 0, exactly 2 decimal places, no rounding | - |
| price.currency | string | Yes | - | - | - | 3 | `^[A-Z]{3}$` (ISO 4217) | Must be in supported currency list | `USD`, `VND`, `EUR` |

### Entity: Order

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| customerRef | UUID (FK) | Yes | Customer.id must exist | - | - | 36 | UUIDv4 | Must reference an existing customer | - |
| lineItems | array\<LineItem\> | Yes | Product.id must exist per item | 1 item | 100 items | - | - | No duplicate productRef within one order; duplicates MUST be rejected with `400` | - |
| lineItems[].productRef | UUID (FK) | Yes | Product.id must exist | - | - | 36 | UUIDv4 | - | - |
| lineItems[].quantity | int | Yes | - | 1 | 1000 | - | `^\d+$` | Must be a whole number | - |
| lineItems[].unitPriceSnapshot | decimal(2dp) | Yes | Copied from Product.price.amount at order time | 0.01 | 999999.99 | - | `^\d{1,6}\.\d{2}$` | Immutable snapshot, server-computed, not client-settable | - |
| totalAmount | decimal(2dp) | Yes | = Σ(quantity × unitPriceSnapshot) | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Server-computed, not client-settable | - |
| status | enum | Yes | Must follow the state machine | - | - | - | - | Default `PLACED`; client cannot set an initial status | `PLACED`, `ACCEPTED`, `INVOICED`, `PAID`, `VERIFIED`, `SHIPPED`, `CLOSED`, `CANCELLED` |
| createdAt | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-generated, immutable | - |
| updatedAt | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-updated on every state change; must be >= createdAt | - |
| invoiceRef | UUID (FK) | No | Invoice.id must exist when present | - | - | 36 | UUIDv4 | Null until an invoice is created | - |

### Entity: Invoice

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated | - |
| orderRef | UUID (FK) | Yes | Order.id must exist, order.status = `ACCEPTED` | - | - | 36 | UUIDv4 | Order must be accepted before invoicing | - |
| billingInfo.name | string | Yes | Copied from Customer.name at issue time | - | - | 2–100 | `^[\p{L} .'-]+$` | Snapshot, not a live reference | - |
| billingInfo.address | string | Yes | Copied from Customer.address | - | - | 5–255 | free text | Snapshot | - |
| totalAmount | decimal(2dp) | Yes | = Order.totalAmount | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Must equal the order's total at issue time | - |
| issueDate | date | Yes | - | - | - | - | `dd/MM/yyyy`, `^\d{2}/\d{2}/\d{4}$` | Must be a real calendar date (reject 31/02); defaults to server current date | - |
| dueDate | date | Yes | Must be >= issueDate | - | - | - | `dd/MM/yyyy` | Default = issueDate + 7 days; must not precede issueDate; must be a real calendar date | - |
| status | enum | Yes | Must follow the state machine | - | - | - | - | Default `ISSUED` on creation | `ISSUED`, `PAID`, `OVERDUE`, `CANCELLED` |

### Entity: Payment

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated | - |
| orderRef | UUID (FK) | Yes | Order.id must exist, order.status = `INVOICED` | - | - | 36 | UUIDv4 | Order must be in a payable state | - |
| amount | decimal(2dp) | Yes | Must equal Invoice.totalAmount | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Exact match required — no partial or over payment | - |
| timestamp | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-generated at submission | - |
| status | enum | Yes | Must follow the state machine | - | - | - | - | Default `PENDING`; client cannot self-verify | `PENDING`, `VERIFIED`, `REJECTED` |
| method | enum | Yes | - | - | - | - | - | - | `CREDIT_CARD`, `BANK_TRANSFER`, `E_WALLET` |

### Validation notes

1. **Enum fields** — strict allow-list, case-sensitive exact match. Reject unknown values, and empty or null where required.
2. **UUID / FK fields** — validate in up to three steps: format (malformed → `400`), existence (well-formed but absent → `404`), and referential state (present but in the wrong workflow state → `409`).
3. **Computed fields** (`totalAmount`, `unitPriceSnapshot`) — never trusted from client input. Always recompute server-side; reject client-supplied values with `400`.
4. **Date fields** (`dd/MM/yyyy`) — two independent layers: regex format, then calendar validity (reject 31/02 even though it matches the regex).
5. **Decimal amounts** — exactly two decimal places. Reject additional precision rather than silently rounding.
6. **Money** — use exact decimal arithmetic throughout. Never binary floating point for persisted amounts.
7. **Sensitive data** — banking account numbers must never appear in logs.

## 5.4 Behavioural workflow

1. Customer places order → order starts `PLACED`
2. Order Staff reviews and accepts → `PLACED` → `ACCEPTED`
3. Accountant creates invoice for the accepted order → invoice `ISSUED`, order → `INVOICED`, `Order.invoiceRef` set
4. Customer pays the invoice → payment `PENDING`, amount must equal the invoice total exactly, order → `PAID`
5. Accountant verifies the payment → payment `VERIFIED`, invoice `PAID`, order → `VERIFIED`, **all three updates atomic**
6. Order Staff ships the paid order → `VERIFIED` → `SHIPPED`
7. Order Staff closes the completed order → `SHIPPED` → `CLOSED`

Reject invalid transitions with `409`.

Note that after step 4 the order is `PAID` while the payment is still `PENDING`. This is intentional: the order records that payment arrived, the payment records that nobody has verified it yet. Implement it exactly as written.

---

# Part 6 — Deliverables checklist

Every item must be present.

**Architecture and design**

1. Quality attributes chosen, with domain-grounded justification (§1.1)
2. ASRs in six-part scenario form with quantified response measures (§1.2)
3. Tactic selection, cited verbatim (§1.3)
4. ADRs, including trade-offs between competing tactics (§1.4)
5. Traceability matrix reconciled against delivered code (§1.5)

**Machine-readable declarations, at the project root**

6. `nfr-trace.json` (§2.1)
7. `create_apis.json` and `workflow_apis.json` (§2.2)
8. `observability.json` (§2.3)
9. `fault-hooks.json` (§2.4)

**Implementation**

10. Data architecture narrative and complete schema
11. Domain entities matching the Field Constraint Table exactly
12. Complete backend: entities, repositories, services, controllers, config, OpenAPI document
13. Cross-cutting mechanisms as shared components
14. Health, metrics, and reset endpoints per §2.3
15. Fault-injection means per §2.4

**Verification**

16. Executable verification suite under `verification/`, one entry point per ASR (§3)
17. Machine-readable results under `verification/results/` (§3.2)

**Deployment**

18. Infrastructure-as-code and container artifacts
19. `start_command.txt` — one line, starts everything
20. Local deployment guide, including the exact commands to run the full verification suite

---

# Part 7 — Execution protocol

Work in this order. Do not stop after producing prose: create the files, run the system, execute the tests, repair what fails, and leave the repository in a verified state.

1. **Design** — choose quality attributes, write ASRs, select tactics, draft ADRs and the traceability matrix.
2. **Implement** — domain, API, persistence, migrations, cross-cutting mechanisms, deployment artifacts, manifests.
3. **Verify** — build from clean, start via `start_command.txt`, run migrations, exercise the full workflow, run the verification suite, confirm every path and function named in `nfr-trace.json` exists.
4. **Repair and reconcile** — fix what failed; update ADRs and traceability to describe the code that exists, not the plan you started with.

Do not claim a check passed unless you executed it and saw it pass.

---

# Part 8 — Final response

Return a concise execution report:

1. Quality attributes chosen and why
2. ASRs with their tactics and thresholds
3. Architecture summary
4. Files created
5. Exact startup command
6. Commands actually executed
7. Build, startup, migration, functional-test and verification-suite results
8. Which ASR verification scripts you ran locally, and what they observed
9. Any remaining failures, stated explicitly

Do not paste the repository into the response. The repository is the deliverable.

State results as you observed them. Do not assign yourself a score or rating.
