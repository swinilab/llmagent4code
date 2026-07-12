#!/bin/bash
cd /home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA12-1207/sdk_chatdev_20260712114006_20260712114006/code_workspace/oms_project
python -m pytest tests/test_services.py -v --tb=short 2>&1
