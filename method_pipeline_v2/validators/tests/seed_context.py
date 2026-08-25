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

Every HTTP call made during seeding is recorded in SeedContext.calls and,
when a log_path is given, dumped to a JSON file for debugging — including
when provisioning crashes partway through.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from validators.tests.test_groups.CustomerTestGroup import CustomerTestGroup
from validators.tests.test_groups.OrderTestGroup import OrderTestGroup
from validators.tests.test_groups.ProductTestGroup import ProductTestGroup
from validators.tests.test_groups.InvoiceTestGroup import InvoiceTestGroup


BULK_PRODUCT_COUNT = 100

# ORDERREF_01, AMOUNT_01, STATUS_01, METHOD_01/02/03 in PaymentTestGroup are
# each a happy-path payment against an INVOICED order - paying one is a
# one-time INVOICED -> PAID transition, so sharing a single seeded order
# across all of them means only the first can ever succeed and the rest see
# a false 409. Each needs its own untouched INVOICED order.
PAYMENT_HAPPY_PATH_ORDER_COUNT = 6

# ORDERREF_01, TOTALAMT_01, ISSUEDATE_01, DUEDATE_01/02, STATUS_01 in
# InvoiceTestGroup are each a happy-path invoice creation against an
# ACCEPTED order - invoicing one is a one-time ACCEPTED -> INVOICED
# transition, so they can't share ctx.order_accepted_id (which is also
# already consumed by the seed's own INVOICED-order provisioning). Each
# needs its own untouched ACCEPTED order.
INVOICE_HAPPY_PATH_ORDER_COUNT = 6


@dataclass
class SeedContext:
    customer_id: str | None = None
    product_id: str | None = None
    bulk_product_ids: list[str] = field(default_factory=list)
    order_placed_id: str | None = None
    order_accepted_id: str | None = None
    order_invoiced_id: str | None = None
    invoice_id: str | None = None
    order_total_amount: str | None = None
    invoice_total_amount: Decimal | None = None
    bulk_invoiced_orders: list[dict[str, Any]] = field(default_factory=list)
    bulk_accepted_order_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)


def _record_call(
    ctx: SeedContext,
    step: str,
    method: str,
    url: str,
    request_body: Any,
    status: int | None,
    response_body: Any,
) -> None:
    ctx.calls.append({
        "step": step,
        "method": method,
        "url": url,
        "request_body": request_body,
        "status": status,
        "response_body": response_body,
    })


def _record_group_call(
    ctx: SeedContext,
    step: str,
    group: Any,
    request_body: Any,
    status: int,
    response_body: Any,
) -> None:
    """Record a call made through an ITestGroup helper (_post/_get), which
    stashes the method/url it used on the group instance."""
    _record_call(
        ctx,
        step,
        getattr(group, "_last_method", ""),
        getattr(group, "_last_url", ""),
        request_body,
        status,
        response_body,
    )


def _write_seed_log(
    ctx: SeedContext,
    base_url: str,
    api_paths: dict[str, str],
    log_path: str,
) -> None:
    payload = {
        "base_url": base_url,
        "api_paths": api_paths,
        "seed_ids": {
            "customer_id": ctx.customer_id,
            "product_id": ctx.product_id,
            "bulk_product_ids": ctx.bulk_product_ids,
            "order_placed_id": ctx.order_placed_id,
            "order_accepted_id": ctx.order_accepted_id,
            "order_invoiced_id": ctx.order_invoiced_id,
            "invoice_id": ctx.invoice_id,
            "order_total_amount": ctx.order_total_amount,
            "invoice_total_amount": ctx.invoice_total_amount,
            "bulk_invoiced_orders": ctx.bulk_invoiced_orders,
            "bulk_accepted_order_ids": ctx.bulk_accepted_order_ids,
        },
        "warnings": ctx.warnings,
        "calls": ctx.calls,
    }
    parent = os.path.dirname(log_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)


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


def _provision_accepted_order(
    ctx: SeedContext,
    base_url: str,
    order_api: str,
    accept_step: dict[str, Any],
    timeout: float,
    label: str,
) -> tuple[Any, str] | None:
    """Create one order and walk it PLACED -> ACCEPTED; return
    (order_group, order_id) or None (with a warning appended) if any step
    fails. The returned order_group is reused by callers that need to
    GET/verify the same order afterward."""
    order_group = OrderTestGroup(
        api=order_api,
        seed_customer_id=ctx.customer_id,
        seed_product_id=ctx.product_id,
    )
    body = order_group._body()
    status, resp = order_group._post(body)
    _record_group_call(ctx, f"create_{label}_order", order_group, body, status, resp)
    if not (status == 201 and isinstance(resp, dict) and resp.get("id")):
        ctx.warnings.append(f"seed {label} order creation failed: {status} {resp}")
        return None
    order_id = resp["id"]

    accept_method = accept_step.get("method", "POST")
    accept_url = base_url + str(accept_step["pathTemplate"]).replace("{id}", order_id)
    try:
        accept_resp = requests.request(accept_method, accept_url, timeout=timeout)
    except requests.RequestException as exc:
        _record_call(ctx, f"accept_{label}_order", accept_method, accept_url, None, None, f"request failed: {exc}")
        ctx.warnings.append(f"acceptOrder call failed for {label} order: {exc}")
        return None

    try:
        accept_body = accept_resp.json()
    except ValueError:
        accept_body = accept_resp.text
    _record_call(
        ctx, f"accept_{label}_order", accept_method, accept_url, None,
        accept_resp.status_code, accept_body,
    )
    if accept_resp.status_code >= 400:
        ctx.warnings.append(
            f"acceptOrder returned {accept_resp.status_code} for {label} order; order stays PLACED"
        )
        return None

    return order_group, order_id


def _provision_invoiced_order(
    ctx: SeedContext,
    base_url: str,
    api_paths: dict[str, str],
    order_api: str,
    accept_step: dict[str, Any],
    timeout: float,
    label: str,
) -> dict[str, Any] | None:
    """Create one order and walk it PLACED -> ACCEPTED -> INVOICED; return
    {"order_id", "invoice_id", "invoice_total_amount"} or None (with a
    warning appended) if any step fails. Mirrors the main lifecycle-order
    flow in _provision() but is reusable so each caller gets its own
    untouched INVOICED order instead of sharing one."""
    accepted = _provision_accepted_order(ctx, base_url, order_api, accept_step, timeout, label)
    if accepted is None:
        return None
    order_group, order_id = accepted

    invoice_group = InvoiceTestGroup(
        api=base_url + api_paths["invoice"],
        seed_order_accepted_id=order_id,
    )
    body = invoice_group._body()
    status, resp = invoice_group._post(body)
    _record_group_call(ctx, f"create_{label}_invoice", invoice_group, body, status, resp)
    if not (status == 201 and isinstance(resp, dict) and resp.get("id")):
        ctx.warnings.append(f"seed {label} invoice creation failed: {status} {resp}")
        return None
    invoice_id = resp["id"]
    try:
        invoice_total_amount = Decimal(str(resp.get("totalAmount")))
    except (InvalidOperation, TypeError):
        ctx.warnings.append(f"seed {label} invoice totalAmount missing/unparseable")
        return None

    get_status, get_resp = order_group._get(order_id)
    _record_group_call(ctx, f"verify_{label}_order_invoiced", order_group, None, get_status, get_resp)
    if not (get_status == 200 and isinstance(get_resp, dict) and get_resp.get("status") == "INVOICED"):
        ctx.warnings.append(f"{label} order did not transition to INVOICED after invoice creation")
        return None

    return {"order_id": order_id, "invoice_id": invoice_id, "invoice_total_amount": invoice_total_amount}


def build_seed_context(
    base_url: str,
    api_paths: dict[str, str],
    workflow_api_paths: dict[str, Any],
    timeout: float,
    log_path: str | None = None,
) -> SeedContext:
    """Create one customer, one product, and orders walked as far through the
    PLACED -> ACCEPTED -> INVOICED lifecycle as the app's declared APIs allow.
    Each step is best-effort: a failure stops that branch and is recorded in
    ctx.warnings, but earlier successfully-provisioned ids are kept.

    If log_path is given, every request/response made during seeding is
    written there as JSON — even when provisioning raises."""
    ctx = SeedContext()
    try:
        _provision(ctx, base_url, api_paths, workflow_api_paths, timeout)
    finally:
        if log_path:
            _write_seed_log(ctx, base_url, api_paths, log_path)
    return ctx


def _provision(
    ctx: SeedContext,
    base_url: str,
    api_paths: dict[str, str],
    workflow_api_paths: dict[str, Any],
    timeout: float,
) -> None:
    customer_group = CustomerTestGroup(api=base_url + api_paths["customer"])
    body = customer_group._body()
    status, resp = customer_group._post(body)
    _record_group_call(ctx, "create_customer", customer_group, body, status, resp)
    if status == 201 and isinstance(resp, dict) and resp.get("id"):
        ctx.customer_id = resp["id"]
    else:
        ctx.warnings.append(f"seed customer creation failed: {status} {resp}")
        return

    product_group = ProductTestGroup(api=base_url + api_paths["product"])
    body = product_group._body()
    status, resp = product_group._post(body)
    _record_group_call(ctx, "create_product", product_group, body, status, resp)
    if status == 201 and isinstance(resp, dict) and resp.get("id"):
        ctx.product_id = resp["id"]
    else:
        ctx.warnings.append(f"seed product creation failed: {status} {resp}")
        return

    # BULK_PRODUCT_COUNT distinct products, so LINEITEMS BC-Max tests can
    # send that many *distinct* productRef items (an order rejecting a
    # repeated productRef as a duplicate must not be confused with an order
    # rejecting too many items). Best-effort: stop and keep whatever
    # succeeded so far if the app starts failing partway through.
    for i in range(BULK_PRODUCT_COUNT):
        bulk_body = product_group._body()
        bulk_body["description"] = f"{bulk_body['description']} (bulk seed #{i + 1})"
        status, resp = product_group._post(bulk_body)
        _record_group_call(ctx, f"create_bulk_product_{i + 1:03d}", product_group, bulk_body, status, resp)
        if status == 201 and isinstance(resp, dict) and resp.get("id"):
            ctx.bulk_product_ids.append(resp["id"])
        else:
            ctx.warnings.append(
                f"seed bulk product #{i + 1}/{BULK_PRODUCT_COUNT} creation failed: "
                f"{status} {resp}; only {len(ctx.bulk_product_ids)} distinct products "
                "seeded - LINEITEMS BC-Max test(s) needing 100 distinct products may "
                "fall back to a repeated productRef"
            )
            break

    order_api = base_url + api_paths["order"]

    # Order #1 is left PLACED and untouched - needed by "wrong state" 409
    # cases in PaymentTestGroup/InvoiceTestGroup.
    placed_group = OrderTestGroup(
        api=order_api,
        seed_customer_id=ctx.customer_id,
        seed_product_id=ctx.product_id,
    )
    body = placed_group._body()
    status, resp = placed_group._post(body)
    _record_group_call(ctx, "create_placed_order", placed_group, body, status, resp)
    if status == 201 and isinstance(resp, dict) and resp.get("id"):
        ctx.order_placed_id = resp["id"]
    else:
        ctx.warnings.append(f"seed PLACED order creation failed: {status} {resp}")
        return

    # Order #2 is pushed through the workflow towards ACCEPTED / INVOICED.
    lifecycle_group = OrderTestGroup(
        api=order_api,
        seed_customer_id=ctx.customer_id,
        seed_product_id=ctx.product_id,
    )
    body = lifecycle_group._body()
    status, resp = lifecycle_group._post(body)
    _record_group_call(ctx, "create_lifecycle_order", lifecycle_group, body, status, resp)
    if not (status == 201 and isinstance(resp, dict) and resp.get("id")):
        ctx.warnings.append(f"seed lifecycle order creation failed: {status} {resp}")
        return

    lifecycle_order_id = resp["id"]
    ctx.order_total_amount = resp.get("totalAmount")

    accept_step = _find_accept_order_step(workflow_api_paths)
    if accept_step is None:
        ctx.warnings.append(
            "workflow_apis.json declares no acceptOrder-equivalent step; "
            "ACCEPTED/INVOICED seed data (Invoice/Payment happy-path and "
            "FK test cases) cannot be provisioned for this app."
        )
        return

    accept_method = accept_step.get("method", "POST")
    accept_url = base_url + str(accept_step["pathTemplate"]).replace("{id}", lifecycle_order_id)
    try:
        accept_resp = requests.request(accept_method, accept_url, timeout=timeout)
    except requests.RequestException as exc:
        _record_call(ctx, "accept_order", accept_method, accept_url, None, None, f"request failed: {exc}")
        ctx.warnings.append(f"acceptOrder call failed: {exc}")
        return

    try:
        accept_body = accept_resp.json()
    except ValueError:
        accept_body = accept_resp.text
    _record_call(
        ctx, "accept_order", accept_method, accept_url, None,
        accept_resp.status_code, accept_body,
    )

    if accept_resp.status_code >= 400:
        ctx.warnings.append(
            f"acceptOrder returned {accept_resp.status_code}; order stays PLACED"
        )
        return

    ctx.order_accepted_id = lifecycle_order_id

    invoice_group = InvoiceTestGroup(
        api=base_url + api_paths["invoice"],
        seed_order_accepted_id=ctx.order_accepted_id,
    )
    body = invoice_group._body()
    status, resp = invoice_group._post(body)
    _record_group_call(ctx, "create_invoice", invoice_group, body, status, resp)
    if status == 201 and isinstance(resp, dict) and resp.get("id"):
        ctx.invoice_id = resp["id"]
        try:
            ctx.invoice_total_amount = Decimal(str(resp.get("totalAmount")))
        except (InvalidOperation, TypeError):
            ctx.warnings.append("seed invoice totalAmount missing/unparseable")
    else:
        ctx.warnings.append(f"seed invoice creation failed: {status} {resp}")
        return

    # Per the domain workflow, invoice creation is expected to move the
    # order from ACCEPTED to INVOICED as a side effect - confirm it did
    # before handing this id to PaymentTestGroup as an INVOICED order.
    get_status, get_resp = lifecycle_group._get(lifecycle_order_id)
    _record_group_call(
        ctx, "verify_order_invoiced", lifecycle_group, None, get_status, get_resp
    )
    if get_status == 200 and isinstance(get_resp, dict) and get_resp.get("status") == "INVOICED":
        ctx.order_invoiced_id = lifecycle_order_id
    else:
        ctx.warnings.append(
            "order did not transition to INVOICED after invoice creation; "
            "Payment happy-path seed unavailable"
        )
        return

    # Dedicated INVOICED orders for PaymentTestGroup's happy-path tests (see
    # PAYMENT_HAPPY_PATH_ORDER_COUNT) - each is consumed by exactly one
    # test, so a failure partway through only shrinks the queue rather than
    # aborting seeding; PaymentTestGroup falls back to the shared
    # order_invoiced_id for whichever tests run out of a dedicated one.
    for i in range(PAYMENT_HAPPY_PATH_ORDER_COUNT):
        entry = _provision_invoiced_order(
            ctx, base_url, api_paths, order_api, accept_step, timeout,
            label=f"payment_bulk_{i + 1:02d}",
        )
        if entry is not None:
            ctx.bulk_invoiced_orders.append(entry)
        else:
            ctx.warnings.append(
                f"only {len(ctx.bulk_invoiced_orders)}/{PAYMENT_HAPPY_PATH_ORDER_COUNT} "
                "dedicated INVOICED orders seeded for Payment happy-path tests; "
                "remaining test(s) fall back to the single shared order_invoiced_id"
            )
            break

    # Dedicated ACCEPTED orders for InvoiceTestGroup's happy-path tests (see
    # INVOICE_HAPPY_PATH_ORDER_COUNT) - ctx.order_accepted_id can't be reused
    # here since it was already consumed (invoiced) above. Best-effort, same
    # pattern as the Payment queue.
    for i in range(INVOICE_HAPPY_PATH_ORDER_COUNT):
        accepted = _provision_accepted_order(
            ctx, base_url, order_api, accept_step, timeout,
            label=f"invoice_bulk_{i + 1:02d}",
        )
        if accepted is not None:
            _, order_id = accepted
            ctx.bulk_accepted_order_ids.append(order_id)
        else:
            ctx.warnings.append(
                f"only {len(ctx.bulk_accepted_order_ids)}/{INVOICE_HAPPY_PATH_ORDER_COUNT} "
                "dedicated ACCEPTED orders seeded for Invoice happy-path tests; "
                "remaining test(s) fall back to the single shared order_accepted_id "
                "(already INVOICED, so those will see a false 409)"
            )
            break
