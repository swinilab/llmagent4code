"""NFR 2.4 - transaction atomicity and isolation, verified against the live stack."""
import concurrent.futures
import uuid

import httpx
import pytest


def _post(base_url: str, path: str, body: dict | None = None) -> int:
    with httpx.Client(base_url=base_url, timeout=30, headers={"X-Client-Id": f"tx-{uuid.uuid4()}"}) as c:
        return c.post(path, json=body).status_code


def test_concurrent_accepts_exactly_one_wins(base_url, placed_order):
    """Isolation: 8 simultaneous accepts, exactly one 200 and seven 409s."""
    oid = placed_order["id"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda _: _post(base_url, f"/api/v1/orders/{oid}/accept"), range(8)))

    assert codes.count(200) == 1, f"expected exactly one winner, got {codes}"
    assert codes.count(409) == 7, f"expected seven losers, got {codes}"


def test_concurrent_payments_only_one_succeeds(base_url, invoiced_order):
    """No double-charging under concurrency."""
    order, _ = invoiced_order
    body = {"orderRef": order["id"], "amount": order["totalAmount"], "method": "CREDIT_CARD"}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(lambda _: _post(base_url, "/api/v1/payments", body), range(6)))

    assert codes.count(201) == 1, f"expected one successful payment, got {codes}"
    assert all(c in (201, 409) for c in codes), codes


def test_concurrent_invoices_only_one_created(base_url, placed_order, client):
    oid = placed_order["id"]
    assert client.post(f"/api/v1/orders/{oid}/accept").status_code == 200
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(
            pool.map(lambda _: _post(base_url, "/api/v1/invoices", {"orderRef": oid}), range(6))
        )
    assert codes.count(201) == 1, f"expected one invoice, got {codes}"


def test_invoice_creation_is_atomic_across_entities(client, placed_order):
    """Invoice row + order.invoice_ref + order.status all land together."""
    oid = placed_order["id"]
    client.post(f"/api/v1/orders/{oid}/accept")
    invoice = client.post("/api/v1/invoices", json={"orderRef": oid}).json()

    order = client.get(f"/api/v1/orders/{oid}").json()
    assert order["status"] == "INVOICED"
    assert order["invoiceRef"] == invoice["id"]
    assert client.get(f"/api/v1/invoices/{invoice['id']}").status_code == 200


def test_failed_payment_leaves_no_partial_state(client, invoiced_order):
    """A rejected payment must not create a row or move the order."""
    order, _ = invoiced_order
    oid = order["id"]
    before = client.get(f"/api/v1/orders/{oid}").json()["status"]

    resp = client.post(
        "/api/v1/payments", json={"orderRef": oid, "amount": "1.00", "method": "CREDIT_CARD"}
    )
    assert resp.status_code == 400

    assert client.get(f"/api/v1/orders/{oid}").json()["status"] == before
    # The order remains payable with the correct amount.
    assert client.post(
        "/api/v1/payments",
        json={"orderRef": oid, "amount": order["totalAmount"], "method": "CREDIT_CARD"},
    ).status_code == 201


def test_order_creation_rolls_back_on_bad_product(client, customer_id, product_id):
    """A partially-valid order writes nothing at all."""
    absent = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer_id,
            "lineItems": [
                {"productRef": product_id, "quantity": 1},
                {"productRef": absent, "quantity": 1},
            ],
        },
    )
    assert resp.status_code == 404
    assert absent in str(resp.json()["detail"])
