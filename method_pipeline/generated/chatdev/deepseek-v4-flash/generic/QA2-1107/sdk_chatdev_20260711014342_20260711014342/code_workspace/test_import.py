"""Quick smoke test for the OMS application."""
import sys
sys.path.insert(0, "oms")

from app.main import app
print("App loaded successfully")
for route in app.routes:
    path = getattr(route, "path", None)
    if path:
        print(f"  Route: {path}")
    else:
        print(f"  Route: {type(route).__name__}")
