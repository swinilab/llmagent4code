"""Shared test fixtures.

Tests create all of their own data and never depend on preloaded business rows.
`BASE_URL` points at the running Docker stack, which is where the ASR scenarios
must be observed - the tactics involve Toxiproxy, real PostgreSQL transactions,
and real concurrency, none of which an in-process client would exercise faithfully.
"""

from __future__ import annotations

import os
import uuid
from decimal import Decimal

import httpx
import pytest

BASE_URL = os.getenv("ORDERMAN_BASE_URL", "http://localhost:8080")
TOXIPROXY_URL = os.getenv("TOXIPROXY_URL", "http://localhost:8474")

API = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http_client:
        yield http_client


@pytest.fixture(scope="session")
def toxiproxy() -> httpx.Client:
    with httpx.Client(base_url=TOXIPROXY_URL, timeout=10.0) as http_client:
        yield http_client


@pytest.fixture(autouse=True)
def reset_state(client: httpx.Client):
    """Clean in-process starting point between scenarios (counters, cache, faults)."""
    client.post("/internal/test/reset")
    yield


def unique_phone() -> str:
    """E.164 phone that is unique per call, so tests never collide."""
    suffix = uuid.uuid4().int % 10**9
    return f"+4420{suffix:09d}"


def make_customer(client: httpx.Client, role: str = "CUSTOMER") -> dict:
    response = client.post(
        "/api/v1/customers",
        json={
            "name": "Ada Lovelace",
            "address": "12 Analytical Engine Road, London",
            "phone": unique_phone(),
            "bankingDetails": {"accountNumber": "123456789012", "bankName": "Bank of Example"},
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_product(client: httpx.Client, amount: str = "19.99", description: str | None = None) -> dict:
    response = client.post(
        "/api/v1/products",
        json={
            "description": description or f"Test product {uuid.uuid4()}",
            "price": {"amount": amount, "currency": "USD"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_order(client: httpx.Client, quantity: int = 2, amount: str = "19.99") -> tuple[dict, dict, dict]:
    customer = make_customer(client)
    product = make_product(client, amount=amount)
    response = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer["id"],
            "lineItems": [{"productRef": product["id"], "quantity": quantity}],
        },
    )
    assert response.status_code == 201, response.text
    return customer, product, response.json()


def advance_to_invoiced(client: httpx.Client) -> tuple[dict, dict]:
    """Drive an order through steps 1-3, returning (order, invoice)."""
    _, _, order = make_order(client)
    accepted = client.post(f"/api/v1/orders/{order['id']}/accept")
    assert accepted.status_code == 200, accepted.text

    invoice = client.post("/api/v1/invoices", json={"orderRef": order["id"]})
    assert invoice.status_code == 201, invoice.text
    return accepted.json(), invoice.json()


def advance_to_paid(client: httpx.Client) -> tuple[dict, dict, dict]:
    """Drive an order through steps 1-4, returning (order, invoice, payment)."""
    order, invoice = advance_to_invoiced(client)
    payment = client.post(
        "/api/v1/payments",
        json={
            "orderRef": order["id"],
            "amount": invoice["totalAmount"],
            "method": "CREDIT_CARD",
        },
    )
    assert payment.status_code == 201, payment.text
    return order, invoice, payment.json()


def metrics(client: httpx.Client) -> dict[str, int]:
    response = client.get("/internal/metrics")
    assert response.status_code == 200, response.text
    return response.json()
