# ADR-002: Circuit Breaker for Payment Gateway Integration

**Date:** 2025-01-01
**Status:** Accepted

## Decision

Implement an async circuit breaker (`CircuitBreaker`) wrapping the payment
gateway call in `PaymentService.create_payment`. The breaker uses a three-state
model: CLOSED → OPEN → HALF_OPEN → CLOSED.

## Context

**NFRs addressed:** NFR 2.2 (Fault Detection and Recovery).

The OMS depends on an external Payment Service Provider (PSP) to validate
payments. If the PSP becomes unavailable or starts returning errors, continuing
to call it would waste resources, increase latency, and cascade failures to
users. The system must detect downstream failures and automatically attempt
recovery without manual intervention.

## Alternatives Considered

1. **Simple retry with exponential backoff** — Retry failed calls a fixed number
   of times with increasing delays. Rejected because retries alone do not stop
   the system from hammering a failing service; under sustained failure, every
   request still incurs the full retry chain, amplifying load on both the OMS
   and the PSP. There is no "open" state to short-circuit calls.

2. **Bulkhead pattern (thread/coroutine isolation)** — Isolate payment calls in
   a dedicated pool so failures don't affect other operations. Rejected as a
   standalone solution because it prevents resource exhaustion but does not
   provide automatic recovery detection or fast-fail behaviour. It complements
   the circuit breaker but does not replace it.

3. **No resilience pattern (fail fast, let user retry)** — Rejected because it
   provides no automatic recovery and degrades user experience; the system would
   keep attempting failing calls indefinitely.

## Consequences

- **Accepted:** When the circuit is OPEN, payment creation raises
  `CircuitBreakerOpenError` immediately (fast-fail), returning a 503 to the
  caller. This prevents cascading failures.
- **Accepted:** After `cb_recovery_timeout` (default 30s), the breaker enters
  HALF_OPEN and allows up to `cb_half_open_max_calls` (default 3) probe calls.
  If all succeed, the circuit closes; if any fails, it re-opens.
- **Benefit:** Automatic recovery — no manual intervention required. The
  `/health/ready` endpoint exposes breaker state for observability.
- **Trade-off:** A small window of rejected calls during HALF_OPEN probing is
  acceptable to validate recovery before fully reopening.