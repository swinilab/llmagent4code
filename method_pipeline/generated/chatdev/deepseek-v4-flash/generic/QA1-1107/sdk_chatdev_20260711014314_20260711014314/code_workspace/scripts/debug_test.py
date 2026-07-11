"""Debug script to test order creation."""
import asyncio
import httpx

BASE_URL = "http://localhost:8007"

async def debug():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Check health
        health_resp = await client.get("/health")
        print(f"Health: {health_resp.status_code} - {health_resp.text}")
        
        # Create customer
        cust_resp = await client.post(
            "/api/v1/customers/",
            json={
                "name": "Debug Customer",
                "address": "123 Test St",
                "phone": "+1-555-TEST",
                "banking_details": {"bank": "Test", "account": "123"},
                "role": "CUSTOMER",
            },
        )
        print(f"Customer create: {cust_resp.status_code}")
        if cust_resp.status_code != 201:
            print(cust_resp.text)
            return
        customer = cust_resp.json()
        print(f"Customer: {customer['id']}")

        # Create product
        prod_resp = await client.post(
            "/api/v1/products/",
            json={
                "description": "Debug Product",
                "pricing": {"base_price": 49.99, "currency": "USD"},
            },
        )
        print(f"Product create: {prod_resp.status_code}")
        if prod_resp.status_code != 201:
            print(prod_resp.text)
            return
        product = prod_resp.json()
        print(f"Product: {product['id']}")

        # Try creating order
        order_data = {
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
            "notes": "Test order",
        }
        print(f"Order data: {order_data}")
        order_resp = await client.post("/api/v1/orders/", json=order_data)
        print(f"Order create: {order_resp.status_code}")
        print(f"Response: {order_resp.text}")

if __name__ == "__main__":
    asyncio.run(debug())
