# API contract — reference application

Enough to drive the workflow and the six scenarios. This application calibrates
the evaluator rather than being evaluated by it, so the full endpoint catalogue
a study submission owes is deliberately not reproduced here.

## Endpoint inventory

| Operation ID | Actor | Method | Path | Purpose | Preconditions | Success | Errors |
|---|---|---|---|---|---|---|---|
| createCustomer | Customer | POST | `/api/v1/customers` | Register a customer | — | 201 | 400 |
| getCustomer | any | GET | `/api/v1/customers/{id}` | Read a customer | exists | 200 | 400, 404 |
| createProduct | Order Staff | POST | `/api/v1/products` | Add a product | — | 201 | 400 |
| getProduct | any | GET | `/api/v1/products/{id}` | Read a product, through the cache | exists | 200 | 400, 404, 503, 504 |
| searchProducts | any | GET | `/api/v1/products?query=` | Search, through admission control | — | 200 | 429, 503 |
| createOrder | Customer | POST | `/api/v1/orders` | Place an order | customer and products exist | 201 | 400, 404 |
| getOrder | any | GET | `/api/v1/orders/{id}` | Read an order | exists | 200 | 400, 404 |
| acceptOrder | Order Staff | POST | `/api/v1/orders/{id}/accept` | PLACED to ACCEPTED | order is PLACED | 200 | 404, 409 |
| createInvoice | Accountant | POST | `/api/v1/invoices` | Issue an invoice | order is ACCEPTED | 201 | 400, 404, 409 |
| getInvoice | any | GET | `/api/v1/invoices/{id}` | Read an invoice | exists | 200 | 400, 404 |
| createPayment | Customer | POST | `/api/v1/payments` | Submit a payment | order is INVOICED, amount exact | 201 | 400, 404, 409 |
| getPayment | any | GET | `/api/v1/payments/{id}` | Read a payment | exists | 200 | 400, 404 |
| verifyPayment | Accountant | POST | `/api/v1/payments/{id}/verify` | Verify atomically | payment is PENDING | 200 | 404, 409, 500 |
| shipOrder | Order Staff | POST | `/api/v1/orders/{id}/ship` | VERIFIED to SHIPPED | order is VERIFIED | 200 | 404, 409 |
| closeOrder | Order Staff | POST | `/api/v1/orders/{id}/close` | SHIPPED to CLOSED | order is SHIPPED | 200 | 404, 409 |
| healthLive | — | GET | `/health/live` | Process liveness | — | 200 | — |
| healthReady | — | GET | `/health/ready` | Service readiness | — | 200 | 503 |
| internalMetrics | — | GET | `/internal/metrics` | Counters | — | 200 | — |
| internalReset | — | POST | `/internal/test/reset` | Clear counters, cache, faults | test hooks enabled | 204 | 404 |

## Seven-step workflow

```
POST /api/v1/customers                     -> 201  customerId
POST /api/v1/products                      -> 201  productId
POST /api/v1/orders                        -> 201  orderId,   order PLACED
POST /api/v1/orders/{orderId}/accept       -> 200  order ACCEPTED
POST /api/v1/invoices                      -> 201  invoiceId, invoice ISSUED, order INVOICED
POST /api/v1/payments                      -> 201  paymentId, payment PENDING, order PAID
POST /api/v1/payments/{paymentId}/verify   -> 200  payment VERIFIED, invoice PAID, order VERIFIED
POST /api/v1/orders/{orderId}/ship         -> 200  order SHIPPED
POST /api/v1/orders/{orderId}/close        -> 200  order CLOSED
```

After payment submission the order is `PAID` while the payment is still
`PENDING`. This pairing looks inconsistent and is not: the order records that
payment arrived, the payment records that nobody has verified it yet. ASR-A4
restores exactly this state when its transaction rolls back.

## Controlled error responses

Every controlled failure carries `{"error": {"code": ..., "message": ...}}`.

| Code | Status | Meaning |
|---|---|---|
| `DEPENDENCY_TIMEOUT` | 504 | a database operation exceeded its time limit |
| `DEPENDENCY_UNAVAILABLE` | 503 | the database could not be reached, or a write had nowhere durable to land |
| `OVERLOAD_REJECTED` | 429 | admission control refused the request; carries `Retry-After` |
| `TRANSACTION_FAILED` | 500 | a transaction was rolled back after an internal fault |
| `VALIDATION_FAILED` | 400 | malformed input or a field-constraint violation |
| `NOT_FOUND` | 404 | well-formed identifier, no such resource |
| `WORKFLOW_CONFLICT` | 409 | the reference exists but is in the wrong state |

The first two are what let an observer tell a slow dependency from an absent
one; both surface as 5xx, and without the code the timeout and degradation
tactics would be indistinguishable from outside.

## Test headers

Active only when `ENABLE_TEST_HOOKS=true`. An unrecognised value is ignored in
silence — a bad test header must never turn a valid request into an error.

| Header | Effect |
|---|---|
| `X-Test-Delay-Ms: <int>` | delays a product search while it holds its admitted slot |
| `X-Test-Fault: transient-db-failures=2` | fails the first two database-read attempts |
| `X-Test-Fault: after-payment-update` | raises inside the verification transaction, after payment and before invoice and order |
