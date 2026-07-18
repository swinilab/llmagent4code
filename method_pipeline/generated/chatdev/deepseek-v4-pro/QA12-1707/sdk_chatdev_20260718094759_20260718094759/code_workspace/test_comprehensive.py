"""Comprehensive import and basic functionality test."""
import asyncio
from src.database import init_db, dispose_engine, get_session
from src.models import Customer, Product, Order, OrderStatus, Payment, PaymentStatus, PaymentMethod, Invoice, InvoiceStatus
from src.schemas import CustomerCreate, CustomerResponse, ProductCreate, ProductResponse, OrderCreate, LineItem, OrderResponse, PaymentCreate, PaymentResponse, InvoiceCreate, InvoiceResponse
from src.repositories import CustomerRepository, ProductRepository, OrderRepository, PaymentRepository, InvoiceRepository
from src.services import CustomerService, ProductService, OrderService, PaymentService, InvoiceService, WorkflowService
from src.middleware import CircuitBreaker, circuit_breaker, RateLimiter, RateLimitMiddleware, register_error_handlers
from src.utils.exceptions import AppError, NotFoundError, ConflictError, ValidationError, PaymentError, ServiceUnavailableError, RateLimitError
from src.config import settings

print("All imports successful!")
print(f"Settings: host={settings.host}, port={settings.port}, db={settings.database_url}")

async def test_db():
    await init_db()
    print("DB initialized successfully")
    await dispose_engine()
    print("DB disposed successfully")

asyncio.run(test_db())
print("All tests passed!")
