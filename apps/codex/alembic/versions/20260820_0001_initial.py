"""Create the complete OMS schema.

Revision ID: 20260820_0001
Revises: None
"""

import sqlalchemy as sa
from alembic import op

revision = "20260820_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(16), nullable=False),
        sa.Column("account_number", sa.String(20), nullable=False),
        sa.Column("bank_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(11), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "internal_updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint("length(name) BETWEEN 2 AND 100", name="customer_name_length"),
        sa.CheckConstraint("length(address) BETWEEN 5 AND 255", name="customer_address_length"),
        sa.CheckConstraint("length(account_number) BETWEEN 6 AND 20", name="account_number_length"),
        sa.CheckConstraint("length(bank_name) BETWEEN 2 AND 100", name="bank_name_length"),
        sa.CheckConstraint(
            "role IN ('CUSTOMER', 'ORDER_STAFF', 'ACCOUNTANT')",
            name="customer_role_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("price_amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("price_currency", sa.String(3), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "internal_updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint("length(description) BETWEEN 3 AND 500", name="product_description_length"),
        sa.CheckConstraint(
            "price_amount >= 0.01 AND price_amount <= 999999.99",
            name="product_price_range",
        ),
        sa.CheckConstraint("price_currency IN ('USD', 'VND', 'EUR')", name="product_currency_allowed"),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aggregate_type", sa.String(50), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint("attempts >= 0", name="outbox_attempts_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_events"),
    )
    op.create_index("ix_outbox_unpublished_created", "outbox_events", ["published_at", "created_at"])
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(9), server_default="PLACED", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "total_amount >= 0.01 AND total_amount <= 99999999.99",
            name="order_total_range",
        ),
        sa.CheckConstraint("length(currency) = 3", name="order_currency_length"),
        sa.CheckConstraint("updated_at >= created_at", name="order_timestamp_order"),
        sa.CheckConstraint(
            "status IN ('PLACED', 'ACCEPTED', 'INVOICED', 'PAID', 'VERIFIED', 'SHIPPED', 'CLOSED', 'CANCELLED')",
            name="order_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.id"], name="fk_orders_customer_id_customers", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        sa.UniqueConstraint("invoice_id", name="uq_orders_invoice_id"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(8, 2), nullable=False),
        sa.CheckConstraint("quantity >= 1 AND quantity <= 1000", name="order_item_quantity_range"),
        sa.CheckConstraint(
            "unit_price_snapshot >= 0.01 AND unit_price_snapshot <= 999999.99",
            name="order_item_price_range",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_order_items_order_id_orders", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name="fk_order_items_product_id_products", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_order_items"),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("billing_name", sa.String(100), nullable=False),
        sa.Column("billing_address", sa.String(255), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(9), server_default="ISSUED", nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "internal_updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint(
            "total_amount >= 0.01 AND total_amount <= 99999999.99",
            name="invoice_total_range",
        ),
        sa.CheckConstraint("due_date >= issue_date", name="invoice_due_after_issue"),
        sa.CheckConstraint("length(billing_name) BETWEEN 2 AND 100", name="invoice_billing_name_length"),
        sa.CheckConstraint(
            "length(billing_address) BETWEEN 5 AND 255", name="invoice_billing_address_length",
        ),
        sa.CheckConstraint(
            "status IN ('ISSUED', 'PAID', 'OVERDUE', 'CANCELLED')", name="invoice_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_invoices_order_id_orders", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_invoices"),
        sa.UniqueConstraint("order_id", name="uq_invoices_order_id"),
    )
    op.create_foreign_key(
        "fk_orders_invoice_id_invoices", "orders", "invoices", ["invoice_id"], ["id"], ondelete="SET NULL",
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column("status", sa.String(8), server_default="PENDING", nullable=False),
        sa.Column("method", sa.String(13), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "internal_updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint("amount >= 0.01 AND amount <= 99999999.99", name="payment_amount_range"),
        sa.CheckConstraint("status IN ('PENDING', 'VERIFIED', 'REJECTED')", name="payment_status_allowed"),
        sa.CheckConstraint(
            "method IN ('CREDIT_CARD', 'BANK_TRANSFER', 'E_WALLET')", name="payment_method_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_payments_order_id_orders", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_constraint("fk_orders_invoice_id_invoices", "orders", type_="foreignkey")
    op.drop_table("invoices")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_outbox_unpublished_created", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_table("products")
    op.drop_table("customers")
