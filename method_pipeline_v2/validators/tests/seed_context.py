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

State transitions (PLACED -> ACCEPTED -> INVOICED) come from workflow_apis.json
when the app ships one. When it doesn't - prompts/latest.md never asked for
that file, so codex and claude-latest have none - the PLACED -> ACCEPTED step
is inferred from the app's *own* OpenAPI document instead: the transition
route is picked out of the routes the app itself publishes under the order
collection path from create_apis.json. That is still not guessing, on two
counts: only published routes are considered, and the order is re-read
afterwards so a mis-identified route surfaces as a warning rather than a
silently wrong seed. Without either source, ACCEPTED/INVOICED seed data
cannot be provisioned and a warning explains why.

Pool sizes matter for attribution. Invoicing and paying are one-time
transitions, so *every* test case that posts an invoice or a payment needs
its own untouched order - negative cases included. Sharing one order lets an
app's state check answer a negative case before it ever evaluates the field
rule under test, which makes the result track the app's internal validation
order instead of its correctness (this is what made TC_INV_BILLNAME_02/03
fail on state-first apps and pass on field-first ones).

Every HTTP call made during seeding is recorded in SeedContext.calls and,
when a log_path is given, dumped to a JSON file for debugging — including
when provisioning crashes partway through.
"""

from __future__ import annotations

import json
import os
import re
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
PAYMENT_HAPPY_PATH_ORDER_COUNT = 20

# ORDERREF_01, TOTALAMT_01, ISSUEDATE_01, DUEDATE_01/02, STATUS_01 in
# InvoiceTestGroup are each a happy-path invoice creation against an
# ACCEPTED order - invoicing one is a one-time ACCEPTED -> INVOICED
# transition, so they can't share ctx.order_accepted_id (which is also
# already consumed by the seed's own INVOICED-order provisioning). Each
# needs its own untouched ACCEPTED order.
INVOICE_HAPPY_PATH_ORDER_COUNT = 30


@dataclass
class SeedContext:
    customer_id: str | None = None
    product_id: str | None = None
    product_price: str | None = None
    bulk_product_ids: list[str] = field(default_factory=list)
    order_placed_id: str | None = None
    order_accepted_id: str | None = None
    order_invoiced_id: str | None = None
    invoice_id: str | None = None
    order_total_amount: str | None = None
    invoice_total_amount: Decimal | None = None
    bulk_invoiced_orders: list[dict[str, Any]] = field(default_factory=list)
    bulk_accepted_order_ids: list[str] = field(default_factory=list)
    # The PLACED -> ACCEPTED transition actually used, whether declared in
    # workflow_apis.json or inferred from the app's OpenAPI. Recorded so the
    # report shows which route the seed relied on.
    accept_step: dict[str, Any] | None = None
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


def _find_declared_accept_step(workflow_api_paths: dict[str, Any]) -> dict[str, Any] | None:
    """Locate the workflow step that moves an Order from PLACED to ACCEPTED,
    as *declared* in workflow_apis.json."""
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


# Candidate locations of the app's own OpenAPI document. FastAPI serves
# /openapi.json by default; apps that version their docs (e.g. chatdev-v2's
# openapi_url="/api/v1/openapi.json") are covered by the versioned variants.
OPENAPI_URL_CANDIDATES = (
    "/openapi.json",
    "/api/v1/openapi.json",
    "/api/openapi.json",
    "/v1/openapi.json",
)

# Path segment naming a dedicated PLACED -> ACCEPTED action route.
ACCEPT_ACTION_SEGMENTS = ("accept",)
# Path segment naming a generic status-setter route, driven by a request body.
STATUS_ACTION_SEGMENTS = ("status", "state")


def _fetch_openapi(
    ctx: SeedContext, base_url: str, timeout: float
) -> dict[str, Any] | None:
    """Fetch the running app's OpenAPI document, trying the conventional
    locations. Returns the parsed spec or None."""
    for candidate in OPENAPI_URL_CANDIDATES:
        url = base_url + candidate
        try:
            resp = requests.get(url, timeout=timeout)
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        try:
            spec = resp.json()
        except ValueError:
            continue
        if isinstance(spec, dict) and isinstance(spec.get("paths"), dict):
            _record_call(ctx, "fetch_openapi", "GET", url, None, resp.status_code,
                         f"<spec with {len(spec['paths'])} paths>")
            return spec
    return None


def _resolve_schema(spec: dict[str, Any], schema: Any, depth: int = 0) -> dict[str, Any]:
    """Resolve a (possibly $ref'd) OpenAPI schema node into a plain dict."""
    if not isinstance(schema, dict) or depth > 5:
        return {}
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        node: Any = spec
        for part in ref[2:].split("/"):
            if not isinstance(node, dict):
                return {}
            node = node.get(part, {})
        return _resolve_schema(spec, node, depth + 1)
    return schema


def _status_field_for_accepted(spec: dict[str, Any], operation: dict[str, Any]) -> str:
    """Name of the request-body field that carries the target status for a
    generic status-setter route. Derived from the operation's own schema:
    the property whose enum contains ACCEPTED. Falls back to "status"."""
    body = operation.get("requestBody")
    if isinstance(body, dict):
        content = body.get("content")
        if isinstance(content, dict):
            for media in ("application/json", "*/*"):
                media_obj = content.get(media)
                if not isinstance(media_obj, dict):
                    continue
                schema = _resolve_schema(spec, media_obj.get("schema"))
                props = schema.get("properties")
                if not isinstance(props, dict):
                    continue
                for prop_name, prop_schema in props.items():
                    resolved = _resolve_schema(spec, prop_schema)
                    enum = resolved.get("enum")
                    if isinstance(enum, list) and "ACCEPTED" in enum:
                        return prop_name
    return "status"


def _discover_accept_order_step(
    ctx: SeedContext, spec: dict[str, Any], order_path: str
) -> dict[str, Any] | None:
    """Infer the PLACED -> ACCEPTED transition from the app's own OpenAPI
    document, given the order collection path from create_apis.json.

    Only routes the app itself publishes are considered - this narrows the
    published contract down to the transition the test suite needs, rather
    than guessing undeclared routes. Two shapes are recognised, both
    observed in the corpus:

      A. a dedicated action route   POST {orders}/{id}/accept
      B. a generic status setter    PUT  {orders}/{id}/status  {"status": "ACCEPTED"}

    The caller verifies the order actually reached ACCEPTED afterwards, so a
    wrong candidate surfaces as a seed warning rather than a silent bad seed.
    """
    prefix = order_path.rstrip("/")
    action_re = re.compile(
        rf"^{re.escape(prefix)}/\{{[^}}/]+\}}/(?P<action>[A-Za-z_-]+)/?$"
    )

    dedicated: dict[str, Any] | None = None
    generic: dict[str, Any] | None = None

    for path, path_item in sorted(spec.get("paths", {}).items()):
        if not isinstance(path_item, dict):
            continue
        match = action_re.match(path)
        if not match:
            continue
        action = match.group("action").lower()
        for method, operation in path_item.items():
            if method.lower() not in ("post", "put", "patch"):
                continue
            if not isinstance(operation, dict):
                continue
            # Normalise the app's own parameter name to the {id} token that
            # the seeding code substitutes into.
            template = re.sub(r"\{[^}/]+\}", "{id}", path)
            if action in ACCEPT_ACTION_SEGMENTS and dedicated is None:
                dedicated = {
                    "method": method.upper(),
                    "pathTemplate": template,
                    "precondition": "PLACED",
                    "discoveredFrom": "openapi:action-route",
                }
            elif action in STATUS_ACTION_SEGMENTS and generic is None:
                field_name = _status_field_for_accepted(spec, operation)
                generic = {
                    "method": method.upper(),
                    "pathTemplate": template,
                    "precondition": "PLACED",
                    "body": {field_name: "ACCEPTED"},
                    "discoveredFrom": "openapi:status-route",
                }

    step = dedicated or generic
    if step is not None:
        ctx.warnings.append(
            "acceptOrder step not declared in workflow_apis.json; inferred "
            f"{step['method']} {step['pathTemplate']} from the app's own OpenAPI "
            f"({step['discoveredFrom']}). Transition is verified by re-reading "
            "the order's status."
        )
    return step


def _resolve_accept_order_step(
    ctx: SeedContext,
    base_url: str,
    api_paths: dict[str, str],
    workflow_api_paths: dict[str, Any],
    timeout: float,
) -> dict[str, Any] | None:
    """The declared step wins; otherwise infer it from the running app's
    OpenAPI so apps generated under a prompt that never asked for
    workflow_apis.json (e.g. prompts/latest.md) are still seedable."""
    declared = _find_declared_accept_step(workflow_api_paths)
    if declared is not None:
        return declared

    spec = _fetch_openapi(ctx, base_url, timeout)
    if spec is None:
        ctx.warnings.append(
            "acceptOrder step is neither declared in workflow_apis.json nor "
            "discoverable: the app serves no OpenAPI document at any of "
            f"{', '.join(OPENAPI_URL_CANDIDATES)}."
        )
        return None

    step = _discover_accept_order_step(ctx, spec, api_paths["order"])
    if step is None:
        ctx.warnings.append(
            "acceptOrder step is neither declared in workflow_apis.json nor "
            "present in the app's OpenAPI: no PLACED -> ACCEPTED transition "
            f"route found under {api_paths['order']}."
        )
    return step


def _perform_accept(
    ctx: SeedContext,
    base_url: str,
    accept_step: dict[str, Any],
    order_id: str,
    timeout: float,
    label: str,
) -> bool:
    """Fire the PLACED -> ACCEPTED transition for one order. Returns whether
    the call itself succeeded (the caller verifies the resulting state)."""
    method = accept_step.get("method", "POST")
    url = base_url + str(accept_step["pathTemplate"]).replace("{id}", order_id)
    body = accept_step.get("body")
    try:
        resp = requests.request(method, url, json=body, timeout=timeout)
    except requests.RequestException as exc:
        _record_call(ctx, f"accept_{label}_order", method, url, body, None,
                     f"request failed: {exc}")
        ctx.warnings.append(f"acceptOrder call failed for {label} order: {exc}")
        return False

    try:
        resp_body = resp.json()
    except ValueError:
        resp_body = resp.text
    _record_call(ctx, f"accept_{label}_order", method, url, body,
                 resp.status_code, resp_body)

    if resp.status_code >= 400:
        ctx.warnings.append(
            f"acceptOrder returned {resp.status_code} for {label} order; "
            "order stays PLACED"
        )
        return False
    return True


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

    if not _perform_accept(ctx, base_url, accept_step, order_id, timeout, label):
        return None

    # The transition route may have been inferred rather than declared, so
    # confirm the order really is ACCEPTED before handing it to a test.
    get_status, get_resp = order_group._get(order_id)
    _record_group_call(ctx, f"verify_{label}_order_accepted", order_group, None, get_status, get_resp)
    if not (get_status == 200 and isinstance(get_resp, dict) and get_resp.get("status") == "ACCEPTED"):
        observed = get_resp.get("status") if isinstance(get_resp, dict) else get_resp
        ctx.warnings.append(
            f"{label} order did not reach ACCEPTED via "
            f"{accept_step.get('method')} {accept_step.get('pathTemplate')} "
            f"(observed status: {observed!r})"
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
        # Prefer the server-echoed price (what the app will actually snapshot
        # onto order line items) over the sent value, in case the app
        # normalizes it (e.g. "10" -> "10.00").
        ctx.product_price = (resp.get("price") or {}).get("amount") or body["price"]["amount"]
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

    accept_step = _resolve_accept_order_step(
        ctx, base_url, api_paths, workflow_api_paths, timeout
    )
    if accept_step is None:
        ctx.warnings.append(
            "ACCEPTED/INVOICED seed data (Invoice/Payment happy-path and "
            "FK test cases) cannot be provisioned for this app."
        )
        return
    ctx.accept_step = accept_step

    if not _perform_accept(ctx, base_url, accept_step, lifecycle_order_id, timeout, "lifecycle"):
        return

    get_status, get_resp = lifecycle_group._get(lifecycle_order_id)
    _record_group_call(ctx, "verify_order_accepted", lifecycle_group, None, get_status, get_resp)
    if not (get_status == 200 and isinstance(get_resp, dict) and get_resp.get("status") == "ACCEPTED"):
        observed = get_resp.get("status") if isinstance(get_resp, dict) else get_resp
        ctx.warnings.append(
            "lifecycle order did not reach ACCEPTED via "
            f"{accept_step.get('method')} {accept_step.get('pathTemplate')} "
            f"(observed status: {observed!r})"
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
