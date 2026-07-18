# ADR-005: Atomic Multi-Entity Transactions via Deferred Commit

**Date:** 2025-01-01
**Status:** Accepted

## Decision

`OrderService.transition_status` accepts a `commit: bool = True` parameter.
When `commit=False`, the method performs the status update and flushes to the
session but does not commit. Callers that need to group multiple entity writes
into a single atomic transaction (e.g. payment verification also flips the
order and invoice status) pass `commit=False` and commit the shared session
themselves once all side-effects succeed.

## Context

**NFRs addressed:** NFR 2.3 (State Preservation — data consistency), NFR 2.2
(Fault Detection and Recovery — no partial state).

Several workflow steps touch multiple entities atomically:
- **Invoice creation:** create invoice → link to order → transition order to
  INVOICED. If the transition commits separately and fails, the order is left
  ACCEPTED with a dangling invoice.
- **Payment verification:** payment → VERIFIED, order → PAID, invoice → PAID.
  If the order transition commits first and the invoice update fails, the order
  is PAID but the invoice remains ISSUED, creating an inconsistency that the
  overdue cron would later flag incorrectly.

## Alternatives Considered

1. **Distributed saga with compensating transactions** — Each step commits
   independently; on failure, compensating actions undo prior steps. Rejected
   because the OMS uses a single SQLite database (no distributed data stores),
   so a saga adds unnecessary complexity. Local transactions are sufficient.

2. **Unit-of-work pattern with explicit transaction context manager** — Wrap
   multi-entity operations in an explicit `async with session.begin():` block.
   Rejected because it would require restructuring every service method to
   accept an externally-managed transaction, breaking the current clean
   per-method API. The `commit` parameter is a lighter-weight approach that
   achieves the same atomicity.

3. **Always commit in the outermost caller, never in services** — Move all
   commit responsibility to controllers. Rejected because it scatters
   transaction boundaries across the HTTP layer and makes services
   non-reusable outside of HTTP contexts (e.g. background workers, recovery).

## Consequences

- **Accepted:** Callers must remember to commit when using `commit=False`.
  This is documented in the method docstring and used in exactly two places
  (`InvoiceService.create_invoice`, `PaymentService.verify_payment`).
- **Benefit:** Multi-entity workflow steps are now truly atomic — either all
  writes commit together or none do, preventing partial/inconsistent state.
- **Trade-off:** The `commit` parameter adds a small amount of conditional
  logic to `transition_status`, but it is a single `if commit:` check.