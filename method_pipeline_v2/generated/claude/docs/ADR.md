# Architectural Decision Records

---

## ADR-001 — Modular monolith over microservices

**Decision.** Ship one deployable FastAPI service with strict internal layering
(controller → service → repository), rather than one service per entity.

**Context.** NFR 2.4 (Transactions) requires ACID semantics across the
order/invoice/payment aggregates: issuing an invoice must move the order to
`INVOICED` and write the invoice row atomically. NFR 1.1 and 1.2 apply
uniformly to all traffic.

**Alternatives considered.**
1. *Microservice per entity.* Rejected: the invoice→order and payment→order
   steps would become distributed transactions needing sagas plus compensating
   actions. That trades a guarantee the prompt asks for (ACID) for scaling we do
   not need at "non-trivial" — not internet-scale — traffic.
2. *Serverless functions per endpoint.* Rejected: per-invocation cold starts
   defeat the shared connection pooling that the rate limiter and cache rely on,
   and a token bucket in a stateless function needs an external store on every
   call anyway.

**Consequences.** One deploy unit, one transaction manager, trivially consistent
reads. The whole service scales as a block; a future extraction of, say,
payments would require reintroducing the saga machinery avoided here. Layer
boundaries are enforced by convention and review, not by process isolation.

---

## ADR-002 — Postgres streaming replication + Redis, for one NFR each half

**Decision.** Satisfy NFR 1.2 with two mechanisms at once: physical streaming
replication to a hot standby, *and* a read-through Redis cache.

**Context.** NFR 1.2 names replication and caching as the two common ways to
maintain multiple copies. NFR 2.3 requires comparing active and standby state —
which presupposes a real standby, not a simulated one.

**Alternatives considered.**
1. *Cache only.* Rejected: a cache is not a durable second copy, and with no
   standby there is nothing for NFR 2.3's resynchronization sweep to compare
   against.
2. *Logical replication.* Rejected: per-table publication adds DDL coordination
   and does not expose `pg_stat_replication.sent_lsn - replay_lsn`, the
   byte-accurate lag signal the resync sweep reports.
3. *Application-level dual writes.* Rejected: dual writes are not atomic, so a
   crash between the two writes silently produces exactly the divergence NFR 2.3
   exists to prevent.

**Consequences.** Real, observable replication with genuine lag measurement, at
the cost of a second Postgres container and asynchronous (not synchronous)
replication — the standby may trail the primary by a bounded amount, which the
sweep surfaces rather than hides. Reads from the replica are eventually
consistent; the write path always reads the primary under lock.

---

## ADR-003 — Pydantic annotated types as the single validation authority

**Decision.** Encode every rule in the Field Constraint Table as a reusable
annotated type in `app/domain/validators.py`, composed into DTOs, with matching
`CHECK` constraints in the database schema.

**Context.** The table is the authoritative source for BVA/EP test design, so
boundaries must hold exactly — no silent rounding, truncation, or relaxation.

**Alternatives considered.**
1. *Hand-written `if` checks per controller.* Rejected: the same rule (2dp money,
   dd/MM/yyyy dates) recurs across four entities; duplicating it guarantees the
   copies drift, and the prompt explicitly asks for extracted shared behaviour.
2. *JSON Schema validation at the gateway.* Rejected: JSON Schema cannot express
   the semantic rules — "reject 31/02/2026", "amount must equal the invoice
   total", "no duplicate productRef" — so a second validation layer would be
   needed regardless.

**Consequences.** One place to change a rule, and the constraint is enforced at
both the API boundary and in the database. The cost is that `\p{L}` from the
table has no stdlib `re` equivalent, so the two unicode-letter rules are
enforced by explicit character-wise validators (`str.isalpha()` is the faithful
`\p{L}` equivalent) rather than by a literal regex — documented inline where it
happens.

**Notable consequence — money as strings.** Monetary fields accept and emit
strings (`"129.99"`), and JSON floats are rejected outright, because
IEEE-754 cannot represent `10.005` exactly and would let a 3-decimal value slip
through as 2. This is visible in the API contract.

---

## ADR-004 — Rate limiting in Redis, failing open

**Decision.** Implement NFR 1.1 as a Redis-backed token bucket driven by an
atomic Lua script; when Redis is unreachable the limiter admits the request.

**Context.** The API runs 4 uvicorn workers, so a per-process bucket would
enforce 4× the intended ceiling. NFR 2.2 requires critical functions to survive
component failure.

**Alternatives considered.**
1. *In-process bucket.* Rejected: the effective limit becomes worker-count
   dependent and resets on every restart.
2. *Fixed-window counter.* Rejected: allows a 2× burst across a window boundary,
   so the "set maximum rate" is not actually held.
3. *Fail closed when Redis is down.* Rejected: it converts a cache outage into a
   total outage, directly contradicting NFR 2.2. Rate limiting is a protection
   tactic, not a correctness one — see the trade-off below.

**Consequences.** The ceiling holds globally and survives restarts. The accepted
risk is explicit: during a Redis outage the service is unprotected from
overload. That is the deliberate trade — availability of the critical path over
strict enforcement of a protective limit — and the outage is visible at
`GET /health/ready` so an operator can act.

---

## ADR-005 — Explicit 400 for malformed ids, overriding FastAPI's 422

**Decision.** Parse path ids through a custom dependency
(`app/api/deps.py::parse_entity_id`) and map body validation failures to 400 via
an exception handler, instead of using FastAPI's `UUID` converter.

**Context.** Implementation note 2 and the `TC_*_ID_*` cases require 400 for a
malformed reference and 404 for a well-formed but non-existent one. FastAPI
answers 422 for both by default.

**Alternatives considered.**
1. *Accept 422 and adjust the tests.* Rejected: the harness is pre-existing and
   the prompt treats any mismatch as a defect — the contract is the fixed point
   here, not the framework default.
2. *Catch `RequestValidationError` only.* Rejected: insufficient on its own,
   because the path converter rejects the value before the handler is reached.

**Consequences.** The three-step FK validation (400 malformed → 404 absent → 409
wrong state) is uniform across all five entities and verified end-to-end. The
cost is a small deviation from FastAPI idiom, which is confined to one
dependency and one handler.

---

## ADR-006 — Pessimistic row locks plus an optimistic version column

**Decision.** Every state transition takes `SELECT … FOR UPDATE` on the
aggregate row, and mutable aggregates additionally carry a `version` column
checked on write.

**Context.** NFR 2.4 requires isolation. Two concurrent `/accept` calls on one
order, or two payments against one invoice, must not both succeed.

**Alternatives considered.**
1. *Optimistic locking alone.* Rejected: the loser learns only at commit time,
   after the workflow side effects have been computed, and must retry the whole
   step.
2. *`SERIALIZABLE` isolation globally.* Rejected: pushes serialization failures
   into every read-only path and costs throughput the NFR 1.1 budget assumes.
3. *Application-level mutex (Redis lock).* Rejected: correctness of the write
   path would then depend on the cache being up, which ADR-004 explicitly
   refuses to allow.

**Consequences.** Conflicting transitions serialize at the database and the
loser gets a clean 409 before doing work. Locks are held only for the duration
of one short transaction. Deadlock risk is bounded by always acquiring
order→payment→invoice locks in a consistent sequence.
