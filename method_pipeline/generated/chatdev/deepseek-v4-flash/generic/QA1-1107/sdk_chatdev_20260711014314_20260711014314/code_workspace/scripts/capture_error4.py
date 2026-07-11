"""Capture the actual error from the server on port 8091."""
import asyncio
import httpx

BASE_URL = "http://localhost:8091"

async def test():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
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

        # Step 2a: Review - capture the full error
        print("\n--- Step 2a: Review ---")
        review_resp = await client.post(f"/api/v1/orders/{order['id']}/review")
        print(f"Review Status: {review_resp.status_code}")
        print(f"Review Headers: {dict(review_resp.headers)}")
        print(f"Review Body: {review_resp.text}")

asyncio.run(test())
