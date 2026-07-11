"""Run the full workflow test against the running server."""
import asyncio
import httpx
from datetime import date, timedelta
BASE_URL = "http://localhost:8091"
BASE_URL = "http://localhost:8090"

async def test():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Create customer
        cust_resp = await client.post(
            "/api/v1/customers/",
            json={"name": "Test Customer", "address": "123 Test St", "phone": "+1-555-TEST", "banking_details": {"bank": "Test Bank", "account": "TEST123"}, "role": "CUSTOMER"},
        )
        print(f"Customer: {cust_resp.status_code}")
        if cust_resp.status_code != 201:
            print(cust_resp.text)
            return
        customer = cust_resp.json()
        print(f"  Customer: {customer['id']}")

        # Create product
        prod_resp = await client.post(
            "/api/v1/products/",
            json={"description": "Test Product", "pricing": {"base_price": 49.99, "currency": "USD"}},
        )
        print(f"Product: {prod_resp.status_code}")
        if prod_resp.status_code != 201:
            print(prod_resp.text)
            return
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
        if order_resp.status_code != 201:
            print(order_resp.text)
            return
        order = order_resp.json()
        print(f"  Order: {order['id']} Status: {order['status']} Total: ${order['total_amount']}")

        # Step 2a: Review
        review_resp = await client.post(f"/api/v1/orders/{order['id']}/review")
        print(f"Review: {review_resp.status_code}")
        order = review_resp.json()
        print(f"  Status: {order['status']}")

        # Step 2b: Accept
        accept_resp = await client.post(f"/api/v1/orders/{order['id']}/accept")
        print(f"Accept: {accept_resp.status_code}")
        order = accept_resp.json()
        print(f"  Status: {order['status']}")

        # Step 3: Create invoice
        today = date.today()
        due = today + timedelta(days=30)
        invoice_resp = await client.post(
            "/api/v1/invoices/",
            json={"order_id": order["id"], "billing_info": {"name": customer["name"]}, "issue_date": today.isoformat(), "due_date": due.isoformat()},
        )
        print(f"Invoice: {invoice_resp.status_code}")
        if invoice_resp.status_code != 201:
            print(invoice_resp.text)
            return
        invoice = invoice_resp.json()
        print(f"  Invoice: {invoice['id']} #{invoice['invoice_number']} Status: {invoice['status']}")

        # Step 4: Pay
        payment_resp = await client.post(
            "/api/v1/payments/",
            json={"order_id": order["id"], "amount": float(order["total_amount"]), "method": "CREDIT_CARD", "transaction_ref": "TXN001"},
        )
        print(f"Payment: {payment_resp.status_code}")
        if payment_resp.status_code != 201:
            print(payment_resp.text)
            return
        payment = payment_resp.json()
        print(f"  Payment: {payment['id']} Status: {payment['status']}")

        # Step 5: Verify payment
        verify_resp = await client.post(f"/api/v1/payments/{payment['id']}/verify")
        print(f"Verify: {verify_resp.status_code}")
        if verify_resp.status_code != 200:
            print(verify_resp.text)
            return
        payment = verify_resp.json()
        print(f"  Payment Status: {payment['status']}")

        # Check order
        order_check = await client.get(f"/api/v1/orders/{order['id']}")
        order = order_check.json()
        print(f"  Order Status: {order['status']}")

        # Step 6: Ship
        ship_resp = await client.post(f"/api/v1/orders/{order['id']}/ship")
        print(f"Ship: {ship_resp.status_code}")
        order = ship_resp.json()
        print(f"  Status: {order['status']}")

        # Step 7: Close
        close_resp = await client.post(f"/api/v1/orders/{order['id']}/close")
        print(f"Close: {close_resp.status_code}")
        order = close_resp.json()
        print(f"  Status: {order['status']}")

        print("\nWORKFLOW COMPLETED SUCCESSFULLY!")

asyncio.run(test())
