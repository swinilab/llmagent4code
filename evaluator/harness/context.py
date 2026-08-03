"""Shared execution context handed to every scenario.

Bundles the four observation channels -- HTTP, application metrics, PostgreSQL,
Toxiproxy -- plus Docker lifecycle control, so a scenario declares what it needs
rather than constructing connections itself. It also owns the workflow seeding
helper, because five of the six scenarios need a product or a full order chain
before they can begin, and that seeding must be identical everywhere for the
runs to be comparable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from .appmetrics import AppMetrics
from .compose import Compose
from .httpclient import HttpHarness, Response
from .pgprobe import PgProbe
from .toxiproxy import Toxiproxy


class SeedError(RuntimeError):
    """A precondition could not be established.

    Seeding uses only endpoints the submission itself declares, so a failure
    here means the functional contract is broken -- the dependent scenario is
    NOT_EXERCISABLE, not FAIL.
    """


@dataclass
class Thresholds:
    raw: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    @classmethod
    def load(cls, path: Path) -> "Thresholds":
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


@dataclass
class WorkflowChain:
    """Identifiers produced by seeding a complete order through to payment."""

    customer_id: str
    product_id: str
    order_id: str
    invoice_id: str
    payment_id: str


class Context:
    def __init__(
        self,
        app_id: str,
        base_url: str,
        compose: Compose,
        pg: PgProbe,
        toxi: Toxiproxy,
        thresholds: Thresholds,
    ):
        self.app_id = app_id
        self.base_url = base_url
        self.http = HttpHarness(base_url)
        self.metrics = AppMetrics(base_url)
        self.compose = compose
        self.pg = pg
        self.toxi = toxi
        self.thresholds = thresholds
        self._manifest: dict[str, Any] | None = None
        self._product_table: str | None = None

    # ── declared API surface ──────────────────────────────────────────────

    def manifest(self) -> dict[str, Any]:
        """Read create_apis.json from the submission.

        Paths are taken from the application's own manifest rather than assumed,
        which is what keeps the harness driveable against three independently
        generated repositories.
        """
        if self._manifest is None:
            path = self.compose.app_dir / "create_apis.json"
            if not path.is_file():
                raise SeedError("create_apis.json is missing")
            import json

            self._manifest = json.loads(path.read_text(encoding="utf-8"))
        return self._manifest

    def create_path(self, entity: str) -> str:
        entry = self.manifest().get(entity)
        if not isinstance(entry, dict) or "path" not in entry:
            raise SeedError(f"create_apis.json has no usable entry for {entity!r}")
        return str(entry["path"])

    def product_table(self) -> str:
        if self._product_table is None:
            self._product_table = self.pg.find_product_table()
        return self._product_table

    # ── seeding ───────────────────────────────────────────────────────────

    def _create(self, entity: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = self.http.post(self.create_path(entity), json_body=body)
        if resp.status != 201 or not isinstance(resp.body, dict):
            raise SeedError(
                f"creating {entity} returned HTTP {resp.status}: {str(resp.body)[:300]}"
            )
        return resp.body

    def seed_customer(self) -> str:
        body = self._create(
            "customer",
            {
                "name": "Evaluation Customer",
                "address": "1 Benchmark Street, Test City",
                "phone": "+84901234567",
                "bankingDetails": {"accountNumber": "123456789012", "bankName": "Test Bank"},
                "role": "CUSTOMER",
            },
        )
        return str(body["id"])

    def seed_product(self, description: str = "Evaluation Product", amount: str = "10.00") -> str:
        body = self._create(
            "product",
            {"description": description, "price": {"amount": amount, "currency": "USD"}},
        )
        return str(body["id"])

    def seed_order(self, customer_id: str, product_id: str, quantity: int = 2) -> str:
        body = self._create(
            "order",
            {
                "customerRef": customer_id,
                "lineItems": [{"productRef": product_id, "quantity": quantity}],
            },
        )
        return str(body["id"])

    def seed_to_payment(self) -> WorkflowChain:
        """Drive the workflow through step 4, leaving it ready for verification.

        Stops deliberately at PENDING payment / ISSUED invoice / PAID order --
        the exact state ASR-A4 must find restored after its rollback.
        """
        customer_id = self.seed_customer()
        product_id = self.seed_product(amount="25.00")
        order_id = self.seed_order(customer_id, product_id, quantity=2)

        self._workflow_post(f"/api/v1/orders/{order_id}/accept", "accept order")

        invoice = self._create("invoice", {"orderRef": order_id})
        invoice_id = str(invoice["id"])

        total = self._order_total(order_id)
        payment = self._create(
            "payment",
            {"orderRef": order_id, "amount": total, "method": "BANK_TRANSFER"},
        )
        return WorkflowChain(customer_id, product_id, order_id, invoice_id, str(payment["id"]))

    def _order_total(self, order_id: str) -> str:
        resp = self.http.get(f"/api/v1/orders/{order_id}")
        if resp.status != 200 or not isinstance(resp.body, dict):
            raise SeedError(f"reading order {order_id} returned HTTP {resp.status}")
        total = resp.body.get("totalAmount")
        if total is None:
            raise SeedError("order response has no totalAmount")
        # Normalise to the two-decimal string form the payment contract requires.
        return f"{Decimal(str(total)):.2f}"

    def _workflow_post(self, path: str, what: str) -> Response:
        resp = self.http.post(path)
        if resp.status != 200:
            raise SeedError(f"{what} returned HTTP {resp.status}: {str(resp.body)[:300]}")
        return resp

    # ── convenience ───────────────────────────────────────────────────────

    def reset(self) -> None:
        self.metrics.reset()

    @staticmethod
    def unknown_uuid() -> str:
        return str(uuid.uuid4())