#!/usr/bin/env python
"""Quick syntax check for all OMS modules."""
import importlib
import os
import sys

# Script lives in oms_backend/scripts/ — go up two levels to reach project root
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

# File-based modules that can't be imported via __import__ with dotted names
_file_modules = {
    "oms_backend.infra.gunicorn.conf",
    "oms_backend.infra.worker",
}

def _try_import(mod: str):
    try:
        if mod in _file_modules:
            importlib.import_module(mod)
        else:
            __import__(mod)
        return True, None
    except Exception as e:
        return False, str(e)

modules = [
    "oms_backend.core.config",
    "oms_backend.core.cache",
    "oms_backend.core.rate_limiter",
    "oms_backend.schemas.domain",
    "oms_backend.models.orm_models",
    "oms_backend.repositories.base",
    "oms_backend.repositories.entities",
    "oms_backend.services.utils",
    "oms_backend.services.customer",
    "oms_backend.services.product",
    "oms_backend.services.order",
    "oms_backend.services.invoice",
    "oms_backend.services.payment",
    "oms_backend.db.connection",
    "oms_backend.api.v1.customer",
    "oms_backend.api.v1.product",
    "oms_backend.api.v1.order",
    "oms_backend.api.v1.invoice",
    "oms_backend.api.v1.payment",
    "oms_backend.api.v1",
    "oms_backend.infra.gunicorn.conf",
    "oms_backend.infra.worker",
]

for mod in modules:
    ok, err = _try_import(mod)
    if ok:
        print(f"OK: {mod}")
    else:
        print(f"FAIL: {mod} — {err}")
        sys.exit(1)

print("\nAll modules import successfully.")
