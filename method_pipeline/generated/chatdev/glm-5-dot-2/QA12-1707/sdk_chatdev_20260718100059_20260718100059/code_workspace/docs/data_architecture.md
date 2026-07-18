# Data Architecture

## Overview

The OMS backend uses a single SQLite database file (`oms.db`) running in WAL
(Write-Ahead Logging) mode. The schema consists of six tables that model the
complete e-commerce order lifecycle: customer ordering → payment processing →
invoicing → shipping → closure.

All tables use UUID strings (36-char) as primary keys, generated client-side
via `uuid.uuid4()`. Every table includes `created_at` and `updated_at`
timestamps via the `TimestampMixin` (composition over inheritance).

## Schema Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────────┐
│  customers   │       │   products   │       │ order_line_items  │
│──────────────│       │──────────────│       │──────────────────│
│ id (PK)      │       │ id (PK)      │       │ id (PK)          │
│ name         │       │ description  │       │ order_id (FK)    │
│ address      │       │ base_price   │       │ product_id (FK)  │
│ phone        │       │ currency     │       │ quantity         │
│ banking_det. │       │ created_at   │       │ unit_price       │
│ role         │       │ updated_at   │       │ currency         │
│ created_at   │       └──────┬───────┘       └──────┬───────────┘
│ updated_at   │              │                      │
└──────┬───────┘              │ (RESTRICT)           │ (CASCADE)
       │ 1:N                  │                      │ N:1
       │                      │                      │
       ▼                      │                      ▼
┌──────────────┐       ┌──────────────────────────────┐
│   orders     │       │         orders (cont.)        │
│──────────────│       │──────────────────────────────│
│ id (PK)      │◄──────│ customer_id (FK, CASCADE)    │
│ status       │       │ invoice_id (FK, SET NULL)    │
│ subtotal     │       │ accepted_at, shipped_at,     │
│ tax          │       │   closed_at                  │
│ total        │       │ created_at, updated_at        │
│ currency     │       └──────┬──────────┬────────────┘
└──────────────┘              │ 1:N      │ 1:1
       │                      ▼          ▼
       │ 1:N           ┌──────────────┐  ┌──────────────┐
       │               │  payments    │  │  invoices    │
       │               │──────────────│  │──────────────│
       │               │ id (PK)      │  │ id (PK)      │
       │               │ order_id(FK) │  │ order_id(FK) │
       │               │ amount       │  │   (UNIQUE)   │
       │               │ timestamp    │  │ billing_info │
       │               │ status       │  │ subtotal     │
       │               │ method       │  │ tax, total   │
       │               │ created_at   │  │ currency     │
       │               │ updated_at   │  │ issue_date   │
       │               └──────────────┘  │ due_date     │
       │                                 │ status       │
       │                                 │ created_at   │
       │                                 │ updated_at   │
       │                                 └──────────────┘
```

## Tables

### 1. `customers`
Stores customer identity, contact, banking details (JSON), and role.
- **PK:** `id` (UUID string)
- **Columns:** `name`, `address`, `phone`, `banking_details` (JSON), `role`
  (enum: customer / order_staff / accountant)
- **Timestamps:** `created_at`, `updated_at`

### 2. `products`
Stores product description and pricing (base price + currency).
- **PK:** `id` (UUID string)
- **Columns:** `description` (text), `base_price` (numeric 12,2),
  `currency` (3-char ISO)
- **Timestamps:** `created_at`, `updated_at`

### 3. `orders`
The central entity tracking the full order lifecycle.
- **PK:** `id` (UUID string)
- **FK:** `customer_id` → `customers.id` (ON DELETE CASCADE),
  `invoice_id` → `invoices.id` (ON DELETE SET NULL)
- **Columns:** `status` (enum: pending → accepted → invoiced → paid →
  shipped → closed / cancelled), `subtotal`, `tax`, `total`, `currency`,
  `accepted_at`, `shipped_at`, `closed_at`
- **Timestamps:** `created_at`, `updated_at`

### 4. `order_line_items`
Junction table between orders and products with a price snapshot.
- **PK:** `id` (UUID string)
- **FK:** `order_id` → `orders.id` (ON DELETE CASCADE),
  `product_id` → `products.id` (ON DELETE RESTRICT)
- **Columns:** `quantity`, `unit_price` (snapshot at order time),
  `currency`
- **No timestamps** (line items are immutable once created)

### 5. `payments`
Records payment attempts against an order.
- **PK:** `id` (UUID string)
- **FK:** `order_id` → `orders.id` (ON DELETE CASCADE)
- **Columns:** `amount`, `timestamp`, `status` (enum: pending / verified /
  failed), `method` (enum: credit_card / bank_transfer / paypal)
- **Timestamps:** `created_at`, `updated_at`

### 6. `invoices`
Created by the accountant for accepted orders; 1:1 with orders.
- **PK:** `id` (UUID string)
- **FK:** `order_id` → `orders.id` (ON DELETE CASCADE, UNIQUE constraint)
- **Columns:** `billing_info` (JSON), `subtotal`, `tax`, `total`,
  `currency`, `issue_date`, `due_date`, `status` (enum: draft / issued /
  paid / overdue)
- **Timestamps:** `created_at`, `updated_at`

## Relationships

| Relationship | Cardinality | Description |
|-------------|-----------|-------------|
| customer → orders | 1:N | A customer can place many orders. FK with `ON DELETE CASCADE`. |
| order → order_line_items | 1:N | An order has many line items. FK with `ON DELETE CASCADE`. |
| order_line_item → product | N:1 | Each line item references a product. FK with `ON DELETE RESTRICT` (cannot delete a product that is referenced by an order). |
| order → invoice | 1:1 | Each order has at most one invoice. `order.invoice_id` FK with `ON DELETE SET NULL`; `invoices.order_id` has a UNIQUE constraint. |
| order → payments | 1:N | An order can have multiple payment attempts (e.g. a failed one followed by a successful one). FK with `ON DELETE CASCADE`. |

## Eager Loading Strategy

All relationship fetching uses SQLAlchemy's `selectin` loading strategy
(`lazy="selectin"` on relationships, explicit `selectinload()` in
`OrderRepository.get_full`). This issues a single `SELECT ... WHERE id IN (...)`
query per relationship level, avoiding N+1 query problems and minimising
round-trips — directly supporting NFR 1.1 (Response Time).

## Durability Strategy (WAL Mode)

On startup, `init_db()` executes the following SQLite pragmas:

```sql
PRAGMA journal_mode=WAL;       -- Write-Ahead Logging: readers don't block writers
PRAGMA synchronous=NORMAL;     -- Durable across app crashes, not power loss
PRAGMA busy_timeout=5000;      -- Wait up to 5s on lock contention before erroring
```

**WAL mode** maintains a separate `-wal` file for uncommitted writes, allowing
concurrent readers to proceed while a write transaction is in progress. This is
critical for the OMS read-heavy workload (many product searches concurrent with
order writes).

**`synchronous=NORMAL`** provides a balance between durability and
performance: every transaction is durable across application process crashes
(the WAL is checkpointed to the main DB), but not across sudden power loss.
This is acceptable for the local-machine deployment target.

**`busy_timeout=5000`** ensures that if a write lock is held by another
connection, SQLite waits up to 5 seconds before returning a "database is
locked" error, smoothing over transient contention.

## State Recovery (NFR 2.3)

On application startup, `RecoveryService.recover()` scans the `orders` table for
all orders in non-terminal states (PENDING, ACCEPTED, INVOICED, PAID, SHIPPED).
These represent orders that were mid-lifecycle when the previous process
unexpectedly terminated. The service logs each recovered order for audit and, in
a production system with external integrations, would re-trigger pending API
calls (e.g. payment gateway confirmation, shipping carrier dispatch). Because
all state is persisted in the durable SQLite WAL database, no data is lost
across restarts.