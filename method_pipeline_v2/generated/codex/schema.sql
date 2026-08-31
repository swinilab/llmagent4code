BEGIN;

CREATE TABLE customers (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(16) NOT NULL,
    account_number VARCHAR(20) NOT NULL,
    bank_name VARCHAR(100) NOT NULL,
    role VARCHAR(11) NOT NULL,
    deleted_at TIMESTAMPTZ NULL,
    version INTEGER NOT NULL DEFAULT 1,
    internal_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_customers_customer_name_length CHECK (length(name) BETWEEN 2 AND 100),
    CONSTRAINT ck_customers_customer_address_length CHECK (length(address) BETWEEN 5 AND 255),
    CONSTRAINT ck_customers_account_number_length CHECK (length(account_number) BETWEEN 6 AND 20),
    CONSTRAINT ck_customers_bank_name_length CHECK (length(bank_name) BETWEEN 2 AND 100),
    CONSTRAINT ck_customers_customer_role_allowed CHECK (role IN ('CUSTOMER', 'ORDER_STAFF', 'ACCOUNTANT'))
);

CREATE TABLE products (
    id UUID PRIMARY KEY,
    description VARCHAR(500) NOT NULL,
    price_amount NUMERIC(8,2) NOT NULL,
    price_currency VARCHAR(3) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    internal_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_products_product_description_length CHECK (length(description) BETWEEN 3 AND 500),
    CONSTRAINT ck_products_product_price_range CHECK (price_amount BETWEEN 0.01 AND 999999.99),
    CONSTRAINT ck_products_product_currency_allowed CHECK (price_currency IN ('USD', 'VND', 'EUR'))
);

CREATE TABLE orders (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    total_amount NUMERIC(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(9) NOT NULL DEFAULT 'PLACED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    invoice_id UUID NULL UNIQUE,
    CONSTRAINT ck_orders_order_total_range CHECK (total_amount BETWEEN 0.01 AND 99999999.99),
    CONSTRAINT ck_orders_order_currency_length CHECK (length(currency) = 3),
    CONSTRAINT ck_orders_order_timestamp_order CHECK (updated_at >= created_at),
    CONSTRAINT ck_orders_order_status_allowed CHECK (
        status IN ('PLACED', 'ACCEPTED', 'INVOICED', 'PAID', 'VERIFIED', 'SHIPPED', 'CLOSED', 'CANCELLED')
    )
);
CREATE INDEX ix_orders_customer_id ON orders(customer_id);

CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL,
    unit_price_snapshot NUMERIC(8,2) NOT NULL,
    CONSTRAINT uq_order_items_order_product UNIQUE (order_id, product_id),
    CONSTRAINT ck_order_items_order_item_quantity_range CHECK (quantity BETWEEN 1 AND 1000),
    CONSTRAINT ck_order_items_order_item_price_range CHECK (
        unit_price_snapshot BETWEEN 0.01 AND 999999.99
    )
);
CREATE INDEX ix_order_items_order_id ON order_items(order_id);

CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL UNIQUE REFERENCES orders(id) ON DELETE RESTRICT,
    billing_name VARCHAR(100) NOT NULL,
    billing_address VARCHAR(255) NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(9) NOT NULL DEFAULT 'ISSUED',
    version INTEGER NOT NULL DEFAULT 1,
    internal_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_invoices_invoice_total_range CHECK (total_amount BETWEEN 0.01 AND 99999999.99),
    CONSTRAINT ck_invoices_invoice_due_after_issue CHECK (due_date >= issue_date),
    CONSTRAINT ck_invoices_invoice_billing_name_length CHECK (length(billing_name) BETWEEN 2 AND 100),
    CONSTRAINT ck_invoices_invoice_billing_address_length CHECK (length(billing_address) BETWEEN 5 AND 255),
    CONSTRAINT ck_invoices_invoice_status_allowed CHECK (status IN ('ISSUED', 'PAID', 'OVERDUE', 'CANCELLED'))
);

ALTER TABLE orders
    ADD CONSTRAINT fk_orders_invoice_id_invoices
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL;

CREATE TABLE payments (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
    amount NUMERIC(10,2) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(8) NOT NULL DEFAULT 'PENDING',
    method VARCHAR(13) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    internal_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_payments_payment_amount_range CHECK (amount BETWEEN 0.01 AND 99999999.99),
    CONSTRAINT ck_payments_payment_status_allowed CHECK (status IN ('PENDING', 'VERIFIED', 'REJECTED')),
    CONSTRAINT ck_payments_payment_method_allowed CHECK (method IN ('CREDIT_CARD', 'BANK_TRANSFER', 'E_WALLET'))
);
CREATE INDEX ix_payments_order_id ON payments(order_id);

CREATE TABLE outbox_events (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    CONSTRAINT ck_outbox_events_outbox_attempts_nonnegative CHECK (attempts >= 0)
);
CREATE INDEX ix_outbox_unpublished_created ON outbox_events(published_at, created_at);

COMMIT;
