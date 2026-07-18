"""Quick smoke test to verify the app imports and creates."""
from oms.main import app
print(f"App created successfully: {app.title} v{app.version}")
print(f"Routes: {len(app.routes)}")
for route in app.routes:
    if hasattr(route, 'path') and '/api/' in str(getattr(route, 'path', '')):
        print(f"  {getattr(route, 'methods', set())} {route.path}")