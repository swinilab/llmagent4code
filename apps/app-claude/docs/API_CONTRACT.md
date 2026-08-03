# OrderMan - API Contract

Base URL: `http://localhost:8080`
API base path: `/api/v1`

This catalog is an **invocation contract**: it tells an external consumer how to
call every operation and what to expect back. Where it appears to conflict with
the generation prompt's Field Constraint Tables, workflow rules, or status-code
rules, those remain authoritative.

All examples below were captured from the running application.

---

## 1. Endpoint inventory

| Operation ID | Actor | Method | Path | Purpose | Preconditions | Success status | Error statuses |
|---|---|---|---|---|---|---|---|
| `createCustomer` | Customer | POST | `/api/v1/customers` | Register a customer | none | 201 | 400, 429, 503, 504 |
| `getCustomer` | any | GET | `/api/v1/customers/{id}` | Retrieve a customer with derived order history | customer exists | 200 | 400, 404, 429, 503, 504 |
| `createProduct` | Order Staff | POST | `/api/v1/products` | Create a product | none | 201 | 400, 429, 503, 504 |
| `getProduct` | any | GET | `/api/v1/products/{id}` | Retrieve a product (served from maintained copy) | product exists | 200 | 400, 404, 429, 503, 504 |
| `searchProducts` | any | GET | `/api/v1/products?query={text}` | Search products by description substring | none | 200 | 400, 429, 503, 504 |
| `createOrder` | Customer | POST | `/api/v1/orders` | Place an order (workflow step 1) | customer and all products exist | 201 | 400, 404, 409, 429, 503, 504 |
| `getOrder` | any | GET | `/api/v1/orders/{id}` | Retrieve an order | order exists | 200 | 400, 404, 429, 503, 504 |
| `acceptOrder` | Order Staff | POST | `/api/v1/orders/{id}/accept` | Accept an order (step 2) | order status `PLACED` | 200 | 400, 404, 409, 429, 503, 504 |
| `createInvoice` | Accountant | POST | `/api/v1/invoices` | Issue an invoice (step 3) | order status `ACCEPTED` | 201 | 400, 404, 409, 429, 503, 504 |
| `getInvoice` | any | GET | `/api/v1/invoices/{id}` | Retrieve an invoice | invoice exists | 200 | 400, 404, 429, 503, 504 |
| `createPayment` | Customer | POST | `/api/v1/payments` | Submit a payment (step 4) | order status `INVOICED`; amount equals invoice total | 201 | 400, 404, 409, 429, 503, 504 |
| `getPayment` | any | GET | `/api/v1/payments/{id}` | Retrieve a payment | payment exists | 200 | 400, 404, 429, 503, 504 |
| `verifyPayment` | Accountant | POST | `/api/v1/payments/{id}/verify` | Verify a payment (step 5) | payment status `PENDING`; order status `PAID` | 200 | 400, 404, 409, 429, 500, 503, 504 |
| `shipOrder` | Order Staff | POST | `/api/v1/orders/{id}/ship` | Ship an order (step 6) | order status `VERIFIED` | 200 | 400, 404, 409, 429, 503, 504 |
| `closeOrder` | Order Staff | POST | `/api/v1/orders/{id}/close` | Close an order (step 7) | order status `SHIPPED` | 200 | 400, 404, 409, 429, 503, 504 |
| `healthLive` | operator | GET | `/health/live` | Liveness probe | none | 200 | - |
| `healthReady` | operator | GET | `/health/ready` | Readiness probe | none | 200 | 503 |
| `getMetrics` | operator | GET | `/internal/metrics` | Runtime counters | none | 200 | - |
| `getAdmissionState` | operator | GET | `/internal/admission` | Admission-control state and peak concurrency | none | 200 | - |
| `resetTestState` | test client | POST | `/internal/test/reset` | Reset counters, cache, injected faults | `ENABLE_TEST_HOOKS=true` | 204 | 404 |

The five observation paths (`/health/live`, `/health/ready`, `/internal/metrics`,
`/internal/admission`, `/internal/test/reset`) bypass admission control, never
consume an admitted slot, are never delayed by `X-Test-Delay-Ms`, and require no
database round-trip. `/health/ready` is the sole exception in *content*: it
reports `503` while the database is unreachable, but still answers promptly.

---

## 2. Error envelope

Every controlled failure carries:

```json
{
  "error": {
    "code": "<code>",
    "message": "<human-readable description>"
  }
}
```

| Code | Meaning | Typical status |
|---|---|---|
| `VALIDATION_ERROR` | Malformed syntax, missing required field, or field-constraint violation | 400 |
| `NOT_FOUND` | Valid identifier but no such resource | 404 |
| `STATE_CONFLICT` | Invalid workflow transition or referential-state conflict | 409 |
| `OVERLOAD_REJECTED` | Admission control refused the request; in-flight limit reached | 429 |
| `DEPENDENCY_TIMEOUT` | A database operation exceeded its per-attempt limit and the bounded retry policy was exhausted | 504 |
| `DEPENDENCY_UNAVAILABLE` | The database could not be reached, or a write was refused because durable state is unavailable | 503 |
| `TRANSACTION_FAILED` | A transaction was rolled back due to an internal fault | 500 |

---

## 3. Request/response contracts

### 3.1 `createCustomer` - POST `/api/v1/customers`

Request:

```json
{
  "name": "Ada Lovelace",
  "address": "12 Analytical Engine Road, London",
  "phone": "+442071234567",
  "bankingDetails": {"accountNumber": "123456789012", "bankName": "Bank of Example"},
  "role": "CUSTOMER"
}
```

Response `201`:

```json
{
  "id": "2e791810-b600-4796-8238-792290d31ce0",
  "name": "Ada Lovelace",
  "address": "12 Analytical Engine Road, London",
  "phone": "+442071234567",
  "bankingDetails": {"accountNumber": "123456789012", "bankName": "Bank of Example"},
  "role": "CUSTOMER",
  "orderHistory": []
}
```

**Server-generated / ignored:** `id` and `orderHistory` are server-derived. Supplying
either is rejected with `400` (unknown keys are forbidden, not ignored).
`role` is fixed at creation and immutable thereafter.

**Side effects:** a Customer row is created. Banking account numbers are never logged.

| Error case | Condition | Status | Response |
|---|---|---|---|
| Name too short | `name` length < 2 | 400 | `{"error":{"code":"VALIDATION_ERROR","message":"name: Value error, name must be between 2 and 100 characters"}}` |
| Name has digits | violates `^[\p{L} .'-]+$` | 400 | `VALIDATION_ERROR` |
| Phone not E.164 | violates `^\+?[1-9]\d{7,14}$` | 400 | `VALIDATION_ERROR` |
| Account number non-numeric | violates `^\d{6,20}$` | 400 | `VALIDATION_ERROR` |
| Invalid role | not in the allow-list (case-sensitive) | 400 | `VALIDATION_ERROR` |
| Client supplies `id` | read-only field | 400 | `VALIDATION_ERROR` |

### 3.2 `createProduct` - POST `/api/v1/products`

Request:

```json
{"description": "Mechanical keyboard, 87 keys", "price": {"amount": "19.99", "currency": "USD"}}
```

Response `201`:

```json
{
  "id": "3f8a2c14-9b7d-4e51-8c30-1a2b3c4d5e6f",
  "description": "Mechanical keyboard, 87 keys",
  "price": {"amount": "19.99", "currency": "USD"}
}
```

**Notes:** `price.amount` must be sent as a **string** with exactly two decimal
places. A JSON float is rejected with `400` rather than rounded, because binary
floating point cannot represent money exactly.

| Error case | Condition | Status |
|---|---|---|
| Amount below minimum | `"0.00"` (< 0.01) | 400 |
| Amount above maximum | `"1000000.00"` (> 999999.99) | 400 |
| Wrong precision | `"19.9"` or `"0.001"` | 400 |
| Float amount | `19.999` | 400 |
| Unsupported currency | `"GBP"`, or lowercase `"usd"` | 400 |
| Description too short | length < 3 | 400 |

### 3.3 `getProduct` - GET `/api/v1/products/{id}`

Response `200`: as in 3.2.

Served from the maintained cached copy when one is fresh. A Product modified
directly in the database is not visible through this endpoint until the copy
expires (`CACHE_TTL_SECONDS`). During a database outage a previously warmed
Product is still served from its retained copy; a never-read Product returns
`503` with `DEPENDENCY_UNAVAILABLE`.

| Error case | Condition | Status | Response |
|---|---|---|---|
| Malformed UUID | `/api/v1/products/not-a-uuid` | 400 | `{"error":{"code":"VALIDATION_ERROR","message":"path.id: Input should be a valid UUID, ..."}}` |
| Unknown UUID | valid UUID, no such row | 404 | `{"error":{"code":"NOT_FOUND","message":"Product <id> was not found"}}` |

### 3.4 `createOrder` - POST `/api/v1/orders`

Request:

```json
{
  "customerRef": "2e791810-b600-4796-8238-792290d31ce0",
  "lineItems": [{"productRef": "3f8a2c14-9b7d-4e51-8c30-1a2b3c4d5e6f", "quantity": 2}]
}
```

Response `201`:

```json
{
  "id": "7c1e5a90-2d34-4f68-9b0a-5e6f7a8b9c0d",
  "customerRef": "2e791810-b600-4796-8238-792290d31ce0",
  "lineItems": [
    {"productRef": "3f8a2c14-9b7d-4e51-8c30-1a2b3c4d5e6f", "quantity": 2, "unitPriceSnapshot": "19.99"}
  ],
  "totalAmount": "39.98",
  "status": "PLACED",
  "createdAt": "2026-08-03T02:22:31.482911Z",
  "updatedAt": "2026-08-03T02:22:31.482911Z",
  "invoiceRef": null
}
```

**Server-computed:** `unitPriceSnapshot` is copied from the product's current
price, and `totalAmount` is the sum of `quantity x unitPriceSnapshot`. Supplying
either is rejected with `400`. `status` always starts at `PLACED`.

**State change:** creates the Order and its line items in one transaction.

| Error case | Condition | Status |
|---|---|---|
| Duplicate `productRef` | same product twice in one order | 400 (not merged) |
| Quantity out of range | `0`, `-1`, or `1001` | 400 |
| Empty `lineItems` | fewer than 1 item | 400 |
| More than 100 items | above the maximum | 400 |
| Client supplies `totalAmount` | computed field | 400 |
| Unknown `customerRef` | valid UUID, no such customer | 404 |
| Unknown `productRef` | valid UUID, no such product | 404 |

### 3.5 `acceptOrder` - POST `/api/v1/orders/{id}/accept`

No request body. Response `200` returns the Order with `status: "ACCEPTED"`.

| Error case | Condition | Status |
|---|---|---|
| Wrong source state | order not `PLACED` (e.g. already accepted) | 409 |
| Unknown order | valid UUID, no such order | 404 |
| Malformed UUID | non-UUID path segment | 400 |

### 3.6 `createInvoice` - POST `/api/v1/invoices`

Request (dates optional):

```json
{"orderRef": "7c1e5a90-2d34-4f68-9b0a-5e6f7a8b9c0d"}
```

Response `201`:

```json
{
  "id": "b2c3d4e5-f6a7-4890-b1c2-d3e4f5a6b7c8",
  "orderRef": "7c1e5a90-2d34-4f68-9b0a-5e6f7a8b9c0d",
  "billingInfo": {"name": "Ada Lovelace", "address": "12 Analytical Engine Road, London"},
  "totalAmount": "39.98",
  "issueDate": "03/08/2026",
  "dueDate": "10/08/2026",
  "status": "ISSUED"
}
```

**Defaults:** `issueDate` defaults to the server's current date; `dueDate`
defaults to `issueDate + 7 days`. `billingInfo` is snapshotted from the Customer
at issue time, not held as a live reference. `totalAmount` equals the Order total.

**State change (one transaction):** Invoice created as `ISSUED`, Order becomes
`INVOICED`, and `Order.invoiceRef` is set.

| Error case | Condition | Status |
|---|---|---|
| Order not accepted | order status is not `ACCEPTED` | 409 |
| Invalid calendar date | `"31/02/2026"` - passes the regex, not a real date | 400 |
| Wrong date format | `"2026-08-01"` or `"1/8/2026"` | 400 |
| `dueDate` before `issueDate` | violates the ordering rule | 400 |
| Unknown order | valid UUID, no such order | 404 |

### 3.7 `createPayment` - POST `/api/v1/payments`

Request:

```json
{"orderRef": "7c1e5a90-2d34-4f68-9b0a-5e6f7a8b9c0d", "amount": "39.98", "method": "CREDIT_CARD"}
```

Response `201`:

```json
{
  "id": "c3d4e5f6-a7b8-4901-c2d3-e4f5a6b7c8d9",
  "orderRef": "7c1e5a90-2d34-4f68-9b0a-5e6f7a8b9c0d",
  "amount": "39.98",
  "timestamp": "2026-08-03T02:22:33.104227Z",
  "status": "PENDING",
  "method": "CREDIT_CARD"
}
```

**State change (one transaction):** Payment created as `PENDING`, Order becomes
`PAID`. This pairing is intentional - see section 5.

| Error case | Condition | Status |
|---|---|---|
| Order not invoiced | order status is not `INVOICED` | 409 |
| Partial payment | amount less than invoice total | 409 |
| Over payment | amount greater than invoice total | 409 |
| Invalid method | not in the allow-list (case-sensitive) | 400 |
| Wrong precision | `"39.9"` | 400 |

### 3.8 `verifyPayment` - POST `/api/v1/payments/{id}/verify`

No request body. Response `200` returns the Payment with `status: "VERIFIED"`.

**State change (one atomic transaction):** Payment becomes `VERIFIED`, Invoice
becomes `PAID`, Order becomes `VERIFIED`. All three updates commit together or
none does.

| Error case | Condition | Status | Response |
|---|---|---|---|
| Payment already verified | payment not `PENDING` | 409 | `STATE_CONFLICT` |
| Injected transaction fault | `X-Test-Fault: after-payment-update` | 500 | `{"error":{"code":"TRANSACTION_FAILED","message":"The transaction was rolled back; no partial state was committed."}}` |
| Unknown payment | valid UUID, no such payment | 404 | `NOT_FOUND` |

### 3.9 `shipOrder` / `closeOrder`

No request bodies. `shipOrder` requires `VERIFIED` and yields `SHIPPED`;
`closeOrder` requires `SHIPPED` and yields `CLOSED`. Any other source state
returns `409`.

### 3.10 Observability operations

`GET /internal/metrics` returns exactly:

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

`GET /internal/admission` returns `max_in_flight_requests`, `in_flight`, and
`peak_in_flight` (the peak recorded by the admission controller since the last
reset).

`POST /internal/test/reset` returns `204` and resets counters, the cache, the
admission peak, and injected-fault state. It never deletes business data and
makes no database round-trip. When `ENABLE_TEST_HOOKS=false` it returns `404`.

---

## 4. Deterministic test headers

Honoured only when `ENABLE_TEST_HOOKS=true`.

| Header | Effect |
|---|---|
| `X-Test-Delay-Ms: <int>` | Delays execution after admission, while holding the admitted slot. Honoured on every public business endpoint; observation paths are exempt. |
| `X-Test-Fault: transient-db-failures=2` | Injects exactly two transient failures at the real Product database-read boundary before the third attempt reaches PostgreSQL. |
| `X-Test-Fault: after-payment-update` | Raises inside the real payment-verification transaction after the Payment update, before the Invoice and Order updates and before commit. |

`X-Test-Fault` carries exactly one directive per request. An unrecognized,
malformed, or out-of-range value in either header is **ignored silently**: the
request proceeds as if the header were absent and returns whatever status it
otherwise would. A bad test header never produces `400`.

---

## 5. Seven-step workflow example

Using symbolic identifiers `customerId`, `productId`, `orderId`, `invoiceId`,
`paymentId`:

| Step | Actor | Request | Expected status | Resulting state |
|---|---|---|---|---|
| 0a | Customer | `POST /api/v1/customers` | 201 | `customerId` created |
| 0b | Order Staff | `POST /api/v1/products` | 201 | `productId` created |
| 1 | Customer | `POST /api/v1/orders` with `customerRef=customerId`, one line item `productRef=productId` | 201 | Order `PLACED` |
| 2 | Order Staff | `POST /api/v1/orders/{orderId}/accept` | 200 | Order `ACCEPTED` |
| 3 | Accountant | `POST /api/v1/invoices` with `orderRef=orderId` | 201 | Invoice `ISSUED`; Order `INVOICED`; `invoiceRef` set |
| 4 | Customer | `POST /api/v1/payments` with `orderRef=orderId`, `amount` = invoice total | 201 | Payment `PENDING`; **Order `PAID`** |
| 5 | Accountant | `POST /api/v1/payments/{paymentId}/verify` | 200 | Payment `VERIFIED`; Invoice `PAID`; Order `VERIFIED` (atomic) |
| 6 | Order Staff | `POST /api/v1/orders/{orderId}/ship` | 200 | Order `SHIPPED` |
| 7 | Order Staff | `POST /api/v1/orders/{orderId}/close` | 200 | Order `CLOSED` |

**Note on step 4.** After step 4 the Order is `PAID` while the Payment is still
`PENDING`. This is correct and intentional: the Order status reflects that
payment was submitted, while the Payment status reflects that an accountant has
not yet verified it. A rollback during step 5 restores exactly this state.

**Order state machine.** `PLACED -> ACCEPTED -> INVOICED -> PAID -> VERIFIED ->
SHIPPED -> CLOSED`, with `CANCELLED` reachable from any state before `SHIPPED`.
Every transition not on this path returns `409`.

---

## 6. Functional-correctness scenario matrix

| Scenario ID | Operation ID | Preconditions | Input partition/boundary | Expected status | Expected body assertions | Expected state after call |
|---|---|---|---|---|---|---|
| FC-01 | `createCustomer` | none | all fields valid | 201 | `id` present; `orderHistory` empty | Customer exists |
| FC-02 | `createCustomer` | none | `name` length 2 (min boundary) | 201 | echoes name | Customer exists |
| FC-03 | `createCustomer` | none | `name` length 100 (max boundary) | 201 | echoes name | Customer exists |
| FC-04 | `createCustomer` | none | `name` length 1 (below min) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-05 | `createCustomer` | none | `name` length 101 (above max) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-06 | `createCustomer` | none | `phone` starts with 0 | 400 | `code=VALIDATION_ERROR` | no change |
| FC-07 | `createCustomer` | none | `accountNumber` 5 digits (below min) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-08 | `createCustomer` | none | `accountNumber` 21 digits (above max) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-09 | `createCustomer` | none | missing required `phone` | 400 | `code=VALIDATION_ERROR` | no change |
| FC-10 | `createCustomer` | none | `role="customer"` (wrong case) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-11 | `createCustomer` | none | client supplies `id` | 400 | `code=VALIDATION_ERROR` | no change |
| FC-12 | `createCustomer` | none | client supplies `orderHistory` | 400 | `code=VALIDATION_ERROR` | no change |
| FC-13 | `createProduct` | none | valid product | 201 | `price.amount` echoed as string | Product exists |
| FC-14 | `createProduct` | none | `amount="0.01"` (min boundary) | 201 | `amount="0.01"` | Product exists |
| FC-15 | `createProduct` | none | `amount="999999.99"` (max boundary) | 201 | `amount="999999.99"` | Product exists |
| FC-16 | `createProduct` | none | `amount="0.00"` (below min) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-17 | `createProduct` | none | `amount="1000000.00"` (above max) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-18 | `createProduct` | none | `amount="0.001"` (3 dp) | 400 | rejected, not rounded | no change |
| FC-19 | `createProduct` | none | `amount=19.999` (JSON float) | 400 | rejected, not rounded | no change |
| FC-20 | `createProduct` | none | `currency="GBP"` (unsupported) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-21 | `createProduct` | none | `description` length 2 (below min) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-22 | `getProduct` | none | malformed UUID | 400 | `code=VALIDATION_ERROR` | no change |
| FC-23 | `getProduct` | none | valid but unknown UUID | 404 | `code=NOT_FOUND` | no change |
| FC-24 | `createOrder` | customer + product exist | one line item, quantity 2 | 201 | `totalAmount` = 2 x price; `status=PLACED` | Order `PLACED` |
| FC-25 | `createOrder` | customer + product exist | quantity 1 (min boundary) | 201 | accepted | Order `PLACED` |
| FC-26 | `createOrder` | customer + product exist | quantity 1000 (max boundary) | 201 | accepted | Order `PLACED` |
| FC-27 | `createOrder` | customer + product exist | quantity 0 (below min) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-28 | `createOrder` | customer + product exist | quantity 1001 (above max) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-29 | `createOrder` | customer + product exist | duplicate `productRef` | 400 | rejected, not merged | no change |
| FC-30 | `createOrder` | customer + product exist | empty `lineItems` | 400 | `code=VALIDATION_ERROR` | no change |
| FC-31 | `createOrder` | product exists | unknown `customerRef` (FK not found) | 404 | `code=NOT_FOUND` | no change |
| FC-32 | `createOrder` | customer exists | unknown `productRef` (FK not found) | 404 | `code=NOT_FOUND` | no change |
| FC-33 | `createOrder` | customer + product exist | client supplies `totalAmount` | 400 | `code=VALIDATION_ERROR` | no change |
| FC-34 | `createOrder` | customer + product exist | client supplies `unitPriceSnapshot` | 400 | `code=VALIDATION_ERROR` | no change |
| FC-35 | `acceptOrder` | Order `PLACED` | valid transition | 200 | `status=ACCEPTED` | Order `ACCEPTED` |
| FC-36 | `acceptOrder` | Order `ACCEPTED` | repeat transition | 409 | `code=STATE_CONFLICT` | unchanged |
| FC-37 | `shipOrder` | Order `PLACED` | illegal transition | 409 | `code=STATE_CONFLICT` | unchanged |
| FC-38 | `closeOrder` | Order `PLACED` | illegal transition | 409 | `code=STATE_CONFLICT` | unchanged |
| FC-39 | `createInvoice` | Order `ACCEPTED` | valid | 201 | `status=ISSUED`; total equals order total | Invoice `ISSUED`; Order `INVOICED` |
| FC-40 | `createInvoice` | Order `PLACED` | reference in wrong workflow state | 409 | `code=STATE_CONFLICT` | unchanged |
| FC-41 | `createInvoice` | Order `ACCEPTED` | `issueDate="31/02/2026"` (invalid calendar date) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-42 | `createInvoice` | Order `ACCEPTED` | `issueDate="2026-08-01"` (wrong format) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-43 | `createInvoice` | Order `ACCEPTED` | `dueDate` before `issueDate` | 400 | `code=VALIDATION_ERROR` | no change |
| FC-44 | `createInvoice` | Order `ACCEPTED` | dates omitted | 201 | `dueDate = issueDate + 7 days` | Invoice `ISSUED` |
| FC-45 | `createPayment` | Order `INVOICED` | amount equals invoice total | 201 | `status=PENDING` | Payment `PENDING`; Order `PAID` |
| FC-46 | `createPayment` | Order `INVOICED` | amount below invoice total | 409 | `code=STATE_CONFLICT` | no change |
| FC-47 | `createPayment` | Order `INVOICED` | amount above invoice total | 409 | `code=STATE_CONFLICT` | no change |
| FC-48 | `createPayment` | Order `PLACED` | reference in wrong workflow state | 409 | `code=STATE_CONFLICT` | no change |
| FC-49 | `createPayment` | Order `INVOICED` | `method="credit_card"` (wrong case) | 400 | `code=VALIDATION_ERROR` | no change |
| FC-50 | `verifyPayment` | Payment `PENDING`, Order `PAID` | valid | 200 | `status=VERIFIED` | Payment `VERIFIED`; Invoice `PAID`; Order `VERIFIED` |
| FC-51 | `verifyPayment` | Payment `VERIFIED` | repeat verification | 409 | `code=STATE_CONFLICT` | unchanged |
| FC-52 | `verifyPayment` | Payment `PENDING` | `X-Test-Fault: after-payment-update` | 500 | `code=TRANSACTION_FAILED` | Payment `PENDING`; Invoice `ISSUED`; Order `PAID` (full rollback) |
| FC-53 | `shipOrder` | Order `VERIFIED` | valid | 200 | `status=SHIPPED` | Order `SHIPPED` |
| FC-54 | `closeOrder` | Order `SHIPPED` | valid | 200 | `status=CLOSED` | Order `CLOSED` (final state) |
| FC-55 | `getCustomer` | customer has orders | derived field | 200 | `orderHistory` contains the order ids | unchanged |
| FC-56 | `getMetrics` | none | always | 200 | exactly the nine integer counters | unchanged |
| FC-57 | `resetTestState` | `ENABLE_TEST_HOOKS=true` | always | 204 | empty body | counters and cache cleared; business data intact |

Final states after the complete workflow: `Order.status=CLOSED`,
`Payment.status=VERIFIED`, `Invoice.status=PAID`.

---

## 7. Cross-artifact consistency

The following artifacts describe the same contract and are kept in agreement:

- `openapi.json` (exported from the live app by `scripts/export_openapi.py`)
- runtime `/openapi.json`, `/docs` (Swagger UI), `/redoc` (ReDoc)
- `create_apis.json`
- `workflow_apis.json`
- this document
- the actual running routes

`openapi.json` is never hand-edited. Re-run `python scripts/export_openapi.py`
after any route change.
