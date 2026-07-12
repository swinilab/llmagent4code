#!/usr/bin/env python
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "oms_backend/tests/test_order.py", "-v", "--tb=short"],
    cwd="/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2-7/generic/QA1-1207/sdk_chatdev_20260712091754_20260712091754/code_workspace"
)
sys.exit(result.returncode)
