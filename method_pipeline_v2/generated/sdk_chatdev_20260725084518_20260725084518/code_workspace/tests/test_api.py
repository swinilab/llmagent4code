"""
Integration tests for OMS API
"""
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app

pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def client():
    """Test client using FastAPI's TestClient for in-process testing"""
    with TestClient(app) as test_client:
        yield test_client


BASE_URL = "/api/v1"


def test_root(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"


def test_health_live(client):
    """Test liveness endpoint"""
    response = client.get(f"{BASE_URL}/health/live")
    assert response.status_code == 200


def test_health_ready(client):
    """Test readiness endpoint"""
    response = client.get(f"{BASE_URL}/health/ready")
    assert response.status_code == 200


def test_health_queue(client):
    """Test queue status endpoint"""
    response = client.get(f"{BASE_URL}/health/queue")
    assert response.status_code == 200
    data = response.json()
    assert "queue_size" in data


def test_create_product(client):
    """Test creating a product"""
    product_data = {
        "description": "Test Product",
        "price": {
            "amount": "19.99",
            "currency": "USD"
        }
    }
    response = client.post(f"{BASE_URL}/products", json=product_data)
    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Test Product"
    assert data["price"]["amount"] == "19.99"
    assert data["price"]["currency"] == "USD"


def test_list_products(client):
    """Test listing products"""
    response = client.get(f"{BASE_URL}/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_customer(client):
    """Test creating a customer"""
    customer_data = {
        "name": "John Doe",
        "address": "123 Main Street, City",
        "phone": "+1234567890",
        "accountNumber": "123456789",
        "bankName": "Test Bank",
        "role": "CUSTOMER"
    }
    response = client.post(f"{BASE_URL}/customers", json=customer_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["role"] == "CUSTOMER"


def test_list_customers(client):
    """Test listing customers"""
    response = client.get(f"{BASE_URL}/customers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_full_workflow(client):
    """Test complete order workflow"""
    # 1. Create a product
    product_data = {
        "description": "Workflow Test Product",
        "price": {
            "amount": "99.99",
            "currency": "USD"
        }
    }
    response = client.post(f"{BASE_URL}/products", json=product_data)
    assert response.status_code == 201
    product = response.json()
    product_id = product["id"]
    
    # 2. Create a customer
    customer_data = {
        "name": "Workflow Customer",
        "address": "456 Test Avenue, City",
        "phone": "+1987654321",
        "accountNumber": "987654321",
        "bankName": "Workflow Bank",
        "role": "CUSTOMER"
    }
    response = client.post(f"{BASE_URL}/customers", json=customer_data)
    assert response.status_code == 201
    customer = response.json()
    customer_id = customer["id"]
    
    # 3. Create an order (async, returns 202)
    order_data = {
        "customerRef": customer_id,
        "lineItems": [
            {"productRef": product_id, "quantity": 2}
        ]
    }
    response = client.post(f"{BASE_URL}/orders", json=order_data)
    assert response.status_code == 202
    
    # Wait for queue to drain
    for _ in range(50):
        queue_response = client.get(f"{BASE_URL}/health/queue")
        queue_data = queue_response.json()
        if queue_data.get("queue_size", 0) == 0:
            break
        time.sleep(0.1)
    
    # Get the created order
    response = client.get(f"{BASE_URL}/orders/recent?limit=1")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) > 0
    order = orders[0]
    order_id = order["id"]
    assert order["status"] == "PLACED"
    
    # 4. Review order
    response = client.put(f"{BASE_URL}/orders/{order_id}/review")
    assert response.status_code == 200
    
    # 5. Accept order (PLACED -> ACCEPTED)
    response = client.put(f"{BASE_URL}/orders/{order_id}/accept")
    assert response.status_code == 200
    order = response.json()
    assert order["status"] == "ACCEPTED"
    
    # 6. Create invoice (ACCEPTED -> INVOICED)
    invoice_data = {"orderRef": order_id}
    response = client.post(f"{BASE_URL}/invoices", json=invoice_data)
    assert response.status_code == 201
    invoice = response.json()
    assert invoice["status"] == "ISSUED"
    
    # Verify order status changed to INVOICED
    response = client.get(f"{BASE_URL}/orders/{order_id}")
    assert response.status_code == 200
    order = response.json()
    assert order["status"] == "INVOICED"
    
    # 7. Create payment (must match invoice amount)
    payment_data = {
        "orderRef": order_id,
        "amount": invoice["totalAmount"],
        "method": "CREDIT_CARD"
    }
    response = client.post(f"{BASE_URL}/payments", json=payment_data)
    assert response.status_code == 201
    payment = response.json()
    assert payment["status"] == "PENDING"
    
    # 8. Verify payment (PENDING -> VERIFIED, order -> VERIFIED)
    response = client.put(f"{BASE_URL}/payments/{payment['id']}/verify")
    assert response.status_code == 200
    
    # Verify order status changed to VERIFIED
    response = client.get(f"{BASE_URL}/orders/{order_id}")
    assert response.status_code == 200
    order = response.json()
    assert order["status"] == "VERIFIED"
    
    # 9. Ship order (VERIFIED -> SHIPPED)
    response = client.put(f"{BASE_URL}/orders/{order_id}/ship")
    assert response.status_code == 200
    order = response.json()
    assert order["status"] == "SHIPPED"
    
    # 10. Close order (SHIPPED -> CLOSED)
    response = client.put(f"{BASE_URL}/orders/{order_id}/close")
    assert response.status_code == 200
    order = response.json()
    assert order["status"] == "CLOSED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
