#!/usr/bin/env python
"""Test runner script."""
import sys
sys.path.insert(0, 'oms_project')

import pytest
sys.exit(pytest.main(["-v", "--tb=short", "oms_project/tests/test_services.py"]))
