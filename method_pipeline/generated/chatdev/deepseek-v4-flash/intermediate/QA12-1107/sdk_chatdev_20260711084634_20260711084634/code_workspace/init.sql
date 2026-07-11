-- Database initialization script.
-- Creates the schema and indexes for the OMS.
-- This is run automatically by the PostgreSQL container on first start.
-- Create tables (SQLAlchemy will also create them via metadata.create_all)
-- but we provide this for standalone setup.

CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address JSONB,
    phone VARCHAR(50) DEFAULT '',
    banking_details JSONB,
    order_history JSONB DEFAULT '[]',
    role VARCHAR(20) DEFAULT 'CUSTOMER',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    base_price_amount NUMERIC(12,2) DEFAULT 0.00,
    base_price_currency VARCHAR(3) DEFAULT 'USD',
    stock INTEGER DEFAULT 0,
    available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_products_available ON products(available);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) REFERENCES customers(id),
    line_items JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'CREATED',
    total_amount NUMERIC(12,2) DEFAULT 0.00,
    total_currency VARCHAR(3) DEFAULT 'USD',
    invoice_ref VARCHAR(32),
    payment_ref VARCHAR(32),
    shipping_address JSONB,
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at);

CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(32) PRIMARY KEY,
    order_id VARCHAR(32) REFERENCES orders(id),
    amount NUMERIC(12,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'PENDING',
    method VARCHAR(30) DEFAULT 'CREDIT_CARD',
    transaction_id VARCHAR(64) DEFAULT '',
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(32) PRIMARY KEY,
    order_id VARCHAR(32) REFERENCES orders(id),
    customer_id VARCHAR(32) REFERENCES customers(id),
    billing_address JSONB,
    line_items JSONB DEFAULT '[]',
    subtotal NUMERIC(12,2) DEFAULT 0.00,
    tax NUMERIC(12,2) DEFAULT 0.00,
    total NUMERIC(12,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'DRAFT',
    issue_date TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_invoices_order ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
