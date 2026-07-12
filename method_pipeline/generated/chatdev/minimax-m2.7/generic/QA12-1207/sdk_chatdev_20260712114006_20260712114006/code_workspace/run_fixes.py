#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "oms_project/tests/test_services.py", "-v", "--tb=short"],
    capture_output=False
)
sys.exit(result.returncode)
