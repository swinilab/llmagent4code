# Data Architecture

## Narrative

The OMS backend is built on a **command-query responsibility segregation (CQRS)**-inspired design where writes (commands: create order, pay invoice) flow through transactional service methods, and reads (queries: list orders, search products) are optimized via indexed views and eager loading.

### Storage Strategy
| Store | Technology | Purpose |
|-------|-----------|---------|
| Primary DB | PostgreSQL 15 (asyncpg) | All business entities; ACID transactions |
| Cache | Redis 7 (aioredis) | Product catalog, session data, rate-limit counters |
| Queue | Redis 7 (Arq) | Async jobs: audit logs, invoice PDFs, emails |
| Config | YAML file | Environment-agnostic configuration |

### Entity Relationship Summary
```
Customer (1) ─── (M) Order (1) ─── (1) Invoice (1) ─── (1) Payment
                          │
                          └── (M) LineItem (M) ─── Product
```

- A **Customer** may have many **Orders**.
- Each **Order** contains multiple **LineItems** referencing **Products**.
- An accepted order generates exactly one **Invoice**.
- An invoice is settled by exactly one **Payment**.
- **Payment** records are the authoritative source of money movement.

### Schema Design Decisions
1. **Natural vs. Surrogate Keys:** All entities use UUID (surrogate) primary keys for distributed safety; business keys (e.g., invoice number) are stored as unique `code` fields.
2. **Status Enums:** Stored as `VARCHAR` with `CHECK` constraints to allow future states without migrations.
3. **Amount Precision:** All monetary amounts stored as `NUMERIC(19,4)` to avoid floating-point rounding; display formatting happens in the API layer.
4. **Soft Deletes:** Orders and Customers use `deleted_at TIMESTAMP NULL` for audit trail; hard deletes are never performed.
5. **Audit Columns:** Every table includes `created_at`, `updated_at`, `created_by` for traceability.

---

## Complete SQL Schema

```sql
-- ============================================================
-- OMS Backend — PostgreSQL Schema (PostgreSQL 15+)
-- ============================================================
-- Run: psql -d oms_db -f db/schema.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────
-- ENUM TYPES
-- ─────────────────────────────────────────────
CREATE TYPE order_status AS ENUM (
    'pending',      -- Customer submitted, awaiting review
    'accepted',    -- Order staff approved
    'invoiced',    -- Accountant issued invoice
    'paid',        -- Payment verified
    'shipped',     -- Order staff dispatched
    'delivered',   -- Confirmed delivery
    'closed',      -- Order staff closed
    'cancelled'    -- Customer or staff cancelled
);

CREATE TYPE invoice_status AS ENUM (
    'draft',
    'issued',
    'paid',
    'overdue',
    'cancelled'
);

CREATE TYPE payment_status AS ENUM (
    'pending',
    'authorized',
    'captured',
    'failed',
    'refunded'
);

CREATE TYPE user_role AS ENUM (
    'customer',
    'order_staff',
    'accountant'
);

-- ─────────────────────────────────────────────
-- CUSTOMERS
-- ─────────────────────────────────────────────
CREATE TABLE customers (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(32)     NOT NULL UNIQUE,  -- e.g., CUST-00001
    name            VARCHAR(255)    NOT NULL,
    email           VARCHAR(255)    NOT NULL UNIQUE,
    phone           VARCHAR(32),
    role            user_role       NOT NULL DEFAULT 'customer',
    -- Address (denormalized for invoice simplicity)
    address_line1   VARCHAR(255),
    address_line2   VARCHAR(255),
    city            VARCHAR(100),
    state           VARCHAR(100),
    postal_code     VARCHAR(20),
    country         VARCHAR(100)    NOT NULL DEFAULT 'US',
    -- Banking (for reference only; PCI-DSS compliance out of scope for this schema)
    bank_name       VARCHAR(255),
    bank_account    VARCHAR(64),
    bank_routing    VARCHAR(32),
    -- Audit
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ     NULL,
    created_by      UUID            NULL REFERENCES customers(id)
);

CREATE INDEX idx_customers_email ON customers(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_customers_code  ON customers(code)  WHERE deleted_at IS NULL;

-- ─────────────────────────────────────────────
-- PRODUCTS
-- ─────────────────────────────────────────────
CREATE TABLE products (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku             VARCHAR(64)     NOT NULL UNIQUE,
    name            VARCHAR(255)    NOT NULL,
    description     TEXT,
    base_price      NUMERIC(19,4)   NOT NULL,
    currency        VARCHAR(3)      NOT NULL DEFAULT 'USD',
    stock_qty       INTEGER         NOT NULL DEFAULT 0,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_sku     ON products(sku);
CREATE INDEX idx_products_name_gin ON products USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

-- ─────────────────────────────────────────────
-- ORDERS
-- ─────────────────────────────────────────────
CREATE TABLE orders (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(32)     NOT NULL UNIQUE,  -- e.g., ORD-20250712-0001
    customer_id     UUID            NOT NULL REFERENCES customers(id),
    status          order_status    NOT NULL DEFAULT 'pending',
    subtotal        NUMERIC(19,4)   NOT NULL DEFAULT 0,
    tax_amount      NUMERIC(19,4)   NOT NULL DEFAULT 0,
    total_amount    NUMERIC(19,4)   NOT NULL DEFAULT 0,
    currency        VARCHAR(3)      NOT NULL DEFAULT 'USD',
    notes           TEXT,
    invoice_id      UUID            NULL REFERENCES invoices(id),  -- FK: links order to its invoice
    -- Shipping
    ship_address    TEXT,
    ship_city       VARCHAR(100),
    ship_state      VARCHAR(100),
    ship_postal     VARCHAR(20),
    ship_country    VARCHAR(100),
    tracking_number VARCHAR(128),
    -- Audit timestamps
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    accepted_at     TIMESTAMPTZ     NULL,
    shipped_at      TIMESTAMPTZ     NULL,
    paid_at         TIMESTAMPTZ     NULL,
    delivered_at    TIMESTAMPTZ     NULL,
    closed_at       TIMESTAMPTZ     NULL,
    deleted_at      TIMESTAMPTZ     NULL,
    created_by      UUID            NULL REFERENCES customers(id),
    accepted_by     UUID            NULL REFERENCES customers(id)
);

CREATE INDEX idx_orders_customer    ON orders(customer_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_orders_status      ON orders(status)     WHERE deleted_at IS NULL;
CREATE INDEX idx_orders_created_at  ON orders(created_at DESC);
CREATE INDEX idx_orders_code        ON orders(code)      WHERE deleted_at IS NULL;

-- ─────────────────────────────────────────────
-- LINE ITEMS
-- ─────────────────────────────────────────────
CREATE TABLE line_items (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id        UUID            NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
    product_id      UUID            NOT NULL REFERENCES products(id),
    quantity        INTEGER         NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(19,4)   NOT NULL,  -- snapshot of product price at order time
    tax_rate        NUMERIC(5,4)    NOT NULL DEFAULT 0,
    line_total      NUMERIC(19,4)   NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_line_items_order    ON line_items(order_id);
CREATE INDEX idx_line_items_product  ON line_items(product_id);

-- ─────────────────────────────────────────────
-- INVOICES
-- ─────────────────────────────────────────────
CREATE TABLE invoices (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(32)     NOT NULL UNIQUE,  -- e.g., INV-20250712-0001
    order_id        UUID            NOT NULL UNIQUE REFERENCES orders(id),
    customer_id     UUID            NOT NULL REFERENCES customers(id),
    status          invoice_status  NOT NULL DEFAULT 'draft',
    subtotal        NUMERIC(19,4)   NOT NULL,
    tax_amount      NUMERIC(19,4)   NOT NULL,
    total_amount    NUMERIC(19,4)   NOT NULL,
    currency        VARCHAR(3)      NOT NULL DEFAULT 'USD',
    issue_date      DATE            NOT NULL,
    due_date        DATE            NOT NULL,
    paid_date       DATE            NULL,
    billing_name    VARCHAR(255),
    billing_address TEXT,
    -- Audit
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      UUID            NULL REFERENCES customers(id)
);

CREATE INDEX idx_invoices_order      ON invoices(order_id);
CREATE INDEX idx_invoices_customer   ON invoices(customer_id);
CREATE INDEX idx_invoices_status     ON invoices(status);
CREATE INDEX idx_invoices_due_date   ON invoices(due_date);

-- ─────────────────────────────────────────────
-- PAYMENTS
-- ─────────────────────────────────────────────
CREATE TABLE payments (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(32)     NOT NULL UNIQUE,  -- e.g., PAY-20250712-0001
    invoice_id      UUID            NOT NULL REFERENCES invoices(id),
    order_id        UUID            NOT NULL REFERENCES orders(id),
    customer_id     UUID            NOT NULL REFERENCES customers(id),
    amount          NUMERIC(19,4)   NOT NULL,
    currency        VARCHAR(3)      NOT NULL DEFAULT 'USD',
    status          payment_status  NOT NULL DEFAULT 'pending',
    method          VARCHAR(32),   -- e.g., bank_transfer, credit_card
    reference       VARCHAR(128),  -- external gateway reference
    gateway         VARCHAR(64),    -- e.g., stripe, paypal
    -- Timestamps
    authorized_at   TIMESTAMPTZ     NULL,
    captured_at     TIMESTAMPTZ     NULL,
    failed_at       TIMESTAMPTZ     NULL,
    refunded_at     TIMESTAMPTZ     NULL,
    -- Audit
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      UUID            NULL REFERENCES customers(id)
);

CREATE INDEX idx_payments_invoice    ON payments(invoice_id);
CREATE INDEX idx_payments_order      ON payments(order_id);
CREATE INDEX idx_payments_customer   ON payments(customer_id);
CREATE INDEX idx_payments_status     ON payments(status);

-- ─────────────────────────────────────────────
-- AUDIT LOG (append-only)
-- ─────────────────────────────────────────────
CREATE TABLE audit_logs (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type     VARCHAR(64)     NOT NULL,
    entity_id       UUID            NOT NULL,
    action          VARCHAR(32)     NOT NULL,
    actor_id        UUID            NULL REFERENCES customers(id),
    payload         JSONB           NOT NULL DEFAULT '{}',
    ip_address      INET            NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_entity        ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_actor         ON audit_logs(actor_id);
CREATE INDEX idx_audit_created       ON audit_logs(created_at DESC);

-- ─────────────────────────────────────────────
-- SEQUENCE TABLE (for human-readable codes)
-- ─────────────────────────────────────────────
CREATE TABLE sequences (
    name            VARCHAR(64)     PRIMARY KEY,
    current_value   BIGINT          NOT NULL DEFAULT 0,
    increment       BIGINT          NOT NULL DEFAULT 1
);

INSERT INTO sequences (name, current_value) VALUES
    ('customer', 0),
    ('order', 0),
    ('invoice', 0),
    ('payment', 0);

-- ============================================================
-- REFRESH MATERIALIZED VIEW FOR PRODUCT SEARCH (NFR 1.1)
-- ============================================================
CREATE MATERIALIZED VIEW product_search_idx AS
    SELECT id, sku, name, description, base_price, currency,
           to_tsvector('english', name || ' ' || COALESCE(description, '')) AS search_vector
    FROM products
    WHERE is_active = TRUE;

CREATE UNIQUE INDEX ON product_search_idx(id);
CREATE INDEX ON product_search_idx USING gin(search_vector);

-- Function to refresh search view (call after product insert/update)
CREATE OR REPLACE FUNCTION refresh_product_search() RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY product_search_idx;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_refresh_product_search
    AFTER INSERT OR UPDATE ON products
    FOR EACH STATEMENT EXECUTE FUNCTION refresh_product_search();
```
