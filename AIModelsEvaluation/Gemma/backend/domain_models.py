from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Customer:
    customer_id: int
    name: str
    address: str
    phone: str
    banking_details: str
    role: str  # 'customer', 'order_staff', 'accountant'
    order_history: List[int] = field(default_factory=list)

@dataclass
class Order:
    order_id: int
    customer_id: int
    items: List[str]
    total_amount: float
    status: str  # 'pending', 'accepted', 'invoiced', 'paid', 'shipped', 'completed'
    order_date: datetime = field(default_factory=datetime.now)
    invoice_reference: Optional[int] = None

@dataclass
class Product:
    product_id: int
    description: str
    price: float

@dataclass
class Payment:
    payment_id: int
    invoice_reference: int
    amount: float
    status: str  # 'pending', 'completed', 'failed'
    payment_method: str
    payment_date: datetime = field(default_factory=datetime.now)

@dataclass
class Invoice:
    invoice_id: int
    customer_id: int
    order_id: int
    amount: float
    status: str  # 'pending', 'paid', 'overdue'
    invoice_date: datetime = field(default_factory=datetime.now)