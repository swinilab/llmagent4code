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
- **NFR 1.1 Limit Event Response:** process events only up to a set maximum rate.
- **NFR 1.2 Maintain Multiple copies of Data:** Two common examples of maintaining multiple copies of data are data replication and caching.
- **NFR 2.1 Exception detection:** detect a system condition that alters
the normal flow of execution. Two common types of exception detection tactics are System exceptions and time out.
- **NFR 2.2 Graceful Degradation:** maintain the most critical system functions in the presence of component failures, while dropping less critical functions.
- **NFR 2.3 State Resynchronization:** the states of the active and standby components are periodically compared to ensure synchronization.
- **NFR 2.4 Transactions:** leverage transactional semantics to ensure that asynchronous messages exchanged between distributed components are atomic, consistent, isolated, and durable (a.k.a ACID properties)

## 3. NFR Trace JSON (mandatory deliverable — machine-readable)

In addition to the human-readable NFR Traceability Matrix (Markdown table), you MUST produce a
separate, machine-readable file named `nfr-trace.json` at the project root. This file lets an
automated reviewer verify that every NFR is backed by real, locatable code — not just prose.

The file has the following content format: 
```json
{
  "nfrTrace": [
    {
      "nfr": "NFR: name",
      "filesImplemented": ["path/to/file1.py", "path/to/file2.py"],
      "librariesUsed": ["library1", "library2"],
      "functionNames": [
        "path/to/file1.py::function1",
        "path/to/file2.py::function2"
      ],
      "tacticUsed": "QA /path/to/tactic",
    },
    // other NFR entries follow the same structure, one per NFR
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
5. This file must stay consistent with the Markdown NFR Traceability Matrix — same NFRs.
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

## Behavior Workflow (must be implemented)
1. Customer places order.
2. Order Staff reviews & accepts.
3. Accountant creates invoice for accepted order.
4. Customer pays invoice.
5. Accountant verifies payment.
6. Order Staff ships paid order.
7. Order Staff closes completed order.

---

# API Manifest (mandatory deliverable — required for automated test generation)

In addition to the OpenAPI spec, you MUST produce a separate, machine-readable file named `create_apis.json` at the project root. This file is the single source of truth a downstream, fully automated functional test harness (eg. the BVA/EP `ITestGroup` validators, one for each entity, eg. `CustomerTestGroup`) to know which URL to POST each entity's creation request to. The harness does NOT parse source code and does NOT guess paths — each test group is constructed with a single `api` string (the full create- endpoint URL) that it passes straight to `requests.post(self.api, json=body)`; anything not declared here is untestable.

## Required structure of `create_apis.json`

```json
{
  "<entity_name>": {
    "method": "<http_method>",
    "path": "/api/v1/<entity_name>"
  },
  // other entities follow the same structure, one per entity
}
```

## Rules for populating this file
1. **Exactly top-level keys must match with entities in the Domain Model** — (lowercase, singular) — one entry per entity from the Domain Model. No omissions, no extra keys, no nesting beyond `method`/`path`.
2. **`method`** — the actual HTTP verb the create endpoint accepts. Must be `"POST"` for all entities per the Backend Requirements (create = POST to the collection endpoint).
3. **`path`** — the actual, real, versioned route path (e.g. `/api/v1/customers`) exactly as
   registered in the routing layer, including any version prefix. Do not include the host/port;
   `path` is appended to the service's base URL by the test harness. No placeholders, no `{id}`.
4. **Synchronous creation only** — every path declared here MUST return the created resource
   directly (eg. `201 Created` with the resource body) in the same response, since the test harness reads `resp.status_code` and `resp.json()` immediately after the POST with no polling step. Only consider synchronous creation endpoints.
5. This file must stay consistent with the OpenAPI spec and the actual running code. Any mismatch (wrong path, wrong method, wrong status code) is treated as a defect.
6. Place this file at the project root alongside `nfr-trace.json` and `/start_command.txt`.

## Automated Test Compatibility (mandatory)

Your API implementation MUST be drivable end-to-end by the `ITestGroup`-based functional test harness using only `create_apis.json` plus the pre-existing BVA/EP test-case spreadsheet (`OMS_TestCases_BVA_EP_EN.xlsx`, one sheet per entity in the Domain Model). Concretely, this means:

- For each entity, `POST {baseUrl}{create_apis.json[entity].path}` with the `validSeed`-equivalent request body MUST return `201` with the created resource in the JSON body — matching the `_check(testcase_id, expected_status, actual_status, body)` assertions already encoded in each test group (e.g. `TC_CUS_NAME_02` expects `201`, `TC_CUS_NAME_01` expects `400`).
- Every field referenced in the Field Constraint Table for that entity must be reachable by sending it under its literal attribute name (dot-notation preserved as nested JSON objects, e.g. `bankingDetails.accountNumber`) in the POST body — the test groups build request bodies by mutating a standard body using exactly these field names.
- `GET {baseUrl}{create_apis.json[entity].path}/{id}` must return `200` for an existing id, `404` for a well-formed but non-existent id, and `400` for a malformed id — matching the `TC_*_ID_*` test cases that call `_get(id)`.

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
