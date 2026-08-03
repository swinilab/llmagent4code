"""Initial OrderMan schema.

Revision ID: 0001
Revises:
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PgUUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("bank_account_number", sa.String(length=20), nullable=False),
        sa.Column("bank_name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "products",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("price_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("price_currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price_amount > 0", name="ck_products_price_positive"),
    )
    op.create_index("ix_products_description", "products", ["description"])

    op.create_table(
        "orders",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("customer_id", PgUUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invoice_id", PgUUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    op.create_table(
        "order_line_items",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "order_id",
            PgUUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", PgUUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_line_items_order_product"),
        sa.CheckConstraint("quantity >= 1 AND quantity <= 1000", name="ck_line_items_quantity_range"),
    )

    op.create_table(
        "invoices",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "order_id",
            PgUUID(as_uuid=True),
            sa.ForeignKey("orders.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("billing_name", sa.String(length=100), nullable=False),
        sa.Column("billing_address", sa.String(length=255), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("due_date >= issue_date", name="ck_invoices_due_after_issue"),
    )

    op.create_table(
        "payments",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_id", PgUUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_table("invoices")
    op.drop_table("order_line_items")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_products_description", table_name="products")
    op.drop_table("products")
    op.drop_table("customers")
