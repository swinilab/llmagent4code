"""Field Constraint Table enforcement and status-code contract."""

from __future__ import annotations

import uuid

import httpx
import pytest

from tests.conftest import make_customer, make_order, make_product, unique_phone


def valid_customer_payload(**overrides) -> dict:
    payload = {
        "name": "Ada Lovelace",
        "address": "12 Analytical Engine Road, London",
        "phone": unique_phone(),
        "bankingDetails": {"accountNumber": "123456789012", "bankName": "Bank of Example"},
        "role": "CUSTOMER",
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------
# UUID handling: 400 for malformed, 404 for valid-but-unknown
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "collection", ["customers", "products", "orders", "payments", "invoices"]
)
def test_malformed_uuid_returns_400(client: httpx.Client, collection: str) -> None:
    assert client.get(f"/api/v1/{collection}/not-a-uuid").status_code == 400


@pytest.mark.parametrize(
    "collection", ["customers", "products", "orders", "payments", "invoices"]
)
def test_unknown_uuid_returns_404(client: httpx.Client, collection: str) -> None:
    response = client.get(f"/api/v1/{collection}/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# --------------------------------------------------------------------------
# Customer constraints
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "A",                    # below the 2-character minimum
        "   ",                  # whitespace-only
        "A" * 101,              # above the 100-character maximum
        "Ada123",               # digits are not permitted by the name regex
        "Ada<script>",          # unsupported punctuation
    ],
)
def test_invalid_customer_name_rejected(client: httpx.Client, name: str) -> None:
    response = client.post("/api/v1/customers", json=valid_customer_payload(name=name))
    assert response.status_code == 400


def test_customer_name_boundaries_accepted(client: httpx.Client) -> None:
    # Exactly at the inclusive minimum and maximum.
    assert client.post("/api/v1/customers", json=valid_customer_payload(name="Al")).status_code == 201
    assert (
        client.post("/api/v1/customers", json=valid_customer_payload(name="A" * 100)).status_code
        == 201
    )


@pytest.mark.parametrize("phone", ["0123456789", "+04412345678", "12345", "+1234567890123456", "abc"])
def test_invalid_phone_rejected(client: httpx.Client, phone: str) -> None:
    assert client.post("/api/v1/customers", json=valid_customer_payload(phone=phone)).status_code == 400


@pytest.mark.parametrize("account", ["12345", "1" * 21, "12345a", ""])
def test_invalid_account_number_rejected(client: httpx.Client, account: str) -> None:
    payload = valid_customer_payload()
    payload["bankingDetails"]["accountNumber"] = account
    assert client.post("/api/v1/customers", json=payload).status_code == 400


@pytest.mark.parametrize("address", ["abcd", "   ", "x" * 256])
def test_invalid_address_rejected(client: httpx.Client, address: str) -> None:
    assert (
        client.post("/api/v1/customers", json=valid_customer_payload(address=address)).status_code
        == 400
    )


@pytest.mark.parametrize("role", ["customer", "ADMIN", "", "Customer"])
def test_invalid_role_rejected(client: httpx.Client, role: str) -> None:
    # Enum matching is case-sensitive against the exact allow-list.
    assert client.post("/api/v1/customers", json=valid_customer_payload(role=role)).status_code == 400


def test_missing_required_field_rejected(client: httpx.Client) -> None:
    payload = valid_customer_payload()
    del payload["phone"]
    assert client.post("/api/v1/customers", json=payload).status_code == 400


def test_client_supplied_readonly_fields_rejected(client: httpx.Client) -> None:
    # id and orderHistory are server-derived and must not be settable.
    assert (
        client.post("/api/v1/customers", json=valid_customer_payload(id=str(uuid.uuid4()))).status_code
        == 400
    )
    assert (
        client.post("/api/v1/customers", json=valid_customer_payload(orderHistory=[])).status_code
        == 400
    )


# --------------------------------------------------------------------------
# Product constraints
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "amount",
    [
        "0.00",        # below the 0.01 minimum
        "0.001",       # more than 2 decimal places
        "19.9",        # fewer than 2 decimal places
        "1000000.00",  # above the 999999.99 maximum
        "19",          # no decimal part
        "-5.00",       # negative
        "abc",
    ],
)
def test_invalid_product_amount_rejected(client: httpx.Client, amount: str) -> None:
    response = client.post(
        "/api/v1/products",
        json={"description": "Valid description", "price": {"amount": amount, "currency": "USD"}},
    )
    assert response.status_code == 400


def test_product_amount_boundaries_accepted(client: httpx.Client) -> None:
    assert make_product(client, amount="0.01")["price"]["amount"] == "0.01"
    assert make_product(client, amount="999999.99")["price"]["amount"] == "999999.99"


def test_float_amount_rejected_not_rounded(client: httpx.Client) -> None:
    # A JSON float cannot represent money exactly; it must be rejected outright.
    response = client.post(
        "/api/v1/products",
        json={"description": "Valid description", "price": {"amount": 19.999, "currency": "USD"}},
    )
    assert response.status_code == 400


@pytest.mark.parametrize("currency", ["usd", "GBP", "US", "USDD", ""])
def test_invalid_currency_rejected(client: httpx.Client, currency: str) -> None:
    response = client.post(
        "/api/v1/products",
        json={"description": "Valid description", "price": {"amount": "9.99", "currency": currency}},
    )
    assert response.status_code == 400


@pytest.mark.parametrize("description", ["ab", "   ", "x" * 501])
def test_invalid_product_description_rejected(client: httpx.Client, description: str) -> None:
    response = client.post(
        "/api/v1/products",
        json={"description": description, "price": {"amount": "9.99", "currency": "USD"}},
    )
    assert response.status_code == 400


# --------------------------------------------------------------------------
# Order constraints
# --------------------------------------------------------------------------


def test_duplicate_product_ref_rejected_with_400(client: httpx.Client) -> None:
    customer = make_customer(client)
    product = make_product(client)
    response = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer["id"],
            "lineItems": [
                {"productRef": product["id"], "quantity": 1},
                {"productRef": product["id"], "quantity": 2},
            ],
        },
    )
    assert response.status_code == 400


@pytest.mark.parametrize("quantity", [0, -1, 1001])
def test_invalid_quantity_rejected(client: httpx.Client, quantity: int) -> None:
    customer = make_customer(client)
    product = make_product(client)
    response = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer["id"],
            "lineItems": [{"productRef": product["id"], "quantity": quantity}],
        },
    )
    assert response.status_code == 400


def test_quantity_boundaries_accepted(client: httpx.Client) -> None:
    for quantity in (1, 1000):
        customer = make_customer(client)
        product = make_product(client, amount="0.01")
        response = client.post(
            "/api/v1/orders",
            json={
                "customerRef": customer["id"],
                "lineItems": [{"productRef": product["id"], "quantity": quantity}],
            },
        )
        assert response.status_code == 201, response.text


def test_empty_line_items_rejected(client: httpx.Client) -> None:
    customer = make_customer(client)
    response = client.post(
        "/api/v1/orders", json={"customerRef": customer["id"], "lineItems": []}
    )
    assert response.status_code == 400


def test_order_rejects_client_supplied_computed_fields(client: httpx.Client) -> None:
    customer = make_customer(client)
    product = make_product(client)
    # totalAmount is server-computed and must never be trusted from the client.
    response = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer["id"],
            "lineItems": [{"productRef": product["id"], "quantity": 1}],
            "totalAmount": "0.01",
        },
    )
    assert response.status_code == 400

    # unitPriceSnapshot is likewise server-computed.
    response = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer["id"],
            "lineItems": [
                {"productRef": product["id"], "quantity": 1, "unitPriceSnapshot": "0.01"}
            ],
        },
    )
    assert response.status_code == 400


def test_order_with_unknown_customer_returns_404(client: httpx.Client) -> None:
    product = make_product(client)
    response = client.post(
        "/api/v1/orders",
        json={
            "customerRef": str(uuid.uuid4()),
            "lineItems": [{"productRef": product["id"], "quantity": 1}],
        },
    )
    assert response.status_code == 404


def test_order_with_unknown_product_returns_404(client: httpx.Client) -> None:
    customer = make_customer(client)
    response = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer["id"],
            "lineItems": [{"productRef": str(uuid.uuid4()), "quantity": 1}],
        },
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------
# Invoice date constraints
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "issue_date",
    [
        "31/02/2026",   # matches the regex but is not a real calendar date
        "30/02/2026",
        "2026-08-01",   # wrong format
        "1/8/2026",     # not zero-padded
        "32/01/2026",
    ],
)
def test_invalid_invoice_dates_rejected(client: httpx.Client, issue_date: str) -> None:
    from tests.conftest import make_order as _make_order

    _, _, order = _make_order(client)
    client.post(f"/api/v1/orders/{order['id']}/accept")
    response = client.post(
        "/api/v1/invoices", json={"orderRef": order["id"], "issueDate": issue_date}
    )
    assert response.status_code == 400


def test_due_date_before_issue_date_rejected(client: httpx.Client) -> None:
    _, _, order = make_order(client)
    client.post(f"/api/v1/orders/{order['id']}/accept")
    response = client.post(
        "/api/v1/invoices",
        json={"orderRef": order["id"], "issueDate": "10/08/2026", "dueDate": "01/08/2026"},
    )
    assert response.status_code == 400


# --------------------------------------------------------------------------
# Payment enum constraints
# --------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["credit_card", "PAYPAL", ""])
def test_invalid_payment_method_rejected(client: httpx.Client, method: str) -> None:
    from tests.conftest import advance_to_invoiced

    order, invoice = advance_to_invoiced(client)
    response = client.post(
        "/api/v1/payments",
        json={"orderRef": order["id"], "amount": invoice["totalAmount"], "method": method},
    )
    assert response.status_code == 400
