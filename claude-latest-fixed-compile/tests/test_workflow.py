"""The 7-step behaviour workflow and its state-machine guards."""
import uuid

import pytest


def test_full_workflow_place_to_close(client, customer_id, product_id):
    """Steps 1-7 end to end, asserting the state after each one."""
    # 1. Customer places order
    resp = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 3}]},
    )
    assert resp.status_code == 201
    order = resp.json()
    oid = order["id"]
    assert order["status"] == "PLACED"
    assert order["totalAmount"] == "389.97"          # 3 x 129.99, server-computed
    assert order["lineItems"][0]["unitPriceSnapshot"] == "129.99"
    assert order["invoiceRef"] is None

    # 2. Order Staff accepts
    assert client.post(f"/api/v1/orders/{oid}/accept").json()["status"] == "ACCEPTED"

    # 3. Accountant invoices
    resp = client.post("/api/v1/invoices", json={"orderRef": oid})
    assert resp.status_code == 201
    invoice = resp.json()
    assert invoice["totalAmount"] == "389.97"
    assert invoice["status"] == "ISSUED"
    assert invoice["billingInfo"]["name"] == "Alice Smith"   # snapshot, not a live ref
    order = client.get(f"/api/v1/orders/{oid}").json()
    assert order["status"] == "INVOICED"
    assert order["invoiceRef"] == invoice["id"]

    # 4. Customer pays
    resp = client.post(
        "/api/v1/payments",
        json={"orderRef": oid, "amount": "389.97", "method": "CREDIT_CARD"},
    )
    assert resp.status_code == 201
    payment = resp.json()
    assert payment["status"] == "PENDING"
    assert client.get(f"/api/v1/orders/{oid}").json()["status"] == "PAID"

    # 5. Accountant verifies
    assert client.post(f"/api/v1/payments/{payment['id']}/verify").json()["status"] == "VERIFIED"
    assert client.get(f"/api/v1/orders/{oid}").json()["status"] == "VERIFIED"

    # 6. Order Staff ships
    assert client.post(f"/api/v1/orders/{oid}/ship").json()["status"] == "SHIPPED"

    # 7. Order Staff closes
    assert client.post(f"/api/v1/orders/{oid}/close").json()["status"] == "CLOSED"


def test_entities_survive_a_cache_round_trip(client, invoiced_order):
    """Regression: a cached entity must rehydrate through its own validators.

    The first GET populates the cache from the database; the second is served
    from the cache. Serialized forms (dd/MM/yyyy dates, 2dp money strings) must
    therefore parse cleanly back in, not just out.
    """
    order, invoice = invoiced_order
    for path in (f"/api/v1/invoices/{invoice['id']}", f"/api/v1/orders/{order['id']}"):
        first = client.get(path)
        second = client.get(path)
        assert first.status_code == 200, path
        assert second.status_code == 200, f"{path} failed on the cached read"
        assert first.json() == second.json(), f"{path} differs between cold and cached read"


def test_invoice_requires_accepted_order(client, placed_order):
    """Step 3 precondition: a PLACED order cannot be invoiced."""
    resp = client.post("/api/v1/invoices", json={"orderRef": placed_order["id"]})
    assert resp.status_code == 409
    assert resp.json()["detail"]["orderStatus"] == "PLACED"


def test_payment_requires_invoiced_order(client, placed_order):
    resp = client.post(
        "/api/v1/payments",
        json={"orderRef": placed_order["id"], "amount": "389.97", "method": "CREDIT_CARD"},
    )
    assert resp.status_code == 409


def test_shipping_requires_verified_payment(client, invoiced_order):
    """Nothing ships until the accountant has verified the payment."""
    order, _ = invoiced_order
    assert client.post(f"/api/v1/orders/{order['id']}/ship").status_code == 409


def test_payment_amount_must_match_invoice_exactly(client, invoiced_order):
    order, invoice = invoiced_order
    for wrong in ("1.00", "389.96", "389.98", "99999999.99"):
        resp = client.post(
            "/api/v1/payments",
            json={"orderRef": order["id"], "amount": wrong, "method": "BANK_TRANSFER"},
        )
        assert resp.status_code == 400, f"{wrong} should be rejected"
        assert resp.json()["detail"]["expected"] == invoice["totalAmount"]


def test_double_payment_rejected(client, invoiced_order):
    order, _ = invoiced_order
    body = {"orderRef": order["id"], "amount": "389.97", "method": "E_WALLET"}
    assert client.post("/api/v1/payments", json=body).status_code == 201
    assert client.post("/api/v1/payments", json=body).status_code == 409


def test_rejected_payment_returns_order_to_invoiced(client, invoiced_order):
    """A rejection must let the customer retry, not strand the order."""
    order, _ = invoiced_order
    pay = client.post(
        "/api/v1/payments",
        json={"orderRef": order["id"], "amount": "389.97", "method": "CREDIT_CARD"},
    ).json()
    resp = client.patch(f"/api/v1/payments/{pay['id']}/verification", json={"status": "REJECTED"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "INVOICED"


def test_terminal_states_reject_further_transitions(client, customer_id, product_id):
    order = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 1}]},
    ).json()
    oid = order["id"]
    assert client.post(f"/api/v1/orders/{oid}/cancel").json()["status"] == "CANCELLED"
    # CANCELLED is terminal
    assert client.post(f"/api/v1/orders/{oid}/accept").status_code == 409
    assert client.post(f"/api/v1/orders/{oid}/ship").status_code == 409
    assert client.post("/api/v1/invoices", json={"orderRef": oid}).status_code == 409


def test_one_invoice_per_order(client, invoiced_order):
    order, _ = invoiced_order
    assert client.post("/api/v1/invoices", json={"orderRef": order["id"]}).status_code == 409


@pytest.mark.parametrize("target", ["SHIPPED", "CLOSED", "PAID", "VERIFIED"])
def test_cannot_skip_workflow_steps(client, placed_order, target):
    """A PLACED order cannot jump straight to a later state."""
    resp = client.patch(f"/api/v1/orders/{placed_order['id']}/status", json={"status": target})
    assert resp.status_code == 409


def test_order_rejects_unknown_customer_and_product(client, customer_id, product_id):
    absent = str(uuid.uuid4())
    assert client.post(
        "/api/v1/orders",
        json={"customerRef": absent, "lineItems": [{"productRef": product_id, "quantity": 1}]},
    ).status_code == 404
    assert client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": absent, "quantity": 1}]},
    ).status_code == 404
