#!/bin/bash
cd /home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA12-1207/sdk_chatdev_20260712114006_20260712114006/code_workspace
python -c "
import subprocess
import sys

result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'oms_project/tests/test_services.py', '-v', '--tb=short'],
    capture_output=True,
    text=True
)
print(result.stdout)
print(result.stderr)
sys.exit(result.returncode)
"
