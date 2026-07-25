#!/usr/bin/env python3
"""Debug server startup and request handling"""
import asyncio
import sys
sys.path.insert(0, '/home/swe/llmagent4code/method_pipeline_v2/generated/sdk_chatdev_20260725084518_20260725084518/code_workspace')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("Testing customer creation via TestClient...")
response = client.post(
    "/api/v1/customers",
    json={
        "name": "Test User",
        "address": "123 Main St",
        "phone": "+1234567890",
        "accountNumber": "123456789",
        "bankName": "Test Bank",
        "role": "CUSTOMER"
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
if response.status_code == 500:
    print("Check server logs for traceback")
