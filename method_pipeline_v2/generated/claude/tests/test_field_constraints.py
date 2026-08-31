"""Boundary Value Analysis / Equivalence Partitioning over the Field Constraint Table.

Each parametrized case names the boundary it probes, so a failure identifies the
exact rule that regressed.
"""
import uuid

import pytest


def _mutate(body: dict, path: str, value) -> dict:
    """Set a dot-notation field, matching how the harness builds request bodies."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in body.items()}
    head, _, tail = path.partition(".")
    if tail:
        out[head] = {**out.get(head, {}), tail: value}
    else:
        out[head] = value
    return out


# --- Customer -----------------------------------------------------------------

CUSTOMER_CASES = [
    # (field, value, expected_status, label)
    ("name", "A", 400, "name below min length 2"),
    ("name", "Al", 201, "name at min length 2"),
    ("name", "A" * 100, 201, "name at max length 100"),
    ("name", "A" * 101, 400, "name above max length 100"),
    ("name", "   ", 400, "name whitespace-only"),
    ("name", "", 400, "name empty"),
    ("name", "Nguyễn Văn An", 201, "name unicode letters allowed"),
    ("name", "O'Brien-Smith Jr.", 201, "name apostrophe hyphen dot allowed"),
    ("name", "Alice2", 400, "name digit violates regex"),
    ("name", "Alice@Home", 400, "name symbol violates regex"),
    ("name", None, 400, "name null but required"),
    ("address", "1234", 400, "address below min length 5"),
    ("address", "12345", 201, "address at min length 5"),
    ("address", "A" * 255, 201, "address at max length 255"),
    ("address", "A" * 256, 400, "address above max length 255"),
    ("address", "     ", 400, "address whitespace-only"),
    ("phone", "1234567", 400, "phone below 8 digits"),
    ("phone", "12345678", 201, "phone at 8 digits"),
    ("phone", "+12345678", 201, "phone with plus at min"),
    ("phone", "123456789012345", 201, "phone at 15 digits"),
    ("phone", "1234567890123456", 400, "phone above 15 digits"),
    ("phone", "0123456789", 400, "phone starts with 0"),
    ("phone", "+0123456789", 400, "phone starts with 0 after plus"),
    ("phone", "+1 415 555 2671", 400, "phone with spaces"),
    ("phone", "abcdefgh", 400, "phone non-numeric"),
    ("bankingDetails.accountNumber", "12345", 400, "account below 6 digits"),
    ("bankingDetails.accountNumber", "123456", 201, "account at 6 digits"),
    ("bankingDetails.accountNumber", "1" * 20, 201, "account at 20 digits"),
    ("bankingDetails.accountNumber", "1" * 21, 400, "account above 20 digits"),
    ("bankingDetails.accountNumber", "12345A", 400, "account non-numeric"),
    ("bankingDetails.bankName", "A", 400, "bank name below min 2"),
    ("bankingDetails.bankName", "AB", 201, "bank name at min 2"),
    ("bankingDetails.bankName", "A" * 100, 201, "bank name at max 100"),
    ("bankingDetails.bankName", "A" * 101, 400, "bank name above max 100"),
    ("bankingDetails.bankName", "Acme & Co. 2", 201, "bank name allowed charset"),
    ("bankingDetails.bankName", "Acme@Bank", 400, "bank name symbol violates regex"),
    ("role", "CUSTOMER", 201, "role CUSTOMER"),
    ("role", "ORDER_STAFF", 201, "role ORDER_STAFF"),
    ("role", "ACCOUNTANT", 201, "role ACCOUNTANT"),
    ("role", "customer", 400, "role lowercase is case-sensitive reject"),
    ("role", "ADMIN", 400, "role not in allowed values"),
    ("role", "", 400, "role empty"),
]


@pytest.mark.parametrize("field,value,expected,label", CUSTOMER_CASES, ids=[c[3] for c in CUSTOMER_CASES])
def test_customer_field_constraints(client, valid_customer_body, field, value, expected, label):
    body = _mutate(valid_customer_body, field, value)
    resp = client.post("/api/v1/customers", json=body)
    assert resp.status_code == expected, f"{label}: {resp.status_code} != {expected} :: {resp.text[:200]}"


def test_customer_missing_required_fields(client, valid_customer_body):
    for field in ("name", "address", "phone", "bankingDetails", "role"):
        body = {k: v for k, v in valid_customer_body.items() if k != field}
        assert client.post("/api/v1/customers", json=body).status_code == 400, field


def test_customer_readonly_fields_rejected(client, valid_customer_body):
    """id and orderHistory are server-derived and not client-settable."""
    for field, value in (("id", str(uuid.uuid4())), ("orderHistory", [str(uuid.uuid4())])):
        assert client.post(
            "/api/v1/customers", json={**valid_customer_body, field: value}
        ).status_code == 400, field


# --- Product ------------------------------------------------------------------

PRODUCT_CASES = [
    ("description", "ab", 400, "description below min 3"),
    ("description", "abc", 201, "description at min 3"),
    ("description", "A" * 500, 201, "description at max 500"),
    ("description", "A" * 501, 400, "description above max 500"),
    ("description", "   ", 400, "description whitespace-only"),
    ("price.amount", "0.00", 400, "price below min 0.01"),
    ("price.amount", "0.01", 201, "price at min 0.01"),
    ("price.amount", "999999.99", 201, "price at max 999999.99"),
    ("price.amount", "1000000.00", 400, "price above max"),
    ("price.amount", "10.0", 400, "price 1 decimal place"),
    ("price.amount", "10", 400, "price no decimal places"),
    ("price.amount", "10.005", 400, "price 3dp must not round"),
    ("price.amount", "-5.00", 400, "price negative"),
    ("price.amount", 10.00, 400, "price as JSON float"),
    ("price.amount", "abc", 400, "price non-numeric"),
    ("price.currency", "USD", 201, "currency USD"),
    ("price.currency", "VND", 201, "currency VND"),
    ("price.currency", "EUR", 201, "currency EUR"),
    ("price.currency", "JPY", 400, "currency not supported"),
    ("price.currency", "usd", 400, "currency lowercase"),
    ("price.currency", "US", 400, "currency too short"),
    ("price.currency", "USDD", 400, "currency too long"),
]


@pytest.mark.parametrize("field,value,expected,label", PRODUCT_CASES, ids=[c[3] for c in PRODUCT_CASES])
def test_product_field_constraints(client, valid_product_body, field, value, expected, label):
    body = _mutate(valid_product_body, field, value)
    resp = client.post("/api/v1/products", json=body)
    assert resp.status_code == expected, f"{label}: {resp.status_code} != {expected} :: {resp.text[:200]}"


# --- Order --------------------------------------------------------------------


@pytest.mark.parametrize(
    "quantity,expected,label",
    [
        (0, 400, "quantity below min 1"),
        (1, 201, "quantity at min 1"),
        (1000, 201, "quantity at max 1000"),
        (1001, 400, "quantity above max 1000"),
        (-1, 400, "quantity negative"),
        (1.5, 400, "quantity fractional"),
        ("2", 201, "quantity numeric string accepted"),
        ("abc", 400, "quantity non-numeric"),
    ],
)
def test_order_quantity_boundaries(client, customer_id, product_id, quantity, expected, label):
    resp = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": quantity}]},
    )
    assert resp.status_code == expected, f"{label}: {resp.status_code} :: {resp.text[:200]}"


def test_order_line_item_count_boundaries(client, customer_id, product_id):
    # 0 items -> below min
    assert client.post(
        "/api/v1/orders", json={"customerRef": customer_id, "lineItems": []}
    ).status_code == 400
    # 101 distinct items -> above max (distinct ids also avoid the duplicate rule)
    too_many = [{"productRef": str(uuid.uuid4()), "quantity": 1} for _ in range(101)]
    assert client.post(
        "/api/v1/orders", json={"customerRef": customer_id, "lineItems": too_many}
    ).status_code == 400


def test_order_duplicate_product_ref_rejected(client, customer_id, product_id):
    resp = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer_id,
            "lineItems": [
                {"productRef": product_id, "quantity": 1},
                {"productRef": product_id, "quantity": 2},
            ],
        },
    )
    assert resp.status_code == 400


def test_order_computed_fields_not_client_settable(client, customer_id, product_id):
    """totalAmount and unitPriceSnapshot are server-owned (Implementation note 3)."""
    base = {"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 1}]}
    assert client.post("/api/v1/orders", json={**base, "totalAmount": "0.01"}).status_code == 400
    assert client.post("/api/v1/orders", json={**base, "status": "SHIPPED"}).status_code == 400
    spoofed = {
        "customerRef": customer_id,
        "lineItems": [{"productRef": product_id, "quantity": 1, "unitPriceSnapshot": "0.01"}],
    }
    assert client.post("/api/v1/orders", json=spoofed).status_code == 400


def test_order_total_is_server_computed(client, customer_id, product_id):
    resp = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 7}]},
    )
    assert resp.json()["totalAmount"] == "909.93"   # 7 x 129.99, exact decimal


# --- Invoice ------------------------------------------------------------------


@pytest.mark.parametrize(
    "issue_date,expected,label",
    [
        ("28/02/2026", 201, "valid date"),
        ("29/02/2024", 201, "leap day in a leap year"),
        ("29/02/2026", 400, "leap day in a non-leap year"),
        ("31/02/2026", 400, "impossible calendar date"),
        ("30/02/2026", 400, "impossible calendar date 30 Feb"),
        ("31/04/2026", 400, "31st of a 30-day month"),
        ("2026-02-28", 400, "ISO format not accepted"),
        ("1/2/2026", 400, "unpadded date"),
        ("00/01/2026", 400, "day zero"),
        ("01/13/2026", 400, "month 13"),
        ("abc", 400, "non-date string"),
    ],
)
def test_invoice_issue_date_validation(client, customer_id, product_id, issue_date, expected, label):
    order = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 1}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/accept")
    resp = client.post("/api/v1/invoices", json={"orderRef": order["id"], "issueDate": issue_date})
    assert resp.status_code == expected, f"{label}: {resp.status_code} :: {resp.text[:200]}"


def test_invoice_due_date_must_not_precede_issue(client, customer_id, product_id):
    order = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 1}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/accept")
    resp = client.post(
        "/api/v1/invoices",
        json={"orderRef": order["id"], "issueDate": "10/03/2026", "dueDate": "09/03/2026"},
    )
    assert resp.status_code == 400


def test_invoice_due_date_defaults_to_issue_plus_seven(client, customer_id, product_id):
    order = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 1}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/accept")
    inv = client.post(
        "/api/v1/invoices", json={"orderRef": order["id"], "issueDate": "01/03/2026"}
    ).json()
    assert inv["issueDate"] == "01/03/2026"
    assert inv["dueDate"] == "08/03/2026"


# --- Payment ------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,expected",
    [("CREDIT_CARD", 201), ("BANK_TRANSFER", 201), ("E_WALLET", 201),
     ("credit_card", 400), ("PAYPAL", 400), ("", 400)],
)
def test_payment_method_allowed_values(client, customer_id, product_id, method, expected):
    order = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 1}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/accept")
    client.post("/api/v1/invoices", json={"orderRef": order["id"]})
    resp = client.post(
        "/api/v1/payments",
        json={"orderRef": order["id"], "amount": order["totalAmount"], "method": method},
    )
    assert resp.status_code == expected


def test_payment_status_not_client_settable(client, invoiced_order):
    """A client cannot self-verify its own payment."""
    order, _ = invoiced_order
    resp = client.post(
        "/api/v1/payments",
        json={
            "orderRef": order["id"],
            "amount": "389.97",
            "method": "CREDIT_CARD",
            "status": "VERIFIED",
        },
    )
    assert resp.status_code == 400


# --- ID handling across every entity ------------------------------------------


@pytest.mark.parametrize("entity", ["customers", "products", "orders", "payments", "invoices"])
def test_get_by_id_contract(client, entity):
    """400 malformed / 404 well-formed-but-absent (Implementation note 2).

    An empty id is excluded deliberately: `/api/v1/<entity>/` is the collection
    route, not a malformed-id request, so it is a different case entirely.
    """
    for malformed in ("not-a-uuid", "12345", "00000000-0000-0000-0000", "g" * 36):
        resp = client.get(f"/api/v1/{entity}/{malformed}")
        assert resp.status_code == 400, f"{entity}/{malformed} -> {resp.status_code}"
    assert client.get(f"/api/v1/{entity}/{uuid.uuid4()}").status_code == 404


def test_get_existing_entity_returns_200(client, customer_id, product_id, placed_order):
    assert client.get(f"/api/v1/customers/{customer_id}").status_code == 200
    assert client.get(f"/api/v1/products/{product_id}").status_code == 200
    assert client.get(f"/api/v1/orders/{placed_order['id']}").status_code == 200
