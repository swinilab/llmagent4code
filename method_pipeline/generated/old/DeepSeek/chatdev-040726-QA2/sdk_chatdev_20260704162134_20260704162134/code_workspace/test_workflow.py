"""
Quick integration test for the OMS API.
Runs the full workflow: Customer → Order → Accept → Invoice → Payment → Verify → Ship → Close.
"""

import httpx
import sys

BASE_URL = "http://localhost:8000"

def main():
    client = httpx.Client(base_url=BASE_URL)

    # 1. Health check
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("[PASS] Health check")

    # 2. Register customer
    r = client.post("/api/v1/customers", json={
        "name": "Jane Doe",
        "address": {"street": "456 Oak Ave", "city": "Portland", "state": "OR", "zip_code": "97201", "country": "USA"},
        "phone": "+1-555-0200",
        "banking_details": {"bank_name": "Pacific Bank", "account_number": "987654321", "routing_number": "121000358"}
    })
    assert r.status_code == 201, f"Create customer failed: {r.text}"
    customer = r.json()
    customer_id = customer["id"]
    print(f"[PASS] Customer created: {customer_id}")

    # 3. Create product
    r = client.post("/api/v1/products", json={
        "description": "Super Widget",
        "base_price": {"amount": 49.99, "currency": "USD"}
    })
    assert r.status_code == 201, f"Create product failed: {r.text}"
    product = r.json()
    product_id = product["id"]
    print(f"[PASS] Product created: {product_id}")

    # 4. Place order (Step 1)
    r = client.post("/api/v1/orders", json={
        "customer_id": customer_id,
        "line_items": [{
            "product_id": product_id,
            "product_description": "Super Widget",
            "quantity": 3,
            "unit_price": {"amount": 49.99, "currency": "USD"}
        }]
    })
    assert r.status_code == 201, f"Place order failed: {r.text}"
    order = r.json()
    order_id = order["id"]
    assert order["status"] == "pending", f"Expected pending, got {order['status']}"
    print(f"[PASS] Order placed: {order_id} (status: {order['status']})")

    # 5. Accept order (Step 2) — staff_id in request body
    staff_id = "00000000-0000-0000-0000-000000000001"
    r = client.patch(f"/api/v1/orders/{order_id}/accept", json={"staff_id": staff_id})
    assert r.status_code == 200, f"Accept order failed: {r.text}"
    order = r.json()
    assert order["status"] == "accepted", f"Expected accepted, got {order['status']}"
    print(f"[PASS] Order accepted (status: {order['status']})")

    # 6. Create invoice (Step 3)
    r = client.post("/api/v1/invoices", json={
        "order_id": order_id,
        "customer_id": customer_id,
        "billing_address": {"street": "456 Oak Ave", "city": "Portland", "state": "OR", "zip_code": "97201", "country": "USA"},
        "tax": {"amount": 7.50, "currency": "USD"},
        "due_date": "2025-08-15"
    })
    assert r.status_code == 201, f"Create invoice failed: {r.text}"
    invoice = r.json()
    invoice_id = invoice["id"]
    assert invoice["status"] == "issued", f"Expected issued, got {invoice['status']}"
    print(f"[PASS] Invoice created: {invoice_id} (status: {invoice['status']})")

    # 7. Test payment amount mismatch rejection (CRITICAL VALIDATION)
    r = client.post("/api/v1/payments", json={
        "order_id": order_id,
        "invoice_id": invoice_id,
        "amount": {"amount": 0.01, "currency": "USD"},
        "method": "credit_card"
    })
    assert r.status_code == 400, f"Expected 400 for mismatched amount, got {r.status_code}: {r.text}"
    detail = r.json()["detail"]
    assert "does not match invoice total" in detail, f"Expected amount mismatch error, got: {detail}"
    print(f"[PASS] Payment amount mismatch correctly rejected: {detail}")

    # 8. Make payment (Step 4) — amount must match invoice total (149.97 + 7.50 = 157.47)
    r = client.post("/api/v1/payments", json={
        "order_id": order_id,
        "invoice_id": invoice_id,
        "amount": {"amount": 157.47, "currency": "USD"},
        "method": "credit_card"
    })
    assert r.status_code == 201, f"Create payment failed: {r.text}"
    payment = r.json()
    payment_id = payment["id"]
    assert payment["status"] == "pending", f"Expected pending, got {payment['status']}"
    print(f"[PASS] Payment created: {payment_id} (status: {payment['status']})")

    # 9. Verify payment (Step 5) — accountant_id in request body
    accountant_id = "00000000-0000-0000-0000-000000000002"
    r = client.patch(f"/api/v1/payments/{payment_id}/verify", json={"accountant_id": accountant_id})
    assert r.status_code == 200, f"Verify payment failed: {r.text}"
    payment = r.json()
    assert payment["status"] == "verified", f"Expected verified, got {payment['status']}"
    print(f"[PASS] Payment verified (status: {payment['status']})")

    # 10. Ship order (Step 6) — staff_id in request body
    r = client.patch(f"/api/v1/orders/{order_id}/ship", json={"staff_id": staff_id})
    assert r.status_code == 200, f"Ship order failed: {r.text}"
    order = r.json()
    assert order["status"] == "shipped", f"Expected shipped, got {order['status']}"
    print(f"[PASS] Order shipped (status: {order['status']})")

    # 11. Close order (Step 7) — staff_id in request body
    r = client.patch(f"/api/v1/orders/{order_id}/close", json={"staff_id": staff_id})
    assert r.status_code == 200, f"Close order failed: {r.text}"
    order = r.json()
    assert order["status"] == "completed", f"Expected completed, got {order['status']}"
    print(f"[PASS] Order completed (status: {order['status']})")

    # 12. Verify final state
    r = client.get(f"/api/v1/orders/{order_id}")
    assert r.status_code == 200
    final = r.json()
    assert final["status"] == "completed"
    print(f"[PASS] Final order state verified: {final['status']}")

    # 13. Verify invoice is paid
    r = client.get(f"/api/v1/invoices/{invoice_id}")
    assert r.status_code == 200
    inv = r.json()
    assert inv["status"] == "paid"
    print(f"[PASS] Invoice status verified: {inv['status']}")

    # 14. Test cancel order
    r = client.post("/api/v1/orders", json={
        "customer_id": customer_id,
        "line_items": [{
            "product_id": product_id,
            "product_description": "Super Widget",
            "quantity": 1,
            "unit_price": {"amount": 49.99, "currency": "USD"}
        }]
    })
    assert r.status_code == 201
    cancel_order_id = r.json()["id"]
    r = client.patch(f"/api/v1/orders/{cancel_order_id}/cancel", json={"reason": "Test cancellation"})
    assert r.status_code == 200, f"Cancel order failed: {r.text}"
    cancelled = r.json()
    assert cancelled["status"] == "cancelled", f"Expected cancelled, got {cancelled['status']}"
    print(f"[PASS] Order cancellation works (status: {cancelled['status']})")

    # 15. Test currency mismatch rejection
    r = client.post("/api/v1/orders", json={
        "customer_id": customer_id,
        "line_items": [{
            "product_id": product_id,
            "product_description": "Super Widget",
            "quantity": 1,
            "unit_price": {"amount": 49.99, "currency": "USD"}
        }]
    })
    assert r.status_code == 201
    order2_id = r.json()["id"]
    r = client.patch(f"/api/v1/orders/{order2_id}/accept", json={"staff_id": staff_id})
    assert r.status_code == 200
    r = client.post("/api/v1/invoices", json={
        "order_id": order2_id,
        "customer_id": customer_id,
        "billing_address": {"street": "456 Oak Ave", "city": "Portland", "state": "OR", "zip_code": "97201", "country": "USA"},
        "tax": {"amount": 0.00, "currency": "USD"},
        "due_date": "2025-08-15"
    })
    assert r.status_code == 201
    invoice2_id = r.json()["id"]
    # Try paying with EUR instead of USD
    r = client.post("/api/v1/payments", json={
        "order_id": order2_id,
        "invoice_id": invoice2_id,
        "amount": {"amount": 49.99, "currency": "EUR"},
        "method": "credit_card"
    })
    assert r.status_code == 400, f"Expected 400 for currency mismatch, got {r.status_code}: {r.text}"
    detail = r.json()["detail"]
    assert "currency" in detail.lower(), f"Expected currency mismatch error, got: {detail}"
    print(f"[PASS] Payment currency mismatch correctly rejected: {detail}")

    print("\n=== ALL TESTS PASSED ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
