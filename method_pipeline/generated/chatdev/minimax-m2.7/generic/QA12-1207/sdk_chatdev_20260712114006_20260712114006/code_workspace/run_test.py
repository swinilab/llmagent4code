#!/usr/bin/env python3
"""Script to run pytest tests programmatically."""
import sys
import os

# Add oms_project to path
sys.path.insert(0, '/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA12-1207/sdk_chatdev_20260712114006_20260712114006/code_workspace/oms_project')

# Change working directory
os.chdir('/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA12-1207/sdk_chatdev_20260712114006_20260712114006/code_workspace/oms_project')

# Run pytest programmatically
import pytest
sys.exit(pytest.main(['tests/test_services.py', '-v', '--tb=short']))
