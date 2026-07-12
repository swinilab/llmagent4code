#!/usr/bin/env python
"""Quick test to verify imports work."""
import sys
sys.path.insert(0, 'oms_backend')

try:
    from src.domain.models import Order, Customer, Product, Payment, Invoice, OrderStatus
    print("✓ Domain models imported successfully")
except Exception as e:
    print(f"✗ Domain model import failed: {e}")
    sys.exit(1)

try:
    from src.infrastructure.database import SessionLocal, init_db
    print("✓ Database module imported successfully")
except Exception as e:
    print(f"✗ Database module import failed: {e}")
    sys.exit(1)

try:
    from src.infrastructure.repositories import OrderRepository
    print("✓ Repositories imported successfully")
except Exception as e:
    print(f"✗ Repository import failed: {e}")
    sys.exit(1)

try:
    from src.services.order_service import OrderService
    print("✓ Services imported successfully")
except Exception as e:
    print(f"✗ Service import failed: {e}")
    sys.exit(1)

try:
    from src.utils.resilience import CircuitBreaker, FeatureFlags, StateManager
    print("✓ Resilience utils imported successfully")
except Exception as e:
    print(f"✗ Resilience utils import failed: {e}")
    sys.exit(1)

print("\nAll imports successful!")
