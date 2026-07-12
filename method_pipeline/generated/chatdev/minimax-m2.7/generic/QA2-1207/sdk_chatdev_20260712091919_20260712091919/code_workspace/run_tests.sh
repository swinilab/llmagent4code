#!/bin/bash
cd oms_backend
python -m pytest tests/test_oms.py -v 2>&1 | head -100
