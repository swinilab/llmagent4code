"""Cases for entities whose validity depends on other entities' state.

Order, Invoice and Payment cannot be probed from a static table: an Invoice is
only creatable against an ACCEPTED order, a Payment only against an INVOICED
one, and each probe consumes the order it acts on. These cases therefore build
their own preconditions and are generated at run time.

The distinction being tested throughout is the specification's three-layer rule
for references:

    malformed identifier      -> 400
    well-formed, nonexistent  -> 404
    exists, wrong state       -> 409

Collapsing any two of those is a common and easy mistake, and it is exactly what
these cases are shaped to catch.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from ...harness.context import Context, SeedError
from .cases import BAD_REQUEST, CONFLICT, NOT_FOUND, OK_CREATE, OK_READ

UNKNOWN_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
MALFORMED_UUID = "not-a-uuid-123"


@dataclass
class RelationalCase:
    """A case that must construct its own preconditions before probing.

    `execute` performs whatever setup it needs and returns the observed status,
    so the surrounding runner stays uniform across static and relational cases.
    """

    id: str
    entity: str
    partition: str
    expected_status: int
    execute: Callable[[Context], int]
    description: str = ""


# ── Order ─────────────────────────────────────────────────────────────────


def _order_body(customer_id: str, product_id: str, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "customerRef": customer_id,
        "lineItems": [{"productRef": product_id, "quantity": 2}],
    }
    body.update(over)
    return body


def order_cases() -> list[RelationalCase]:
    e = "order"

    def valid(ctx: Context) -> int:
        c, p = ctx.seed_customer(), ctx.seed_product()
        return ctx.http.post(ctx.create_path(e), json_body=_order_body(c, p)).status

    def malformed_customer(ctx: Context) -> int:
        p = ctx.seed_product()
        return ctx.http.post(ctx.create_path(e), json_body=_order_body(MALFORMED_UUID, p)).status

    def unknown_customer(ctx: Context) -> int:
        p = ctx.seed_product()
        return ctx.http.post(ctx.create_path(e), json_body=_order_body(UNKNOWN_UUID, p)).status

    def unknown_product(ctx: Context) -> int:
        c = ctx.seed_customer()
        return ctx.http.post(ctx.create_path(e), json_body=_order_body(c, UNKNOWN_UUID)).status

    def duplicate_product(ctx: Context) -> int:
        c, p = ctx.seed_customer(), ctx.seed_product()
        body = _order_body(c, p)
        body["lineItems"] = [
            {"productRef": p, "quantity": 1},
            {"productRef": p, "quantity": 3},
        ]
        return ctx.http.post(ctx.create_path(e), json_body=body).status

    def _quantity(q: Any) -> Callable[[Context], int]:
        def run(ctx: Context) -> int:
            c, p = ctx.seed_customer(), ctx.seed_product()
            body = _order_body(c, p)
            body["lineItems"][0]["quantity"] = q
            return ctx.http.post(ctx.create_path(e), json_body=body).status

        return run

    def empty_items(ctx: Context) -> int:
        c = ctx.seed_customer()
        body = _order_body(c, ctx.seed_product())
        body["lineItems"] = []
        return ctx.http.post(ctx.create_path(e), json_body=body).status

    def too_many_items(ctx: Context) -> int:
        c = ctx.seed_customer()
        products = [ctx.seed_product(description=f"Bulk item {i}") for i in range(101)]
        body = _order_body(c, products[0])
        body["lineItems"] = [{"productRef": pid, "quantity": 1} for pid in products]
        return ctx.http.post(ctx.create_path(e), json_body=body).status

    def client_total(ctx: Context) -> int:
        c, p = ctx.seed_customer(), ctx.seed_product()
        body = _order_body(c, p)
        body["totalAmount"] = "1.00"
        return ctx.http.post(ctx.create_path(e), json_body=body).status

    def client_snapshot(ctx: Context) -> int:
        c, p = ctx.seed_customer(), ctx.seed_product()
        body = _order_body(c, p)
        body["lineItems"][0]["unitPriceSnapshot"] = "0.01"
        return ctx.http.post(ctx.create_path(e), json_body=body).status

    def client_status(ctx: Context) -> int:
        c, p = ctx.seed_customer(), ctx.seed_product()
        body = _order_body(c, p)
        body["status"] = "SHIPPED"
        return ctx.http.post(ctx.create_path(e), json_body=body).status

    def total_is_computed(ctx: Context) -> int:
        """The server's total must equal quantity x price, not the client's word.

        Returns 200 when the arithmetic is right so this can be asserted like
        any other status; a mismatch reports 0 to fail loudly. Comparison is in
        Decimal because a system storing money in binary floating point would
        otherwise pass here and drift elsewhere.
        """
        quantity = 2
        unit_price = Decimal("12.34")
        c = ctx.seed_customer()
        p = ctx.seed_product(amount=str(unit_price))
        resp = ctx.http.post(
            ctx.create_path(e), json_body=_order_body(c, p, )
        )
        if resp.status != 201 or not isinstance(resp.body, dict):
            return resp.status or 0
        try:
            return 200 if Decimal(str(resp.body["totalAmount"])) == unit_price * quantity else 0
        except (KeyError, ValueError, TypeError):
            return 0

    return [
        RelationalCase("TC_ORD_VALID", e, "valid creation", OK_CREATE, valid),
        RelationalCase("TC_ORD_CUST_MALFORMED", e, "malformed customerRef", BAD_REQUEST,
                       malformed_customer),
        RelationalCase("TC_ORD_CUST_UNKNOWN", e, "nonexistent customerRef", NOT_FOUND,
                       unknown_customer),
        RelationalCase("TC_ORD_PROD_UNKNOWN", e, "nonexistent productRef", NOT_FOUND,
                       unknown_product),
        RelationalCase("TC_ORD_DUPLICATE_PRODUCT", e, "duplicate productRef", BAD_REQUEST,
                       duplicate_product,
                       "duplicates are rejected, never merged"),
        RelationalCase("TC_ORD_QTY_MIN", e, "quantity 1 (at min)", OK_CREATE, _quantity(1)),
        RelationalCase("TC_ORD_QTY_ZERO", e, "quantity 0 (below min)", BAD_REQUEST, _quantity(0)),
        RelationalCase("TC_ORD_QTY_MAX", e, "quantity 1000 (at max)", OK_CREATE, _quantity(1000)),
        RelationalCase("TC_ORD_QTY_ABOVE", e, "quantity 1001 (above max)", BAD_REQUEST,
                       _quantity(1001)),
        RelationalCase("TC_ORD_QTY_FRACTIONAL", e, "fractional quantity", BAD_REQUEST,
                       _quantity(1.5)),
        RelationalCase("TC_ORD_ITEMS_EMPTY", e, "no line items (below min)", BAD_REQUEST,
                       empty_items),
        RelationalCase("TC_ORD_ITEMS_ABOVE", e, "101 line items (above max)", BAD_REQUEST,
                       too_many_items),
        RelationalCase("TC_ORD_CLIENT_TOTAL", e, "client supplies computed totalAmount",
                       BAD_REQUEST, client_total),
        RelationalCase("TC_ORD_CLIENT_SNAPSHOT", e, "client supplies unitPriceSnapshot",
                       BAD_REQUEST, client_snapshot),
        RelationalCase("TC_ORD_CLIENT_STATUS", e, "client supplies initial status",
                       BAD_REQUEST, client_status),
        RelationalCase("TC_ORD_TOTAL_COMPUTED", e, "server computes totalAmount correctly",
                       OK_READ, total_is_computed,
                       "quantity x unit price, in exact decimal arithmetic"),
    ]


# ── Invoice ───────────────────────────────────────────────────────────────


def invoice_cases() -> list[RelationalCase]:
    e = "invoice"

    def _accepted_order(ctx: Context) -> str:
        c, p = ctx.seed_customer(), ctx.seed_product()
        order_id = ctx.seed_order(c, p)
        ctx.http.post(f"/api/v1/orders/{order_id}/accept")
        return order_id

    def valid(ctx: Context) -> int:
        return ctx.http.post(ctx.create_path(e),
                             json_body={"orderRef": _accepted_order(ctx)}).status

    def wrong_state(ctx: Context) -> int:
        """An order still PLACED has not reached the invoiceable state."""
        c, p = ctx.seed_customer(), ctx.seed_product()
        order_id = ctx.seed_order(c, p)  # left at PLACED
        return ctx.http.post(ctx.create_path(e), json_body={"orderRef": order_id}).status

    def unknown_order(ctx: Context) -> int:
        return ctx.http.post(ctx.create_path(e), json_body={"orderRef": UNKNOWN_UUID}).status

    def malformed_order(ctx: Context) -> int:
        return ctx.http.post(ctx.create_path(e), json_body={"orderRef": MALFORMED_UUID}).status

    def _date(field: str, value: str) -> Callable[[Context], int]:
        def run(ctx: Context) -> int:
            body = {"orderRef": _accepted_order(ctx), field: value}
            return ctx.http.post(ctx.create_path(e), json_body=body).status

        return run

    def due_before_issue(ctx: Context) -> int:
        body = {
            "orderRef": _accepted_order(ctx),
            "issueDate": "10/06/2026",
            "dueDate": "01/06/2026",
        }
        return ctx.http.post(ctx.create_path(e), json_body=body).status

    def client_total(ctx: Context) -> int:
        body = {"orderRef": _accepted_order(ctx), "totalAmount": "1.00"}
        return ctx.http.post(ctx.create_path(e), json_body=body).status

    return [
        RelationalCase("TC_INV_VALID", e, "valid creation against ACCEPTED order",
                       OK_CREATE, valid),
        RelationalCase("TC_INV_WRONG_STATE", e, "order not yet ACCEPTED", CONFLICT, wrong_state,
                       "referential state violation, distinct from 400 and 404"),
        RelationalCase("TC_INV_ORDER_UNKNOWN", e, "nonexistent orderRef", NOT_FOUND, unknown_order),
        RelationalCase("TC_INV_ORDER_MALFORMED", e, "malformed orderRef", BAD_REQUEST,
                       malformed_order),
        RelationalCase("TC_INV_DATE_IMPOSSIBLE", e, "31/02 is not a calendar date", BAD_REQUEST,
                       _date("issueDate", "31/02/2026"),
                       "matches the regex but is not a real date"),
        RelationalCase("TC_INV_DATE_MONTH_13", e, "month 13", BAD_REQUEST,
                       _date("issueDate", "01/13/2026")),
        RelationalCase("TC_INV_DATE_WRONG_FORMAT", e, "ISO format instead of dd/MM/yyyy",
                       BAD_REQUEST, _date("issueDate", "2026-06-01")),
        RelationalCase("TC_INV_DUE_BEFORE_ISSUE", e, "dueDate precedes issueDate", BAD_REQUEST,
                       due_before_issue),
        RelationalCase("TC_INV_CLIENT_TOTAL", e, "client supplies computed totalAmount",
                       BAD_REQUEST, client_total),
    ]


# ── Payment ───────────────────────────────────────────────────────────────


def payment_cases() -> list[RelationalCase]:
    e = "payment"

    def _invoiced_order(ctx: Context) -> tuple[str, str]:
        """Drive an order to INVOICED and report its exact total."""
        c = ctx.seed_customer()
        p = ctx.seed_product(amount="25.00")
        order_id = ctx.seed_order(c, p, quantity=2)
        ctx.http.post(f"/api/v1/orders/{order_id}/accept")
        inv = ctx.http.post(ctx.create_path("invoice"), json_body={"orderRef": order_id})
        if inv.status != 201:
            raise SeedError(f"invoice creation returned HTTP {inv.status}")
        total = ctx.http.get(f"/api/v1/orders/{order_id}").body["totalAmount"]
        return order_id, f"{Decimal(str(total)):.2f}"

    def valid(ctx: Context) -> int:
        order_id, total = _invoiced_order(ctx)
        return ctx.http.post(
            ctx.create_path(e),
            json_body={"orderRef": order_id, "amount": total, "method": "BANK_TRANSFER"},
        ).status

    def _amount(delta: str) -> Callable[[Context], int]:
        """Pay a different amount than the invoice total; exact match is required."""

        def run(ctx: Context) -> int:
            order_id, total = _invoiced_order(ctx)
            wrong = f"{Decimal(total) + Decimal(delta):.2f}"
            return ctx.http.post(
                ctx.create_path(e),
                json_body={"orderRef": order_id, "amount": wrong, "method": "BANK_TRANSFER"},
            ).status

        return run

    def wrong_state(ctx: Context) -> int:
        """A PLACED order has no invoice to pay against."""
        c, p = ctx.seed_customer(), ctx.seed_product()
        order_id = ctx.seed_order(c, p)
        return ctx.http.post(
            ctx.create_path(e),
            json_body={"orderRef": order_id, "amount": "50.00", "method": "BANK_TRANSFER"},
        ).status

    def _method(value: Any) -> Callable[[Context], int]:
        def run(ctx: Context) -> int:
            order_id, total = _invoiced_order(ctx)
            return ctx.http.post(
                ctx.create_path(e),
                json_body={"orderRef": order_id, "amount": total, "method": value},
            ).status

        return run

    def client_status(ctx: Context) -> int:
        order_id, total = _invoiced_order(ctx)
        return ctx.http.post(
            ctx.create_path(e),
            json_body={
                "orderRef": order_id,
                "amount": total,
                "method": "BANK_TRANSFER",
                "status": "VERIFIED",
            },
        ).status

    return [
        RelationalCase("TC_PAY_VALID", e, "valid payment matching invoice total",
                       OK_CREATE, valid),
        RelationalCase("TC_PAY_UNDERPAY", e, "amount below invoice total", BAD_REQUEST,
                       _amount("-0.01"),
                       "partial payment is out of scope; exact match required"),
        RelationalCase("TC_PAY_OVERPAY", e, "amount above invoice total", BAD_REQUEST,
                       _amount("0.01")),
        RelationalCase("TC_PAY_WRONG_STATE", e, "order not INVOICED", CONFLICT, wrong_state),
        RelationalCase("TC_PAY_METHOD_CARD", e, "method CREDIT_CARD", OK_CREATE,
                       _method("CREDIT_CARD")),
        RelationalCase("TC_PAY_METHOD_WALLET", e, "method E_WALLET", OK_CREATE,
                       _method("E_WALLET")),
        RelationalCase("TC_PAY_METHOD_UNKNOWN", e, "method not in allow-list", BAD_REQUEST,
                       _method("CASH")),
        RelationalCase("TC_PAY_METHOD_LOWERCASE", e, "method wrong case", BAD_REQUEST,
                       _method("bank_transfer")),
        RelationalCase("TC_PAY_CLIENT_STATUS", e, "client attempts to self-verify",
                       BAD_REQUEST, client_status,
                       "status is server-controlled; a client cannot verify its own payment"),
    ]


def all_relational_cases() -> list[RelationalCase]:
    return order_cases() + invoice_cases() + payment_cases()