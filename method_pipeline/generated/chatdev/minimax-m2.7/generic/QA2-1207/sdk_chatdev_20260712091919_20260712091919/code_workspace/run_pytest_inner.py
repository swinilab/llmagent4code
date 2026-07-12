#!/usr/bin/env python3
import subprocess
import sys
import os

os.chdir("/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA2-1207/sdk_chatdev_20260712091919_20260712091919/code_workspace")

# Run pytest via subprocess
result = subprocess.run(
    ["/bin/bash", "-c", "source .venv/bin/activate && python -m pytest oms_backend/tests/test_oms.py -v --tb=short 2>&1 | head -200"],
    capture_output=True,
    text=True
)
print("STDOUT:", result.stdout[:5000])
print("STDERR:", result.stderr[:2000])
print("Return code:", result.returncode)
