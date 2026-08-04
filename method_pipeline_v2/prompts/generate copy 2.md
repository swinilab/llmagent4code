# OrderMan Tactic-Guided Code-Generation Prompt

## 1. Mission

Act as a senior backend software architect and implementation engineer.

Create a complete, runnable repository for a backend-only Order Management System named **OrderMan**. Work directly in the current repository: create the files, run the project, execute the tests, repair defects, and leave the repository in a verified state. Do not stop after producing architecture prose, and do not merely paste a conceptual solution into the final response.

Implement the six prescribed tactics and all ASRs defined in this prompt. The task does **not** ask you to select alternative tactics.

This prompt is the authoritative source of truth for generation. If generated OpenAPI, ADRs, traceability files, API documentation, or code comments conflict with this prompt, this prompt takes precedence. Do not modify the requirements to make local tests easier, and do not include claimed scores or ratings in the final report.

---

## 2. Fixed scope, technology, and generation constraints

- Backend-only Order Management System named **OrderMan**.
- No frontend.
- No authentication or authorization; actor roles are domain data only.
- Complete seven-step workflow from order placement through closure.
- API base path: `/api/v1`.
- Application port: `8080`.
- Fixed technology baseline:
  - Python 3.12
  - FastAPI
  - SQLAlchemy 2.x
  - Alembic
  - PostgreSQL 16
  - Docker and Docker Compose
  - Toxiproxy
  - pytest
- PostgreSQL communication must pass through Toxiproxy.
- All public JSON validation failures return HTTP `400`.
- Malformed UUID returns `400`.
- Valid but unknown UUID returns `404`.
- Workflow or referential-state conflict returns `409`.

### Required external configuration

```text
APP_PORT=8080
MAX_IN_FLIGHT_REQUESTS=10
DB_OPERATION_TIMEOUT_MS=1000
DB_MAX_ATTEMPTS=3
DB_RETRY_BACKOFF_MS=100
CACHE_TTL_SECONDS=5
ENABLE_TEST_HOOKS=false
```

The deployment environment sets `ENABLE_TEST_HOOKS=true`.

At startup the application MUST emit one structured log line to stdout reporting the effective value of every key above. Include `ENABLE_TEST_HOOKS` explicitly.

### Additional generation constraints

- Pin all direct dependency versions.
- No manual source-code or configuration edits may be required after generation.
- Database migrations must run automatically as part of startup.
- Tests must create their own data and must not depend on preloaded business data.
- Every file must be complete and runnable; do not use placeholders, ellipses, TODO-only functions, or "repeat this pattern" comments.
- Test hooks are permitted only as specified in this prompt and must be disabled unless `ENABLE_TEST_HOOKS=true`.
- Follow every externally observable contract exactly. Do not rename or alter required paths, field names, status codes, metric names, configuration keys, tactic names, or response measures.

### Authenticity of implemented mechanisms

Every required behavior must be produced by the real architectural mechanism at runtime:

- Do not implement fake metrics, precomputed answers, fabricated responses, or test-only behavior that bypasses the mechanism it is meant to demonstrate.
- Every counter must be incremented at the exact location where the corresponding mechanism executes, and must agree with externally observable evidence such as PostgreSQL server-side query statistics, Toxiproxy state, Docker restart counts, and raw HTTP responses.

---

## 3. Prescribed architectural tactics

Use these exact tactic strings in all ADRs, the Markdown traceability matrix, and `nfr-trace.json`.

### Performance

1. `Performance > Manage Resources > Maintain Multiple Copies of Data`
2. `Performance > Control Resource Demand > Manage Work Requests > Limit Event Response`

### Availability

3. `Availability > Detect Faults > Timeout`
4. `Availability > Recover from Faults > Preparation and Repair > Retry`
5. `Availability > Recover from Faults > Preparation and Repair > Graceful Degradation`
6. `Availability > Prevent Faults > Transactions`

Do not paraphrase these names. Do not use `Maintain Multiple Copies of Computations` as evidence for caching. Do not shorten `Graceful Degradation` to `Degradation`.

`Performance > Manage Resources > Bound Queue Sizes` is intentionally outside the scope of this task because its runtime evidence depends strongly on implementation-specific queue semantics. Do not report it as one of the six required tactics.

Additional incidental framework behavior may exist, but it must not substitute for any required tactic and must not be reported as the implementation evidence for a required tactic.

---

## 4. Architecturally significant requirements and required response measures

Each scenario is both an architectural requirement and an automated acceptance contract. Each scenario maps to exactly one selected tactic.

The response measures below are externally observable acceptance requirements.

### Scope of the tactics versus scope of the scenarios

Each scenario names a concrete endpoint, entity, or fault so that the requirement is observable. **The named element is a representative probe, not the boundary of the tactic.** Each tactic must be implemented at its natural architectural scope - normally a cross-cutting component applied wherever the concern arises - and the scenario merely selects one place to observe it.

Concretely: implementing admission control only on Product search, a timeout only on the Product read path, or a transaction boundary only in payment verification satisfies the letter of the scenario while failing the requirement. A mechanism reachable only from the endpoint named in a scenario is an implementation defect.

The one deliberate exception is the maintained-copy tactic (ASR-P1), whose scope of applicability is a design decision the ADR must state and justify; see that scenario's reusability obligation.

### Controlled error-response contract (applies to all ASRs)

Every controlled failure response (`429`, `500`, `503`, `504`) MUST carry a JSON body of this shape:

```json
{
  "error": {
    "code": "<one of the codes below>",
    "message": "<human-readable description>"
  }
}
```

Allowed `code` values and their exact meaning:

```text
DEPENDENCY_TIMEOUT        - a database operation exceeded the configured per-attempt
                            time limit and the bounded retry policy was exhausted
DEPENDENCY_UNAVAILABLE    - the database could not be reached at all (connection
                            refused/reset), or a write was refused because durable
                            state is unavailable
OVERLOAD_REJECTED         - admission control refused the request because the
                            in-flight limit was reached
TRANSACTION_FAILED        - a transaction was rolled back due to an internal fault
```

These codes distinguish timeout detection (ASR-A1) from dependency unavailability (ASR-A3). Emitting `DEPENDENCY_TIMEOUT` for a connection-refused condition, or `DEPENDENCY_UNAVAILABLE` for an exceeded time limit, is a defect. The distinction must reflect the real cause observed at the database boundary.

Additional keys inside `error` are permitted. The `code` and `message` keys are mandatory.

### ASR-P1 - Cached product-read performance

- **Tactic:** `Performance > Manage Resources > Maintain Multiple Copies of Data`
- **Source:** concurrent API clients.
- **Stimulus:** sustained repeated reads of the same Product through the API, including reads issued concurrently, while that Product's row may be modified directly in PostgreSQL outside the application.
- **Environment:** normal operation; PostgreSQL available.
- **Artifact:** the Product read path, the maintained cached copy, and the persistence adapter. Unlike the other scenarios, the named entity here is also the intended scope: see the reusability obligation below.
- **Required response:**
  - a Product modified directly in the database is not observed through the API until the maintained copy expires or is invalidated;
  - once `CACHE_TTL_SECONDS` has elapsed, a subsequent read reflects the current database state;
  - repeated reads are served primarily from the maintained copy while PostgreSQL remains authoritative.
- **Required response measures:**
  - a read issued immediately after an out-of-band database update, and within `CACHE_TTL_SECONDS`, returns the previously cached value;
  - a read issued after `CACHE_TTL_SECONDS` has elapsed returns the updated value;
  - cache hit rate `>= 95%`;
  - p95 response time `<= 200 ms`;
  - error rate `<= 1%`;
  - under sustained concurrent reads of a single Product, database reads are bounded by TTL-driven refills - on the order of one refill per TTL interval, not one per cache miss.
- **Interaction with admission control:** the concurrent reads in this scenario stay within `MAX_IN_FLIGHT_REQUESTS`, so a correctly implemented system admits all of them and the measures above describe admitted requests only. This scenario measures the maintained copy, not the admission policy; ASR-P2 measures the admission policy. A cached read must therefore complete quickly enough that it releases its slot promptly - a cache hit that occupies an admitted slot for hundreds of milliseconds converts a read-throughput workload into an overload condition and will show up here as a latency failure.
- **Implementation obligation:** implement a real cache lookup/population path with TTL or invalidation. Under concurrency, concurrent misses for the same key must not each issue their own database read - use single-flight, a per-key lock, or an equivalent mechanism so that one refill serves the concurrent waiters. Hard-coded Product responses, fabricated counters, or a cache that is not used by the Product-read endpoint are prohibited.
- **Reusability obligation:** the caching mechanism must be a reusable component that is not coupled to Product-specific code. Which entities it is actually applied to is an explicit architectural decision, not an accident of implementation: justify that decision in the ADR for this tactic. Note that entities whose state advances through the workflow are poor caching candidates, because a stale copy would make workflow state and transaction rollbacks externally observable as incorrect - ASR-A4 in particular requires post-rollback `Order` and `Payment` states to be read back accurately.

### ASR-P2 - Controlled response under overload

- **Tactic:** `Performance > Control Resource Demand > Manage Work Requests > Limit Event Response`
- **Source:** an automated overload client.
- **Stimulus:** a burst of concurrent Product-search requests far exceeding `MAX_IN_FLIGHT_REQUESTS`, each held in-flight long enough to keep admitted slots occupied (via `X-Test-Delay-Ms` while test hooks are enabled).
- **Environment:** overload operation with `MAX_IN_FLIGHT_REQUESTS=10`.
- **Artifact:** the public request-admission path. Product search is the probe; admission control governs the public API surface as a whole.
- **Required response:** the system admits only the configured amount of concurrent work and immediately rejects excess work with a controlled response instead of allowing unbounded waiting.
- **Required response measures:**
  - concurrently admitted requests never exceed `MAX_IN_FLIGHT_REQUESTS`;
  - admitted requests still succeed; the mechanism does not reject everything;
  - every request that cannot be admitted returns HTTP `429` with `Retry-After`, or controlled HTTP `503`;
  - p95 latency of controlled rejections is `<= 500 ms`;
  - unhandled HTTP `500` count is `0`;
  - application crash and unplanned restart count is `0`;
  - `requests_accepted_total` increases by the number of admitted requests, and `requests_rejected_total` by the number of controlled rejections; together they account for every request that reached admission control;
  - `/health/ready` returns `200` within 2 seconds after the overload stops.
- **Implementation obligation:** admission/response limiting must be a single cross-cutting mechanism governing every public business endpoint, not a guard attached to Product search. `MAX_IN_FLIGHT_REQUESTS` bounds concurrent admitted business requests system-wide. The observation paths listed in Section 5 (`/health/*`, `/internal/metrics`, `/internal/test/reset`) are the sole exemption: they bypass admission control entirely and never consume a slot. Rejection must be **immediate** - a request that cannot be admitted is refused at once and does not wait in a queue for a slot. Do not satisfy this ASR with a bounded work queue that admits requests and makes them wait; that is a different tactic and is outside the scope of this task. Client-side timeouts, connection drops, or accidental web-server failures do not satisfy this ASR. Controlled rejections carry `error.code = "OVERLOAD_REJECTED"`.

### ASR-A1 - Dependency timeout detection

- **Tactic:** `Availability > Detect Faults > Timeout`
- **Source:** PostgreSQL communication through Toxiproxy.
- **Stimulus:** an uncached Product read while database latency injected through Toxiproxy far exceeds `DB_OPERATION_TIMEOUT_MS`, so that no attempt can complete within its time limit.
- **Environment:** database dependency timing fault.
- **Artifact:** the database access path. An uncached Product read is the probe; the time limit governs every database operation.
- **Required response:** the application stops waiting when the configured database-operation time limit is exceeded and returns a controlled failure after the bounded retry policy completes.
- **Required response measures:**
  - configured per-attempt database timeout is `<= 1.2 seconds`;
  - total client response time is `<= 4.5 seconds`;
  - response is controlled HTTP `503` or `504` with `error.code = "DEPENDENCY_TIMEOUT"`;
  - requests hanging longer than 4.5 seconds: `0`;
  - `timeouts_total` increases;
  - the application remains live.
- **Timing budget guidance:** with `DB_OPERATION_TIMEOUT_MS=1000` and `DB_MAX_ATTEMPTS=3`, three exhausted attempts consume approximately 3.0 seconds plus backoff. Backoff between attempts MAY be skipped when the previous attempt failed by timeout rather than by a transient error, since the timeout itself already provided delay. Keep the total bounded well inside 4.5 seconds; do not tune the per-attempt timeout upward toward the 1.2-second ceiling.
- **Implementation obligation:** apply the timeout to the real database operation or connection path, as a single policy covering all database access - reads and writes, every entity, and the connection-acquisition step. A time limit reachable only from the Product read path, or implemented only in the calling HTTP client, is insufficient.

### ASR-A2 - Recovery from transient database faults

- **Tactic:** `Availability > Recover from Faults > Preparation and Repair > Retry`
- **Source:** an automated test client.
- **Stimulus:** an uncached, read-only Product GET carries `X-Test-Fault: transient-db-failures=2`.
- **Environment:** test hooks enabled; the first two database-boundary attempts fail with a transient fault and the third attempt can execute normally.
- **Artifact:** the database resilience path. The Product read is the probe; the retry policy governs database access generally, subject to the safety rule below.
- **Required response:** retry only the transient fault, stop at the configured attempt limit, and return the Product after the third attempt succeeds.
- **Required response measures:**
  - HTTP response is `200`;
  - `db_product_read_attempts_total` increases by exactly `3`;
  - `retry_attempts_total` increases by exactly `2`;
  - total attempts never exceed `DB_MAX_ATTEMPTS=3`;
  - malformed requests, unknown IDs, and workflow conflicts do not increase `retry_attempts_total`;
  - no infinite retry loop.
- **Implementation obligation:** use a bounded retry policy with explicit retryable-fault classification and bounded backoff, implemented once and applied at the database boundary rather than inside a single repository. Retrying validation, `404`, or `409` responses is prohibited.
- **Retry safety rule:** retry is only permissible where re-execution cannot duplicate an effect. Read operations and operations that failed before any write was issued may be retried. A write or transaction that may already have been applied at the database MUST NOT be blindly re-executed; either establish that the operation is idempotent, or retry the whole transaction only when it is known to have been rolled back. Duplicate Payments, Invoices, or workflow transitions caused by retry are defects. State the classification rule and this boundary in the ADR for this tactic.

### ASR-A3 - Graceful degradation during database outage

- **Tactic:** `Availability > Recover from Faults > Preparation and Repair > Graceful Degradation`
- **Source:** PostgreSQL failure injected through Toxiproxy.
- **Stimulus:** with one Product already read through the API (its copy warmed) and another never read, the PostgreSQL Toxiproxy proxy is disabled for a sustained period many times longer than `CACHE_TTL_SECONDS`. During the outage the system receives repeated reads of the warmed Product, reads of the unwarmed Product, and state-changing requests. The proxy is then re-enabled.
- **Environment:** database dependency unavailable.
- **Artifact:** the maintained-copy read path and every state-changing API path. The two Products are the probe; safe failure during a dependency outage applies to all endpoints requiring durable state.
- **Required response:** the warmed read capability remains available; operations that require unavailable durable state fail safely; normal service resumes automatically after database recovery.
- **Required response measures:**
  - warmed Product-read success rate during the outage `>= 99%`;
  - warmed Product-read p95 `<= 200 ms`;
  - reads of the unwarmed Product return controlled HTTP `503` or `504` with `error.code = "DEPENDENCY_UNAVAILABLE"`;
  - state-changing requests on any endpoint - entity creation and workflow transitions alike - return controlled HTTP `503` with `error.code = "DEPENDENCY_UNAVAILABLE"`, and none of them reports success;
  - unhandled HTTP `500` count is `0`;
  - process crash and unplanned restart count is `0`;
  - recovery time after the proxy is re-enabled is `<= 10 seconds`;
  - post-recovery functional smoke tests pass.
- **Degraded-read TTL note:** the warmed entry must remain servable for the entire outage, which lasts far longer than `CACHE_TTL_SECONDS`. A cache that simply expires the entry and then fails cannot satisfy the success-rate requirement. Implement an explicit degraded-mode policy - for example, serving a stale-but-known copy when the database is unreachable, while still refreshing normally during healthy operation. Document this policy in the ADR for this tactic. Do not disable TTL during normal operation to achieve this; ASR-P1 requires a post-expiry read to reflect the current database state under healthy conditions.
- **Implementation obligation:** degraded reads must use data populated before the outage. Fabricated data, false write success, or returning failure for every capability do not satisfy this ASR.
- **Interaction with admission control:** a degraded read served from the maintained copy must not wait on the unreachable database, and requests that cannot proceed must fail fast with `DEPENDENCY_UNAVAILABLE` rather than occupying an admitted slot until they time out. Otherwise a dependency outage silently converts into an overload condition and the system answers `429` where this scenario requires `503`. Admission control stays active during the outage, but correctly implemented fail-fast behavior keeps in-flight demand well below `MAX_IN_FLIGHT_REQUESTS`; controlled rejections are not an acceptable substitute for the responses required above.

### ASR-A4 - Atomic payment verification

- **Tactic:** `Availability > Prevent Faults > Transactions`
- **Source:** automated accountant payment-verification request.
- **Stimulus:** `POST /api/v1/payments/{paymentId}/verify` carries `X-Test-Fault: after-payment-update`.
- **Environment:** test hooks enabled; the fault is raised after the Payment row is changed but before the Invoice and Order changes complete and before commit.
- **Artifact:** the persistence transaction boundary. Payment verification is the probe; every operation that updates more than one record runs inside one atomic transaction.
- **Required response:** all changes are rolled back as one atomic unit; no partial state is externally visible.
- **Required response measures:**
  - faulted request returns controlled HTTP `500` or `503` with `error.code = "TRANSACTION_FAILED"`;
  - after the fault, `Payment.status=PENDING`, `Invoice.status=ISSUED`, and `Order.status=PAID`;
  - partial commits and inconsistent records: `0`;
  - `transaction_rollbacks_total` increases;
  - a subsequent verification request without the fault succeeds;
  - final states become `Payment.status=VERIFIED`, `Invoice.status=PAID`, and `Order.status=VERIFIED`.
- **Clarification of the post-rollback state:** `Order.status=PAID` together with `Payment.status=PENDING` is the **correct** expected state, not an inconsistency. Workflow step 4 (create Payment) advances the Order to `PAID` when the payment is submitted; the Payment itself remains `PENDING` until an accountant verifies it in step 5. The rollback therefore restores exactly the state that existed at the end of step 4. Do not redesign the workflow to "fix" this apparent mismatch - doing so violates Section 7.
- **Implementation obligation:** place all three updates in one real database transaction with no intermediate commit. The same transaction discipline applies to every multi-record operation - notably Invoice creation and Payment creation, which also advance Order state - so that no workflow step can leave a partially applied change behind. Payment verification is the scenario exercised here, not the only place the tactic is required.

---

## 5. Required observability and deterministic test interfaces

These interfaces exist so that an external client can inject stimuli and measure outcomes automatically. They must expose real behavior, not precomputed test answers.

### Health endpoints

```text
GET /health/live
GET /health/ready
```

- `/health/live` reports whether the process is alive.
- `/health/ready` reports whether the service is ready for normal operations.
- During a database outage, liveness may remain `200`; readiness must accurately reflect normal-service readiness.

### Observation paths must remain available

The system is observed *while* it is overloaded or while its database is unavailable. The following paths are observation infrastructure, not business traffic, and MUST therefore remain servable under every condition this prompt exercises:

```text
GET  /health/live
GET  /health/ready
GET  /internal/metrics
POST /internal/test/reset
```

Concretely:

- They MUST NOT pass through admission control. They are never rejected with `429`, and they never consume an admitted request slot. During the ASR-P2 overload, `/health/ready` must still answer.
- They MUST NOT require a database round-trip to produce their response. `/internal/metrics` reads in-process counters only. During the ASR-A3 outage, `/internal/metrics` and `/health/live` must still return `200` with a valid body.
- `/health/ready` is the sole exception to the previous point in terms of *content*: it is expected to report not-ready during a database outage. It must still respond promptly rather than hang or error — report the unready state in the response, do not fail to answer.
- They MUST NOT be delayed by `X-Test-Delay-Ms`.

An application whose metrics or health endpoints become unreachable during a fault cannot be observed at all, which is a defect in its own right.

### Metrics endpoint

```text
GET /internal/metrics
```

Return JSON with exactly these top-level keys and integer values:

```json
{
  "cache_hits_total": 0,
  "cache_misses_total": 0,
  "db_product_reads_total": 0,
  "db_product_read_attempts_total": 0,
  "requests_accepted_total": 0,
  "requests_rejected_total": 0,
  "timeouts_total": 0,
  "retry_attempts_total": 0,
  "transaction_rollbacks_total": 0
}
```

Semantics:

- Counters are monotonic until reset.
- `db_product_read_attempts_total` increments once for every attempt entering the real Product database-read boundary, including injected transient failures.
- `db_product_reads_total` increments only when an attempt is actually sent to PostgreSQL.
- `retry_attempts_total` counts attempts after the initial attempt.
- `requests_accepted_total` and `requests_rejected_total` are updated by the real admission-control decision.
- Metrics must increment at the location where the actual mechanism executes.

Counter scope - note that the two names beginning `db_product_` are **deliberately Product-scoped**, because ASR-P1 and ASR-A2 observe the Product read path specifically. They are narrow probes and must not be widened to count all entities. Every other counter is **system-wide**: `timeouts_total`, `retry_attempts_total`, and `transaction_rollbacks_total` count events wherever the corresponding mechanism fires, and `requests_accepted_total` / `requests_rejected_total` count admission decisions across all business endpoints. A system-wide counter that only ever increments on the Product path indicates the mechanism was not applied at its required scope.

### Structured operational logging

The application MUST write one structured log line (JSON object per line) to stdout for each of the following events, so that a failed scenario can be diagnosed from container logs alone:

- a controlled overload rejection;
- a database operation that exceeded its time limit;
- a retry attempt, including the attempt number;
- a degraded read served while the database is unreachable;
- a transaction rollback.

Each line must include at minimum an event name, a UTC timestamp, and the `error.code` where one applies.

### Test reset endpoint

Available only when `ENABLE_TEST_HOOKS=true`:

```text
POST /internal/test/reset
```

It must:

- reset all counters;
- clear the application cache;
- clear all injected-fault state;
- return HTTP `204`.

It resets in-process state only: it never deletes business data from PostgreSQL, and it must succeed without a database round-trip so that it stays callable during a dependency outage.

This endpoint establishes a clean starting point between scenarios; it is not exercised in the middle of one. Clearing the cache discards the maintained copies that ASR-A3 depends on, so a reset issued during an outage legitimately leaves warmed reads unavailable until the database returns. Do not add special-case logic to preserve entries across a reset.

When test hooks are disabled, `/internal/test/*` routes must return `404`, and test headers must be ignored safely.

### Required deterministic test headers

Only when `ENABLE_TEST_HOOKS=true`:

- `X-Test-Delay-Ms: <integer>` delays execution **after admission and while occupying an admitted request slot**, so that an overload client can exercise the real admission policy. It is honoured on every public business endpoint, not only Product search, so that admission control can be observed wherever it applies; the observation paths above are exempt.
- `X-Test-Fault: transient-db-failures=2` injects exactly two transient failures at the real Product database-read boundary before the third attempt can reach PostgreSQL.
- `X-Test-Fault: after-payment-update` raises an exception inside the real payment-verification transaction after updating Payment but before updating Invoice and Order and before commit.

Header parsing rules:

- `X-Test-Fault` carries **exactly one** directive per request. Do not implement comma-separated or repeated-header composition.
- An `X-Test-Fault` or `X-Test-Delay-Ms` value that is unrecognized, malformed, or out of range MUST be **ignored silently**: the request proceeds as if the header were absent, and the response status is whatever the request would otherwise produce. Do not return `400` for a bad test header, and do not fail the request.
- When `ENABLE_TEST_HOOKS=false`, both headers are ignored with no side effect of any kind.

The hooks create deterministic stimuli. They must not bypass the cache, admission control, timeout, retry, graceful-degradation, or transaction mechanisms they are meant to exercise.

---

## 6. Toxiproxy and deployment contract

`docker-compose.yml` must include:

- `app`;
- `db` using PostgreSQL 16;
- `toxiproxy`;
- an initialization service or script that creates a proxy named `postgres`.

Required proxy contract:

```text
Toxiproxy API host port: 8474
Proxy name: postgres
Proxy listen address inside Docker network: 0.0.0.0:8666
Proxy upstream: db:5432
Application database host/port: toxiproxy:8666
```

The application must never use `db:5432` directly.

The `app` service must have:

```text
cpus: 2.0
mem_limit: 2g
```

`start_command.txt` must be at the project root, contain exactly one non-empty line, and start the whole system. Use:

```text
docker compose up --build -d
```

All services must become ready without additional commands.

---

## 7. Domain and validation contract

### Domain Model (complete definitions required)
- **Customer:** id, name, address, phone, banking details, order history, role.
- **Order:** id, customer ref, line items, amounts, status (enum with full lifecycle), timestamps, invoice ref.
- **Product:** id, description, pricing (base + currency).
- **Payment:** id, order ref, amount, timestamp, status, method.
- **Invoice:** id, order ref, billing info, amounts, issue/due dates, status.

### Field Constraint Table (mandatory - implementation must enforce every constraint below exactly as specified)

This table is the authoritative source for all field-level validation rules. Every constraint listed here (Required, Min/Max, Length, Format/Regex, Semantic rule, Allowed Values) MUST be implemented as actual validation logic in the corresponding entity/DTO/controller layer - not merely documented. Exact numeric boundaries and regex patterns must be honored precisely, with no silent rounding, truncation, or relaxed validation.

Notation: a length written `2-100` means minimum 2 characters and maximum 100 characters, both inclusive.

### Entity: Customer

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| name | string | Yes | - | - | - | 2-100 | `^[\p{L} .'-]+$` | Must not be blank or whitespace-only | - |
| address | string | Yes | - | - | - | 5-255 | free text | Must not be blank or whitespace-only | - |
| phone | string | Yes | - | - | - | 8-15 digits | `^\+?[1-9]\d{7,14}$` (E.164) | Must not start with 0 after country code | - |
| bankingDetails.accountNumber | string | Yes | - | - | - | 6-20 | `^\d{6,20}$` (numeric only) | - | - |
| bankingDetails.bankName | string | Yes | - | - | - | 2-100 | `^[\p{L}0-9 .&-]+$` | - | - |
| role | enum | Yes | - | - | - | - | - | Fixed at creation | `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT` |
| orderHistory | array\<UUID\> | No (read-only, server-derived) | - | 0 | unbounded (soft cap 10,000) | - | - | Not settable by client | - |

### Entity: Product

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| description | string | Yes | - | - | - | 3-500 | free text | Must not be blank or whitespace-only | - |
| price.amount | decimal(2dp) | Yes | - | 0.01 | 999999.99 | - | `^\d{1,6}\.\d{2}$` | Must be > 0, exactly 2 decimal places, no rounding | - |
| price.currency | string | Yes | - | - | - | 3 | `^[A-Z]{3}$` (ISO 4217) | Must be in supported currency list | `USD`, `VND`, `EUR` |

### Entity: Order

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated, immutable | - |
| customerRef | UUID (FK) | Yes | Customer.id must exist | - | - | 36 | UUIDv4 | Must reference an existing, non-deleted customer | - |
| lineItems | array\<LineItem\> | Yes | Product.id must exist per item | 1 item | 100 items | - | - | No duplicate productRef within the same order; duplicates MUST be rejected with HTTP 400 | - |
| lineItems[].productRef | UUID (FK) | Yes | Product.id must exist | - | - | 36 | UUIDv4 | - | - |
| lineItems[].quantity | int | Yes | - | 1 | 1000 | - | `^\d+$` | Must be a whole number | - |
| lineItems[].unitPriceSnapshot | decimal(2dp) | Yes | Copied from Product.price.amount at order time | 0.01 | 999999.99 | - | `^\d{1,6}\.\d{2}$` | Immutable snapshot; must equal product price at creation time, server-computed, not client-settable | - |
| totalAmount | decimal(2dp) | Yes | = sum of (lineItems.quantity x unitPriceSnapshot) | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Server-computed, not client-settable | - |
| status | enum | Yes | Must follow the defined state machine | - | - | - | - | Default `PLACED` on creation; client cannot set an arbitrary initial status | `PLACED`, `ACCEPTED`, `INVOICED`, `PAID`, `VERIFIED`, `SHIPPED`, `CLOSED`, `CANCELLED` |
| createdAt | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-generated, immutable | - |
| updatedAt | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-updated on every state change; must be >= createdAt | - |
| invoiceRef | UUID (FK) | No | Invoice.id must exist when present | - | - | 36 | UUIDv4 | Null until Accountant creates invoice | - |

### Entity: Payment

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated | - |
| orderRef | UUID (FK) | Yes | Order.id must exist, order.status = `INVOICED` | - | - | 36 | UUIDv4 | Order must be in a payable state | - |
| amount | decimal(2dp) | Yes | Must equal Invoice.totalAmount for the referenced invoice | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Exact match required - no partial or over payment allowed (current scope) | - |
| timestamp | datetime | Yes | - | - | - | - | ISO 8601 UTC | Server-generated at submission | - |
| status | enum | Yes | Must follow the defined state machine | - | - | - | - | Default `PENDING` on creation; client cannot self-verify | `PENDING`, `VERIFIED`, `REJECTED` |
| method | enum | Yes | - | - | - | - | - | - | `CREDIT_CARD`, `BANK_TRANSFER`, `E_WALLET` |

### Entity: Invoice

| Attribute | Type | Required | Depends on | Min | Max | Length | Format/Regex | Semantic rule | Allowed Values / Equivalence Classes |
|---|---|---|---|---|---|---|---|---|---|
| id | UUID | Yes | - | - | - | 36 | UUIDv4 | Server-generated | - |
| orderRef | UUID (FK) | Yes | Order.id must exist, order.status = `ACCEPTED` | - | - | 36 | UUIDv4 | Order must be accepted before invoicing | - |
| billingInfo.name | string | Yes | Copied from Customer.name at issue time | - | - | 2-100 | `^[\p{L} .'-]+$` | Snapshot, not a live reference | - |
| billingInfo.address | string | Yes | Copied from Customer.address | - | - | 5-255 | free text | Snapshot | - |
| totalAmount | decimal(2dp) | Yes | = Order.totalAmount | 0.01 | 99999999.99 | - | `^\d{1,8}\.\d{2}$` | Must equal the referenced order's total at issue time | - |
| issueDate | date | Yes | - | - | - | - | `dd/MM/yyyy`, regex `^\d{2}/\d{2}/\d{4}$` | Must be a real calendar date (e.g. reject 31/02/2026); defaults to server current date | - |
| dueDate | date | Yes | Must be >= issueDate | - | - | - | `dd/MM/yyyy` | Default = issueDate + 7 days; must not precede issueDate; must be a real calendar date | - |
| status | enum | Yes | Must follow the defined state machine | - | - | - | - | Default `ISSUED` on creation | `ISSUED`, `PAID`, `OVERDUE`, `CANCELLED` |

### Implementation notes for validation logic
1. **Enum fields** have no numeric/length boundary - enforce via strict allow-list validation (case-sensitive exact match against the Allowed Values list); reject unknown values and empty/null when required.
2. **UUID / FK fields** must be validated in two steps: (a) format validation (reject malformed UUID strings with 400), (b) existence validation (reject valid-format but non-existent references with 404), and where relevant (c) referential state validation (reject references to entities not in the required workflow state, e.g. paying against a non-`INVOICED` order, with 409).
3. **Computed/derived fields** (`totalAmount`, `unitPriceSnapshot`) must never be trusted from client input - always recompute server-side; reject any client-supplied value for these fields with HTTP 400.
4. **Date fields** (`dd/MM/yyyy`) require two independent validation layers: (a) regex format check, and (b) calendar semantic validity check (reject non-existent dates such as 31/02 or 30/02 even if they match the regex).
5. **Decimal amount fields** must enforce exactly 2 decimal places - reject additional precision rather than silently rounding.

Additional resolutions:

- Duplicate `productRef` values in one order are rejected with HTTP `400`; do not merge them.
- Client-supplied read-only, server-generated, snapshot, or computed fields are rejected with HTTP `400`.
- `role` is immutable after Customer creation.
- Use precise decimal arithmetic; never use binary floating-point for persisted money.
- Preserve exact two-decimal semantics without silent rounding.
- All enum matching is case-sensitive.
- Do not log banking account numbers.

---

## 8. Functional API and documentation contract

### Creation manifest

Create `create_apis.json` at the project root with exactly:

```json
{
  "customer": {"method": "POST", "path": "/api/v1/customers"},
  "product": {"method": "POST", "path": "/api/v1/products"},
  "order": {"method": "POST", "path": "/api/v1/orders"},
  "payment": {"method": "POST", "path": "/api/v1/payments"},
  "invoice": {"method": "POST", "path": "/api/v1/invoices"}
}
```

For all five entities:

- `POST` returns `201` and the created resource synchronously.
- `GET <collection-path>/{id}` returns:
  - `200` for an existing ID;
  - `404` for a valid UUID that does not exist;
  - `400` for a malformed UUID.
- Paths, methods, and response codes must match the running code and OpenAPI document.
- The five create operations must not return `202`.

### Product-read and search endpoints

```text
GET /api/v1/products/{id}
GET /api/v1/products?query={text}
```

Both paths must pass through the real cache and admission-control mechanisms where applicable.

### Workflow manifest

Create `workflow_apis.json` at the project root with exactly:

```json
{
  "acceptOrder": {
    "method": "POST",
    "pathTemplate": "/api/v1/orders/{id}/accept"
  },
  "verifyPayment": {
    "method": "POST",
    "pathTemplate": "/api/v1/payments/{id}/verify"
  },
  "shipOrder": {
    "method": "POST",
    "pathTemplate": "/api/v1/orders/{id}/ship"
  },
  "closeOrder": {
    "method": "POST",
    "pathTemplate": "/api/v1/orders/{id}/close"
  }
}
```

### Seven-step workflow and state transitions

1. Customer creates Order:
   - Order starts as `PLACED`.
2. Order Staff accepts Order:
   - `PLACED -> ACCEPTED`.
3. Accountant creates Invoice:
   - Invoice starts as `ISSUED`;
   - Order becomes `INVOICED`;
   - `Order.invoiceRef` is set.
4. Customer creates Payment:
   - Payment starts as `PENDING`;
   - amount must exactly equal the Invoice total;
   - Order becomes `PAID`.
5. Accountant verifies Payment:
   - Payment becomes `VERIFIED`;
   - Invoice becomes `PAID`;
   - Order becomes `VERIFIED`;
   - all three updates are atomic.
6. Order Staff ships Order:
   - `VERIFIED -> SHIPPED`.
7. Order Staff closes Order:
   - `SHIPPED -> CLOSED`.

Reject invalid transitions with HTTP `409`.

Note that after step 4 the Order is `PAID` while the Payment is still `PENDING`. This is intentional and correct: the Order status reflects that payment was submitted, and the Payment status reflects that it has not yet been verified by an accountant. ASR-A4 depends on this being implemented exactly as written.

Invoice creation and Payment creation must also use transaction boundaries where they update more than one record. Payment verification is the transaction exercised by ASR-A4, but the requirement is not limited to it.

### API contract documentation for functional-correctness testing

The repository and running application must expose a complete API contract so that an external consumer can identify every endpoint, construct valid and invalid requests, and verify responses without reading the implementation source code.

The generated documentation is an **invocation contract**, not the correctness oracle. The Field Constraint Tables, workflow rules, status-code rules, and acceptance criteria in this prompt remain authoritative if generated documentation conflicts with them.

#### Runtime documentation endpoints

Expose:

```text
GET /docs
GET /redoc
GET /openapi.json
```

Requirements:

- `/docs` serves Swagger UI.
- `/redoc` serves ReDoc.
- `/openapi.json` returns a valid OpenAPI 3.1 document generated from the actual running routes.
- Export the same contract to repository-root `openapi.json`.
- The exported file and runtime document must describe the same paths, operations, schemas, and status codes.
- Every public operation must have a stable, unique `operationId`.

To guarantee the exported file cannot drift from the running routes, provide an executable exporter at `scripts/export_openapi.py` that imports the real application object and writes repository-root `openapi.json`. Run it as the final step of generation, and document it in the README as the command to re-run after any route change. A hand-maintained `openapi.json` is a defect.

#### Mandatory OpenAPI content

For every public endpoint, document:

- HTTP method and exact versioned path;
- purpose and workflow preconditions;
- path, query, and header parameters;
- complete request-body schema;
- required and optional fields;
- field formats, enum values, numeric boundaries, string-length boundaries, and nested-object structure;
- at least one valid request example;
- at least one successful response example;
- all applicable response status codes;
- response-body schema for each status;
- representative error examples;
- state changes and important side effects.

At minimum, document these response classes where applicable:

```text
200 - successful retrieval or workflow action
201 - successful synchronous creation
204 - successful reset operation with no response body
400 - malformed UUID, invalid syntax, missing required field, or field-constraint violation
404 - valid identifier but resource not found
409 - invalid workflow state, referential-state conflict, or illegal transition
429 - controlled overload rejection
500 - controlled injected transaction failure
503 - dependency unavailable or degraded write operation
504 - dependency timeout
```

Do not advertise a response code that the running implementation cannot produce.

#### Mandatory human-readable API catalog

Create:

```text
docs/API_CONTRACT.md
```

It must contain:

1. **Endpoint inventory**

   One row per public operation:

   ```text
   Operation ID | Actor | Method | Path | Purpose | Preconditions |
   Success status | Error statuses
   ```

2. **Request/response contracts**

   For every operation:

   - request JSON example;
   - successful response JSON example;
   - each relevant error case with:
     - triggering condition;
     - expected HTTP status;
     - representative response JSON;
   - fields generated or ignored by the server;
   - state transition and side effects.

3. **Seven-step workflow example**

   Show the complete sequence using symbolic identifiers:

   ```text
   customerId
   productId
   orderId
   invoiceId
   paymentId
   ```

   Include the request and expected response status for each step.

4. **Functional-correctness scenario matrix**

   Include, at minimum:

   ```text
   Scenario ID | Operation ID | Preconditions | Input partition/boundary |
   Expected status | Expected body assertions | Expected state after call
   ```

   Cover:

   - one valid creation scenario for each entity;
   - minimum and maximum accepted boundaries;
   - one value immediately below and above each important numeric/length boundary;
   - missing required fields;
   - invalid enum values;
   - malformed UUID;
   - valid but unknown UUID;
   - foreign-key not found;
   - valid reference in the wrong workflow state;
   - attempts to supply computed, server-generated, immutable, or read-only fields;
   - invalid and valid workflow transitions;
   - duplicate `productRef` in an Order;
   - invalid decimal precision;
   - invalid calendar dates;
   - final states after the complete workflow.

The catalog must reflect the actual implementation and must not replace any mandatory validation or test.

#### Cross-artifact consistency

The following artifacts must agree:

```text
openapi.json
create_apis.json
workflow_apis.json
docs/API_CONTRACT.md
actual running routes
```

In particular:

- identical paths and methods;
- identical request field names and nesting;
- identical success and error status codes;
- identical workflow preconditions and state transitions;
- identical response schemas.

Any contradiction is an implementation defect.

---

## 9. Required execution protocol

Perform the work in this order:

1. **Plan**
   - Create `architecture/ADRs.md`.
   - Create an initial `architecture/tactic-traceability.md`.
   - Define modules, transaction boundaries, cache behavior, admission-control behavior, fault behavior, and observability.

2. **Implement**
   - Implement the full domain, REST API, persistence, migrations, selected tactics, Docker artifacts, and machine-readable manifests.
   - Every file must be complete. Do not use placeholders, ellipses, TODO-only functions, or "repeat this pattern" comments.

3. **Verify**
   - Build the containers from a clean state.
   - Start the complete system using the exact command stored in `start_command.txt`.
   - Run migrations.
   - Run project tests.
   - Exercise the complete business workflow.
   - Run `scripts/export_openapi.py` and confirm repository-root `openapi.json` matches the runtime document.
   - Confirm that every path and function listed in `nfr-trace.json` exists and that all required health, metrics, documentation, and test-control interfaces can be invoked.

4. **Repair and finalize**
   - Repair build, startup, migration, test, API-contract, and traceability defects.
   - Update the ADRs and traceability files to describe the code that actually exists, not the initial plan.
   - Do not claim a check passed unless you executed it successfully.

---

## 10. Architecture documentation and traceability deliverables

### ADRs

Create `architecture/ADRs.md`.

For each of the six selected tactics, provide a concise ADR containing:

- tactic string exactly as specified;
- decision;
- ASR context;
- implementation mechanism;
- alternatives considered;
- consequences and trade-offs;
- affected components;
- **scope of applicability** - where in the system the tactic takes effect, and any deliberate exclusions with their reasoning;
- verification scenario.

Also document the overall module structure, persistence choice, cache choice, overload-control choice, retry/fault-classification policy, and the degraded-mode cache policy required by ASR-A3.

The ADR for the caching tactic must additionally state the **scope of applicability**: which entities are served from a maintained copy, which are not, and the reasoning for each exclusion. Read-mostly reference data and entities whose state advances through the seven-step workflow warrant different decisions; state both explicitly rather than describing only the entity exercised by ASR-P1.

### Human-readable traceability

Create `architecture/tactic-traceability.md` with one row per ASR and these columns:

```text
ASR ID | QA | Exact tactic | Mechanism | Component/module |
Files | Functions/configuration | Runtime metrics | Verification scenario
```

The final table must describe actual delivered artifacts.

### Machine-readable traceability

Create `nfr-trace.json` at the project root:

```json
{
  "nfrTrace": [
    {
      "scenarioId": "ASR-P1",
      "nfr": "Cached product-read performance",
      "tacticUsed": "Performance > Manage Resources > Maintain Multiple Copies of Data",
      "filesImplemented": [],
      "functionNames": [],
      "configurationKeys": [],
      "librariesUsed": [],
      "metrics": [],
      "verificationMethod": ""
    }
  ]
}
```

Populate exactly six entries, in ASR order: `ASR-P1`, `ASR-P2`, `ASR-A1`, `ASR-A2`, `ASR-A3`, `ASR-A4`.

Rules:

- Use the exact tactic string assigned to that ASR.
- `filesImplemented` contains only real project-relative paths.
- `functionNames` uses `relative/path.py::qualified_function_or_method`.
- Each function must exist verbatim and directly implement or configure the tactic.
- `configurationKeys` lists real environment variables or configuration keys used by the mechanism.
- `librariesUsed` lists actual dependencies; use `[]` when hand-written.
- `metrics` lists only names exposed by `/internal/metrics`.
- `verificationMethod` summarizes the corresponding executable scenario.
- Do not list planned or nonexistent files/functions.
- The JSON, ADRs, Markdown matrix, code, and OpenAPI document must not contradict one another.

---

## 11. Required repository structure and implementation deliverables

At minimum, deliver:

```text
README.md
start_command.txt
create_apis.json
workflow_apis.json
nfr-trace.json
openapi.json
Dockerfile
docker-compose.yml
requirements.txt or pyproject.toml with lock file
alembic.ini
alembic/
architecture/ADRs.md
architecture/tactic-traceability.md
docs/API_CONTRACT.md
scripts/export_openapi.py
app/
tests/
```

Implementation must include:

- domain entities and enums;
- request and response DTOs;
- validation and error mapping;
- repositories;
- services with business logic and transaction boundaries;
- controllers/routes;
- cache mechanism with single-flight refill and a degraded-mode policy;
- admission-control and controlled-rejection mechanism;
- timeout and retry policy;
- graceful-degradation behavior;
- metrics, structured logging, and health endpoints;
- deterministic test hooks;
- PostgreSQL schema and migrations;
- OpenAPI document consistent with running routes, produced by `scripts/export_openapi.py`;
- Swagger UI and ReDoc runtime documentation;
- complete `docs/API_CONTRACT.md` describing every public operation;
- unit and integration tests;
- local deployment and verification instructions.

Use composition over inheritance. Avoid duplicated cross-cutting logic.

---

## 12. Submission contract

The delivered repository must:

1. build from a clean checkout;
2. start using the single command in `start_command.txt`;
3. run database migrations automatically;
4. expose all functional, health, metrics, documentation, and test-control interfaces prescribed by this prompt;
5. accept every prescribed external configuration key;
6. route PostgreSQL communication through Toxiproxy;
7. expose deterministic test hooks only when `ENABLE_TEST_HOOKS=true`;
8. provide consistent OpenAPI, API manifests, ADRs, and traceability artifacts;
9. contain no fabricated metrics, precomputed outputs, hidden bypasses, or special responses that avoid the real mechanism;
10. require no manual source-code or configuration edits after generation.

The repository must be operable and observable by an external client without manual intervention.

---

## 13. Final response

After completing the repository, return only a concise execution report containing:

1. architecture summary;
2. files created;
3. exact startup command;
4. commands actually executed;
5. build, startup, migration, functional-test, traceability, and observability-interface results;
6. which of the six ASR scenarios you executed locally and their observed results;
7. any remaining failures stated explicitly.

Do not paste the entire repository into the final response. The repository files are the deliverable.