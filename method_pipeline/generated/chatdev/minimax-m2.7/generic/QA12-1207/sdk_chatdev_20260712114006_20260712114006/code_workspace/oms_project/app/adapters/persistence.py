"""
In-memory repository implementations for OMS.
Provides SQLite-backed persistent storage with transaction support.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.domain.entities.models import (
    Customer, Order, Product, Payment, Invoice, OrderStatus,
    PaymentStatus, InvoiceStatus, UserRole, Currency,
    Address, BankingDetails, Money, LineItem
)
from app.domain.repositories.interfaces import (
    CustomerRepository, OrderRepository, ProductRepository,
    PaymentRepository, InvoiceRepository
)


def _json_dumps(obj) -> str:
    """Serialize object to JSON string."""
    return json.dumps(obj, default=str)


def _json_loads(s) -> Any:
    """Deserialize JSON string to object."""
    if s is None:
        return None
    return json.loads(s) if isinstance(s, str) else s


class DatabaseManager:
    """Manages SQLite database connections and schema."""

    _local = threading.local()
    _lock = threading.RLock()

    def __init__(self, db_path: str = "oms.db"):
        self.db_path = db_path
        self._initialized = False
        self._init_db_path = None

    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level='DEFERRED'
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def close_connection(self):
        """Close thread-local connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    def init_schema(self):
        """Initialize database schema."""
        with self._lock:
            if self._init_db_path != self.db_path:
                self._initialized = False
                self._init_db_path = self.db_path
            if self._initialized:
                return
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    address_json TEXT,
                    banking_details_json TEXT,
                    role TEXT NOT NULL DEFAULT 'CUSTOMER',
                    order_history_json TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    sku TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    price_json TEXT NOT NULL,
                    stock_quantity INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    category TEXT,
                    weight REAL,
                    dimensions_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    line_items_json TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    subtotal_json TEXT,
                    tax_total_json TEXT,
                    discount_total_json TEXT,
                    total_json TEXT,
                    currency TEXT DEFAULT 'USD',
                    invoice_id TEXT,
                    payment_id TEXT,
                    shipping_address_json TEXT,
                    notes TEXT,
                    accepted_at TEXT,
                    shipped_at TEXT,
                    completed_at TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    amount_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    method TEXT,
                    transaction_ref TEXT,
                    payment_timestamp TEXT,
                    processed_at TEXT,
                    failure_reason TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    invoice_number TEXT UNIQUE NOT NULL,
                    order_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    billing_address_json TEXT,
                    line_items_json TEXT,
                    subtotal_json TEXT,
                    tax_total_json TEXT,
                    discount_total_json TEXT,
                    total_json TEXT,
                    status TEXT NOT NULL DEFAULT 'DRAFT',
                    issue_date TEXT,
                    due_date TEXT,
                    paid_date TEXT,
                    notes TEXT,
                    terms TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.commit()
            self._initialized = True


class InMemoryCustomerRepository(CustomerRepository):
    """In-memory customer repository using SQLite."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _row_to_customer(self, row) -> Customer:
        if not row:
            return None
        data = dict(row)
        data['address'] = _json_loads(data.pop('address_json'))
        data['banking_details'] = _json_loads(data.pop('banking_details_json'))
        data['order_history'] = _json_loads(data.pop('order_history_json')) or []
        data['is_active'] = bool(data['is_active'])
        return Customer.from_dict(data)

    def save(self, entity: Customer) -> Customer:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        if not entity.created_at:
            entity.created_at = datetime.fromisoformat(now)
        entity.updated_at = datetime.fromisoformat(now)

        cursor.execute("""
            INSERT OR REPLACE INTO customers
            (id, name, email, phone, address_json, banking_details_json,
             role, order_history_json, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.id, entity.name, entity.email, entity.phone,
            _json_dumps(entity.address.to_dict() if entity.address else None),
            _json_dumps(entity.banking_details.to_dict() if entity.banking_details else None),
            entity.role.value, _json_dumps(entity.order_history),
            int(entity.is_active), entity.created_at.isoformat(), entity.updated_at.isoformat()
        ))
        conn.commit()
        return entity

    def find_by_id(self, entity_id: str) -> Optional[Customer]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        return self._row_to_customer(row) if row else None

    def find_by_email(self, email: str) -> Optional[Customer]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE email = ?", (email,))
        row = cursor.fetchone()
        return self._row_to_customer(row) if row else None

    def find_by_role(self, role: UserRole) -> List[Customer]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE role = ?", (role.value,))
        return [self._row_to_customer(row) for row in cursor.fetchall()]

    def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[Customer]:
        entity = self.find_by_id(entity_id)
        if not entity:
            return None
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return self.save(entity)

    def delete(self, entity_id: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = ?", (entity_id,))
        conn.commit()
        return cursor.rowcount > 0


class InMemoryProductRepository(ProductRepository):
    """In-memory product repository using SQLite."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _row_to_product(self, row) -> Product:
        if not row:
            return None
        data = dict(row)
        data['price'] = _json_loads(data.pop('price_json'))
        data['dimensions'] = _json_loads(data.pop('dimensions_json'))
        data['is_active'] = bool(data['is_active'])
        return Product.from_dict(data)

    def save(self, entity: Product) -> Product:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        if not entity.created_at:
            entity.created_at = datetime.fromisoformat(now)
        entity.updated_at = datetime.fromisoformat(now)

        cursor.execute("""
            INSERT OR REPLACE INTO products
            (id, sku, name, description, price_json, stock_quantity, is_active,
             category, weight, dimensions_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.id, entity.sku, entity.name, entity.description,
            _json_dumps(entity.price.to_dict()),
            entity.stock_quantity, int(entity.is_active),
            entity.category, entity.weight,
            _json_dumps(entity.dimensions.to_dict() if entity.dimensions else None),
            entity.created_at.isoformat(), entity.updated_at.isoformat()
        ))
        conn.commit()
        return entity

    def find_by_id(self, entity_id: str) -> Optional[Product]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        return self._row_to_product(row) if row else None

    def find_by_sku(self, sku: str) -> Optional[Product]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE sku = ?", (sku,))
        row = cursor.fetchone()
        return self._row_to_product(row) if row else None

    def find_all(self) -> List[Product]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE is_active = 1")
        return [self._row_to_product(row) for row in cursor.fetchall()]

    def search(self, query: str, category: Optional[str] = None) -> List[Product]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "SELECT * FROM products WHERE is_active = 1 AND (name LIKE ? OR description LIKE ?) AND category = ?",
                (f"%{query}%", f"%{query}%", category)
            )
        else:
            cursor.execute(
                "SELECT * FROM products WHERE is_active = 1 AND (name LIKE ? OR description LIKE ?)",
                (f"%{query}%", f"%{query}%")
            )
        return [self._row_to_product(row) for row in cursor.fetchall()]

    def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[Product]:
        entity = self.find_by_id(entity_id)
        if not entity:
            return None
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return self.save(entity)

    def update_stock(self, product_id: str, quantity: int) -> Optional[Product]:
        product = self.find_by_id(product_id)
        if not product:
            return None
        product.stock_quantity = quantity
        return self.save(product)

    def reserve_stock(self, product_id: str, quantity: int) -> bool:
        product = self.find_by_id(product_id)
        if not product or product.stock_quantity < quantity:
            return False
        product.stock_quantity -= quantity
        self.save(product)
        return True

    def release_stock(self, product_id: str, quantity: int) -> bool:
        product = self.find_by_id(product_id)
        if not product:
            return False
        product.stock_quantity += quantity
        self.save(product)
        return True

    def delete(self, entity_id: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (entity_id,))
        conn.commit()
        return cursor.rowcount > 0


class InMemoryOrderRepository(OrderRepository):
    """In-memory order repository using SQLite."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _row_to_order(self, row) -> Order:
        if not row:
            return None
        data = dict(row)
        data['line_items'] = _json_loads(data.pop('line_items_json')) or []
        data['subtotal'] = _json_loads(data.pop('subtotal_json'))
        data['tax_total'] = _json_loads(data.pop('tax_total_json'))
        data['discount_total'] = _json_loads(data.pop('discount_total_json'))
        data['total'] = _json_loads(data.pop('total_json'))
        data['shipping_address'] = _json_loads(data.pop('shipping_address_json'))
        data['metadata'] = _json_loads(data.pop('metadata_json'))
        return Order.from_dict(data)

    def save(self, entity: Order) -> Order:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        if not entity.created_at:
            entity.created_at = datetime.fromisoformat(now)
        entity.updated_at = datetime.fromisoformat(now)

        line_items_dicts = [item.to_dict() if hasattr(item, 'to_dict') else item for item in entity.line_items]

        cursor.execute("""
            INSERT OR REPLACE INTO orders
            (id, customer_id, line_items_json, status, subtotal_json, tax_total_json,
             discount_total_json, total_json, currency, invoice_id, payment_id,
             shipping_address_json, notes, accepted_at, shipped_at, completed_at,
             metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.id, entity.customer_id, _json_dumps(line_items_dicts),
            entity.status.value,
            _json_dumps(entity.subtotal.to_dict()),
            _json_dumps(entity.tax_total.to_dict()),
            _json_dumps(entity.discount_total.to_dict()),
            _json_dumps(entity.total.to_dict()),
            entity.currency.value, entity.invoice_id, entity.payment_id,
            _json_dumps(entity.shipping_address.to_dict() if entity.shipping_address else None),
            entity.notes, entity.accepted_at, entity.shipped_at, entity.completed_at,
            _json_dumps(entity.metadata), entity.created_at.isoformat(), entity.updated_at.isoformat()
        ))
        conn.commit()
        return entity

    def find_by_id(self, entity_id: str) -> Optional[Order]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        return self._row_to_order(row) if row else None

    def find_by_customer(self, customer_id: str) -> List[Order]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE customer_id = ?", (customer_id,))
        return [self._row_to_order(row) for row in cursor.fetchall()]

    def find_by_status(self, status: OrderStatus) -> List[Order]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE status = ?", (status.value,))
        return [self._row_to_order(row) for row in cursor.fetchall()]

    def find_all(self) -> List[Order]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders")
        return [self._row_to_order(row) for row in cursor.fetchall()]

    def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[Order]:
        entity = self.find_by_id(entity_id)
        if not entity:
            return None
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return self.save(entity)

    def update_status(self, order_id: str, status: OrderStatus) -> Optional[Order]:
        order = self.find_by_id(order_id)
        if not order:
            return None
        order.status = status
        now = datetime.now(timezone.utc)
        if status == OrderStatus.ACCEPTED:
            order.accepted_at = now
        elif status == OrderStatus.SHIPPED:
            order.shipped_at = now
        elif status == OrderStatus.COMPLETED:
            order.completed_at = now
        return self.save(order)

    def delete(self, entity_id: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders WHERE id = ?", (entity_id,))
        conn.commit()
        return cursor.rowcount > 0


class InMemoryPaymentRepository(PaymentRepository):
    """In-memory payment repository using SQLite."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _row_to_payment(self, row) -> Payment:
        if not row:
            return None
        data = dict(row)
        data['amount'] = _json_loads(data.pop('amount_json'))
        data['metadata'] = _json_loads(data.pop('metadata_json'))
        return Payment.from_dict(data)

    def save(self, entity: Payment) -> Payment:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        if not entity.created_at:
            entity.created_at = datetime.fromisoformat(now)
        entity.updated_at = datetime.fromisoformat(now)

        cursor.execute("""
            INSERT OR REPLACE INTO payments
            (id, order_id, customer_id, amount_json, status, method,
             transaction_ref, payment_timestamp, processed_at, failure_reason,
             metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.id, entity.order_id, entity.customer_id,
            _json_dumps(entity.amount.to_dict()),
            entity.status.value, entity.method.value if entity.method else None,
            entity.transaction_ref, entity.payment_timestamp,
            entity.processed_at, entity.failure_reason,
            _json_dumps(entity.metadata),
            entity.created_at.isoformat(), entity.updated_at.isoformat()
        ))
        conn.commit()
        return entity

    def find_by_id(self, entity_id: str) -> Optional[Payment]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        return self._row_to_payment(row) if row else None

    def find_by_order(self, order_id: str) -> List[Payment]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,))
        return [self._row_to_payment(row) for row in cursor.fetchall()]

    def find_by_customer(self, customer_id: str) -> List[Payment]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE customer_id = ?", (customer_id,))
        return [self._row_to_payment(row) for row in cursor.fetchall()]

    def find_by_status(self, status: PaymentStatus) -> List[Payment]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE status = ?", (status.value,))
        return [self._row_to_payment(row) for row in cursor.fetchall()]

    def find_all(self) -> List[Payment]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments")
        return [self._row_to_payment(row) for row in cursor.fetchall()]

    def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[Payment]:
        entity = self.find_by_id(entity_id)
        if not entity:
            return None
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return self.save(entity)

    def update_status(self, payment_id: str, status: PaymentStatus) -> Optional[Payment]:
        payment = self.find_by_id(payment_id)
        if not payment:
            return None
        payment.status = status
        if status == PaymentStatus.PROCESSING:
            payment.processed_at = datetime.now(timezone.utc).isoformat()
        return self.save(payment)

    def delete(self, entity_id: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM payments WHERE id = ?", (entity_id,))
        conn.commit()
        return cursor.rowcount > 0


class InMemoryInvoiceRepository(InvoiceRepository):
    """In-memory invoice repository using SQLite."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _row_to_invoice(self, row) -> Invoice:
        if not row:
            return None
        data = dict(row)
        data['line_items'] = _json_loads(data.pop('line_items_json')) or []
        data['subtotal'] = _json_loads(data.pop('subtotal_json'))
        data['tax_total'] = _json_loads(data.pop('tax_total_json'))
        data['discount_total'] = _json_loads(data.pop('discount_total_json'))
        data['total'] = _json_loads(data.pop('total_json'))
        data['billing_address'] = _json_loads(data.pop('billing_address_json'))
        data['metadata'] = _json_loads(data.pop('metadata_json'))
        return Invoice.from_dict(data)

    def save(self, entity: Invoice) -> Invoice:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        if not entity.created_at:
            entity.created_at = datetime.fromisoformat(now)
        entity.updated_at = datetime.fromisoformat(now)

        line_items_dicts = [item.to_dict() if hasattr(item, 'to_dict') else item for item in entity.line_items]

        cursor.execute("""
            INSERT OR REPLACE INTO invoices
            (id, invoice_number, order_id, customer_id, billing_address_json,
             line_items_json, subtotal_json, tax_total_json, discount_total_json,
             total_json, status, issue_date, due_date, paid_date, notes, terms,
             metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.id, entity.invoice_number, entity.order_id, entity.customer_id,
            _json_dumps(entity.billing_address.to_dict() if entity.billing_address else None),
            _json_dumps(line_items_dicts),
            _json_dumps(entity.subtotal.to_dict()),
            _json_dumps(entity.tax_total.to_dict()),
            _json_dumps(entity.discount_total.to_dict()),
            _json_dumps(entity.total.to_dict()),
            entity.status.value,
            entity.issue_date.isoformat() if entity.issue_date else None,
            entity.due_date.isoformat() if entity.due_date else None,
            entity.paid_date.isoformat() if entity.paid_date else None,
            entity.notes, entity.terms,
            _json_dumps(entity.metadata),
            entity.created_at.isoformat(), entity.updated_at.isoformat()
        ))
        conn.commit()
        return entity

    def find_by_id(self, entity_id: str) -> Optional[Invoice]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        return self._row_to_invoice(row) if row else None

    def find_by_number(self, invoice_number: str) -> Optional[Invoice]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,))
        row = cursor.fetchone()
        return self._row_to_invoice(row) if row else None

    def find_by_order(self, order_id: str) -> Optional[Invoice]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        return self._row_to_invoice(row) if row else None

    def find_by_customer(self, customer_id: str) -> List[Invoice]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE customer_id = ?", (customer_id,))
        return [self._row_to_invoice(row) for row in cursor.fetchall()]

    def find_by_status(self, status: InvoiceStatus) -> List[Invoice]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE status = ?", (status.value,))
        return [self._row_to_invoice(row) for row in cursor.fetchall()]

    def find_all(self) -> List[Invoice]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices")
        return [self._row_to_invoice(row) for row in cursor.fetchall()]

    def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[Invoice]:
        entity = self.find_by_id(entity_id)
        if not entity:
            return None
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        return self.save(entity)

    def update_status(self, invoice_id: str, status: InvoiceStatus) -> Optional[Invoice]:
        invoice = self.find_by_id(invoice_id)
        if not invoice:
            return None
        invoice.status = status
        now = datetime.now(timezone.utc)
        if status == InvoiceStatus.PAID:
            invoice.paid_date = now
        return self.save(invoice)

    def delete(self, entity_id: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE id = ?", (entity_id,))
        conn.commit()
        return cursor.rowcount > 0
