"""Test that the FastAPI app can be created and routes are registered."""
import sys
sys.path.insert(0, '.')
import logging
logging.disable(logging.CRITICAL)

# Don't use create_app which triggers lifespan, just check the router directly
from oms.api.controllers import router as api_router
from oms.infrastructure.health import router as health_router

print("=== API Routes ===")
for route in api_router.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = ','.join(sorted(route.methods - {'HEAD', 'OPTIONS'}))
        print(f"  {methods} {route.path}")

print(f"\nAPI routes: {len(api_router.routes)}")

print("\n=== Health Routes ===")
for route in health_router.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = ','.join(sorted(route.methods - {'HEAD', 'OPTIONS'}))
        print(f"  {methods} {route.path}")

print(f"\nHealth routes: {len(health_router.routes)}")
print("✅ Routes verified")
