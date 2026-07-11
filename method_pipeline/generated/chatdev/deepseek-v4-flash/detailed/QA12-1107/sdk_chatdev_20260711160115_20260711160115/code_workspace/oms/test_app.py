"""Test that the FastAPI app can be created and routes are registered."""
import sys
sys.path.insert(0, '.')
import logging
logging.disable(logging.CRITICAL)

from oms.main import create_app

app = create_app()

print(f"Total top-level routes: {len(app.routes)}")

print("\n=== All Routes ===")
route_count = 0
for route in app.routes:
    if type(route).__name__ == '_IncludedRouter':
        # Included router - access its original_router.routes
        for sub in route.original_router.routes:
            if hasattr(sub, 'methods') and hasattr(sub, 'path'):
                methods = ','.join(sorted(sub.methods - {'HEAD', 'OPTIONS'}))
                print(f"  {methods} {sub.path}")
                route_count += 1
    elif hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = ','.join(sorted(route.methods - {'HEAD', 'OPTIONS'}))
        print(f"  {methods} {route.path}")
        route_count += 1

print(f"\nTotal routes: {route_count}")
print("✅ App created successfully")
