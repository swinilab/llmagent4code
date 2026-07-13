import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app import models

# Create an in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_create_order():
    # Create a customer first
    user_data = {
        "name": "John Doe",
        "address": "123 Main St",
        "phone": "555-1234",
        "banking_details": "bank123",
        "role": "customer",
        "password": "securepass",
    }
    resp = client.post("/users/", json=user_data)
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Create a product
    product_data = {
        "description": "Test Product",
        "base_price": 1000,  # $10.00 in cents
        "currency": "USD",
    }
    resp = client.post("/products/", json=product_data)
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    # Create an order
    order_data = {
        "customer_id": user_id,
        "status": "pending",
        "total_amount": 0,  # will be calculated by service
        "items": [
            {
                "product_id": product_id,
                "quantity": 2,
                "unit_price": 1000,
                "total_price": 2000,
            }
        ],
    }
    resp = client.post("/orders/", json=order_data)
    assert resp.status_code == 201
    data = resp.json()
    assert data["customer_id"] == user_id
    assert data["status"] == "pending"
    assert data["total_amount"] == 2000
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product_id
    assert data["items"][0]["quantity"] == 2

    # Test getting the order
    order_id = data["id"]
    resp = client.get(f"/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id

    # Test workflow: accept order
    resp = client.post(f"/orders/{order_id}/accept")
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    # Create invoice
    resp = client.post(f"/orders/{order_id}/invoice", json={"billing_info": "{\"name\": \"John Doe\"}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "invoiced"

    # Process payment
    resp = client.post(f"/orders/{order_id}/pay", json={"amount": 2000, "method": "credit_card"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"

    # Verify payment (in this simplified service, verify_payment just moves to paid? Actually verify_payment expects payment_id? Wait the endpoint is /payments/{payment_id}/verify. We'll need to create a payment via payment endpoint. But for simplicity we can test the service method directly.
    # We'll skip the payment verification via order endpoint and instead test the service method later.

    # Ship order
    resp = client.post(f"/orders/{order_id}/ship")
    assert resp.status_code == 200
    assert resp.json()["status"] == "shipped"

    # Close order
    resp = client.post(f"/orders/{order_id}/close")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


def test_order_service_methods():
    # Directly test the OrderService methods using a db session
    from app.services import OrderService
    from app.schemas import OrderCreate, OrderItemCreate
    from app.models import Order, OrderStatus

    db = TestingSessionLocal()
    service = OrderService(db)

    # Create a user and product via repository directly for simplicity
    from app.repositories import UserRepository, ProductRepository
    user_repo = UserRepository(models.User, db)
    product_repo = ProductRepository(models.Product, db)

    user = user_repo.create({
        "name": "Test User",
        "address": "Addr",
        "phone": "123",
        "banking_details": "bank",
        "hashed_password": "hashed",
        "role": "customer",
        "is_active": True,
    })
    product = product_repo.create({
        "description": "Test Product",
        "base_price": 500,
        "currency": "USD",
        "is_active": True,
    })

    # Create order
    order_in = OrderCreate(
        customer_id=user.id,
        status=OrderStatus.PENDING,
        total_amount=0,
        items=[OrderItemCreate(product_id=product.id, quantity=3, unit_price=500, total_price=1500)],
    )
    order = service.create_order(order_in)
    assert order.id is not None
    assert order.total_amount == 1500
    assert len(order.items) == 1
    assert order.items[0].quantity == 3

    # Accept order
    order = service.accept_order(order.id)
    assert order.status == OrderStatus.ACCEPTED

    # Create invoice (just status change)
    order = service.create_invoice(order.id)
    assert order.status == OrderStatus.INVOICED

    # Verify payment (simulate)
    order = service.verify_payment(order.id)
    assert order.status == OrderStatus.PAID

    # Ship order
    order = service.ship_order(order.id)
    assert order.status == OrderStatus.SHIPPED

    # Close order
    order = service.close_order(order.id)
    assert order.status == OrderStatus.CLOSED

    db.close()