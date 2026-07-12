# Data Architecture Narrative and Schema

## Overview

The OMS backend uses SQLite with SQLAlchemy ORM for data persistence. The architecture prioritizes:
- **Crash Safety** (NFR 2.3) via WAL journal mode
- **ACID Compliance** via SQLite transactions
- **State Recovery** via idempotency keys and snapshots

## Data Architecture Principles

### 1. Aggregate Pattern
Each aggregate (Customer, Order, Invoice, Payment) has exactly one repository. Line items are embedded in Order as JSON to simplify the model while maintaining consistency.

### 2. Idempotency
All state-changing operations support idempotency keys to prevent duplicate processing after crashes or network issues.

### 3. Snapshot-based Recovery
State snapshots are saved at key workflow transitions to enable recovery after unexpected termination.

## Schema

### customers
```
customers
├── id (PK, String[36])
├── name (String[255], NOT NULL)
├── email (String[255], UNIQUE, NOT NULL)
├── phone (String[50])
├── address_json (JSON)
├── banking_details_json (JSON)
├── role (String[20], DEFAULT 'customer')
├── created_at (DateTime)
└── updated_at (DateTime)
```

### products
```
products
├── id (PK, String[36])
├── sku (String[100], UNIQUE, NOT NULL)
├── description (Text)
├── base_price (Float, NOT NULL)
├── currency (String[3], DEFAULT 'USD')
├── stock_quantity (Integer, DEFAULT 0)
├── is_active (Boolean, DEFAULT True)
├── created_at (DateTime)
└── updated_at (DateTime)
```

### orders
```
orders
├── id (PK, String[36])
├── customer_id (FK -> customers.id, NOT NULL)
├── line_items_json (JSON, NOT NULL)
├── status (String[20], DEFAULT 'pending')
├── subtotal (Float, DEFAULT 0.0)
├── tax (Float, DEFAULT 0.0)
├── shipping (Float, DEFAULT 0.0)
├── total (Float, DEFAULT 0.0)
├── currency (String[3], DEFAULT 'USD')
├── invoice_id (FK -> invoices.id, NULLABLE)
├── shipping_address_json (JSON)
├── notes (Text)
├── idempotency_key (String[100], UNIQUE, NULLABLE)
├── created_at (DateTime)
├── updated_at (DateTime)
├── accepted_at (DateTime, NULLABLE)
├── shipped_at (DateTime, NULLABLE)
└── completed_at (DateTime, NULLABLE)
```

### invoices
```
invoices
├── id (PK, String[36])
├── order_id (FK -> orders.id, NOT NULL)
├── customer_id (FK -> customers.id, NOT NULL)
├── billing_address_json (JSON)
├── subtotal (Float, DEFAULT 0.0)
├── tax (Float, DEFAULT 0.0)
├── total (Float, DEFAULT 0.0)
├── currency (String[3], DEFAULT 'USD')
├── status (String[20], DEFAULT 'draft')
├── issue_date (DateTime)
├── due_date (DateTime, NULLABLE)
├── paid_date (DateTime, NULLABLE)
├── idempotency_key (String[100], UNIQUE, NULLABLE)
├── created_at (DateTime)
└── updated_at (DateTime)
```

### payments
```
payments
├── id (PK, String[36])
├── order_id (FK -> orders.id, NOT NULL)
├── invoice_id (FK -> invoices.id, NOT NULL)
├── customer_id (FK -> customers.id, NOT NULL)
├── amount (Float, NOT NULL)
├── currency (String[3], DEFAULT 'USD')
├── method (String[50], DEFAULT 'bank_transfer')
├── status (String[20], DEFAULT 'pending')
├── transaction_ref (String[255])
├── idempotency_key (String[100], UNIQUE, NULLABLE)
├── created_at (DateTime)
└── processed_at (DateTime, NULLABLE)
```

### state_snapshots
```
state_snapshots
├── id (PK, String[36])
├── entity_type (String[50], NOT NULL)
├── entity_id (String[36], NOT NULL)
├── state_json (JSON, NOT NULL)
├── timestamp (DateTime, NOT NULL)
├── last_event (String[255])
└── is_recovery_point (Boolean, DEFAULT False)
```

## Relationships

```
Customer (1) ──────< Order (M)
    │                   │
    │                   │
    └──< Payment (M)    │
            │           │
            │           │
            └──< Invoice (1)
                    │
                    │
                    └──< Order (1) via invoice_id
```

## Indexes

- `customers.email` - UNIQUE index for fast lookup
- `products.sku` - UNIQUE index for fast lookup
- `orders.customer_id` - Index for customer order history
- `orders.status` - Index for pending order queries
- `orders.idempotency_key` - UNIQUE index for duplicate detection
- `invoices.order_id` - UNIQUE index (one invoice per order)
- `invoices.idempotency_key` - UNIQUE index for duplicate detection
- `payments.order_id` - Index for order payment history
- `payments.invoice_id` - Index for invoice payment history
- `payments.idempotency_key` - UNIQUE index for duplicate detection

## JSON Fields

### address_json Structure
```json
{
  "street": "string",
  "city": "string",
  "state": "string",
  "postal_code": "string",
  "country": "string"
}
```

### line_items_json Structure
```json
[
  {
    "id": "uuid",
    "product_id": "uuid",
    "product_description": "string",
    "quantity": 1,
    "unit_price": 99.99,
    "currency": "USD"
  }
]
```

## Transaction Boundaries

### Order Placement
- Single transaction: Create order with line items
- Snapshot saved after commit

### Invoice Creation
- Single transaction: Create invoice
- Idempotency check prevents duplicates

### Payment Processing
- Transaction 1: Create payment (PENDING)
- Transaction 2: Process payment (update to COMPLETED/FAILED)
- Snapshot saved after each state transition

### State Recovery
- On startup: Query state_snapshots for pending orders
- Verify order status against snapshot
- Resume from last known good state

## WAL Mode Configuration

```sql
PRAGMA journal_mode=WAL;        -- Write-ahead logging for crash safety
PRAGMA synchronous=NORMAL;      -- Balanced safety vs performance
PRAGMA foreign_keys=ON;         -- Enforce referential integrity
PRAGMA busy_timeout=5000;       -- 5 second lock timeout
```

## Backup Strategy

While WAL mode provides crash safety, for production:
1. Regular `sqlite3 .backup` commands
2. Replicate to cloud storage
3. Consider PostgreSQL migration for multi-instance deployment
