"""Functional tests: the seven-step workflow and its state machine."""

from __future__ import annotations

import httpx

from tests.conftest import advance_to_invoiced, advance_to_paid, make_order


def test_complete_seven_step_workflow(client: httpx.Client) -> None:
    _, _, order = make_order(client, quantity=2, amount="19.99")
    order_id = order["id"]
    assert order["status"] == "PLACED"
    # totalAmount is server-computed: 2 x 19.99
    assert order["totalAmount"] == "39.98"
    assert order["invoiceRef"] is None
    assert order["lineItems"][0]["unitPriceSnapshot"] == "19.99"

    # Step 2 - accept
    accepted = client.post(f"/api/v1/orders/{order_id}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"

    # Step 3 - invoice; Order advances and invoiceRef is set
    invoice = client.post("/api/v1/invoices", json={"orderRef": order_id})
    assert invoice.status_code == 201
    invoice_body = invoice.json()
    assert invoice_body["status"] == "ISSUED"
    assert invoice_body["totalAmount"] == "39.98"

    order_after_invoice = client.get(f"/api/v1/orders/{order_id}").json()
    assert order_after_invoice["status"] == "INVOICED"
    assert order_after_invoice["invoiceRef"] == invoice_body["id"]

    # Step 4 - payment; Order becomes PAID while Payment stays PENDING
    payment = client.post(
        "/api/v1/payments",
        json={"orderRef": order_id, "amount": "39.98", "method": "CREDIT_CARD"},
    )
    assert payment.status_code == 201
    payment_id = payment.json()["id"]
    assert payment.json()["status"] == "PENDING"
    assert client.get(f"/api/v1/orders/{order_id}").json()["status"] == "PAID"

    # Step 5 - verify; all three records advance atomically
    verified = client.post(f"/api/v1/payments/{payment_id}/verify")
    assert verified.status_code == 200
    assert verified.json()["status"] == "VERIFIED"
    assert client.get(f"/api/v1/invoices/{invoice_body['id']}").json()["status"] == "PAID"
    assert client.get(f"/api/v1/orders/{order_id}").json()["status"] == "VERIFIED"

    # Steps 6 and 7
    assert client.post(f"/api/v1/orders/{order_id}/ship").json()["status"] == "SHIPPED"
    assert client.post(f"/api/v1/orders/{order_id}/close").json()["status"] == "CLOSED"


def test_invalid_transitions_return_409(client: httpx.Client) -> None:
    _, _, order = make_order(client)
    order_id = order["id"]

    # PLACED cannot ship or close directly.
    assert client.post(f"/api/v1/orders/{order_id}/ship").status_code == 409
    assert client.post(f"/api/v1/orders/{order_id}/close").status_code == 409

    client.post(f"/api/v1/orders/{order_id}/accept")
    # Accepting twice is an illegal repeat transition.
    assert client.post(f"/api/v1/orders/{order_id}/accept").status_code == 409


def test_invoice_requires_accepted_order(client: httpx.Client) -> None:
    _, _, order = make_order(client)
    # Order is still PLACED, not ACCEPTED.
    response = client.post("/api/v1/invoices", json={"orderRef": order["id"]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATE_CONFLICT"


def test_payment_requires_invoiced_order(client: httpx.Client) -> None:
    _, _, order = make_order(client)
    response = client.post(
        "/api/v1/payments",
        json={"orderRef": order["id"], "amount": "39.98", "method": "CREDIT_CARD"},
    )
    assert response.status_code == 409


def test_payment_amount_must_match_invoice_exactly(client: httpx.Client) -> None:
    order, invoice = advance_to_invoiced(client)

    under = client.post(
        "/api/v1/payments",
        json={"orderRef": order["id"], "amount": "10.00", "method": "CREDIT_CARD"},
    )
    assert under.status_code == 409

    over = client.post(
        "/api/v1/payments",
        json={"orderRef": order["id"], "amount": "99999.99", "method": "BANK_TRANSFER"},
    )
    assert over.status_code == 409

    exact = client.post(
        "/api/v1/payments",
        json={"orderRef": order["id"], "amount": invoice["totalAmount"], "method": "E_WALLET"},
    )
    assert exact.status_code == 201


def test_invoice_default_dates(client: httpx.Client) -> None:
    _, invoice = advance_to_invoiced(client)
    from datetime import datetime, timedelta

    issue = datetime.strptime(invoice["issueDate"], "%d/%m/%Y").date()
    due = datetime.strptime(invoice["dueDate"], "%d/%m/%Y").date()
    assert due == issue + timedelta(days=7)


def test_customer_order_history_is_server_derived(client: httpx.Client) -> None:
    customer, _, order = make_order(client)
    body = client.get(f"/api/v1/customers/{customer['id']}").json()
    assert order["id"] in body["orderHistory"]


def test_double_verify_is_conflict(client: httpx.Client) -> None:
    _, _, payment = advance_to_paid(client)
    assert client.post(f"/api/v1/payments/{payment['id']}/verify").status_code == 200
    assert client.post(f"/api/v1/payments/{payment['id']}/verify").status_code == 409
