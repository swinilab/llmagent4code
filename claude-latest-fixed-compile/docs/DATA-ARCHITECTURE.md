# Data Architecture

## Narrative

The store is a single normalized Postgres database, replicated to a hot standby
and fronted by a Redis cache. Three properties drive the design:

**Money never loses precision.** Every monetary column is `NUMERIC`, never
`float`, and every monetary field crosses the API as a string. The Field
Constraint Table demands exactly two decimal places with no silent rounding; a
binary float cannot represent `10.005`, so accepting one would quietly turn an
invalid value into a valid-looking `10.00`. `NUMERIC(10,2)` covers product-scale
money (max `999999.99`) and `NUMERIC(12,2)` order-scale money (max
`99999999.99`), matching the table's two regex widths exactly.

**Snapshots are copies, not references.** `unit_price_snapshot` on a line item
and `billing_name`/`billing_address` on an invoice are physically duplicated at
write time rather than joined at read time. This is intentional denormalization:
a later price change or address correction must not retroactively alter an order
already placed or an invoice already issued. The snapshot is the legal record.

**The workflow state lives in one column, guarded twice.** `orders.status` is
constrained by a `CHECK` to the eight legal values, and the legal *transitions*
between them are held in `ORDER_TRANSITIONS` in the domain layer. The database
prevents an impossible value; the service layer prevents an impossible path.

Reads follow a three-tier chain — Redis → replica → primary — degrading at each
hop rather than failing (NFR 1.2 / 2.2). Writes always go to the primary inside
one transaction (NFR 2.4). Cache entries are invalidated on every mutation, and
a background sweep evicts anything that diverges anyway (NFR 2.3).

## Schema

```
customers                          products
─────────────────────────          ─────────────────────────
id              uuid  PK           id              uuid  PK
name            varchar(100)       description     varchar(500)
address         varchar(255)       price_amount    numeric(10,2)
phone           varchar(16)        price_currency  varchar(3)
account_number  varchar(20)        created_at      timestamptz
bank_name       varchar(100)
role            varchar(16)        CHECK price_amount BETWEEN 0.01 AND 999999.99
deleted         boolean            CHECK price_currency IN (USD,VND,EUR)
created_at      timestamptz

CHECK char_length(name) BETWEEN 2 AND 100
CHECK char_length(address) BETWEEN 5 AND 255
CHECK role IN (CUSTOMER,ORDER_STAFF,ACCOUNTANT)
INDEX ix_customers_deleted


orders                                        order_line_items
──────────────────────────────────            ──────────────────────────────────
id            uuid  PK                        id                  uuid  PK
customer_ref  uuid  FK → customers.id         order_id            uuid FK → orders.id CASCADE
total_amount  numeric(12,2)                   product_ref         uuid FK → products.id
status        varchar(16)                     quantity            integer
created_at    timestamptz                     unit_price_snapshot numeric(10,2)
updated_at    timestamptz
invoice_ref   uuid  (→ invoices.id)           CHECK quantity BETWEEN 1 AND 1000
version       integer  (optimistic lock)      CHECK unit_price_snapshot BETWEEN 0.01 AND 999999.99
                                              UNIQUE (order_id, product_ref)   ← no duplicate productRef
CHECK total_amount BETWEEN 0.01 AND 99999999.99
CHECK status IN (PLACED,ACCEPTED,INVOICED,PAID,VERIFIED,SHIPPED,CLOSED,CANCELLED)
CHECK updated_at >= created_at
INDEX ix_orders_customer_ref, ix_orders_status


invoices                                      payments
──────────────────────────────────            ──────────────────────────────────
id               uuid  PK                     id           uuid  PK
order_ref        uuid  FK → orders.id         order_ref    uuid FK → orders.id
billing_name     varchar(100)  ← snapshot     amount       numeric(12,2)
billing_address  varchar(255)  ← snapshot     timestamp    timestamptz
total_amount     numeric(12,2)                status       varchar(16)
issue_date       date                         method       varchar(16)
due_date         date                         version      integer
status           varchar(16)
version          integer                      CHECK amount BETWEEN 0.01 AND 99999999.99
                                              CHECK status IN (PENDING,VERIFIED,REJECTED)
CHECK due_date >= issue_date                  CHECK method IN (CREDIT_CARD,BANK_TRANSFER,E_WALLET)
CHECK status IN (ISSUED,PAID,OVERDUE,CANCELLED)   INDEX ix_payments_order_ref
UNIQUE (order_ref)   ← one invoice per order
INDEX ix_invoices_status
```

## Order state machine

```
   PLACED ──accept──▶ ACCEPTED ──invoice──▶ INVOICED ──pay──▶ PAID
      │                   │                     │               │
      │                   │                     │            verify
      │                   │                     │               ▼
      │                   │                     │           VERIFIED
      │                   │                     │               │
      │                   │                     │             ship
      │                   │                     │               ▼
      │                   │                     │            SHIPPED
      │                   │                     │               │
      │                   │                     │             close
      │                   │                     │               ▼
      ▼                   ▼                     ▼            CLOSED  (terminal)
   CANCELLED ◀────────────┴─────────────────────┘

CANCELLED and CLOSED are terminal. SHIPPED may only be reached from VERIFIED —
i.e. nothing ships until an accountant has verified the payment.
```

`payments`: `PENDING → VERIFIED | REJECTED` (both terminal). A rejection returns
the order to `INVOICED` so the customer can retry.

`invoices`: `ISSUED → PAID | OVERDUE | CANCELLED`, and `OVERDUE → PAID | CANCELLED`.

## Derived and server-owned fields

| Field | Rule |
|---|---|
| `orders.total_amount` | `Σ(quantity × unit_price_snapshot)`, recomputed server-side; a client-supplied value is rejected with 400. |
| `order_line_items.unit_price_snapshot` | Copied from `products.price_amount` at order creation; immutable thereafter. |
| `invoices.billing_*` | Copied from the customer at issue time. |
| `invoices.total_amount` | Copied from the order total at issue time. |
| `invoices.due_date` | Defaults to `issue_date + 7 days`. |
| `orders.status`, `payments.status`, `invoices.status` | Server-owned; the initial value is fixed and clients drive changes only through the workflow endpoints. |
| `customers.order_history` | Derived by query, never stored as a column; capped at 10,000. |
