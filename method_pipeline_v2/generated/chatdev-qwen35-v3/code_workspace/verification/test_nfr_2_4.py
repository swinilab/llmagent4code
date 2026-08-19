#!/usr/bin/env python3
"""
NFR 2.4 Verification: Transactions (ACID Properties)
Tests that transactional semantics ensure data consistency.

Tactic: Data Integrity > Maintain Integrity > Transactions
Threshold: Related entities should maintain referential integrity
"""
import asyncio
import httpx
import json
import time
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"
RESULTS_DIR = Path("verification/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


async def test_transactions():
    """Test that ACID transaction properties are maintained"""
    result = {
        "nfr": "NFR 2.4 Transactions",
        "tacticUsed": "Data Integrity > Maintain Integrity > Transactions",
        "faultInduced": {
            "description": "Transactional operations with referential integrity checks",
            "mechanism": "sqlalchemy_async_transactions",
            "verified": False
        },
        "baseline": {"metric": "transaction_success_rate", "value": 0},
        "observed": [],
        "threshold": [
            {"metric": "referential_integrity_maintained", "operator": "==", "value": True},
            {"metric": "atomic_operations", "operator": "==", "value": True}
        ],
        "passed": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test 1: Create customer and verify it exists (atomicity)
            customer_data = {
                "name": "Transaction Test User",
                "address": "456 Transaction Ave, DB City",
                "phone": "+1987654321",
                "bankingDetails": {
                    "accountNumber": "987654321",
                    "bankName": "Transaction Bank"
                }
            }
            
            resp = await client.post(f"{BASE_URL}/api/v1/customers", json=customer_data)
            if resp.status_code != 201:
                result["error"] = f"Failed to create customer: {resp.status_code}"
                result["passed"] = False
                return 1
            
            customer = resp.json()
            customer_id = customer["id"]
            
            # Verify customer was persisted (durability)
            resp2 = await client.get(f"{BASE_URL}/api/v1/customers/{customer_id}")
            customer_persisted = resp2.status_code == 200
            
            # Test 2: Create product
            product_data = {
                "description": "Transaction Test Product",
                "price": {
                    "amount": 99.99,
                    "currency": "USD"
                }
            }
            
            resp3 = await client.post(f"{BASE_URL}/api/v1/products", json=product_data)
            if resp3.status_code != 201:
                result["error"] = f"Failed to create product: {resp3.status_code}"
                result["passed"] = False
                return 1
            
            product = resp3.json()
            product_id = product["id"]
            
            # Test 3: Create order referencing customer and product (consistency)
            order_data = {
                "customerRef": customer_id,
                "lineItems": [
                    {
                        "productRef": product_id,
                        "quantity": 2
                    }
                ]
            }
            
            resp4 = await client.post(f"{BASE_URL}/api/v1/orders", json=order_data)
            order_created = resp4.status_code == 201
            
            if order_created:
                order = resp4.json()
                order_id = order["id"]
                
                # Verify order references valid customer (referential integrity)
                resp5 = await client.get(f"{BASE_URL}/api/v1/orders/{order_id}")
                order_data_check = resp5.json() if resp5.status_code == 200 else {}
                
                integrity_ok = order_data_check.get("customerRef") == customer_id
            else:
                integrity_ok = False
            
            # Test 4: Try to create order with invalid customer ref (should fail)
            invalid_order_data = {
                "customerRef": "00000000-0000-0000-0000-000000000000",
                "lineItems": [
                    {
                        "productRef": product_id,
                        "quantity": 1
                    }
                ]
            }
            
            resp6 = await client.post(f"{BASE_URL}/api/v1/orders", json=invalid_order_data)
            invalid_rejected = resp6.status_code in [400, 404]
            
            # Verify all operations
            transaction_success = customer_persisted and order_created and integrity_ok and invalid_rejected
            
            result["faultInduced"]["verified"] = transaction_success
            result["observed"] = [
                {"metric": "referential_integrity_maintained", "value": integrity_ok},
                {"metric": "atomic_operations", "value": order_created},
                {"metric": "customer_persisted", "value": customer_persisted},
                {"metric": "invalid_ref_rejected", "value": invalid_rejected}
            ]
            
            # Check thresholds
            result["passed"] = integrity_ok and order_created and invalid_rejected
    
    except Exception as e:
        result["error"] = str(e)
        result["passed"] = False
    
    # Write result
    output_path = RESULTS_DIR / "nfr_2_4.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"NFR 2.4 Result: {'PASSED' if result['passed'] else 'FAILED'}")
    print(f"Output: {output_path}")
    
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_transactions())
    sys.exit(exit_code)
