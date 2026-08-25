"""Shared test fixtures.

The suite runs against the live stack (`docker compose up --build -d`) rather
than mocks, so what it verifies is the deployed system.
"""
import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("OMS_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session", autouse=True)
def require_running_stack(base_url: str) -> None:
    try:
        resp = httpx.get(f"{base_url}/health/ready", timeout=10)
    except httpx.HTTPError as exc:
        pytest.exit(f"OMS is not reachable at {base_url}: {exc}", returncode=1)
    if not resp.json().get("checks", {}).get("primary") == "up":
        pytest.exit("OMS primary database is not up; start with `docker compose up -d`", 1)


@pytest.fixture
def client(base_url: str):
    # A unique client id per test keeps the shared token bucket from making
    # unrelated tests throttle each other.
    with httpx.Client(
        base_url=base_url, timeout=30, headers={"X-Client-Id": f"pytest-{uuid.uuid4()}"}
    ) as c:
        yield c


@pytest.fixture
def valid_customer_body() -> dict:
    """The `validSeed`-equivalent body for Customer."""
    return {
        "name": "Alice Smith",
        "address": "12 Elm Street, Springfield",
        "phone": "+14155552671",
        "bankingDetails": {"accountNumber": "12345678", "bankName": "Acme Bank"},
        "role": "CUSTOMER",
    }


@pytest.fixture
def valid_product_body() -> dict:
    return {"description": "Mechanical keyboard", "price": {"amount": "129.99", "currency": "USD"}}


@pytest.fixture
def customer_id(client, valid_customer_body) -> str:
    resp = client.post("/api/v1/customers", json=valid_customer_body)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.fixture
def product_id(client, valid_product_body) -> str:
    resp = client.post("/api/v1/products", json=valid_product_body)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.fixture
def placed_order(client, customer_id, product_id) -> dict:
    resp = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 3}]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def invoiced_order(client, placed_order) -> tuple[dict, dict]:
    """An order advanced to INVOICED, with its invoice."""
    oid = placed_order["id"]
    assert client.post(f"/api/v1/orders/{oid}/accept").status_code == 200
    resp = client.post("/api/v1/invoices", json={"orderRef": oid})
    assert resp.status_code == 201, resp.text
    return placed_order, resp.json()
