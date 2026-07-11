"""Quick test of accept order."""
import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8070"

async def test():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Create customer
        cust_resp = await client.post(
            "/api/v1/customers/",
            json={"name": "Test2", "address": "456 St", "phone": "555", "banking_details": {}, "role": "CUSTOMER"},
        )
        print(f"Customer: {cust_resp.status_code}")
        customer = cust_resp.json()
        
        # Create product
        prod_resp = await client.post(
            "/api/v1/products/",
            json={"description": "Test Product 2", "pricing": {"base_price": 20, "currency": "USD"}},
        )
        print(f"Product: {prod_resp.status_code}")
        product = prod_resp.json()
        
        # Create order
        order_data = {
            "customer_id": customer["id"],
            "line_items": [
                {
                    "product_id": product["id"],
                    "product_description": "Test Product 2",
                    "quantity": 1,
                    "unit_price": 20,
                    "currency": "USD",
                }
            ],
            "notes": "Test order",
        }
        order_resp = await client.post("/api/v1/orders/", json=order_data)
        print(f"Order create: {order_resp.status_code}")
        order = order_resp.json()
        print(f"Order ID: {order['id']}, Status: {order['status']}")
        
        # Accept order
        accept_resp = await client.post(f"/api/v1/orders/{order['id']}/accept")
        print(f"Accept: {accept_resp.status_code}")
        if accept_resp.status_code != 200:
            print(f"Response: {accept_resp.text}")
        else:
            order = accept_resp.json()
            print(f"Order status: {order['status']}")

asyncio.run(test())
