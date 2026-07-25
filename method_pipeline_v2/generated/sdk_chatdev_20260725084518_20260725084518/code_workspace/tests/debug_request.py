#!/usr/bin/env python3
"""Debug controller validation"""
import sys
sys.path.insert(0, '/home/swe/llmagent4code/method_pipeline_v2/generated/sdk_chatdev_20260725084518_20260725084518/code_workspace')

from app.controllers.customer_controller import CustomerCreateRequest
from app.models.customer import CustomerRole

try:
    request = CustomerCreateRequest(
        name="Test User",
        address="123 Main St",
        phone="+1234567890",
        accountNumber="123456789",
        bankName="Test Bank",
        role="CUSTOMER"
    )
    print(f"Request created: {request}")
    print(f"Request dict: {request.model_dump()}")
except Exception as e:
    print(f"Error creating request: {e}")
    import traceback
    traceback.print_exc()
