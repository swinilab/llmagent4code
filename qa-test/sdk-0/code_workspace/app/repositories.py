"""Repository layer using raw SQLite with schema aligned to ORM models.
All table and column names now match the ORM definitions (plural table names, JSON columns for complex fields).
"""
import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from app.db import get_connection
from app.models import (
    CustomerDTO,
    ProductDTO,
    OrderDTO,
    PaymentDTO,
    InvoiceDTO,
    OrderCreateDTO,
    LineItem,
)

# Helper to serialize Decimal to string
def dec_to_str(d: Decimal) -> str:
    return format(d, 'f')

def str_to_dec(s: str) -> Decimal:
    return Decimal(s)

# Customer Repository
class CustomerRepository:
    @staticmethod
    def create(customer: CustomerDTO):
        conn = get_connection()
        cur = conn.cursor()
        # banking_details stored as JSON
        banking_json = json.dumps({
            "accountNumber": customer.bankingDetails.accountNumber,
            "bankName": customer.bankingDetails.bankName,
        })
        cur.execute(
            "INSERT INTO customers (id, name, address, phone, banking_details, role) VALUES (?,?,?,?,?,?)",
            (
                customer.id,
                customer.name,
                customer.address,
                customer.phone,
                banking_json,
                customer.role,
            ),
        )
        conn.commit()
        conn.close()
        return customer

    @staticmethod
    def get_by_id(customer_id: str) -> Optional[CustomerDTO]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        banking = json.loads(row["banking_details"])
        return CustomerDTO(
            id=row["id"],
            name=row["name"],
            address=row["address"],
            phone=row["phone"],
            bankingDetails={
    @staticmethod
    def set_invoice_ref(order_id: str, invoice_id: str):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE orders SET invoice_id=?, status=? WHERE id=?",
            (invoice_id, 'INVOICED', order_id),
        )
        conn.commit()
        conn.close()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (id, description, price_amount, price_currency) VALUES (?,?,?,?)",
            (
                product.id,
                product.description,
                dec_to_str(product.price.amount),
                product.price.currency,
            ),
        )
        conn.commit()
        conn.close()
        return product

    @staticmethod
    def get_by_id(product_id: str) -> Optional[ProductDTO]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return ProductDTO(
            id=row["id"],
            description=row["description"],
            price={
                "amount": str_to_dec(row["price_amount"]),
                "currency": row["price_currency"],
            },
        )

# Order Repository
    @staticmethod
    def update_status(payment_id: str, new_status: str):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE payments SET status=?, timestamp=? WHERE id=?",
            (new_status, datetime.utcnow().isoformat(), payment_id),
        )
        conn.commit()
        conn.close()
        cur.execute(
            "INSERT INTO orders (id, customer_id, line_items, total_amount, status, created_at, updated_at, invoice_id) VALUES (?,?,?,?,?,?,?,?)",
            (
                order.id,
                order.customerRef,
                json.dumps([item.dict() for item in order.lineItems]),
    @staticmethod
    def update_invoice_status(invoice_id: str, new_status: str):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE invoices SET status=? WHERE id=?",
            (new_status, invoice_id),
        )
        conn.commit()
        conn.close()
    @staticmethod
    def get_by_id(order_id: str) -> Optional[OrderDTO]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        line_items_data = json.loads(row["line_items"])
        line_items = [LineItem(**item) for item in line_items_data]
        return OrderDTO(
            id=row["id"],
            customerRef=row["customer_id"],
            lineItems=line_items,
            totalAmount=str_to_dec(row["total_amount"]),
            status=row["status"],
            createdAt=datetime.fromisoformat(row["created_at"]),
            updatedAt=datetime.fromisoformat(row["updated_at"]),
            invoiceRef=row["invoice_id"],
        )

    @staticmethod
    def update_status(order_id: str, new_status: str):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE orders SET status=?, updated_at=? WHERE id=?",
            (new_status, datetime.utcnow().isoformat(), order_id),
        )
        conn.commit()
        conn.close()

# Payment Repository
class PaymentRepository:
    @staticmethod
    def create(payment: PaymentDTO):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO payments (id, order_id, amount, timestamp, status, method) VALUES (?,?,?,?,?,?)",
            (
                payment.id,
                payment.orderRef,
                dec_to_str(payment.amount),
                payment.timestamp.isoformat(),
                payment.status,
                payment.method,
            ),
        )
        conn.commit()
        conn.close()
        return payment

    @staticmethod
    def get_by_id(payment_id: str) -> Optional[PaymentDTO]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE id=?", (payment_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return PaymentDTO(
            id=row["id"],
            orderRef=row["order_id"],
            amount=str_to_dec(row["amount"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            status=row["status"],
            method=row["method"],
        )

# Invoice Repository
class InvoiceRepository:
    @staticmethod
    def create(invoice: InvoiceDTO):
        conn = get_connection()
        cur = conn.cursor()
        billing_json = json.dumps({
            "name": invoice.billingInfo_name,
            "address": invoice.billingInfo_address,
        })
        cur.execute(
            "INSERT INTO invoices (id, order_id, billing_info, total_amount, issue_date, due_date, status) VALUES (?,?,?,?,?,?,?)",
            (
                invoice.id,
                invoice.orderRef,
                billing_json,
                dec_to_str(invoice.totalAmount),
                invoice.issueDate,
                invoice.dueDate,
                invoice.status,
            ),
        )
        conn.commit()
        conn.close()
        return invoice

    @staticmethod
    def get_by_id(invoice_id: str) -> Optional[InvoiceDTO]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        billing = json.loads(row["billing_info"])
        return InvoiceDTO(
            id=row["id"],
            orderRef=row["order_id"],
            billingInfo_name=billing.get("name"),
            billingInfo_address=billing.get("address"),
            totalAmount=str_to_dec(row["total_amount"]),
            issueDate=row["issue_date"],
            dueDate=row["due_date"],
        )

# Invoice Repository
