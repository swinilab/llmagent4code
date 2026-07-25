#!/usr/bin/env python3
"""Debug customer model validation locally"""
import sys
sys.path.insert(0, '/home/swe/llmagent4code/method_pipeline_v2/generated/sdk_chatdev_20260725084518_20260725084518/code_workspace')

from app.models.customer import Customer, BankingDetails, CustomerRole

try:
    banking = BankingDetails(
        accountNumber="123456",
        bankName="Test Bank"
    )
    print(f"BankingDetails created: {banking}")
    
    customer = Customer(
        name="John Doe",
        address="123 Main Street, City",
        phone="+1234567890",
        bankingDetails=banking,
        role="CUSTOMER"
    )
    print(f"Customer created: {customer}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
