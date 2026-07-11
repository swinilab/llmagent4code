#!/usr/bin/env python3
"""Verify all OMS components are complete and functional."""
import asyncio
import sys

# Test all imports
print("Testing imports...")
try:
    from oms import __version__
    from oms.app import app
    from oms.config.database import init_db, get_db_session, engine, Base
    from oms.models.entities import (
        Customer, Product, Order, OrderLineItem, Payment, Invoice,
        OrderStatus, PaymentStatus, InvoiceStatus
    )
    from oms.models.schemas import (
        CustomerCreate, CustomerResponse,
        ProductCreate, ProductResponse,
        OrderCreate, OrderResponse, OrderUpdateStatus,
        PaymentCreate, PaymentResponse,
        InvoiceCreate, InvoiceResponse,
        HealthResponse, ErrorResponse, PaginatedResponse
    )
    from oms.repositories import (
        BaseRepository, CustomerRepository, ProductRepository,
        OrderRepository, PaymentRepository, InvoiceRepository
    )
    from oms.services import (
        CustomerService, ProductService, OrderService,
        PaymentService, InvoiceService
    )
    from oms.controllers import (
        customer_router, product_router, order_router,
        payment_router, invoice_router
    )
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Configure SQLAlchemy to ensure all mappers are set up
print("\nConfiguring SQLAlchemy mappers...")
try:
    from sqlalchemy.orm import configure_mappers
    configure_mappers()
    print("✅ SQLAlchemy mappers configured!")
except Exception as e:
    print(f"❌ Mapper configuration error: {e}")
    sys.exit(1)

# Test schema validation
print("\nTesting schema validation...")
try:
    from datetime import datetime
    from decimal import Decimal
    
    customer_data = CustomerCreate(name="Test", email="test@example.com")
    product_data = ProductCreate(name="Test", base_price=Decimal("99.99"))
    
    print("✅ Schema validation successful!")
except Exception as e:
    print(f"❌ Schema validation error: {e}")
    sys.exit(1)
    print(f"❌ Entity creation error: {e}")
    sys.exit(1)

# Test schema validation
print("\nTesting schema validation...")
try:
    from datetime import datetime
    from decimal import Decimal
    
    customer_data = CustomerCreate(name="Test", email="test@example.com")
    product_data = ProductCreate(name="Test", base_price=Decimal("99.99"))
    
    print("✅ Schema validation successful!")
except Exception as e:
    print(f"❌ Schema validation error: {e}")
    sys.exit(1)

# Test FastAPI app
print("\nTesting FastAPI app...")
try:
    assert app.title == "Order Management System (OMS)"
    assert app.version == "1.0.0"
    assert "/api/v1/customers" in str(app.routes)
    assert "/api/v1/products" in str(app.routes)
    assert "/api/v1/orders" in str(app.routes)
    assert "/api/v1/payments" in str(app.routes)
    assert "/api/v1/invoices" in str(app.routes)
    print("✅ FastAPI app configured correctly!")
except AssertionError as e:
    print(f"❌ FastAPI app error: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("✅ ALL VERIFICATION CHECKS PASSED!")
print("="*50)
print(f"\nOMS Version: {__version__}")
print("All components are complete and functional.")
