#!/usr/bin/env python3
"""Debug customer creation with traceback"""
import httpx
import traceback

try:
    response = httpx.post(
        "http://localhost:8001/api/v1/customers",
        json={
            "name": "Test User",
            "address": "123 Main St",
            "phone": "+1234567890",
            "accountNumber": "123456",
            "bankName": "Test Bank",
            "role": "CUSTOMER"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
    traceback.print_exc()
