"""Run the full workflow test against the running server on port 8070."""
import asyncio
import sys
import os
from datetime import date, timedelta

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_URL = "http://127.0.0.1:8070"


async def test_full_workflow():
    """Execute the complete 7-step order workflow via the REST API."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        print("=" * 60)
        print("OMS Complete Workflow Test")
        print("=" * 60)

        # Step 0: Seed data - create a customer and some products
        print("\n[Setup] Creating customer and products...")

        cust_resp = await client.post(
            "/api/v1/customers/",
            json={
                "name": "Test Customer",
                "address": "123 Test St",
                "phone": "+1-555-TEST",
                "banking_details": {"bank": "Test Bank", "account": "TEST123"},
                "role": "CUSTOMER",
            },
        )
        assert cust_resp.status_code == 201, f"Failed to create customer: {cust_resp.text}"
        customer = cust_resp.json()
        print(f"  Customer created: {customer['id']} - {customer['name']}")

        prod_resp = await client.post(
            "/api/v1/products/",
            json={
                "description": "Test Product - Widget",
                "pricing": {"base_price": 49.99, "currency": "USD"},
            },
        )
        assert prod_resp.status_code == 201, f"Failed to create product: {prod_resp.text}"
        product = prod_resp.json()
        print(f"  Product created: {product['id']} - {product['description']}")

        # Step 1: Customer places order
        print("\n[Step 1] Customer places order...")
        order_resp = await client.post(
            "/api/v1/orders/",
            json={
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
            },
        )
        assert order_resp.status_code == 201, f"Failed to create order: {order_resp.text}"
        order = order_resp.json()
        print(f"  Order created: {order['id']} - Status: {order['status']}")
        print(f"  Total: ${order['total_amount']}")

        # Step 2: Order Staff reviews & accepts
        print("\n[Step 2] Order Staff accepts order...")
        accept_resp = await client.post(f"/api/v1/orders/{order['id']}/accept")
        assert accept_resp.status_code == 200, f"Failed to accept order: {accept_resp.text}"
        order = accept_resp.json()
        print(f"  Order accepted: Status -> {order['status']}")

        # Step 3: Accountant creates invoice
        print("\n[Step 3] Accountant creates invoice...")
        today = date.today()
        due = today + timedelta(days=30)
        invoice_resp = await client.post(
            "/api/v1/invoices/",
            json={
                "order_id": order["id"],
                "billing_info": {
                    "customer_name": customer["name"],
                    "customer_address": customer["address"],
                    "customer_phone": customer["phone"],
                },
                "issue_date": today.isoformat(),
                "due_date": due.isoformat(),
            },
        )
        assert invoice_resp.status_code == 201, f"Failed to create invoice: {invoice_resp.text}"
        invoice = invoice_resp.json()
        print(f"  Invoice created: {invoice['id']} - #{invoice['invoice_number']}")
        print(f"  Invoice Status: {invoice['status']}")

        # Issue the invoice
        issue_resp = await client.post(f"/api/v1/invoices/{invoice['id']}/issue")
        assert issue_resp.status_code == 200, f"Failed to issue invoice: {issue_resp.text}"
        invoice = issue_resp.json()
        print(f"  Invoice issued: Status -> {invoice['status']}")

        # Check order status updated to INVOICED
        order_check = await client.get(f"/api/v1/orders/{order['id']}")
        order = order_check.json()
        print(f"  Order status after invoicing: {order['status']}")

        # Step 4: Customer pays invoice
        print("\n[Step 4] Customer pays invoice...")
        payment_resp = await client.post(
            "/api/v1/payments/",
            json={
                "order_id": order["id"],
                "amount": float(order["total_amount"]),
                "currency": "USD",
                "method": "CREDIT_CARD",
                "transaction_ref": "TXN-TEST-001",
            },
        )
        assert payment_resp.status_code == 201, f"Failed to create payment: {payment_resp.text}"
        payment = payment_resp.json()
        print(f"  Payment created: {payment['id']} - Status: {payment['status']}")

        # Step 5: Accountant verifies payment
        print("\n[Step 5] Accountant verifies payment...")
        verify_resp = await client.post(f"/api/v1/payments/{payment['id']}/verify")
        assert verify_resp.status_code == 200, f"Failed to verify payment: {verify_resp.text}"
        payment = verify_resp.json()
        print(f"  Payment verified: Status -> {payment['status']}")

        # Check order status updated to PAID
        order_check = await client.get(f"/api/v1/orders/{order['id']}")
        order = order_check.json()
        print(f"  Order status after payment: {order['status']}")

        # Check invoice marked as paid
        invoice_check = await client.get(f"/api/v1/invoices/{invoice['id']}")
        invoice = invoice_check.json()
        print(f"  Invoice status after payment: {invoice['status']}")

        # Step 6: Order Staff ships paid order
        print("\n[Step 6] Order Staff ships order...")
        ship_resp = await client.post(f"/api/v1/orders/{order['id']}/ship")
        assert ship_resp.status_code == 200, f"Failed to ship order: {ship_resp.text}"
        order = ship_resp.json()
        print(f"  Order shipped: Status -> {order['status']}")

        # Step 7: Order Staff closes completed order
        print("\n[Step 7] Order Staff closes order...")
        close_resp = await client.post(f"/api/v1/orders/{order['id']}/close")
        assert close_resp.status_code == 200, f"Failed to close order: {close_resp.text}"
        order = close_resp.json()
        print(f"  Order closed: Status -> {order['status']}")

        print("\n" + "=" * 60)
        print("WORKFLOW COMPLETED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
