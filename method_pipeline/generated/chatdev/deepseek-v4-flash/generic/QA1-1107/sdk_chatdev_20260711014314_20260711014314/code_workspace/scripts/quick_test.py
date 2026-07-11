"""Quick test of order creation."""
import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8070"

async def test():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Create customer
        cust_resp = await client.post(
            "/api/v1/customers/",
            json={"name": "Test", "address": "123 St", "phone": "555", "banking_details": {}, "role": "CUSTOMER"},
        )
        print(f"Customer: {cust_resp.status_code}")
        customer = cust_resp.json()
        
        # Create product
        prod_resp = await client.post(
            "/api/v1/products/",
            json={"description": "Test Product", "pricing": {"base_price": 10, "currency": "USD"}},
        )
        print(f"Product: {prod_resp.status_code}")
        product = prod_resp.json()
        
        # Create order
        order_data = {
            "customer_id": customer["id"],
            "line_items": [
                {
                    "product_id": product["id"],
                    "product_description": "Test Product",
                    "quantity": 1,
                    "unit_price": 10,
                    "currency": "USD",
                }
            ],
            "notes": "Test order",
        }
        print(f"Sending order...")
        order_resp = await client.post("/api/v1/orders/", json=order_data)
        print(f"Order: {order_resp.status_code}")
        print(f"Response: {order_resp.text}")

asyncio.run(test())
