#!/usr/bin/env python3
"""Script to run pytest tests."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "oms_project/tests/test_services.py", "-v", "--tb=short", "--ignore=run_test.py", "--ignore=run_tests.py", "--ignore=test_imports.py"],
    capture_output=True,
    text=True,
    cwd="/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA12-1207/sdk_chatdev_20260712114006_20260712114006/code_workspace"
)
print(result.stdout)
print(result.stderr)
sys.exit(result.returncode)
