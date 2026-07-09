"""Initial schema — create all tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Customer role enum
    sa.Enum("CUSTOMER", "ORDER_STAFF", "ACCOUNTANT", name="customer_role_enum").create(op.get_bind())

    # Order status enum
    sa.Enum(
        "CREATED", "ACCEPTED", "INVOICED", "PAID", "SHIPPED", "CLOSED", "CANCELLED",
        name="order_status_enum",
    ).create(op.get_bind())

    # Payment method enum
    sa.Enum(
        "CREDIT_CARD", "DEBIT_CARD", "BANK_TRANSFER", "DIGITAL_WALLET",
        name="payment_method_enum",
    ).create(op.get_bind())

    # Payment status enum
    sa.Enum(
        "PENDING", "COMPLETED", "FAILED", "REFUNDED",
        name="payment_status_enum",
    ).create(op.get_bind())

    # Invoice status enum
    sa.Enum(
        "DRAFT", "ISSUED", "PAID", "CANCELLED",
        name="invoice_status_enum",
    ).create(op.get_bind())

    # Customers
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("banking_details", sa.Text(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("CUSTOMER", "ORDER_STAFF", "ACCOUNTANT", name="customer_role_enum"),
            nullable=False,
            server_default="CUSTOMER",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Products
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("stock_available", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Orders
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "CREATED", "ACCEPTED", "INVOICED", "PAID", "SHIPPED", "CLOSED", "CANCELLED",
                name="order_status_enum",
            ),
            nullable=False,
            server_default="CREATED",
        ),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    # Order line items
    op.create_table(
        "order_line_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_line_items_order_id", "order_line_items", ["order_id"])

    # Payments
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column(
            "method",
            postgresql.ENUM(
                "CREDIT_CARD", "DEBIT_CARD", "BANK_TRANSFER", "DIGITAL_WALLET",
                name="payment_method_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("PENDING", "COMPLETED", "FAILED", "REFUNDED", name="payment_status_enum"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])

    # Invoices
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("billing_name", sa.String(255), nullable=False),
        sa.Column("billing_address", sa.Text(), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column(
            "status",
            postgresql.ENUM("DRAFT", "ISSUED", "PAID", "CANCELLED", name="invoice_status_enum"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_order_id", "invoices", ["order_id"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("payments")
    op.drop_table("order_line_items")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("customers")

    sa.Enum(name="invoice_status_enum").drop(op.get_bind())
    sa.Enum(name="payment_status_enum").drop(op.get_bind())
    sa.Enum(name="payment_method_enum").drop(op.get_bind())
    sa.Enum(name="order_status_enum").drop(op.get_bind())
    sa.Enum(name="customer_role_enum").drop(op.get_bind())
