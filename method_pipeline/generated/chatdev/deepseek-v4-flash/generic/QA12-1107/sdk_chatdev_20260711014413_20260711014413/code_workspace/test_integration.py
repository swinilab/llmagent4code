"""
Quick integration test for the OMS backend.
Verifies the full workflow including invoice status updates on payment.
Updated to work with async queue processing: write endpoints return 202,
tests wait for queue drain and verify results via GET endpoints.
"""
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

BASE = os.environ.get("OMS_TEST_BASE_URL", "http://localhost:8000")


def req(method, path, body=None):
    if body and method.upper() in ("GET", "DELETE"):
        # Encode as query parameters for GET/DELETE requests
        url = f"{BASE}{path}?{urllib.parse.urlencode(body)}"
        data = None
    else:
        url = f"{BASE}{path}"
        data = json.dumps(body).encode() if body else None

    r = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(r)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}


def wait_for_queue():
    """Poll the queue health endpoint until the queue is drained."""
    for _ in range(30):
        q = req("GET", "/health/queue")
        if q.get("queue_size", 1) == 0:
            return
        time.sleep(0.1)
    print("⚠️  Queue did not drain within timeout")


# 1. Health check
print("=== Health Check ===")
print(req("GET", "/health/live"))
print(req("GET", "/health/ready"))

# 2. Create customer
print("\n=== Create Customer ===")
cust = req("POST", "/api/v1/customers", {
    "name": "Alice",
    "address": "123 Main St",
    "phone": "555-0100",
    "banking_details": "ACC-12345"
})
print(f"Customer: {cust['id']}")
CUSTOMER_ID = cust["id"]

# 3. Create product
print("\n=== Create Product ===")
prod = req("POST", "/api/v1/products", {
    "name": "Widget",
    "base_price": 19.99,
    "stock_quantity": 100
})
print(f"Product: {prod['id']}")
PRODUCT_ID = prod["id"]

# 4. Place order (Step 1) — now returns 202 Accepted
print("\n=== Place Order ===")
result = req("POST", "/api/v1/orders", {
    "customer_id": CUSTOMER_ID,
    "items": [{"product_id": PRODUCT_ID, "quantity": 2}]
})
print(f"Order queued: {result}")
wait_for_queue()

# Retrieve the order
order = req("GET", "/api/v1/orders", {"limit": 1})
order = order["orders"][0]
ORDER_ID = order["id"]
print(f"Order: {ORDER_ID}, status: {order['status']}")

# 5. Review order
print("\n=== Review Order ===")
order = req("PUT", f"/api/v1/orders/{ORDER_ID}/review")
print(f"Status: {order['status']}")

# 6. Accept order
print("\n=== Accept Order ===")
order = req("PUT", f"/api/v1/orders/{ORDER_ID}/accept")
print(f"Status: {order['status']}")

# 7. Create invoice (Step 3) — now returns 202 Accepted
print("\n=== Create Invoice ===")
result = req("POST", "/api/v1/invoices", {
    "order_id": ORDER_ID,
    "billing_info": "Invoice for Alice - Widget x2"
})
print(f"Invoice queued: {result}")
wait_for_queue()

# Retrieve the invoice
inv = req("GET", "/api/v1/invoices", {"limit": 1})
inv = inv["invoices"][0]
INVOICE_ID = inv["id"]
print(f"Invoice: {INVOICE_ID}, status: {inv['status']}")

# 8. Process payment (Step 4) — now returns 202 Accepted
print("\n=== Process Payment ===")
result = req("POST", "/api/v1/payments", {
    "order_id": ORDER_ID,
    "amount": 39.98,
    "method": "CREDIT_CARD"
})
print(f"Payment queued: {result}")
wait_for_queue()

# Retrieve the payment
pay = req("GET", "/api/v1/payments", {"limit": 1})
pay = pay["payments"][0]
PAYMENT_ID = pay["id"]
print(f"Payment: {PAYMENT_ID}, status: {pay['status']}")

# 9. Verify invoice status was updated by payment processing
print("\n=== Verify Invoice Status After Payment ===")
inv_after = req("GET", f"/api/v1/invoices/{INVOICE_ID}")
print(f"Invoice status: {inv_after['status']}, paid_at: {inv_after.get('paid_at')}")
assert inv_after["status"] == "PAID", f"Invoice should be PAID but got {inv_after['status']}"
assert inv_after.get("paid_at") is not None, "Invoice paid_at should be set"
print("✅ Invoice correctly marked as PAID")

# 10. Verify payment
print("\n=== Verify Payment ===")
pay = req("PUT", f"/api/v1/payments/{PAYMENT_ID}/verify")
print(f"Payment status: {pay['status']}")

# 11. Ship order
print("\n=== Ship Order ===")
order = req("PUT", f"/api/v1/orders/{ORDER_ID}/ship")
print(f"Status: {order['status']}")

# 12. Close order
print("\n=== Close Order ===")
order = req("PUT", f"/api/v1/orders/{ORDER_ID}/close")
print(f"Status: {order['status']}")

# 13. Final state
print("\n=== Final Order ===")
order = req("GET", f"/api/v1/orders/{ORDER_ID}")
print(json.dumps(order, indent=2))
assert order["status"] == "CLOSED"
print("\n🎉 All tests passed!")
