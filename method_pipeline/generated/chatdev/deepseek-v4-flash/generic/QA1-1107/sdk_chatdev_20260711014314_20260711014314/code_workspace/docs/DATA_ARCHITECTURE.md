# Data Architecture Narrative

## Overview

The Order Management System uses a relational data model with six core entities: Customer, Product, Order, OrderLineItem, Payment, and Invoice. The schema is designed to support the complete 7-step order lifecycle while maintaining referential integrity and audit trails.

## Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────┐
│  Customer   │       │   Product    │
├─────────────┤       ├──────────────┤
│ id (PK)     │       │ id (PK)      │
│ name        │       │ description  │
│ address     │       │ pricing (JSON)│
│ phone       │       │ created_at   │
│ banking_det │       │ updated_at   │
│ role        │       └──────────────┘
│ created_at  │              │
│ updated_at  │              │
└──────┬──────┘              │
       │                     │
       │ 1                   │ N
       │                     │
       │  ┌──────────────────┘
       │  │
       │  │  ┌──────────────────────┐
       │  │  │   OrderLineItem      │
       │  │  ├──────────────────────┤
       │  │  │ id (PK)              │
       │  │  │ order_id (FK)        │
       │  │  │ product_id (FK)      │
       │  │  │ product_description  │
       │  │  │ quantity             │
       │  │  │ unit_price           │
       │  │  │ currency             │
       │  │  │ line_total           │
       │  │  └──────────────────────┘
       │  │
       │  │         N
       └──┼─────────┼──┐
           │  Order  │  │
           ├─────────┤  │
           │ id (PK) │  │
           │ cust_id │  │
           │ status  │  │
           │ subtotal│  │
           │ tax_amt │  │
           │ ship_amt│  │
           │ total   │  │
           │ currency│  │
           │ inv_ref │  │
           │ notes   │  │
           │ created │  │
           │ updated │  │
           └────┬────┘  │
                │       │
       ┌────────┼───────┘
       │        │
       │  N     │  N
  ┌────┴───┐ ┌──┴────────┐
  │ Payment│ │  Invoice  │
  ├────────┤ ├───────────┤
  │ id(PK) │ │ id (PK)   │
  │order_id│ │ order_id  │
  │ amount │ │ inv_number│
  │ curr   │ │ bill_info │
  │ status │ │ subtotal  │
  │ method │ │ tax_amt   │
  │ tx_ref │ │ ship_amt  │
  │ paid_at│ │ total     │
  │ created│ │ currency  │
  │ updated│ │ status    │
  └────────┘ │ issue_dt  │
              │ due_dt    │
              │ paid_at   │
              │ created   │
              │ updated   │
              └───────────┘
```

## Key Design Decisions

### 1. UUID Primary Keys
All entities use UUID v4 strings as primary keys. This enables:
- Distributed ID generation without coordination
- No sequential ID guessing
- Consistent 36-character string format across all tables

### 2. JSON for Flexible Fields
- `Customer.banking_details`: Stores bank name, account number, etc. as flexible JSON
- `Product.pricing`: Stores base_price, currency, and optional discount tiers
- `Invoice.billing_info`: Stores customer billing address, contact info at time of invoicing

### 3. Decimal for Monetary Values
All monetary fields use `Numeric(12, 2)` to avoid floating-point rounding errors. This includes:
- `Order.subtotal`, `tax_amount`, `shipping_cost`, `total_amount`
- `OrderLineItem.unit_price`, `line_total`
- `Payment.amount`
- `Invoice.subtotal`, `tax_amount`, `shipping_cost`, `total_amount`

### 4. Status Enums with Lifecycle
Each stateful entity has a defined status lifecycle:
- **OrderStatus:** PENDING → REVIEW → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED (or CANCELLED from most states)
- **PaymentStatus:** PENDING → COMPLETED / FAILED / REFUNDED
- **InvoiceStatus:** DRAFT → ISSUED → PAID / OVERDUE / CANCELLED

### 5. Audit Timestamps
Every entity has `created_at` and `updated_at` timestamps with `server_default=func.now()` and `onupdate=func.now()` for automatic audit trail.

### 6. Referential Integrity
Foreign keys with cascade delete on OrderLineItem ensure data consistency:
- `OrderLineItem.order_id → Order.id` (cascade delete)
- `Order.customer_id → Customer.id`
- `Payment.order_id → Order.id`
- `Invoice.order_id → Order.id`

## Complete Schema (SQLite DDL)

```sql
CREATE TABLE customers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(500) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    banking_details JSON NOT NULL DEFAULT '{}',
    role VARCHAR(20) NOT NULL DEFAULT 'CUSTOMER',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id VARCHAR(36) PRIMARY KEY,
    description VARCHAR(1000) NOT NULL,
    pricing JSON NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL REFERENCES customers(id),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    shipping_cost NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    invoice_ref VARCHAR(36),
    notes VARCHAR(2000),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_line_items (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id VARCHAR(36) NOT NULL REFERENCES products(id),
    product_description VARCHAR(1000) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(12,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    line_total NUMERIC(12,2) NOT NULL
);

CREATE TABLE payments (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES orders(id),
    amount NUMERIC(12,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    method VARCHAR(20) NOT NULL,
    transaction_ref VARCHAR(100),
    paid_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE invoices (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES orders(id),
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    billing_info JSON NOT NULL DEFAULT '{}',
    subtotal NUMERIC(12,2) NOT NULL,
    tax_amount NUMERIC(12,2) NOT NULL,
    shipping_cost NUMERIC(12,2) NOT NULL,
    total_amount NUMERIC(12,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    paid_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```
