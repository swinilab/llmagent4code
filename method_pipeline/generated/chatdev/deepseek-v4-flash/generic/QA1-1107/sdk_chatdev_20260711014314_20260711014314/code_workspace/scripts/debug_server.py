"""Start server and run test, capturing server logs."""
import asyncio
import httpx
import subprocess
import time
import sys
from datetime import date, timedelta

async def test():
    # Start server
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8091"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/swe/llmagent4code/method_pipeline/generated/chatdev/deepseek-v4-flash/generic/QA1-1107/sdk_chatdev_20260711014314_20260711014314/code_workspace",
    )
    time.sleep(3)
    
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8091", timeout=30) as client:
            # Create customer
            cust_resp = await client.post(
                "/api/v1/customers/",
                json={"name": "Test Customer", "address": "123 Test St", "phone": "+1-555-TEST", "banking_details": {"bank": "Test Bank", "account": "TEST123"}, "role": "CUSTOMER"},
            )
            print(f"Customer: {cust_resp.status_code}")
            customer = cust_resp.json()
            print(f"  Customer: {customer['id']}")

            # Create product
            prod_resp = await client.post(
                "/api/v1/products/",
                json={"description": "Test Product", "pricing": {"base_price": 49.99, "currency": "USD"}},
            )
            print(f"Product: {prod_resp.status_code}")
            product = prod_resp.json()
            print(f"  Product: {product['id']}")

            # Step 1: Place order
            order_resp = await client.post(
                "/api/v1/orders/",
                json={
                    "customer_id": customer["id"],
                    "line_items": [{"product_id": product["id"], "product_description": product["description"], "quantity": 2, "unit_price": 49.99}],
                    "notes": "Test order",
                },
            )
            print(f"Order: {order_resp.status_code}")
            order = order_resp.json()
            print(f"  Order: {order['id']} Status: {order['status']}")

            # Step 2a: Review
            print("\n--- Step 2a: Review ---")
            review_resp = await client.post(f"/api/v1/orders/{order['id']}/review")
            print(f"Review Status: {review_resp.status_code}")
            print(f"Review Body: {review_resp.text}")
    finally:
        proc.terminate()
        stdout, stderr = proc.communicate()
        print("\n=== SERVER STDOUT ===")
        print(stdout.decode()[-2000:])
        print("\n=== SERVER STDERR ===")
        print(stderr.decode()[-2000:])

asyncio.run(test())
