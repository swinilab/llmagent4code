# Overview
Design and implement a production-grade, backend-only e-commerce Order Management System (OMS).
Structure your response strictly as: Context → Architecture → Tasks → Deliverables → Output.

---

# Context
You are building a OMS backend that serves the APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure. The system serves three roles (Customer, Order Staff, Accountant) and must handle non-trivial traffic. No authentication is required.

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
- The **module/component** where it lives
- A one-line **verification method** (how a reviewer would confirm it works)

Non-Functional Requirements to satisfy:
- **NFR 1.1 Response Time:** core journeys (product search, cart, checkout) must minimize round-trip latency under load.
- **NFR 1.2 Concurrency & Resource Utilization:** system must exploit available server resources with minimal queuing.
- **NFR 1.3 Queue Management:** sudden spikes must not crash the system.
- **NFR 2.1 Graceful Degradation:** Under extreme resource contention, the system must degrade non-essential features to ensure core checkout functionality remains available.
- **NFR 2.2 Fault Detection and Recovery:** The application must detect internal component failures and automatically attempt to recover or reconnect, minimizing user-facing errors.
- **NFR 2.3 State Preservation:** In the event of an unexpected application process crash, the system must be able to restore its operational state and resume processing pending orders upon restart with minimal data loss.

## 3. NFR Trace JSON (mandatory deliverable — machine-readable)

In addition to the human-readable NFR Traceability Matrix (Markdown table), you MUST produce a
separate, machine-readable file named `nfr-trace.json` at the project root. This file lets an
automated reviewer verify that every NFR is backed by real, locatable code — not just prose.

For **every** NFR listed above, provide one entry with:
- **`nfr`** — the NFR ID and short name exactly as written above (e.g. `"NFR 2.2 Fault Detection and Recovery"`).
- **`filesImplemented`** — array of actual file paths (relative to project root) where this NFR
  is implemented. No placeholders; every path must correspond to a real file you delivered.
- **`librariesUsed`** — array of third-party libraries/frameworks that provide the mechanism
  (e.g. `"tenacity"`, `"circuitbreaker"`, `"asyncio.Queue"`, `"redis"`). Use `[]` if none — do not
  omit the key.
- **`functionNames`** — array of the actual function/method names (as written in code, e.g.
  `"reconnect_with_backoff"`, not a paraphrase) that call or configure the library/mechanism named
  in `librariesUsed` to satisfy this specific NFR. Each entry MUST be qualified with its file so
  it is unambiguous which of the `filesImplemented` it lives in, using the form
  `"<relative/file/path>::<function_or_method_name>"` (e.g.
  `"app/db/connection_pool.py::get_connection_with_retry"`). Every function listed must actually
  exist in the delivered file and must be the function that directly invokes the library — not a
  caller several layers up. If a mechanism is implemented without a third-party library (so
  `librariesUsed` is `[]`), still list the hand-written function(s) that implement the tactic. Do
  not omit the key; use `[]` only if genuinely no dedicated function exists (e.g. the mechanism is
  purely declarative configuration with no executable code, such as a Docker healthcheck directive).
- **`tacticUsed`** — the specific architectural tactic from Bass, Clements & Kazman,
  *Software Architecture in Practice*, that this implementation realizes. Use the tactic's
  category and exact name from the book (e.g. `"Availability > Detect Faults > Ping/Echo"`,
  `"Performance > Manage Resources > Introduce Concurrency"`). Do not invent tactic names; if
  no tactic from the book cleanly applies, state `"tacticUsed": "N/A — <one-line justification>"`.
- **`verificationMethod`** — one line describing how a reviewer confirms this in practice
  (should match the Verification Method column in the Markdown matrix).

### Required structure of `nfr-trace.json`

```json
{
  "nfrTrace": [
    {
      "nfr": "NFR 1.1 Response Time",
      "filesImplemented": ["app/services/order_service.py", "app/cache/response_cache.py"],
      "librariesUsed": ["fastapi", "aiocache"],
      "functionNames": [
        "app/cache/response_cache.py::get_or_set_cached_product_list",
        "app/services/order_service.py::get_checkout_summary"
      ],
      "tacticUsed": "Performance > Manage Resources > Maintain Multiple Copies of Computations",
      "verificationMethod": "Load test with k6 shows p95 latency < 200ms for checkout endpoint"
    },
    {
      "nfr": "NFR 1.2 Concurrency & Resource Utilization",
      "filesImplemented": ["app/main.py"],
      "librariesUsed": ["uvicorn", "asyncio"],
      "functionNames": ["app/main.py::create_app", "app/main.py::run_with_worker_pool"],
      "tacticUsed": "Performance > Manage Resources > Introduce Concurrency",
      "verificationMethod": "ab -c 100 shows throughput scales near-linearly up to worker count"
    },
    {
      "nfr": "NFR 1.3 Queue Management",
      "filesImplemented": ["app/queue/queue_manager.py"],
      "librariesUsed": ["asyncio.Queue"],
      "functionNames": [
        "app/queue/queue_manager.py::enqueue_order_task",
        "app/queue/queue_manager.py::get_queue_depth"
      ],
      "tacticUsed": "Performance > Control Resource Demand > Bound Queue Sizes",
      "verificationMethod": "Burst of 1000 requests returns 202 without dropped connections; queue_size bounded per /health/queue"
    },
    {
      "nfr": "NFR 2.1 Graceful Degradation",
      "filesImplemented": ["app/degradation/degradation_manager.py"],
      "librariesUsed": [],
      "functionNames": [
        "app/degradation/degradation_manager.py::should_degrade_feature",
        "app/degradation/degradation_manager.py::disable_non_essential_endpoints"
      ],
      "tacticUsed": "Availability > Recover from Faults > Degradation",
      "verificationMethod": "Kill background worker under load; checkout endpoint still returns 2xx while non-essential endpoints return 503"
    },
    {
      "nfr": "NFR 2.2 Fault Detection and Recovery",
      "filesImplemented": ["app/health/liveness.py", "app/db/connection_pool.py"],
      "librariesUsed": ["tenacity"],
      "functionNames": [
        "app/health/liveness.py::check_db_liveness",
        "app/db/connection_pool.py::get_connection_with_retry"
      ],
      "tacticUsed": "Availability > Detect Faults > Ping/Echo; Availability > Recover from Faults > Retry",
      "verificationMethod": "Kill DB connection mid-request; observe automatic reconnect within N seconds via /health/ready"
    },
    {
      "nfr": "NFR 2.3 State Preservation",
      "filesImplemented": ["app/persistence/wal.py"],
      "librariesUsed": ["sqlite3"],
      "functionNames": [
        "app/persistence/wal.py::append_to_wal",
        "app/persistence/wal.py::replay_wal_on_startup"
      ],
      "tacticUsed": "Availability > Recover from Faults > State Resynchronization",
      "verificationMethod": "Kill process mid-queue-processing, restart, confirm pending orders resume from persisted state with no loss"
    }
  ]
}
```

### Rules for populating this file
1. One entry per NFR — no omissions, no merging two NFRs into one entry.
2. `filesImplemented` must list files that actually exist in your deliverable; this will be
   spot-checked and any non-existent path is treated as a defect.
3. `functionNames` must list only functions/methods that actually exist, verbatim, in the files
   under `filesImplemented` — spot-checked the same as `filesImplemented`, and any function that
   cannot be found at that path is treated as a defect. Each entry must be the specific function
   that directly calls into the library/mechanism claimed in `librariesUsed` for that NFR (e.g.
   the function that calls `tenacity.retry(...)`, not the outer request handler that merely calls
   that function). If one function serves multiple NFRs, it is fine to list it under each relevant
   NFR entry — do not force artificial one-function-per-NFR separation.
4. `tacticUsed` must cite real tactic names from Bass/Clements/Kazman's tactic categories
   (Availability, Performance, and any other quality attribute chapter tactics you draw on) —
   do not paraphrase or invent tactic names not in the book.
5. This file must stay consistent with the Markdown NFR Traceability Matrix — same NFRs, same
   verification methods, no contradictions.
6. Place this file at the project root alongside `create_apis.json` and `/start_command.txt`.

---

# Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum with full lifecycle), timestamps, invoice ref.
- **Product:** id, description, pricing (base + currency).
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

## Field Constraint Table (mandatory — implementation must enforce every constraint below exactly as specified)

This table is the authoritative source for all field-level validation rules. Every constraint listed here (Required, Min/Max, Length, Format/Regex, Semantic rule, Allowed Values) MUST be implemented as actual validation logic in the corresponding entity/DTO/controller layer — not merely documented. This table will also be used as the basis for Boundary Value Analysis (BVA) and Equivalence Partitioning (EP) test design, so exact numeric boundaries and regex patterns must be honored precisely, with no silent rounding, truncation, or relaxed validation.

### Entity: Customer

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| name | string | Yes | - | - | - | 2–100 | `^[\p{L} .'-]+$` | Must not be blank or whitespace-only | - |
| address | string | Yes | - | - | - | 5–255 | free text | Must not be blank or whitespace-only | - |
| phone | string | Yes | - | - | - | 8–15 digits | `^\+?[1-9]\d{7,14}$` (E.164) | Must not start with 0 after country code | - |
| bankingDetails.accountNumber | string | Yes | - | - | - | 6–20 | `^\d{6,20}$` (numeric only) | - | - |
| bankingDetails.bankName | string | Yes | - | - | - | 2–100 | `^[\p{L}0-9 .&-]+$` | - | - |
| role | enum | Yes | - | - | - | - | - | Fixed at creation | `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT` |
| orderHistory | array\<UUID\> | No (read-only, server-derived) | - | 0 | unbounded (soft cap 10,000) | - | - | Not settable by client | - |

### Entity: Product

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| description | string | Yes | - | - | - | 3–500 | free text | Must not be blank or whitespace-only | - |
| price.amount | decimal(2dp) | Yes | - | 0.01 | 999999.99 | - | `^\d{1,6}\.\d{2}$` | Must be > 0, exactly 2 decimal places, no rounding | - |
| price.currency | string | Yes | - | - | - | 3 | `^[A-Z]{3}$` (ISO 4217) | Must be in supported currency list | `USD`, `VND`, `EUR` |

### Entity: Order

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| customerRef | UUID (FK) | Yes | Customer.id must exist | - | - | 36 | UUIDv4 | Must reference an existing, non-deleted customer | - |
| lineItems | array\<LineItem\> | Yes | Product.id must exist per item | 1 item | 100 items | - | - | No duplicate productRef within same order (merge policy TBD) | - |
| lineItems[].productRef | UUID (FK) | Yes | Product.id must exist | - | - | 36 | UUIDv4 | - | - |
| lineItems[].quantity | int | Yes | - | 1 | 1000 | - | `^\d+$` | Must be a whole number | - |
| lineItems[].unitPriceSnapshot | decimal(2dp) | Yes | Copied from Product.price.amount at order time | 0.01 | 999999.99 | - | `^\d{1,6}\.\d{2}$` | Immutable snapshot; must equal product price at creation time, server-computed, not client-settable | - |
| totalAmount | decimal(2dp) | Yes | = Σ(lineItems.quantity × unitPriceSnapshot) | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Server-computed, not client-settable | - |
| status | enum | Yes | Must follow the defined state machine | - | - | - | - | Default `PLACED` on creation; client cannot set an arbitrary initial status | `PLACED`, `ACCEPTED`, `INVOICED`, `PAID`, `VERIFIED`, `SHIPPED`, `CLOSED`, `CANCELLED` |
| createdAt | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-generated, immutable | - |
| updatedAt | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-updated on every state change; must be >= createdAt | - |
| invoiceRef | UUID (FK) | No | Invoice.id must exist when present | - | - | 36 | UUIDv4 | Null until Accountant creates invoice | - |

### Entity: Payment

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated | - |
| orderRef | UUID (FK) | Yes | Order.id must exist, order.status = `INVOICED` | - | - | 36 | UUIDv4 | Order must be in a payable state | - |
| amount | decimal(2dp) | Yes | Must equal Invoice.totalAmount for the referenced invoice | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Exact match required — no partial or over payment allowed (current scope) | - |
| timestamp | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-generated at submission | - |
| status | enum | Yes | Must follow the defined state machine | - | - | - | - | Default `PENDING` on creation; client cannot self-verify | `PENDING`, `VERIFIED`, `REJECTED` |
| method | enum | Yes | - | - | - | - | - | - | `CREDIT_CARD`, `BANK_TRANSFER`, `E_WALLET` |

### Entity: Invoice

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated | - |
| orderRef | UUID (FK) | Yes | Order.id must exist, order.status = `ACCEPTED` | - | - | 36 | UUIDv4 | Order must be accepted before invoicing | - |
| billingInfo.name | string | Yes | Copied from Customer.name at issue time | - | - | 2–100 | `^[\p{L} .'-]+$` | Snapshot, not a live reference | - |
| billingInfo.address | string | Yes | Copied from Customer.address | - | - | 5–255 | free text | Snapshot | - |
| totalAmount | decimal(2dp) | Yes | = Order.totalAmount | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Must equal the referenced order's total at issue time | - |
| issueDate | date | Yes | - | - | - | - | `dd/MM/yyyy`, regex `^\d{2}/\d{2}/\d{4}$` | Must be a real calendar date (e.g. reject 31/02/2026); defaults to server current date | - |
| dueDate | date | Yes | Must be >= issueDate | - | - | - | `dd/MM/yyyy` | Default = issueDate + 7 days; must not precede issueDate; must be a real calendar date | - |
| status | enum | Yes | Must follow the defined state machine | - | - | - | - | Default `ISSUED` on creation | `ISSUED`, `PAID`, `OVERDUE`, `CANCELLED` |

### Implementation notes for validation logic
1. **Enum fields** have no numeric/length boundary — enforce via strict allow-list validation (case-sensitive exact match against the Allowed Values list); reject unknown values and empty/null when required.
2. **UUID / FK fields** must be validated in two steps: (a) format validation (reject malformed UUID strings with 400), (b) existence validation (reject valid-format but non-existent references with 404), and where relevant (c) referential state validation (reject references to entities not in the required workflow state, e.g. paying against a non-`INVOICED` order, with 409).
3. **Computed/derived fields** (`totalAmount`, `unitPriceSnapshot`) must never be trusted from client input — always recompute server-side and ignore or reject client-supplied values that don't match.
4. **Date fields** (`dd/MM/yyyy`) require two independent validation layers: (a) regex format check, and (b) calendar semantic validity check (reject non-existent dates such as 31/02 or 30/02 even if they match the regex).
5. **Decimal amount fields** must enforce exactly 2 decimal places — reject additional precision rather than silently rounding.

---

# API Manifest (mandatory deliverable — required for automated test generation)

In addition to the OpenAPI spec, you MUST produce a separate, machine-readable file named
`create_apis.json` at the project root. This file is the single source of truth a downstream,
fully automated functional test harness (the BVA/EP `ITestGroup` validators — `CustomerTestGroup`,
`ProductTestGroup`, `OrderTestGroup`, `PaymentTestGroup`, `InvoiceTestGroup`) uses to know which
URL to POST each entity's creation request to. The harness does NOT parse source code and does
NOT guess paths — each test group is constructed with a single `api` string (the full create-
endpoint URL) that it passes straight to `requests.post(self.api, json=body)`; anything not
declared here is untestable.

## Required structure of `create_apis.json`

```json
{
  "customer": {
    "method": "POST",
    "path": "/api/v1/customers"
  },
  "product": {
    "method": "POST",
    "path": "/api/v1/products"
  },
  "order": {
    "method": "POST",
    "path": "/api/v1/orders"
  },
  "payment": {
    "method": "POST",
    "path": "/api/v1/payments"
  },
  "invoice": {
    "method": "POST",
    "path": "/api/v1/invoices"
  }
}
```

## Rules for populating this file
1. **Exactly these five top-level keys** — `customer`, `product`, `order`, `payment`, `invoice`
   (lowercase, singular) — one entry per entity from the Domain Model. No omissions, no extra
   keys, no nesting beyond `method`/`path`.
2. **`method`** — the actual HTTP verb the create endpoint accepts. Must be `"POST"` for all five
   entities per the Backend Requirements (create = POST to the collection endpoint).
3. **`path`** — the actual, real, versioned route path (e.g. `/api/v1/customers`) exactly as
   registered in the routing layer, including any version prefix. Do not include the host/port;
   `path` is appended to the service's base URL by the test harness. No placeholders, no `{id}`.
4. **Synchronous creation only** — every path declared here MUST return the created resource
   directly (`201 Created` with the resource body) in the same response, since the test harness
   reads `resp.status_code` and `resp.json()` immediately after the POST with no polling step. If
   your implementation queues creation asynchronously, this file is the wrong contract for it —
   make these five endpoints synchronous.
5. This file must stay consistent with the OpenAPI spec and the actual running code — it will be
   spot-checked against both; any mismatch (wrong path, wrong method, wrong status code) is
   treated as a defect.
6. Place this file at the project root alongside `nfr-trace.json` and `/start_command.txt`.

## Automated Test Compatibility (mandatory)

Your API implementation MUST be drivable end-to-end by the `ITestGroup`-based functional test
harness using only `create_apis.json` plus the pre-existing BVA/EP test-case spreadsheet
(`OMS_TestCases_BVA_EP_EN.xlsx`, one sheet per entity: Customer, Product, Order, Payment,
Invoice). Concretely, this means:

- For each entity, `POST {baseUrl}{create_apis.json[entity].path}` with the `validSeed`-equivalent
  request body MUST return `201` with the created resource in the JSON body — matching the
  `_check(testcase_id, expected_status, actual_status, body)` assertions already encoded in each
  test group (e.g. `TC_CUS_NAME_02` expects `201`, `TC_CUS_NAME_01` expects `400`).
- Every field referenced in the Field Constraint Table for that entity must be reachable by
  sending it under its literal attribute name (dot-notation preserved as nested JSON objects,
  e.g. `bankingDetails.accountNumber`) in the POST body — the test groups build request bodies
  by mutating a standard body using exactly these field names.
- `GET {baseUrl}{create_apis.json[entity].path}/{id}` must return `200` for an existing id,
  `404` for a well-formed but non-existent id, and `400` for a malformed id — matching the
  `TC_*_ID_*` test cases that call `_get(id)`.

---

# User Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

---

# Backend Requirements 
Per entity produce three **complete** layers:
- **Service** (business logic, transaction boundaries, orchestration of cross-cutting concerns)
- **Controller** (REST endpoints, request/response mapping, validation)
- **Routing / API definition** (OpenAPI-friendly, versioned paths)

---

# Infrastructure Requirements
Provide complete, runnable artifacts to install and deploy on local machine as a production environment.

---

# Code Quality & Conciseness Rules
- **No placeholders, no "repeat this pattern", no `// ... similar for other fields`.** Every file must be complete and runnable.
- **Be concise:** Do not pad with boilerplate.
- **Prefer composition over inheritance.** Extract shared behavior into utilities/hooks/base classes rather than duplicating.

---

# Deliverables Checklist (every item must appear in the output)
1. NFR Traceability Matrix.
2. ADRs for major decisions.
3. `nfr-trace.json` (see NFR Trace JSON section above) — mandatory, machine-readable, at project root.
4. Data architecture narrative + complete schema.
5. Shared domain models (used by both FE and BE), matching the Field Constraint Table above exactly.
6. Complete backend code: entities, repositories, services, controllers, config, OpenAPI spec — with validation logic implementing every constraint in the Field Constraint Table.
7. `create_apis.json` (see API Manifest section above) — mandatory, machine-readable, at project root.
8. IaC config and documents.
9. Local deployment guide.
10. Verification steps showing how to observe each NFR being satisfied.

---

# Output Requirements
- Produce **complete, functional code** for every component listed — no abbreviations.
- Organize the response with clear headers matching the sections above.
- Where a file is long, still emit it in full; do not truncate.
- Every cross-cutting concern must be **visible in code**, not only described in prose.
- For automation testing purpose, a text file named "/start_command.txt" that contains a single command to start the whole project (docker or other command)
