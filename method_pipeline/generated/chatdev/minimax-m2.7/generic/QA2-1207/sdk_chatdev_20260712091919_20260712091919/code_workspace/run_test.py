#!/usr/bin/env python
"""Simple test runner for OMS backend."""
import subprocess
import sys
import os

os.chdir('/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2-7/generic/QA2-1207/sdk_chatdev_20260712091919_20260712091919/code_workspace/oms_backend')

result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/test_oms.py', '-v', '--tb=short', '-x'],
    capture_output=True,
    text=True,
    cwd='.'
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
sys.exit(result.returncode)
