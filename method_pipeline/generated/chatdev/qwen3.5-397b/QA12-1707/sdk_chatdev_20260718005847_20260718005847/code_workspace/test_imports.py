"""Test all imports work correctly."""
print("Testing imports...")

from oms.models.customer import Customer, CustomerCreate
from oms.models.product import Product, ProductCreate
from oms.models.order import Order, OrderStatus, OrderLineItem, OrderCreate
from oms.models.payment import Payment, PaymentStatus, PaymentCreate
from oms.models.invoice import Invoice, InvoiceStatus, InvoiceCreate

from oms.repositories.customer_repository import CustomerRepository
from oms.repositories.product_repository import ProductRepository
from oms.repositories.order_repository import OrderRepository
from oms.repositories.payment_repository import PaymentRepository
from oms.repositories.invoice_repository import InvoiceRepository

from oms.services.customer_service import CustomerService
from oms.services.product_service import ProductService
from oms.services.order_service import OrderService
from oms.services.payment_service import PaymentService
from oms.services.invoice_service import InvoiceService

from oms.controllers.customer_controller import customer_router
from oms.controllers.product_controller import product_router
from oms.controllers.order_controller import order_router
from oms.controllers.payment_controller import payment_router
from oms.controllers.invoice_controller import invoice_router

from oms.app import app
from oms.server import run

print("All imports successful!")
