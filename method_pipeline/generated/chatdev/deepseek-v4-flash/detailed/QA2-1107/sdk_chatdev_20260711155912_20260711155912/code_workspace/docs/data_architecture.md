# Data Architecture

## Schema Overview

The OMS uses PostgreSQL 16 with 7 tables:

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  customers  │────→│     orders       │←────│  payments    │
└─────────────┘     │                  │     └──────────────┘
                    │ status: enum      │
┌─────────────┐     │ version: int (OL) │     ┌──────────────┐
│  products   │────→│ invoice_ref: str  │←────│  invoices    │
└─────────────┘     └──────────────────┘     └──────────────┘
                           │
                    ┌──────┴──────┐
                    │ order_line_  │
                    │   items      │
                    └─────────────┘

┌──────────────────┐
│ outbox_messages  │  (transactional outbox)
└──────────────────┘
```

## Order State-Transition Table

| From | Event | To | Guard | Persistence | Criticality |
|------|-------|----|-------|-------------|-------------|
| CREATED | review_accept | ACCEPTED | Order Staff role | Synchronous | Core |
| ACCEPTED | create_invoice | INVOICED | Accountant role; invoice exists | Synchronous | Core |
| INVOICED | pay | PAID | Payment completed; amount match | Synchronous | Core |
| PAID | ship | SHIPPED | Order Staff role | Synchronous | Core |
| SHIPPED | close | CLOSED | Order Staff role | Synchronous | Core |
| CREATED | cancel | CANCELLED | Any role | Synchronous | Core |
| ACCEPTED | cancel | CANCELLED | Any role | Synchronous | Core |
| INVOICED | cancel | CANCELLED | Any role | Synchronous | Core |
| PAID | cancel | CANCELLED | Any role | Synchronous | Core |
| SHIPPED | cancel | CANCELLED | Any role | Synchronous | Core |

**Durability annotations:**
- **Synchronous (Core):** Written to PostgreSQL within the same transaction as the state change. If the write fails, the entire operation is rolled back. The client receives an error and must retry.
- **Asynchronous (Degradable):** Side-effects (analytics logging, recommendation tracking) are written to the outbox table in the same transaction but delivered asynchronously by the background worker. If the delivery fails, the outbox message remains unprocessed and is retried on the next poll cycle.

## Entity-Relationship Details

### customers
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| name | VARCHAR(255) | NOT NULL |
| address | TEXT | NOT NULL |
| phone | VARCHAR(50) | NOT NULL |
| banking_details | TEXT | NOT NULL |
| role | ENUM(user_role) | NOT NULL, default 'CUSTOMER' |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |
| version | INTEGER | NOT NULL, default 1 |

### products
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| description | TEXT | NOT NULL |
| base_price | FLOAT | NOT NULL |
| currency | ENUM(currency) | NOT NULL, default 'USD' |
| available | BOOLEAN | NOT NULL, default true |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |
| version | INTEGER | NOT NULL, default 1 |

### orders
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| customer_id | UUID | FK → customers.id, NOT NULL |
| status | ENUM(order_status) | NOT NULL, default 'CREATED' |
| total_amount | FLOAT | NOT NULL, default 0.0 |
| currency | ENUM(currency) | NOT NULL, default 'USD' |
| invoice_ref | VARCHAR(255) | NULLABLE |
| invoice_ref | VARCHAR(255) | NULLABLE |
| accepted_at_ts | TIMESTAMPTZ | NULLABLE |
| invoiced_at_ts | TIMESTAMPTZ | NULLABLE |
| paid_at_ts | TIMESTAMPTZ | NULLABLE |
| shipped_at_ts | TIMESTAMPTZ | NULLABLE |
| closed_at_ts | TIMESTAMPTZ | NULLABLE |
| cancelled_at_ts | TIMESTAMPTZ | NULLABLE |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |
| version | INTEGER | NOT NULL, default 1 |

Indexes: `ix_orders_customer_id`, `ix_orders_status`

### order_line_items
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| order_id | UUID | FK → orders.id, NOT NULL |
| product_id | UUID | FK → products.id, NOT NULL |
| invoice_ref | VARCHAR(255) | NULLABLE |
| currency | ENUM(currency) | NOT NULL, default 'USD' |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |
| version | INTEGER | NOT NULL, default 1 |

Index: `ix_order_line_items_order_id`

### payments
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| order_id | UUID | FK → orders.id, NOT NULL |
| amount | FLOAT | NOT NULL |
| payment_timestamp | TIMESTAMPTZ | NOT NULL, default now() |
| status | ENUM(payment_status) | NOT NULL, default 'PENDING' |
| method | ENUM(payment_method) | NOT NULL |
| idempotency_key | VARCHAR(255) | UNIQUE, NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |
| version | INTEGER | NOT NULL, default 1 |

Indexes: `ix_payments_order_id`, `ix_payments_idempotency_key`

### invoices
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| order_id | UUID | FK → orders.id, NOT NULL |
| billing_info | TEXT | NOT NULL |
| amount | FLOAT | NOT NULL |
| currency | ENUM(currency) | NOT NULL, default 'USD' |
| issue_date | TIMESTAMPTZ | NOT NULL, default now() |
| due_date | TIMESTAMPTZ | NOT NULL |
| status | ENUM(invoice_status) | NOT NULL, default 'DRAFT' |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |
| version | INTEGER | NOT NULL, default 1 |

Index: `ix_invoices_order_id`

### outbox_messages
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| aggregate_type | VARCHAR(100) | NOT NULL |
| aggregate_id | VARCHAR(100) | NOT NULL |
| event_type | VARCHAR(100) | NOT NULL |
| payload | TEXT | NOT NULL (JSON) |
| processed_at | TIMESTAMPTZ | NULLABLE |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |
| version | INTEGER | NOT NULL, default 1 |

Index: `ix_outbox_processed_at`
