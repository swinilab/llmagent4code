#!/usr/bin/env python3
"""Test runner script"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "oms_backend/tests/test_oms.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    cwd="/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA2-1207/sdk_chatdev_20260712091919_20260712091919/code_workspace"
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
