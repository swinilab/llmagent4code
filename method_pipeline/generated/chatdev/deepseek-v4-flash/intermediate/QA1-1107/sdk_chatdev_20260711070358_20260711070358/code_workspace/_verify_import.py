"""Verify the OMS app can be imported and has the expected structure."""
from oms.main import app

print(f"App created successfully: {app.title}")
print(f"Routes: {len(app.routes)}")
print(f"OpenAPI URL: {app.openapi_url}")

# List all routes
for route in app.routes:
    if hasattr(route, "methods") and hasattr(route, "path"):
        print(f"  {route.methods} {route.path}")
