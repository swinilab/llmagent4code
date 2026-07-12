#!/usr/bin/env python3
"""Run the OMS Backend tests."""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now run pytest programmatically
import pytest

if __name__ == "__main__":
    exit_code = pytest.main([
        "oms_backend/tests/test_oms.py",
        "-v",
        "--tb=short",
        "--no-header"
    ])
    sys.exit(exit_code)
