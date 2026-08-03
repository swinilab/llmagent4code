"""End-to-end checks on the reference application over HTTP.

Driven through Starlette's TestClient against SQLite, so the workflow and the
transaction boundary can be verified without a container stack. The scenarios
that need real fault injection -- timeout, outage -- still require Docker and
Toxiproxy; what is checked here is everything that does not.

The transaction test is the important one. It asserts the same post-rollback
triple the evaluator asserts, so a disagreement between this file and
asr_a4_transaction.py would surface here rather than during a live run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "evaluator" / "reference_app"

os.environ.setdefault("DATABASE_URL", f"sqlite:///{REFERENCE / '_test.db'}")
os.environ.setdefault("ENABLE_TEST_HOOKS", "true")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REFERENCE))

pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.database import engine  # noqa: E402


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _customer(client) -> str:
    r = client.post(
        "/api/v1/customers",
        json={
            "name": "Reference Customer",
            "address": "1 Calibration Road, Test City",
            "phone": "+84901234567",
            "bankingDetails": {"accountNumber": "123456789012", "bankName": "Test Bank"},
            "role": "CUSTOMER",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _product(client, amount: str = "25.00") -> str:
    r = client.post(
        "/api/v1/products",
        json={"description": "Calibration product", "price": {"amount": amount, "currency": "USD"}},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _to_payment(client) -> dict[str, str]:
    """Drive the workflow to the end of step 4."""
    customer_id = _customer(client)
    product_id = _product(client)
    order = client.post(
        "/api/v1/orders",
        json={"customerRef": customer_id, "lineItems": [{"productRef": product_id, "quantity": 2}]},
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    assert client.post(f"/api/v1/orders/{order_id}/accept").status_code == 200
    invoice = client.post("/api/v1/invoices", json={"orderRef": order_id})
    assert invoice.status_code == 201, invoice.text

    total = client.get(f"/api/v1/orders/{order_id}").json()["totalAmount"]
    payment = client.post(
        "/api/v1/payments",
        json={"orderRef": order_id, "amount": total, "method": "BANK_TRANSFER"},
    )
    assert payment.status_code == 201, payment.text
    return {
        "order": order_id,
        "invoice": invoice.json()["id"],
        "payment": payment.json()["id"],
    }


def test_seven_step_workflow_completes(client) -> None:
    ids = _to_payment(client)

    # After step 4 the order is PAID while the payment is still PENDING. This
    # pairing looks wrong at a glance and is exactly what ASR-A4 restores.
    assert client.get(f"/api/v1/orders/{ids['order']}").json()["status"] == "PAID"
    assert client.get(f"/api/v1/payments/{ids['payment']}").json()["status"] == "PENDING"

    assert client.post(f"/api/v1/payments/{ids['payment']}/verify").status_code == 200
    assert client.get(f"/api/v1/orders/{ids['order']}").json()["status"] == "VERIFIED"
    assert client.get(f"/api/v1/invoices/{ids['invoice']}").json()["status"] == "PAID"

    assert client.post(f"/api/v1/orders/{ids['order']}/ship").status_code == 200
    assert client.post(f"/api/v1/orders/{ids['order']}/close").status_code == 200
    assert client.get(f"/api/v1/orders/{ids['order']}").json()["status"] == "CLOSED"


def test_illegal_transition_is_refused(client) -> None:
    ids = _to_payment(client)
    r = client.post(f"/api/v1/orders/{ids['order']}/ship")
    assert r.status_code == 409, "shipping an unverified order must conflict"


def test_transaction_rolls_back_all_three_rows(client) -> None:
    """ASR-A4, asserted exactly as the evaluator asserts it."""
    ids = _to_payment(client)
    before = client.get("/internal/metrics").json()["transaction_rollbacks_total"]

    faulted = client.post(
        f"/api/v1/payments/{ids['payment']}/verify",
        headers={"X-Test-Fault": "after-payment-update"},
    )
    assert faulted.status_code in (500, 503)
    assert faulted.json()["error"]["code"] == "TRANSACTION_FAILED"

    # The rollback must restore the state at the end of step 4, in full.
    assert client.get(f"/api/v1/payments/{ids['payment']}").json()["status"] == "PENDING"
    assert client.get(f"/api/v1/invoices/{ids['invoice']}").json()["status"] == "ISSUED"
    assert client.get(f"/api/v1/orders/{ids['order']}").json()["status"] == "PAID"

    after = client.get("/internal/metrics").json()["transaction_rollbacks_total"]
    assert after > before

    # A clean retry must then succeed, proving nothing was left wedged.
    assert client.post(f"/api/v1/payments/{ids['payment']}/verify").status_code == 200
    assert client.get(f"/api/v1/payments/{ids['payment']}").json()["status"] == "VERIFIED"


def test_retry_absorbs_injected_transient_failures(client) -> None:
    """ASR-A2: three attempts, two retries, one read reaching the database."""
    product_id = _product(client)
    client.post("/internal/test/reset")
    before = client.get("/internal/metrics").json()

    r = client.get(
        f"/api/v1/products/{product_id}",
        headers={"X-Test-Fault": "transient-db-failures=2"},
    )
    assert r.status_code == 200, r.text

    after = client.get("/internal/metrics").json()
    assert after["db_product_read_attempts_total"] - before["db_product_read_attempts_total"] == 3
    assert after["retry_attempts_total"] - before["retry_attempts_total"] == 2
    # Only the successful attempt should have reached PostgreSQL.
    assert after["db_product_reads_total"] - before["db_product_reads_total"] == 1


def test_non_transient_failures_are_not_retried(client) -> None:
    client.post("/internal/test/reset")
    before = client.get("/internal/metrics").json()["retry_attempts_total"]

    assert client.get("/api/v1/products/not-a-uuid").status_code == 400
    assert client.get("/api/v1/products/3fa85f64-5717-4562-b3fc-2c963f66afa6").status_code == 404

    after = client.get("/internal/metrics").json()["retry_attempts_total"]
    assert after == before, "validation and not-found must never be retried"


def test_identifier_contract(client) -> None:
    product_id = _product(client)
    assert client.get(f"/api/v1/products/{product_id}").status_code == 200
    assert client.get("/api/v1/products/3fa85f64-5717-4562-b3fc-2c963f66afa6").status_code == 404
    assert client.get("/api/v1/products/not-a-uuid").status_code == 400


def test_server_controlled_fields_are_rejected(client) -> None:
    customer_id = _customer(client)
    product_id = _product(client)
    r = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer_id,
            "lineItems": [{"productRef": product_id, "quantity": 1}],
            "totalAmount": "1.00",
        },
    )
    assert r.status_code == 400


def test_duplicate_product_refs_are_rejected(client) -> None:
    customer_id = _customer(client)
    product_id = _product(client)
    r = client.post(
        "/api/v1/orders",
        json={
            "customerRef": customer_id,
            "lineItems": [
                {"productRef": product_id, "quantity": 1},
                {"productRef": product_id, "quantity": 2},
            ],
        },
    )
    assert r.status_code == 400, "duplicates are rejected, never merged"


def test_metrics_schema_matches_the_contract(client) -> None:
    body = client.get("/internal/metrics").json()
    from evaluator.harness.appmetrics import REQUIRED_KEYS

    assert set(body) == set(REQUIRED_KEYS)
    assert all(isinstance(v, int) for v in body.values())


def test_reset_returns_204_and_clears_counters(client) -> None:
    client.get("/api/v1/products/not-a-uuid")
    assert client.post("/internal/test/reset").status_code == 204
    assert client.get("/internal/metrics").json()["cache_hits_total"] == 0


def test_unrecognised_test_header_is_ignored(client) -> None:
    """A bad directive must not turn a valid request into an error."""
    product_id = _product(client)
    r = client.get(
        f"/api/v1/products/{product_id}", headers={"X-Test-Fault": "not-a-real-directive"}
    )
    assert r.status_code == 200


def test_observation_paths_answer(client) -> None:
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code in (200, 503)
