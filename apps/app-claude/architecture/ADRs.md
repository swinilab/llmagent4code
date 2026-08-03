# OrderMan - Architecture Decision Records

## Module structure

```
app/
  core/          cross-cutting mechanisms, owned once and applied system-wide
    config.py        effective external configuration
    admission.py     admission control (ASR-P2)
    cache.py         TTL cache with single-flight and degraded mode (ASR-P1, ASR-A3)
    errors.py        controlled-error contract
    metrics.py       in-process counters
    logging.py       structured stdout events
    test_hooks.py    deterministic fault/delay injection
  persistence/
    database.py      THE database boundary: timeout, retry, transactions, health gate
    models.py        SQLAlchemy ORM mapping
    repositories.py  plain data access over an injected Session
  domain/
    enums.py         enumerations and the order state machine
  schemas/
    common.py        Field Constraint Table validators
    dto.py           request/response DTOs
  services/          business logic and transaction boundaries
  api/               routes, middleware, error handlers
```

The guiding rule is that each architectural tactic is implemented **once**, in a
component of its own, and applied at its natural scope. Services and repositories
contain no timeout, retry, admission, or transaction logic; they inherit those
policies from `app/core` and `app/persistence/database.py`. Composition is used
throughout - there is no inheritance hierarchy among services or repositories.

**Persistence choice.** PostgreSQL 16 via SQLAlchemy 2.x with the synchronous
psycopg2 driver. Synchronous sessions are executed on a worker thread by the API
layer, which makes the per-attempt timeout genuinely enforceable: the caller can
abandon a hung attempt at its deadline without leaving a half-cancelled asyncio
task holding a connection. Money is `NUMERIC(12,2)` mapped to `decimal.Decimal`;
binary floating point is never used for persisted amounts.

**Cache choice.** A hand-written in-process `TtlCache` rather than Redis. The
maintained copy must remain readable while the database is unreachable, and an
in-process copy has no additional network dependency that could fail at the same
time. It is also what allows a cache hit to complete in well under a millisecond,
which ASR-P1 requires so that hits release their admitted slot promptly.

**Overload-control choice.** A non-blocking counting semaphore in ASGI
middleware. See ADR-2.

**Retry / fault-classification policy.** See ADR-4.

**Degraded-mode cache policy.** See ADR-5.

---

## ADR-1 - `Performance > Manage Resources > Maintain Multiple Copies of Data`

**Decision.** Maintain an in-process, TTL-bounded copy of Product read results,
refilled through a single-flight loader.

**ASR context.** ASR-P1. Sustained repeated reads of the same Product, including
concurrent reads, while the row may be modified directly in PostgreSQL. Requires
>=95% hit rate, p95 <=200 ms, <=1% errors, and database reads bounded by
TTL-driven refills rather than one per miss.

**Implementation mechanism.** `app/core/cache.py::TtlCache.get_or_load`. A fresh
entry is served directly as a hit. On a miss the caller takes a per-key lock and
re-checks before loading, so concurrent misses for the same key produce exactly
one database read while the other waiters observe the freshly stored value. The
cache stores fully rendered response DTOs, so a hit performs no ORM work.
`app/services/product_service.py::get_product` supplies the loader and key policy.

**Alternatives considered.**
- *Redis / external cache*: adds a second network dependency that would likely be
  unreachable during the same outage ASR-A3 exercises, and cannot serve a
  sub-millisecond hit. Rejected.
- *Cache-aside without single-flight*: simpler, but a burst of concurrent misses
  issues one database read each, violating the TTL-bounded-refill measure.
  Rejected.
- *Caching at the HTTP layer*: would bypass the application's own read path and
  could not implement the degraded-mode policy ASR-A3 needs. Rejected.

**Consequences and trade-offs.** Reads may be up to `CACHE_TTL_SECONDS` stale by
design; this is exactly the observable behaviour ASR-P1 specifies. Because the
copy is per-process, the service runs a single uvicorn worker so that counters
and the cache are authoritative for the whole service. Horizontal scaling would
require either sticky routing or accepting per-instance copies.

**Affected components.** `app/core/cache.py`, `app/services/product_service.py`,
`app/api/routes_business.py::get_product`.

**Scope of applicability.** This is the one tactic whose scope is a deliberate
design decision rather than a system-wide policy.

- **Product - cached.** Read-mostly reference data. Its state does not advance
  through the seven-step workflow, so a bounded-stale copy is safe and is what
  ASR-P1 measures.
- **Order, Payment, Invoice - deliberately excluded.** These entities advance
  through the workflow, and their status is the externally observable result of
  transactions. A stale copy would make workflow state and transaction rollbacks
  visible as incorrect: ASR-A4 requires reading back `Payment.status=PENDING`,
  `Invoice.status=ISSUED`, and `Order.status=PAID` *immediately* after a
  rollback, which a cached copy could not guarantee.
- **Customer - deliberately excluded.** Although customer identity is
  read-mostly, the response embeds `orderHistory`, which is derived from Order
  state and therefore inherits the same staleness hazard.

The `TtlCache` component itself is entity-agnostic and keyed by opaque strings,
so applying it to another entity is a configuration decision, not a code change.

**Verification scenario.**
`tests/test_asr_performance.py::test_asrp1_stale_within_ttl_then_fresh_after_ttl`
(out-of-band `UPDATE` invisible within the TTL, visible after it),
`::test_asrp1_concurrent_reads_hit_rate_latency_and_db_bound`, and
`::test_asrp1_single_flight_bounds_concurrent_misses`.

---

## ADR-2 - `Performance > Control Resource Demand > Manage Work Requests > Limit Event Response`

**Decision.** Bound concurrently admitted business requests with a non-blocking
counting semaphore in ASGI middleware, rejecting excess work immediately.

**ASR context.** ASR-P2. A burst far exceeding `MAX_IN_FLIGHT_REQUESTS`, each
request held in-flight. Requires that concurrent admission never exceeds the
limit, that admitted requests still succeed, that excess receives `429` with
`Retry-After`, that rejection p95 <=500 ms, and that `/health/ready` answers
within 2 s after the burst.

**Implementation mechanism.**
`app/core/admission.py::AdmissionController.slot` acquires a slot with a strictly
non-blocking `_try_acquire`; a request that cannot take one is refused at once.
`app/api/middleware.py::AdmissionControlMiddleware.dispatch` applies this to every
public business endpoint and emits the `OVERLOAD_REJECTED` envelope with
`Retry-After`. The controller also records `peak_in_flight` at the instant a slot
is taken, exposed at `/internal/admission` as the authoritative measure of
concurrent admission.

**Alternatives considered.**
- *Bounded work queue*: admits requests and makes them wait. That is a different
  tactic (Bound Queue Sizes), explicitly out of scope, and violates the
  immediate-rejection requirement. Rejected.
- *Per-route rate limiting*: would satisfy the letter of the scenario via Product
  search while leaving the rest of the API ungoverned. Rejected as an
  implementation defect by the prompt's own criterion.
- *Web-server connection limit*: manifests as dropped connections rather than a
  controlled response with a diagnosable body. Rejected.

**Consequences and trade-offs.** Under overload the system sheds load rather than
degrading latency for everyone - a deliberate choice favouring predictability.
Clients must handle `429` and honour `Retry-After`. The limit is process-wide, so
it composes with the single-worker decision from ADR-1.

**Affected components.** `app/core/admission.py`, `app/api/middleware.py`,
`app/api/routes_ops.py::get_admission_state`.

**Scope of applicability.** System-wide across every public business endpoint
under `/api/v1`. The sole exemptions are the observation paths -
`/health/live`, `/health/ready`, `/internal/metrics`, `/internal/admission`,
`/internal/test/reset` - and the documentation routes. These bypass admission
entirely and never consume a slot, because a system that cannot be observed while
overloaded cannot be diagnosed.

**Verification scenario.**
`tests/test_asr_performance.py::test_asrp2_admission_control_under_overload`,
`::test_asrp2_retry_after_header_on_rejection`, and
`::test_observation_paths_bypass_admission_control`. Measured on a 60-request
simultaneous burst over pre-warmed connections: exactly 10 admitted, 50 rejected,
rejection p95 31 ms.

---

## ADR-3 - `Availability > Detect Faults > Timeout`

**Decision.** Bound every database operation with a per-attempt time limit of
`DB_OPERATION_TIMEOUT_MS`, enforced at three layers.

**ASR context.** ASR-A1. Injected latency far exceeding the limit on an uncached
Product read. Requires per-attempt timeout <=1.2 s, total response <=4.5 s, a
controlled `503`/`504` carrying `DEPENDENCY_TIMEOUT`, `timeouts_total` to
increase, and the application to stay live.

**Implementation mechanism.** `app/persistence/database.py::_run_attempt` submits
each attempt to a worker pool and abandons it at its deadline. Defence in depth:
the engine is configured with a matching `connect_timeout` and a server-side
`statement_timeout`, so a query that already reached PostgreSQL is cancelled
there rather than merely abandoned by the client, and connection acquisition is
bounded by `pool_timeout`. Exceeded limits increment `timeouts_total` and emit a
`db_operation_timeout` event.

**Alternatives considered.**
- *Client-side HTTP timeout only*: detects nothing at the database boundary and
  leaves the connection working. Explicitly insufficient per the prompt.
  Rejected.
- *`statement_timeout` alone*: does not cover connection acquisition or a
  network-level stall before the statement is sent. Kept as one layer, not the
  whole mechanism.

**Consequences and trade-offs.** A legitimately slow query is cut off at 1 s; the
budget is deliberately not tuned up toward the 1.2 s ceiling. Abandoned attempts
briefly retain a pool thread, which is why the pool is sized above
`MAX_IN_FLIGHT_REQUESTS`.

**Affected components.** `app/persistence/database.py`, `app/core/config.py`.

**Scope of applicability.** System-wide. Every read and write of every entity
flows through `run_with_resilience`, so no code path reaches PostgreSQL without
the time limit. It is not reachable-only-from-Product.

**Verification scenario.**
`tests/test_asr_availability.py::test_asra1_timeout_detection` (5 s injected
latency; observed controlled response well inside the 4.5 s budget with
`DEPENDENCY_TIMEOUT`) and `::test_asra1_no_request_hangs_beyond_budget`.

---

## ADR-4 - `Availability > Recover from Faults > Preparation and Repair > Retry`

**Decision.** Apply a bounded retry policy with explicit retryable-fault
classification once, at the database boundary.

**ASR context.** ASR-A2. Two injected transient faults before a third attempt
succeeds. Requires HTTP `200`, `db_product_read_attempts_total` +3,
`retry_attempts_total` +2, never more than `DB_MAX_ATTEMPTS`, no retry for
validation/`404`/`409`, and no infinite loop.

**Implementation mechanism.**
`app/persistence/database.py::run_with_resilience` loops at most
`DB_MAX_ATTEMPTS` times. `::is_retryable` classifies faults: injected transient
faults, timeouts, and connection-level failures are retryable; everything else is
not. `DomainError` and `ControlledError` are re-raised before classification, so
a `400`/`404`/`409` can never be retried or reclassified as a dependency problem.
Each retry increments `retry_attempts_total` and logs `db_retry_attempt` with the
attempt number.

**Fault-classification rule.** Retryable = injected transient fault, exceeded
time limit, or a connection-level failure (refused, reset, closed, unreachable).
Non-retryable = every business outcome, every already-classified controlled
error, and any exception not matching the transient patterns.

**Retry safety rule and its boundary.** Retry is permitted only where
re-execution cannot duplicate an effect.

- **Reads are retried.** All `get`/`search` operations pass `retryable=True`.
- **Writes are never blindly re-executed.** Every write path - customer, product,
  and order creation, invoice and payment creation, every workflow transition,
  and payment verification - passes `retryable=False`. A write that failed after
  the statement reached PostgreSQL may already have been applied, and re-running
  it could produce duplicate Payments, Invoices, or workflow transitions. Rather
  than guess, the operation surfaces a controlled failure and the client decides.

**Backoff.** `DB_RETRY_BACKOFF_MS`, scaled by attempt number, is applied only
when the previous attempt failed by a transient error. It is deliberately skipped
after a timeout, because the elapsed time limit already provided the delay - this
is what keeps three exhausted attempts well inside the 4.5 s budget of ASR-A1.

**Alternatives considered.**
- *Retry inside each repository*: duplicates the policy and guarantees drift.
  Rejected.
- *Unbounded retry with exponential backoff*: cannot satisfy a bounded response
  time. Rejected.
- *Retrying writes idempotently via client-supplied keys*: a real option, but it
  would require an idempotency-key contract the prompt does not define. Rejected
  as out of scope; the safety rule above is applied instead.

**Consequences and trade-offs.** Transient read faults are invisible to clients.
Write faults surface to the client even when they might have been safe to retry -
a deliberate bias toward correctness over availability for state-changing work.

**Affected components.** `app/persistence/database.py`, every service module.

**Scope of applicability.** System-wide at the database boundary, subject to the
read/write safety rule above.

**Verification scenario.**
`tests/test_asr_availability.py::test_asra2_retry_recovers_after_two_transient_faults`
(exactly 3 attempts, exactly 2 retries, HTTP 200),
`::test_asra2_attempts_never_exceed_max`,
`::test_asra2_non_transient_failures_are_not_retried`, and
`::test_asra2_workflow_conflict_is_not_retried`.

---

## ADR-5 - `Availability > Recover from Faults > Preparation and Repair > Graceful Degradation`

**Decision.** During a database outage, serve warmed Product reads from their
retained copy, refuse operations needing durable state fast and explicitly, and
recover automatically via a background prober.

**ASR context.** ASR-A3. The proxy is disabled for far longer than
`CACHE_TTL_SECONDS`. Requires warmed-read success >=99% at p95 <=200 ms, unwarmed
reads and all state-changing requests to return controlled `503`/`504` with
`DEPENDENCY_UNAVAILABLE`, zero unhandled `500`s, zero restarts, and recovery
<=10 s.

**Degraded-mode cache policy.** `TtlCache` retains an entry after its TTL expires
instead of discarding it. During healthy operation an expired entry is always
refilled, so ASR-P1's post-TTL freshness requirement is preserved - the TTL is
never disabled. Only when the refill fails with `DependencyUnavailableError` is
the retained copy served, logged as `degraded_read_served`. A Product never read
before has no copy to fall back to, so its read correctly surfaces
`DEPENDENCY_UNAVAILABLE`.

**Fail-fast health gate.** `app/persistence/database.py::DependencyHealthGate` is
the second half of the mechanism. Once a connection-level failure is observed the
gate opens and subsequent operations fail immediately rather than re-paying the
connection timeout. This matters for two reasons: a degraded read must not wait
on the unreachable database (it would blow the 200 ms budget), and a request that
cannot proceed must not occupy an admitted slot until it times out - otherwise
the outage silently converts into an overload condition and the system would
answer `429` where this scenario requires `503`.

**Background recovery probing.** Recovery is detected by a dedicated daemon
thread (`_recovery_prober`), never by a user request. An earlier design let one
request per interval act as the probe; measurement showed those probes paying
~300 ms each and pushing warmed-read p95 to 313 ms against a 200 ms budget.
Moving probing off the request path brought p95 to ~0 ms while keeping recovery
automatic and well inside 10 s.

**Alternatives considered.**
- *Expire-and-fail*: a plain TTL cache cannot meet the >=99% success requirement
  across an outage lasting many multiples of the TTL. Rejected.
- *Disabling the TTL during outages by extending it globally*: would violate
  ASR-P1's requirement that a post-expiry read reflect current state under
  healthy conditions. Rejected.
- *Queuing writes for later replay*: reports false success for work that may
  never be applied, and is explicitly disallowed. Rejected.
- *Returning failure for every capability*: not degradation. Rejected.

**Consequences and trade-offs.** During an outage warmed Product data may be
arbitrarily stale - accepted deliberately, since availability of read capability
is the stated goal. Writes are unavailable, which is the honest and safe outcome.

**Affected components.** `app/core/cache.py`,
`app/persistence/database.py::DependencyHealthGate`, `_recovery_prober`,
`app/services/product_service.py`, `app/api/routes_ops.py::health_ready`.

**Scope of applicability.** The degraded-read policy applies wherever a
maintained copy exists (Product, per ADR-1). Fail-fast refusal with
`DEPENDENCY_UNAVAILABLE` applies system-wide to every endpoint requiring durable
state - entity creation and workflow transitions alike.

**Verification scenario.**
`tests/test_asr_availability.py::test_asra3_graceful_degradation_during_outage`
(15 s outage = 3x TTL; observed 100% warmed-read success, p95 within budget, all
unwarmed reads and writes `503`/`DEPENDENCY_UNAVAILABLE`, zero unhandled 500s,
recovery and post-recovery smoke tests passing) and
`::test_asra3_state_changing_workflow_transitions_fail_safely`.

---

## ADR-6 - `Availability > Prevent Faults > Transactions`

**Decision.** Run every multi-record operation inside exactly one database
transaction with no intermediate commit.

**ASR context.** ASR-A4. A fault raised after the Payment row is updated but
before the Invoice and Order updates and before commit. Requires a controlled
`500`/`503` with `TRANSACTION_FAILED`, post-rollback state of
`Payment.status=PENDING` / `Invoice.status=ISSUED` / `Order.status=PAID`, zero
partial commits, `transaction_rollbacks_total` to increase, and a subsequent
clean verification to reach `VERIFIED`/`PAID`/`VERIFIED`.

**Implementation mechanism.**
`app/persistence/database.py::session_scope` is the single transaction boundary:
it commits on success and rolls back on any exception.
`app/services/order_service.py::verify_payment` performs all three updates inside
one scope. An injected `InjectedTransactionFault` triggers a real rollback, which
increments `transaction_rollbacks_total`, logs `transaction_rollback`, and raises
`TransactionFailedError`.

A domain error (`400`/`404`/`409`) also rolls its unit back, but is deliberately
**not** counted as a transaction rollback - a rejected business rule is the
expected outcome of validation, not a fault.

**Post-rollback state.** `Order.status=PAID` together with
`Payment.status=PENDING` is the correct expected state, not an inconsistency.
Workflow step 4 advances the Order to `PAID` when payment is submitted, while the
Payment remains `PENDING` until an accountant verifies it in step 5. The rollback
restores exactly the end-of-step-4 state.

**Alternatives considered.**
- *Separate transactions per record with compensating actions*: introduces a
  window where partial state is externally visible, which is precisely what this
  ASR forbids. Rejected.
- *Application-level two-phase commit*: unnecessary complexity for a single
  database. Rejected.

**Consequences and trade-offs.** Multi-record operations hold their transaction
slightly longer and cannot be retried blindly (see ADR-4). In exchange, no
workflow step can leave a partially applied change behind.

**Affected components.** `app/persistence/database.py::session_scope`,
`app/services/order_service.py`, `app/services/product_service.py`,
`app/services/customer_service.py`.

**Scope of applicability.** System-wide across every multi-record operation, not
only payment verification. Invoice creation (Invoice + Order status +
`invoiceRef`), Payment creation (Payment + Order status), order creation (Order +
its line items), and every workflow transition each run in exactly one
transaction.

**Verification scenario.**
`tests/test_asr_availability.py::test_asra4_transaction_rollback_leaves_no_partial_state`
(faulted verify returns `TRANSACTION_FAILED`; all three records observed at their
pre-transaction values; clean retry reaches the final states) and
`::test_asra4_invoice_creation_is_atomic`.
