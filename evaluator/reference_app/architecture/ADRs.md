# Architecture Decision Records — reference application

These record how each prescribed tactic is realised here. This application is a
calibration instrument for the evaluator, not a study submission, so the records
are brief: their purpose is to be resolvable by the traceability gate and to
explain the two decisions that are genuinely non-obvious.

## ADR-1 — Performance > Manage Resources > Maintain Multiple Copies of Data

**Decision.** An in-process TTL cache in front of the product read, keyed by
product id, with per-key single-flight refill.

**ASR context.** ASR-P1: a thousand reads at concurrency fifty must reach the
database only a handful of times, while the database stays authoritative.

**Mechanism.** `ProductCache.get` returns a fresh entry directly. On a miss it
takes a per-key lock, re-checks under it, and loads once; concurrent readers of
the same key wait on that single load and are then served as hits.

**Alternatives considered.** An external cache such as Redis would work but adds
a dependency whose failure modes would confound the availability scenarios. A
cache without single-flight was rejected because fifty concurrent misses would
each issue their own read and exhaust the budget on the first refill.

**Consequences.** Readers of the same product serialise briefly during a refill.
The cache is per-process, so it would not survive horizontal scaling — acceptable
here, where the deployment is a single container.

**Affected components.** `app/cache.py`, `app/services.py`.

**Verification.** A row is changed directly in PostgreSQL; the API must serve
the old value before expiry and the new one after.

## ADR-2 — Performance > Control Resource Demand > Manage Work Requests > Limit Event Response

**Decision.** A counting semaphore on the public product paths that refuses
immediately when full.

**ASR context.** ASR-P2: two hundred simultaneous requests against a limit of
ten must produce controlled rejections, not unbounded waiting.

**Mechanism.** `AdmissionMiddleware` calls `try_acquire`, which either takes a
slot or returns at once. A refusal answers 429 with `Retry-After` and
`OVERLOAD_REJECTED`.

**Alternatives considered.** A bounded work queue was rejected deliberately: it
also ends up rejecting, but only after making callers wait, which is a different
tactic and outside this study's scope.

**Consequences.** Under load the system sheds work rather than degrading for
everyone. Throughput is capped by the configured limit even when spare capacity
exists.

**Affected components.** `app/admission.py`.

**Verification.** Rejection p95 must stay under 500 ms — the measure that
separates immediate refusal from queueing.

## ADR-3 — Availability > Detect Faults > Timeout

**Decision.** PostgreSQL `statement_timeout`, set per connection, plus a bounded
connect timeout.

**ASR context.** ASR-A1: with five seconds of injected latency the client must
be answered in well under it.

**Mechanism.** A connect-event listener issues `SET statement_timeout` on every
new connection. The connect timeout bounds establishment, which is what would
otherwise hang during an outage.

**Alternatives considered.** Racing a Python timer against the query was
rejected: it abandons the caller while the server keeps working, so the load is
never actually shed.

**Consequences.** Long legitimate queries are also bounded. Acceptable here,
where no query is expected to approach the limit.

**Affected components.** `app/database.py`.

**Verification.** Client-side elapsed time, not a counter — a system that waits
out the fault and then reports a timeout is caught by the stopwatch.

## ADR-4 — Availability > Recover from Faults > Preparation and Repair > Retry

**Decision.** A bounded retry with explicit fault classification.

**ASR context.** ASR-A2: two transient failures must be absorbed, the third
attempt must succeed, and the ceiling must hold.

**Mechanism.** `classify` maps driver errors to timeout, unavailable, or
transient. `with_retry` retries the first and third and never the second: a
refused connection cannot succeed on a later attempt, so retrying it would spend
the budget to reach the same outcome more slowly. Backoff is skipped after a
timeout, which has already supplied the delay backoff exists to create.

**Alternatives considered.** Retrying every exception was rejected because it
would retry validation failures and not-found responses, which can never
succeed.

**Consequences.** A misclassified error is either retried when it should not be
or not retried when it should; classification is therefore the load-bearing part
and is tested directly.

**Affected components.** `app/database.py`.

**Verification.** Attempt and retry counters, cross-checked against a pg_stat
scan delta of exactly one.

## ADR-5 — Availability > Recover from Faults > Preparation and Repair > Graceful Degradation

**Decision.** Each cache entry carries two lifetimes: a TTL governing freshness,
and a longer horizon governing how long a stale copy may be served *while the
database is unreachable*.

**ASR context.** ASR-A3 requires a warmed entry to survive a sixty-second
outage, while ASR-P1 requires entries to expire after five seconds. A single
lifetime cannot satisfy both.

**Mechanism.** When the loader reports the database unreachable, `_load_and_store`
falls back to the existing entry if there is one and it is within the degraded
horizon. Nothing is served for a key that was never loaded, so no data is
invented; writes fail with `DEPENDENCY_UNAVAILABLE` rather than reporting a
success that did not persist.

**Alternatives considered.** Lengthening the TTL was rejected: it satisfies the
outage and fails the staleness probe, because the post-expiry read would keep
serving the old value.

**Consequences.** During an outage clients may receive data up to a minute old.
That is the trade the tactic exists to make, and it is confined to reads.

**Affected components.** `app/cache.py`.

**Verification.** Warmed reads succeed at 99% during the outage while the
unwarmed read and every write return a controlled failure.

## ADR-6 — Availability > Prevent Faults > Transactions

**Decision.** Payment verification updates payment, invoice and order inside one
transaction with no intermediate commit.

**ASR context.** ASR-A4: a fault raised between the first and second update must
leave no partial state.

**Mechanism.** `session_scope` opens one transaction, commits on success and
rolls back on any exception. `verify_payment` performs all three updates inside
it; the injected fault is raised after the payment row changes and before the
other two.

**Alternatives considered.** Per-entity transactions with compensating updates
were rejected: compensation can itself fail, leaving exactly the inconsistency
the tactic is meant to prevent.

**Consequences.** The three updates are serialised and hold their locks for the
duration of the request.

**Affected components.** `app/services.py`, `app/database.py`.

**Verification.** Row statuses read straight from PostgreSQL, not through the
API, so no cache or in-memory shadow can answer on the database's behalf.

## Module structure

`config` reads settings once into a frozen object. `observability` owns counters,
controlled errors and structured logging. `cache`, `admission` and `database`
each hold one cross-cutting mechanism. `services` holds business logic and the
transaction boundaries; `main` maps HTTP to services and nothing else.

## Deliberate defects

`config.Settings` carries six `defect_*` switches, all off by default. Each
disables one mechanism in the way a plausible-but-wrong implementation would, so
the evaluator can be checked for false negatives as well as false positives.
They exist only because this application is an instrument; a study submission
would have no such thing.
