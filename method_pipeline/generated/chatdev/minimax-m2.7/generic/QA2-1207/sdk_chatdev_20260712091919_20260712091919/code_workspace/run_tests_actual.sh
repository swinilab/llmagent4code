#!/bin/bash
cd /home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA2-1207/sdk_chatdev_20260712091919_20260712091919/code_workspace
source .venv/bin/activate
python -m pytest oms_backend/tests/test_oms.py -v --tb=short 2>&1 | head -200
