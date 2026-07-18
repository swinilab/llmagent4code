# ADR-004: Graceful Degradation via Resource-Aware Middleware

**Date:** 2025-01-01
**Status:** Accepted

## Decision

Implement `GracefulDegradationMiddleware` that monitors CPU and memory usage
via `psutil` (non-blocking, `interval=None`). When either resource exceeds a
configured threshold, non-essential endpoints return 503 while core checkout
endpoints continue to be served.

## Context

**NFRs addressed:** NFR 2.1 (Graceful Degradation), NFR 1.1 (Response Time).

Under extreme resource contention (CPU > 85%, memory > 85%), the system must
prioritise core checkout functionality (order creation, payment, invoicing)
over ancillary features (product search). This ensures customers can always
complete purchases even when the server is under heavy load.

## Alternatives Considered

1. **Rate limiting (token bucket per endpoint)** — Limit requests per second per
   endpoint. Rejected because rate limiting does not respond to actual resource
   contention — it applies uniformly regardless of whether the server is
   struggling. A fixed rate limit might reject core checkout traffic while the
   server still has capacity, or fail to protect under genuine contention.

2. **Connection-level backpressure (limit concurrent connections)** — Cap the
   number of simultaneous in-flight requests. Rejected as a standalone solution
   because it does not differentiate between essential and non-essential
   endpoints; all requests would be rejected equally once the limit is hit,
   including core checkout.

3. **Blocking `psutil.cpu_percent(interval=0.5)`** — Rejected because a 500 ms
   blocking call on the ASGI event loop would stall every concurrent request,
   directly violating NFR 1.1 and NFR 1.2. The non-blocking `interval=None`
   variant returns immediately and establishes an internal baseline.

## Consequences

- **Accepted:** Non-essential endpoints (`/api/v1/products/search`) return 503
  with `{"degraded": true}` during contention. Core endpoints
  (`/orders`, `/payments`, `/invoices`, `/customers`) remain fully available.
- **Accepted:** The degradation check runs at most every
  `degradation_check_interval` (default 10s), so there is a brief window where
  the degraded flag may be stale. This is acceptable — the check is cheap and
  the interval is short.
- **Benefit:** Automatic recovery — when resources drop below threshold, the
  middleware lifts degradation and all endpoints are restored. No manual
  intervention required.
- **Trade-off:** `psutil.cpu_percent(interval=None)` requires a priming call at
  startup to establish a baseline; the first read returns 0.0. This is handled in
  `__init__`.