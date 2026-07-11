"""
Initial database schema for the Order Management System.

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    sa.Enum("CUSTOMER", "ORDER_STAFF", "ACCOUNTANT", name="user_role_enum").create(
        op.get_bind(), checkfirst=True
    )
    sa.Enum("USD", "EUR", "GBP", name="currency_enum").create(
        op.get_bind(), checkfirst=True
    )
    sa.Enum(
        "CREATED", "ACCEPTED", "INVOICED", "PAID", "SHIPPED", "CLOSED", "CANCELLED",
        name="order_status_enum",
    ).create(op.get_bind(), checkfirst=True)
    sa.Enum(
        "PENDING", "COMPLETED", "FAILED", "REFUNDED",
        name="payment_status_enum",
    ).create(op.get_bind(), checkfirst=True)
    sa.Enum(
        "CREDIT_CARD", "DEBIT_CARD", "BANK_TRANSFER", "DIGITAL_WALLET",
        name="payment_method_enum",
    ).create(op.get_bind(), checkfirst=True)
    sa.Enum(
        "DRAFT", "ISSUED", "PAID", "OVERDUE", "CANCELLED",
        name="invoice_status_enum",
    ).create(op.get_bind(), checkfirst=True)

    # ── Customers ─────────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("banking_details", sa.Text, nullable=False),
        sa.Column(
            "role",
            sa.Enum("CUSTOMER", "ORDER_STAFF", "ACCOUNTANT", name="user_role_enum"),
            nullable=False,
            server_default="CUSTOMER",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    # ── Products ──────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("base_price", sa.Float, nullable=False),
        sa.Column(
            "currency",
            sa.Enum("USD", "EUR", "GBP", name="currency_enum"),
            nullable=False,
            server_default="USD",
        ),
        sa.Column("available", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    # ── Orders ────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("CREATED", "ACCEPTED", "INVOICED", "PAID", "SHIPPED", "CLOSED", "CANCELLED",
                    name="order_status_enum"),
            nullable=False,
            server_default="CREATED",
        ),
        sa.Column("total_amount", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "currency",
            sa.Enum("USD", "EUR", "GBP", name="currency_enum"),
            nullable=False,
            server_default="USD",
        ),
        sa.Column("invoice_ref", sa.String(255), nullable=True),
        sa.Column("paid_at_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    # ── Order Line Items ──────────────────────────────────────────────────
    op.create_table(
        "order_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column(
            "currency",
            sa.Enum("USD", "EUR", "GBP", name="currency_enum"),
            nullable=False,
            server_default="USD",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    # ── Payments ──────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("payment_timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "COMPLETED", "FAILED", "REFUNDED", name="payment_status_enum"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "method",
            sa.Enum("CREDIT_CARD", "DEBIT_CARD", "BANK_TRANSFER", "DIGITAL_WALLET",
                    name="payment_method_enum"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    # ── Invoices ──────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("billing_info", sa.Text, nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column(
            "currency",
            sa.Enum("USD", "EUR", "GBP", name="currency_enum"),
            nullable=False,
            server_default="USD",
        ),
        sa.Column("issue_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "ISSUED", "PAID", "OVERDUE", "CANCELLED", name="invoice_status_enum"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )

    # ── Outbox Messages ───────────────────────────────────────────────────
    op.create_table(
        "outbox_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_order_line_items_order_id", "order_line_items", ["order_id"])
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])
    op.create_index("ix_invoices_order_id", "invoices", ["order_id"])
    op.create_index("ix_outbox_processed_at", "outbox_messages", ["processed_at"])


def downgrade() -> None:
    op.drop_table("outbox_messages")
    op.drop_table("invoices")
    op.drop_table("payments")
    op.drop_table("order_line_items")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("customers")

    sa.Enum(name="invoice_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_method_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="order_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="currency_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role_enum").drop(op.get_bind(), checkfirst=True)
