"""
Test script to verify the OMS implementation.
Uses FastAPI TestClient for direct testing without running server.
"""

from fastapi.testclient import TestClient
from oms.app import app

client = TestClient(app)


def test_oms():
    """Test the OMS API endpoints."""
    base_url = ""  # TestClient doesn't need base URL
    
    # Test health endpoint
    print("Testing health endpoint...")
    response = client.get(f"{base_url}/health")
    print(f"Health: {response.json()}")
    
    # Test root endpoint
    print("\nTesting root endpoint...")
    response = client.get(f"{base_url}/")
    print(f"Root: {response.json()}")
    
    # Test creating a customer
    print("\nCreating customer...")
    import time
    customer_response = client.post(
        f"{base_url}/api/v1/customers",
        json={"name": "Test Customer", "email": f"test_{int(time.time())}@example.com"}
    )
    print(f"Customer created: {customer_response.json()}")
    customer_id = customer_response.json()["id"]
    # Test creating a product
    print("\nCreating product...")
    product_response = client.post(
        f"{base_url}/api/v1/products",
        json={"name": "Test Product", "base_price": 29.99, "stock_quantity": 100}
    )
    print(f"Product created: {product_response.json()}")
    product_id = product_response.json()["id"]
    
    # Test creating an order
    print("\nCreating order...")
    order_response = client.post(
        f"{base_url}/api/v1/orders",
        json={"customer_id": customer_id, "line_items": [{"product_id": product_id, "quantity": 2}]}
    )
    print(f"Order created: {order_response.json()}")
    order_id = order_response.json()["id"]
    
    # Test reviewing order (accept)
    print("\nReviewing order (accept)...")
    review_response = client.post(
        f"{base_url}/api/v1/orders/{order_id}/review",
        json={"accept": True, "notes": "Approved"}
    )
    print(f"Order reviewed: {review_response.json()}")
    
    # Test creating invoice
    print("\nCreating invoice...")
    invoice_response = client.post(
        f"{base_url}/api/v1/invoices",
        json={"order_id": order_id, "billing_name": "Test Customer", "tax_rate": 0.1}
    )
    print(f"Invoice created: {invoice_response.json()}")
    
    # Test creating payment
    print("\nCreating payment...")
    payment_response = client.post(
        f"{base_url}/api/v1/payments",
        json={"order_id": order_id, "amount": 65.98, "method": "credit_card"}
    )
    print(f"Payment created: {payment_response.json()}")
    payment_id = payment_response.json()["id"]
    
    # Test verifying payment
    print("\nVerifying payment...")
    verify_response = client.post(
        f"{base_url}/api/v1/payments/{payment_id}/verify",
        json={"confirmed": True}
    )
    print(f"Payment verified: {verify_response.json()}")
    
    # Test shipping order
    print("\nShipping order...")
    ship_response = client.post(
        f"{base_url}/api/v1/orders/{order_id}/ship",
        json={"notes": "Shipped via FedEx"}
    )
    print(f"Order shipped: {ship_response.json()}")
    
    # Test completing order
    print("\nCompleting order...")
    complete_response = client.post(
        f"{base_url}/api/v1/orders/{order_id}/complete",
        json={"notes": "Delivered successfully"}
    )
    print(f"Order completed: {complete_response.json()}")
    
    print("\n=== All tests passed! ===")


if __name__ == "__main__":
    test_oms()
