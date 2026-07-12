#!/usr/bin/env python
import sys
sys.path.insert(0, 'oms_backend')

try:
    from src.domain.models import Customer, Order, Product, Payment, Invoice
    print("Domain models OK")
except Exception as e:
    print(f"Domain models import error: {e}")

try:
    from src.infrastructure.database import init_db, engine
    print("Database OK")
except Exception as e:
    print(f"Database import error: {e}")

try:
    from src.infrastructure.repositories import CustomerRepository, OrderRepository
    print("Repositories OK")
except Exception as e:
    print(f"Repositories import error: {e}")

try:
    from src.services.order_service import OrderService
    print("Services OK")
except Exception as e:
    print(f"Services import error: {e}")

try:
    from src.controllers.order_controller import order_router
    print("Controllers OK")
except Exception as e:
    print(f"Controllers import error: {e}")

try:
    from src.main import app
    print("Main app OK")
except Exception as e:
    print(f"Main app import error: {e}")

print("All imports successful!")
