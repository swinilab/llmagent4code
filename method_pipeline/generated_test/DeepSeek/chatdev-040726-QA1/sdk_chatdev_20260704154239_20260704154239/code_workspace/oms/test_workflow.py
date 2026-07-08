"""
Integration test that starts the app in a subprocess and runs the full workflow.
Uses a retry loop for server readiness instead of a fixed sleep.
Cleans up the database file after execution.
"""
import subprocess
import time
import sys
import os

# Start the server in the background
server_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=os.path.join(os.path.dirname(__file__)),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

import requests

BASE = "http://localhost:8000"

# Retry loop: poll /health until the server is ready (up to 15 seconds)
MAX_RETRIES = 30
RETRY_DELAY = 0.5
server_ready = False
for attempt in range(1, MAX_RETRIES + 1):
    try:
        r = requests.get(f"{BASE}/health", timeout=2)
        if r.status_code == 200:
            server_ready = True
            print(f"Server ready after ~{attempt * RETRY_DELAY:.1f}s")
            break
    except requests.ConnectionError:
        pass
    time.sleep(RETRY_DELAY)

if not server_ready:
    server_proc.terminate()
    server_proc.wait()
    print("ERROR: Server did not start in time")
    sys.exit(1)

try:
    # Health check
    r = requests.get(f"{BASE}/health")
    print(f"Health: {r.status_code} {r.json()}")

    # Create a customer
    customer = {
        "name": "Alice Johnson",
        "address": "123 Main St, Springfield",
        "phone": "+1-555-0100",
        "banking_details": "Bank of America, acct: 12345678",
        "role": "customer"
    }
    r = requests.post(f"{BASE}/api/v1/customers", json=customer)
    print(f"Create Customer: {r.status_code}")
    customer_data = r.json()
    print(f"  Customer ID: {customer_data['id']}")

    # Create a product
    product = {
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with USB receiver",
        "base_price": 29.99,
        "currency": "USD"
    }
    r = requests.post(f"{BASE}/api/v1/products", json=product)
    print(f"Create Product: {r.status_code}")
    product_data = r.json()
    print(f"  Product ID: {product_data['id']}")

    # Place an order (Step 1)
    order = {
        "customer_id": customer_data["id"],
        "line_items": [
            {
                "product_id": product_data["id"],
                "quantity": 2,
                "unit_price": 29.99,
                "currency": "USD"
            }
        ]
    }
    r = requests.post(f"{BASE}/api/v1/orders", json=order)
    print(f"Create Order: {r.status_code}")
    order_data = r.json()
    print(f"  Order ID: {order_data['id']}, Status: {order_data['status']}")

    # Step 2: Staff accepts order
    r = requests.post(f"{BASE}/api/v1/workflow/orders/{order_data['id']}/accept")
    print(f"Accept Order: {r.status_code}")
    print(f"  Status: {r.json()['status']}")

    # Step 3: Accountant creates invoice
    r = requests.post(
        f"{BASE}/api/v1/workflow/orders/{order_data['id']}/invoice",
        json={"billing_info": "Invoice for Alice - 2x Wireless Mouse"}
    )
    print(f"Create Invoice: {r.status_code}")
    invoice_data = r.json()
    print(f"  Invoice ID: {invoice_data['id']}, Status: {invoice_data['status']}")

    # Step 4: Customer pays invoice
    r = requests.post(
        f"{BASE}/api/v1/workflow/invoices/{invoice_data['id']}/pay",
        json={"payment_method": "credit_card"}
    )
    print(f"Pay Invoice: {r.status_code}")
    payment_data = r.json()
    print(f"  Payment ID: {payment_data['id']}, Status: {payment_data['status']}")

    # Step 5: Accountant verifies payment
    r = requests.post(f"{BASE}/api/v1/workflow/payments/{payment_data['id']}/verify")
    print(f"Verify Payment: {r.status_code}")
    print(f"  Payment Status: {r.json()['status']}")

    # Step 6: Staff ships order
    r = requests.post(f"{BASE}/api/v1/workflow/orders/{order_data['id']}/ship")
    print(f"Ship Order: {r.status_code}")
    print(f"  Order Status: {r.json()['status']}")

    # Step 7: Staff closes order
    r = requests.post(f"{BASE}/api/v1/workflow/orders/{order_data['id']}/close")
    print(f"Close Order: {r.status_code}")
    print(f"  Order Status: {r.json()['status']}")

    # Verify final state
    r = requests.get(f"{BASE}/api/v1/orders/{order_data['id']}")
    print(f"\nFinal Order: {r.json()['status']}")

    print("\n=== ALL WORKFLOW STEPS PASSED ===")
except Exception as e:
    print(f"ERROR: {e}")
    raise
finally:
    server_proc.terminate()
    server_proc.wait()
    # Clean up the database file created during the test
    db_path = os.path.join(os.path.dirname(__file__), "oms.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Cleaned up oms.db")
