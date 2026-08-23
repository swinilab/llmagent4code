"""
seed_context.py
────────────────
Provisions real seed data (customer, product, orders in PLACED/ACCEPTED/
INVOICED states, invoice) against the running generated app before the
functional test groups execute.

Without this, every *TestGroup falls back to its own placeholder default
(e.g. "<seed: existing product id>") for any field that references another
entity, so FK-dependent and GET-by-id test cases send garbage instead of a
real UUID and can never pass regardless of the app's correctness.

State transitions (PLACED -> ACCEPTED -> INVOICED) are only attempted via
steps declared in workflow_apis.json, consistent with the harness's
documented contract of never guessing undeclared routes. If an app doesn't
ship workflow_apis.json (or omits the relevant step), ACCEPTED/INVOICED
seed data simply cannot be provisioned for it and the corresponding
placeholders are left in place; a warning explains why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from validators.tests.test_groups.CustomerTestGroup import CustomerTestGroup
from validators.tests.test_groups.OrderTestGroup import OrderTestGroup
from validators.tests.test_groups.ProductTestGroup import ProductTestGroup
from validators.tests.test_groups.InvoiceTestGroup import InvoiceTestGroup


@dataclass
class SeedContext:
    customer_id: str | None = None
    product_id: str | None = None
    order_placed_id: str | None = None
    order_accepted_id: str | None = None
    order_invoiced_id: str | None = None
    invoice_id: str | None = None
    order_total_amount: str | None = None
    invoice_total_amount: Decimal | None = None
    warnings: list[str] = field(default_factory=list)


def _find_accept_order_step(workflow_api_paths: dict[str, Any]) -> dict[str, Any] | None:
    """Locate the workflow step that moves an Order from PLACED to ACCEPTED."""
    for key, entry in workflow_api_paths.items():
        if key.lower() == "acceptorder":
            return entry
    for entry in workflow_api_paths.values():
        if (
            isinstance(entry, dict)
            and str(entry.get("precondition", "")).upper() == "PLACED"
            and "order" in str(entry.get("pathTemplate", "")).lower()
        ):
            return entry
    return None


def build_seed_context(
    base_url: str,
    api_paths: dict[str, str],
    workflow_api_paths: dict[str, Any],
    timeout: float,
) -> SeedContext:
    """Create one customer, one product, and orders walked as far through the
    PLACED -> ACCEPTED -> INVOICED lifecycle as the app's declared APIs allow.
    Each step is best-effort: a failure stops that branch and is recorded in
    ctx.warnings, but earlier successfully-provisioned ids are kept."""
    ctx = SeedContext()

    customer_group = CustomerTestGroup(api=base_url + api_paths["customer"])
    status, resp = customer_group._post(customer_group._body())
    if status == 201 and isinstance(resp, dict) and resp.get("id"):
        ctx.customer_id = resp["id"]
    else:
        ctx.warnings.append(f"seed customer creation failed: {status} {resp}")
        return ctx

    product_group = ProductTestGroup(api=base_url + api_paths["product"])
    status, resp = product_group._post(product_group._body())
    if status == 201 and isinstance(resp, dict) and resp.get("id"):
        ctx.product_id = resp["id"]
    else:
        ctx.warnings.append(f"seed product creation failed: {status} {resp}")
        return ctx

    order_api = base_url + api_paths["order"]

    # Order #1 is left PLACED and untouched - needed by "wrong state" 409
    # cases in PaymentTestGroup/InvoiceTestGroup.
    placed_group = OrderTestGroup(
        api=order_api,
        seed_customer_id=ctx.customer_id,
        seed_product_id=ctx.product_id,
    )
    status, resp = placed_group._post(placed_group._body())
    if status == 201 and isinstance(resp, dict) and resp.get("id"):
        ctx.order_placed_id = resp["id"]
    else:
        ctx.warnings.append(f"seed PLACED order creation failed: {status} {resp}")
        return ctx

    # Order #2 is pushed through the workflow towards ACCEPTED / INVOICED.
    lifecycle_group = OrderTestGroup(
        api=order_api,
        seed_customer_id=ctx.customer_id,
        seed_product_id=ctx.product_id,
    )
    status, resp = lifecycle_group._post(lifecycle_group._body())
    if not (status == 201 and isinstance(resp, dict) and resp.get("id")):
        ctx.warnings.append(f"seed lifecycle order creation failed: {status} {resp}")
        return ctx

    lifecycle_order_id = resp["id"]
    ctx.order_total_amount = resp.get("totalAmount")

    accept_step = _find_accept_order_step(workflow_api_paths)
    if accept_step is None:
        ctx.warnings.append(
            "workflow_apis.json declares no acceptOrder-equivalent step; "
            "ACCEPTED/INVOICED seed data (Invoice/Payment happy-path and "
            "FK test cases) cannot be provisioned for this app."
        )
        return ctx

    accept_url = base_url + str(accept_step["pathTemplate"]).replace("{id}", lifecycle_order_id)
    try:
        accept_resp = requests.request(
            accept_step.get("method", "POST"), accept_url, timeout=timeout
        )
    except requests.RequestException as exc:
        ctx.warnings.append(f"acceptOrder call failed: {exc}")
        return ctx

    if accept_resp.status_code >= 400:
        ctx.warnings.append(
            f"acceptOrder returned {accept_resp.status_code}; order stays PLACED"
        )
        return ctx

    ctx.order_accepted_id = lifecycle_order_id

    invoice_group = InvoiceTestGroup(
        api=base_url + api_paths["invoice"],
        seed_order_accepted_id=ctx.order_accepted_id,
    )
    status, resp = invoice_group._post(invoice_group._body())
    if status == 201 and isinstance(resp, dict) and resp.get("id"):
        ctx.invoice_id = resp["id"]
        try:
            ctx.invoice_total_amount = Decimal(str(resp.get("totalAmount")))
        except (InvalidOperation, TypeError):
            ctx.warnings.append("seed invoice totalAmount missing/unparseable")
    else:
        ctx.warnings.append(f"seed invoice creation failed: {status} {resp}")
        return ctx

    # Per the domain workflow, invoice creation is expected to move the
    # order from ACCEPTED to INVOICED as a side effect - confirm it did
    # before handing this id to PaymentTestGroup as an INVOICED order.
    get_status, get_resp = lifecycle_group._get(lifecycle_order_id)
    if get_status == 200 and isinstance(get_resp, dict) and get_resp.get("status") == "INVOICED":
        ctx.order_invoiced_id = lifecycle_order_id
    else:
        ctx.warnings.append(
            "order did not transition to INVOICED after invoice creation; "
            "Payment happy-path seed unavailable"
        )

    return ctx
