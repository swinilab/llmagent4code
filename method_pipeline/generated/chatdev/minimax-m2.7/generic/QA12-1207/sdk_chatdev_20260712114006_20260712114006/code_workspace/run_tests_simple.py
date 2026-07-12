#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA12-1207/sdk_chatdev_20260712114006_20260712114006/code_workspace')
os.chdir('/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA12-1207/sdk_chatdev_20260712114006_20260712114006/code_workspace/oms_project')
import pytest
sys.exit(pytest.main(['tests/test_services.py', '-v', '--tb=short']))