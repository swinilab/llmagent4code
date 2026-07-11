import httpx
import asyncio
import subprocess
import time

async def test():
    # Start server on a different port
    proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)
    
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=30) as client:
            # Create customer
            cust_resp = await client.post("/api/v1/customers/", json={
                "name": "Test Customer",
                "address": "123 Test St",
                "phone": "+1-555-TEST",
                "banking_details": {"bank": "Test Bank", "account": "TEST123"},
                "role": "CUSTOMER",
            })
            print(f"Customer: {cust_resp.status_code}")
            if cust_resp.status_code != 201:
                print(f"Error: {cust_resp.text}")
                return
            customer = cust_resp.json()
            
            # Create product
            prod_resp = await client.post("/api/v1/products/", json={
                "description": "Test Product - Widget",
                "pricing": {"base_price": 49.99, "currency": "USD"},
            })
            print(f"Product: {prod_resp.status_code}")
            if prod_resp.status_code != 201:
                print(f"Error: {prod_resp.text}")
                return
            product = prod_resp.json()
            
            # Create order
            order_resp = await client.post("/api/v1/orders/", json={
                "customer_id": customer["id"],
                "line_items": [
                    {
                        "product_id": product["id"],
                        "product_description": product["description"],
                        "quantity": 2,
                        "unit_price": 49.99,
                        "currency": "USD",
                    }
                ],
                "notes": "Please handle with care",
            })
            print(f"Order: {order_resp.status_code}")
            if order_resp.status_code != 201:
                print(f"Error: {order_resp.text}")
            else:
                order = order_resp.json()
                print(f"Order created: {order['id']} - Status: {order['status']}")
                
                # Test review
                review_resp = await client.post(f"/api/v1/orders/{order['id']}/review")
                print(f"Review: {review_resp.status_code}")
                if review_resp.status_code == 200:
                    order = review_resp.json()
                    print(f"  Status -> {order['status']}")
                
                # Test accept
                accept_resp = await client.post(f"/api/v1/orders/{order['id']}/accept")
                print(f"Accept: {accept_resp.status_code}")
                if accept_resp.status_code == 200:
                    order = accept_resp.json()
                    print(f"  Status -> {order['status']}")
    finally:
        proc.terminate()
        proc.wait()

asyncio.run(test())
