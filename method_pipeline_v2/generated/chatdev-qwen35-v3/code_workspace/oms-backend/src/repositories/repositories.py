import sqlite3
import json
import uuid
from typing import Dict, List, Optional, Any, TypeVar, Generic
from abc import ABC, abstractmethod
from datetime import datetime
import threading

T = TypeVar("T")


class BaseRepository(Generic[T], ABC):
    """Base repository with in-memory storage and file persistence."""
    
    def __init__(self, db_path: str, table_name: str):
        self.db_path = db_path
        self.table_name = table_name
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def _serialize(self, obj: Any) -> str:
        """Serialize object to JSON string."""
        if hasattr(obj, "model_dump"):
            return json.dumps(obj.model_dump())
        return json.dumps(obj)
    
    def _deserialize(self, data: str, model_class: type) -> Any:
        """Deserialize JSON string to model object."""
        obj_data = json.loads(data)
        return model_class(**obj_data)
    
    def save(self, entity: T) -> T:
        """Save entity to database."""
        with self._lock:
            entity_id = getattr(entity, "id", str(uuid.uuid4()))
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"INSERT OR REPLACE INTO {self.table_name} (id, data, created_at) VALUES (?, ?, ?)",
                    (entity_id, self._serialize(entity), datetime.utcnow().isoformat())
                )
                conn.commit()
            return entity
    
    def find_by_id(self, entity_id: str, model_class: type) -> Optional[T]:
        """Find entity by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"SELECT data FROM {self.table_name} WHERE id = ?",
                (entity_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._deserialize(row[0], model_class)
            return None
    
    def find_all(self, model_class: type) -> List[T]:
        """Find all entities."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"SELECT data FROM {self.table_name}")
            return [self._deserialize(row[0], model_class) for row in cursor.fetchall()]
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    f"DELETE FROM {self.table_name} WHERE id = ?",
                    (entity_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"SELECT 1 FROM {self.table_name} WHERE id = ?",
                (entity_id,)
            )
            return cursor.fetchone() is not None


class CustomerRepository(BaseRepository):
    def __init__(self, db_path: str = "oms.db"):
        super().__init__(db_path, "customers")
    
    def save(self, customer) -> type(customer):
        return super().save(customer)
    
    def find_by_id(self, customer_id: str):
        from src.models import Customer
        return super().find_by_id(customer_id, Customer)
    
    def find_all(self) -> List:
        from src.models import Customer
        return super().find_all(Customer)


class ProductRepository(BaseRepository):
    def __init__(self, db_path: str = "oms.db"):
        super().__init__(db_path, "products")
    
    def save(self, product) -> type(product):
        return super().save(product)
    
    def find_by_id(self, product_id: str):
        from src.models import Product
        return super().find_by_id(product_id, Product)
    
    def find_all(self) -> List:
        from src.models import Product
        return super().find_all(Product)


class OrderRepository(BaseRepository):
    def __init__(self, db_path: str = "oms.db"):
        super().__init__(db_path, "orders")
    
    def save(self, order) -> type(order):
        return super().save(order)
    
    def find_by_id(self, order_id: str):
        from src.models import Order
        return super().find_by_id(order_id, Order)
    
    def find_all(self) -> List:
        from src.models import Order
        return super().find_all(Order)
    
    def update_status(self, order_id: str, new_status: str) -> bool:
        """Update order status and updatedAt timestamp."""
        with self._lock:
            order = self.find_by_id(order_id)
            if not order:
                return False
            
            order.status = new_status
            order.updatedAt = datetime.utcnow().isoformat() + "Z"
            self.save(order)
            return True
    
    def set_invoice_ref(self, order_id: str, invoice_id: str) -> bool:
        """Set invoice reference on order."""
        with self._lock:
            order = self.find_by_id(order_id)
            if not order:
                return False
            
            order.invoiceRef = invoice_id
            order.updatedAt = datetime.utcnow().isoformat() + "Z"
            self.save(order)
            return True


class PaymentRepository(BaseRepository):
    def __init__(self, db_path: str = "oms.db"):
        super().__init__(db_path, "payments")
    
    def save(self, payment) -> type(payment):
        return super().save(payment)
    
    def find_by_id(self, payment_id: str):
        from src.models import Payment
        return super().find_by_id(payment_id, Payment)
    
    def find_all(self) -> List:
        from src.models import Payment
        return super().find_all(Payment)
    
    def find_by_order_ref(self, order_id: str) -> List:
        """Find all payments for an order."""
        payments = self.find_all()
        return [p for p in payments if p.orderRef == order_id]


class InvoiceRepository(BaseRepository):
    def __init__(self, db_path: str = "oms.db"):
        super().__init__(db_path, "invoices")
    
    def save(self, invoice) -> type(invoice):
        return super().save(invoice)
    
    def find_by_id(self, invoice_id: str):
        from src.models import Invoice
        return super().find_by_id(invoice_id, Invoice)
    
    def find_all(self) -> List:
        from src.models import Invoice
        return super().find_all(Invoice)
    
    def find_by_order_ref(self, order_id: str):
        """Find invoice by order reference."""
        invoices = self.find_all()
        for inv in invoices:
            if inv.orderRef == order_id:
                return inv
        return None
