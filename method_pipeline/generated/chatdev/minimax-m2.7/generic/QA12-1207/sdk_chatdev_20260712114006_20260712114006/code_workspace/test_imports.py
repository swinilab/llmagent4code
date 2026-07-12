#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

# Test imports
try:
    from app.domain.entities.models import *
    print("Models import: OK")
except Exception as e:
    print(f"Models import ERROR: {e}")

try:
    from app.domain.repositories.interfaces import *
    print("Repositories import: OK")
except Exception as e:
    print(f"Repositories import ERROR: {e}")

try:
    from app.adapters.persistence import *
    print("Persistence import: OK")
except Exception as e:
    print(f"Persistence import ERROR: {e}")

try:
    from app.service_layer.services.customer_service import CustomerService
    print("CustomerService import: OK")
except Exception as e:
    print(f"CustomerService import ERROR: {e}")

try:
    from app.core.config import AppConfig, configure_app, get_registry
    print("Config import: OK")
except Exception as e:
    print(f"Config import ERROR: {e}")

try:
    from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry
    print("CircuitBreaker import: OK")
except Exception as e:
    print(f"CircuitBreaker import ERROR: {e}")

try:
    from app.core.rate_limiter import RateLimiter, RateLimiterRegistry
    print("RateLimiter import: OK")
except Exception as e:
    print(f"RateLimiter import ERROR: {e}")

try:
    from app.core.events import EventBus, Event
    print("Events import: OK")
except Exception as e:
    print(f"Events import ERROR: {e}")

try:
    from app.api.schemas import *
    print("Schemas import: OK")
except Exception as e:
    print(f"Schemas import ERROR: {e}")

try:
    from app.main import app, create_app
    print("Main app import: OK")
except Exception as e:
    print(f"Main app import ERROR: {e}")

print("\nAll imports completed!")
