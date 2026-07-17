"""Test the app directly using TestClient."""
from fastapi.testclient import TestClient
from oms.app import app

client = TestClient(app)

print("Testing health endpoint...")
response = client.get("/health")
print(f"Health: {response.status_code} - {response.json()}")

print("\nTesting root endpoint...")
response = client.get("/")
print(f"Root: {response.status_code} - {response.json()}")

print("\nCreating customer...")
response = client.post(
    "/api/v1/customers",
    json={"name": "Test Customer 2", "email": "test2@example.com"}
)
print(f"Customer create: {response.status_code} - {response.json()}")

if response.status_code == 201:
    customer_id = response.json()["id"]
    print(f"Customer ID: {customer_id}")
else:
    print(f"Error detail: {response.json()}")
