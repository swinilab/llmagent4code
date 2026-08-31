"""
workflow_suite.py
─────────────────
Integration-level checks for the Behavior Workflow the prompt requires:

    1. Customer places order          -> PLACED
    2. Order Staff reviews & accepts  -> ACCEPTED
    3. Accountant creates invoice     -> INVOICED
    4. Customer pays invoice          -> PAID
    5. Accountant verifies payment    -> VERIFIED
    6. Order Staff ships paid order   -> SHIPPED
    7. Order Staff closes order       -> CLOSED

This is deliberately separate from the BVA/EP suite in validators/tests/
test_groups/, which is unit-level: those cases check one field constraint at
a time against a single create endpoint. Nothing here re-scores them. What
this module adds is the part a per-field suite cannot see - whether the
entities compose into a working state machine across requests.

Three sub-scores are reported, because "no route" and "route that behaves
wrongly" are different defects:

  capability   - does the app publish a route for each transition at all
  happy path   - does an order actually reach each expected state
  precondition - are out-of-order transitions rejected with 409, per the
                 prompt's Implementation note #2 ("reject references to
                 entities not in the required workflow state ... with 409")

Transition routes come from the app's own OpenAPI document (or from
workflow_apis.json when the app ships one), never from guessing: see
seed_context._fetch_openapi. Every state assertion is made by re-reading the
entity, so a mis-identified route fails loudly instead of scoring silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import requests

from validators.tests.seed_context import (
    _fetch_openapi,
    _resolve_schema,
    SeedContext,
)
from validators.tests.test_groups.CustomerTestGroup import CustomerTestGroup
from validators.tests.test_groups.InvoiceTestGroup import InvoiceTestGroup
from validators.tests.test_groups.OrderTestGroup import OrderTestGroup
from validators.tests.test_groups.PaymentTestGroup import PaymentTestGroup
from validators.tests.test_groups.ProductTestGroup import ProductTestGroup


# Ordered lifecycle: (step id, human label, expected order status afterwards)
LIFECYCLE = [
    ("place",   "Customer places order",         "PLACED"),
    ("accept",  "Order Staff accepts order",     "ACCEPTED"),
    ("invoice", "Accountant creates invoice",    "INVOICED"),
    ("pay",     "Customer pays invoice",         "PAID"),
    ("verify",  "Accountant verifies payment",   "VERIFIED"),
    ("ship",    "Order Staff ships order",       "SHIPPED"),
    ("close",   "Order Staff closes order",      "CLOSED"),
]

# Steps driven by a create endpoint already declared in create_apis.json.
CREATE_DRIVEN_STEPS = {"place": "order", "invoice": "invoice", "pay": "payment"}

# Steps that need a transition route discovered on the entity, as
# (step id -> (owning entity, accepted path segments)).
TRANSITION_STEPS = {
    "accept": ("order", ("accept",)),
    "ship":   ("order", ("ship",)),
    "close":  ("order", ("close",)),
    "verify": ("payment", ("verify", "verification")),
}

STATUS_SEGMENTS = ("status", "state")


@dataclass
class WorkflowCheck:
    """One integration assertion."""
    check_id: str
    category: str            # "capability" | "happy_path" | "precondition"
    description: str
    result: bool
    expected: Any
    actual: Any
    method: str = ""
    url: str = ""
    detail: Any = None


@dataclass
class WorkflowReport:
    checks: list[WorkflowCheck] = field(default_factory=list)
    transitions: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def add(self, check: WorkflowCheck) -> None:
        self.checks.append(check)

    def by_category(self, category: str) -> list[WorkflowCheck]:
        return [c for c in self.checks if c.category == category]


# ──────────────────────────────────────────────────────────────────────────
#  Transition discovery
# ──────────────────────────────────────────────────────────────────────────

def _target_status_field(spec: dict[str, Any], operation: dict[str, Any],
                         target: str) -> str | None:
    """Field carrying the target status on a generic status-setter route,
    taken from the operation's own schema (the property whose enum contains
    `target`). None when the route cannot express this transition."""
    body = operation.get("requestBody")
    if not isinstance(body, dict):
        return None
    content = body.get("content")
    if not isinstance(content, dict):
        return None
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
            if isinstance(enum, list) and target in enum:
                return prop_name
    return None


def discover_transitions(
    spec: dict[str, Any],
    api_paths: dict[str, str],
    workflow_api_paths: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Map each transition step to the route that performs it.

    A route declared in workflow_apis.json wins; otherwise the step is
    inferred from routes the app itself publishes under the relevant
    collection path. Two shapes are recognised, both present in the corpus:
    a dedicated action route (POST {orders}/{id}/accept) and a generic
    status setter (PUT {orders}/{id}/status with {"status": "ACCEPTED"}).
    """
    declared = {k.lower(): v for k, v in (workflow_api_paths or {}).items()
                if isinstance(v, dict)}
    found: dict[str, dict[str, Any]] = {}

    for step, (entity, segments) in TRANSITION_STEPS.items():
        declared_entry = declared.get(f"{step}order") or declared.get(f"{step}payment")
        if declared_entry and declared_entry.get("pathTemplate"):
            found[step] = {
                "method": declared_entry.get("method", "POST"),
                "pathTemplate": re.sub(r"\{[^}/]+\}", "{id}",
                                       str(declared_entry["pathTemplate"])),
                "source": "workflow_apis.json",
            }
            continue

        prefix = api_paths.get(entity, "").rstrip("/")
        if not prefix:
            continue
        action_re = re.compile(
            rf"^{re.escape(prefix)}/\{{[^}}/]+\}}/(?P<action>[A-Za-z_-]+)/?$"
        )
        target_status = dict((s, st) for s, _, st in LIFECYCLE).get(step, "")

        # An app may publish several routes matching one step (claude-latest
        # has both POST .../verify and PATCH .../verification). Rank by the
        # segment's position in `segments` - the canonical spelling first -
        # rather than by however the paths happen to sort.
        dedicated: tuple[int, dict[str, Any]] | None = None
        generic: dict[str, Any] | None = None
        for path, path_item in sorted(spec.get("paths", {}).items()):
            if not isinstance(path_item, dict):
                continue
            match = action_re.match(path)
            if not match:
                continue
            action = match.group("action").lower()
            for method, operation in path_item.items():
                if method.lower() not in ("post", "put", "patch") or not isinstance(operation, dict):
                    continue
                template = re.sub(r"\{[^}/]+\}", "{id}", path)
                if action in segments:
                    rank = segments.index(action)
                    if dedicated is None or rank < dedicated[0]:
                        dedicated = (rank, {
                            "method": method.upper(),
                            "pathTemplate": template,
                            "source": "openapi:action-route",
                        })
                elif action in STATUS_SEGMENTS and generic is None:
                    field_name = _target_status_field(spec, operation, target_status)
                    if field_name:
                        generic = {
                            "method": method.upper(),
                            "pathTemplate": template,
                            "body": {field_name: target_status},
                            "source": "openapi:status-route",
                        }
        step_route = dedicated[1] if dedicated is not None else generic
        if step_route is not None:
            found[step] = step_route

    return found


# ──────────────────────────────────────────────────────────────────────────
#  HTTP helpers
# ──────────────────────────────────────────────────────────────────────────

def _call(report: WorkflowReport, method: str, url: str, body: Any,
          timeout: float) -> tuple[int | None, Any]:
    try:
        resp = requests.request(method, url, json=body, timeout=timeout)
    except requests.RequestException as exc:
        report.calls.append({"method": method, "url": url, "request_body": body,
                             "status": None, "response_body": f"request failed: {exc}"})
        return None, f"request failed: {exc}"
    try:
        parsed = resp.json()
    except ValueError:
        parsed = resp.text
    report.calls.append({"method": method, "url": url, "request_body": body,
                         "status": resp.status_code, "response_body": parsed})
    return resp.status_code, parsed


def _order_status(report: WorkflowReport, base_url: str, api_paths: dict[str, str],
                  order_id: str, timeout: float) -> Any:
    status, body = _call(report, "GET", f"{base_url}{api_paths['order']}/{order_id}",
                         None, timeout)
    if status == 200 and isinstance(body, dict):
        return body.get("status")
    return None


def _fire_transition(report: WorkflowReport, base_url: str, route: dict[str, Any],
                     entity_id: str, timeout: float) -> tuple[int | None, Any, str, str]:
    method = route.get("method", "POST")
    url = base_url + str(route["pathTemplate"]).replace("{id}", entity_id)
    status, body = _call(report, method, url, route.get("body"), timeout)
    return status, body, method, url


# ──────────────────────────────────────────────────────────────────────────
#  Suite
# ──────────────────────────────────────────────────────────────────────────

def _make_order(report: WorkflowReport, base_url: str, api_paths: dict[str, str],
                customer_id: str, product_id: str, timeout: float) -> str | None:
    """Create one PLACED order using the BVA/EP suite's known-valid body."""
    group = OrderTestGroup(api=base_url + api_paths["order"],
                           seed_customer_id=customer_id, seed_product_id=product_id)
    status, body = _call(report, "POST", base_url + api_paths["order"],
                         group._body(), timeout)
    if status == 201 and isinstance(body, dict) and body.get("id"):
        return body["id"]
    return None


def _advance_to(report: WorkflowReport, base_url: str, api_paths: dict[str, str],
                transitions: dict[str, dict[str, Any]], order_id: str,
                target: str, timeout: float) -> bool:
    """Walk a PLACED order forward to `target`. Staging for the precondition
    cases - not scored itself."""
    if target == "PLACED":
        return True
    if "accept" not in transitions:
        return False
    _fire_transition(report, base_url, transitions["accept"], order_id, timeout)
    if _order_status(report, base_url, api_paths, order_id, timeout) != "ACCEPTED":
        return False
    if target == "ACCEPTED":
        return True
    inv = InvoiceTestGroup(api=base_url + api_paths["invoice"],
                           seed_order_accepted_id=order_id)
    status, body = _call(report, "POST", base_url + api_paths["invoice"],
                         inv._body(), timeout)
    if not (status == 201 and isinstance(body, dict)):
        return False
    return (target == "INVOICED"
            and _order_status(report, base_url, api_paths, order_id, timeout) == "INVOICED")


# Precondition cases: (check id, order state to stage, description, action).
NEGATIVE_CASES = [
    ("WF_P_01_INVOICE_FROM_PLACED", "PLACED",
     "create invoice for a PLACED order", "invoice"),
    ("WF_P_02_PAY_FROM_ACCEPTED", "ACCEPTED",
     "pay an ACCEPTED (not INVOICED) order", "pay"),
    ("WF_P_03_SHIP_FROM_INVOICED", "INVOICED",
     "ship an INVOICED (not VERIFIED) order", "ship"),
    ("WF_P_04_CLOSE_FROM_ACCEPTED", "ACCEPTED",
     "close an ACCEPTED (not SHIPPED) order", "close"),
    ("WF_P_05_ACCEPT_TWICE", "ACCEPTED",
     "accept an already ACCEPTED order", "accept"),
]


def _emit_unrun(report: WorkflowReport, reason: str) -> None:
    """Record every happy-path and precondition check that never got to run,
    as a failure carrying the reason. Keeps the check set - and so the
    denominator - identical for every app."""
    for index, (step, label, target) in enumerate(LIFECYCLE, start=1):
        report.add(WorkflowCheck(
            check_id=f"WF_H_{index:02d}_{step.upper()}", category="happy_path",
            description=f"{label} -> {target}", result=False,
            expected=target, actual=f"not run: {reason}",
        ))
    for check_id, _state, description, _action in NEGATIVE_CASES:
        report.add(WorkflowCheck(
            check_id=check_id, category="precondition", description=description,
            result=False, expected=409, actual=f"not run: {reason}",
        ))


def run_workflow_suite(base_url: str, api_paths: dict[str, str],
                       workflow_api_paths: dict[str, Any] | None,
                       timeout: float = 10.0) -> WorkflowReport:
    """Run the integration-level workflow checks against a running app."""
    report = WorkflowReport()

    spec = _fetch_openapi(SeedContext(), base_url, timeout) or {}
    if not spec:
        report.warnings.append(
            "app serves no OpenAPI document; transition routes could only come "
            "from workflow_apis.json"
        )
    transitions = discover_transitions(spec, api_paths, workflow_api_paths)
    report.transitions = transitions

    # ---- C. capability -------------------------------------------------
    for step, _label, _target in LIFECYCLE:
        if step in CREATE_DRIVEN_STEPS:
            route = api_paths.get(CREATE_DRIVEN_STEPS[step], "")
            present = bool(route)
        else:
            route = transitions.get(step, {}).get("pathTemplate", "")
            present = step in transitions
        report.add(WorkflowCheck(
            check_id=f"WF_C_{step.upper()}",
            category="capability",
            description=f"app publishes a route for lifecycle step '{step}'",
            result=present, expected="route published",
            actual=route or "not found", detail=transitions.get(step),
        ))

    # ---- seed the actors the workflow needs ----------------------------
    cust = CustomerTestGroup(api=base_url + api_paths["customer"])
    status, body = _call(report, "POST", base_url + api_paths["customer"],
                         cust._body(), timeout)
    customer_id = body.get("id") if status == 201 and isinstance(body, dict) else None
    prod = ProductTestGroup(api=base_url + api_paths["product"])
    status, body = _call(report, "POST", base_url + api_paths["product"],
                         prod._body(), timeout)
    product_id = body.get("id") if status == 201 and isinstance(body, dict) else None
    if not (customer_id and product_id):
        reason = ("could not create the customer/product the workflow needs "
                  "(the app rejected or failed the create request)")
        report.warnings.append(reason)
        # Emit the remaining checks as failures rather than returning early.
        # Returning here would leave only the 7 capability checks, and an app
        # whose every request 500s would score 7/7 = 100% - a fabricated pass.
        # The denominator has to stay the same across apps for the numbers to
        # be comparable at all.
        _emit_unrun(report, reason)
        return report

    # ---- A. happy path -------------------------------------------------
    order_id = _make_order(report, base_url, api_paths, customer_id, product_id, timeout)
    placed_status = (_order_status(report, base_url, api_paths, order_id, timeout)
                     if order_id else "order not created")
    report.add(WorkflowCheck(
        check_id="WF_H_01_PLACE", category="happy_path",
        description="Customer places order -> PLACED",
        result=placed_status == "PLACED", expected="PLACED", actual=placed_status,
    ))

    invoice_total: Any = None
    payment_id: str | None = None
    for index, (step, label, target) in enumerate(LIFECYCLE[1:], start=2):
        check_id = f"WF_H_{index:02d}_{step.upper()}"
        if order_id is None:
            report.add(WorkflowCheck(check_id, "happy_path", f"{label} -> {target}",
                                     False, target, "skipped: no order"))
            continue

        if step == "invoice":
            inv = InvoiceTestGroup(api=base_url + api_paths["invoice"],
                                   seed_order_accepted_id=order_id)
            status, body = _call(report, "POST", base_url + api_paths["invoice"],
                                 inv._body(), timeout)
            if status == 201 and isinstance(body, dict):
                invoice_total = body.get("totalAmount")
        elif step == "pay":
            total = None
            if invoice_total is not None:
                try:
                    total = Decimal(str(invoice_total))
                except Exception:
                    total = None
            pay = PaymentTestGroup(api=base_url + api_paths["payment"],
                                   seed_order_invoiced_id=order_id,
                                   seed_invoice_total_amount=total)
            status, body = _call(report, "POST", base_url + api_paths["payment"],
                                 pay._body(), timeout)
            if status == 201 and isinstance(body, dict):
                payment_id = body.get("id")
        elif step == "verify":
            route = transitions.get("verify")
            if route is None or payment_id is None:
                report.add(WorkflowCheck(
                    check_id, "happy_path", f"{label} -> {target}", False, target,
                    "no verify route published" if route is None else "no payment created"))
                continue
            _fire_transition(report, base_url, route, payment_id, timeout)
        else:
            route = transitions.get(step)
            if route is None:
                report.add(WorkflowCheck(check_id, "happy_path", f"{label} -> {target}",
                                         False, target, f"no {step} route published"))
                continue
            _fire_transition(report, base_url, route, order_id, timeout)

        observed = _order_status(report, base_url, api_paths, order_id, timeout)
        report.add(WorkflowCheck(check_id, "happy_path", f"{label} -> {target}",
                                 observed == target, target, observed))

    # ---- B. precondition enforcement -----------------------------------
    # Each case gets its own order, so a rejected call cannot disturb another.
    for check_id, from_state, description, action in NEGATIVE_CASES:
        oid = _make_order(report, base_url, api_paths, customer_id, product_id, timeout)
        if oid is None or not _advance_to(report, base_url, api_paths, transitions,
                                          oid, from_state, timeout):
            report.add(WorkflowCheck(check_id, "precondition", description, False,
                                     409, f"could not stage an order in {from_state}"))
            continue

        if action == "invoice":
            inv = InvoiceTestGroup(api=base_url + api_paths["invoice"],
                                   seed_order_accepted_id=oid)
            status, body = _call(report, "POST", base_url + api_paths["invoice"],
                                 inv._body(), timeout)
        elif action == "pay":
            pay = PaymentTestGroup(api=base_url + api_paths["payment"],
                                   seed_order_invoiced_id=oid)
            status, body = _call(report, "POST", base_url + api_paths["payment"],
                                 pay._body(), timeout)
        else:
            route = transitions.get(action)
            if route is None:
                report.add(WorkflowCheck(check_id, "precondition", description, False,
                                         409, f"no {action} route published"))
                continue
            status, body, _m, _u = _fire_transition(report, base_url, route, oid, timeout)

        report.add(WorkflowCheck(check_id, "precondition", description,
                                 status == 409, 409, status, detail=body))

    return report
