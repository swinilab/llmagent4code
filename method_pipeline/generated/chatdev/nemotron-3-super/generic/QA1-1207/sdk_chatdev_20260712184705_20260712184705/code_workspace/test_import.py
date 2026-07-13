import sys
sys.path.insert(0, 'oms_backend')
try:
    from oms_backend.app.main import app
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)