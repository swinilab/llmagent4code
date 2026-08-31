"""
PaymentTestGroup - implements ITestGroup for the Payment entity.

Source: OMS_TestCases_BVA_EP_EN.xlsx, sheet "Payment" (TC_PAY_*).

Notes:
- All test cases exercise POST /payments.
- `amount` test cases reference `invoice.totalAmount` for the seeded, already
  -invoiced order; `seed_invoice_total_amount` must be set to the exact
  totalAmount of the invoice tied to `seed_order_invoiced_id` for the
  exact-match tests (TC_PAY_AMOUNT_01..03) to be meaningful.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from interfaces.base import ITestGroup, TestResult

NEEDS_SEED_ORDER_INVOICED = "<seed: order status=INVOICED>"
NEEDS_SEED_ORDER_PLACED = "<seed: order status=PLACED>"
NOT_FOUND_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
DEFAULT_INVOICE_TOTAL = Decimal("100.00")


class PaymentTestGroup(ITestGroup):
    """Functional BVA/EP tests for the Payment entity."""

    def __init__(
        self,
        api: str,
        seed_order_invoiced_id: str | None = None,
        seed_order_placed_id: str | None = None,
        seed_invoice_total_amount: Decimal | None = None,
        seed_bulk_invoiced_orders: list[dict[str, Any]] | None = None,
    ):
        self.api = api
        self.seed_order_invoiced_id = seed_order_invoiced_id or NEEDS_SEED_ORDER_INVOICED
        self.seed_order_placed_id = seed_order_placed_id or NEEDS_SEED_ORDER_PLACED
        self.seed_invoice_total_amount = seed_invoice_total_amount or DEFAULT_INVOICE_TOTAL
        # Queue of fresh, not-yet-paid INVOICED orders - one per happy-path
        # payment test. Paying an order is a one-time INVOICED -> PAID
        # transition, so happy-path tests can't share a single order (the
        # first successful payment would leave the rest seeing a false 409).
        self._invoiced_order_queue: list[dict[str, Any]] = list(seed_bulk_invoiced_orders or [])

        self.standard_request_body: dict[str, Any] = {
            "orderRef": self.seed_order_invoiced_id,
            "amount": str(self.seed_invoice_total_amount),
            "method": "CREDIT_CARD",
        }

        self.testcases: list[str] = [
            "TC_PAY_ORDERREF_01", "TC_PAY_ORDERREF_02", "TC_PAY_ORDERREF_03",
            "TC_PAY_ORDERREF_04",
            "TC_PAY_AMOUNT_01", "TC_PAY_AMOUNT_02", "TC_PAY_AMOUNT_03",
            "TC_PAY_AMOUNT_04", "TC_PAY_AMOUNT_05", "TC_PAY_AMOUNT_06",
            "TC_PAY_STATUS_01", "TC_PAY_STATUS_02", "TC_PAY_STATUS_03",
            "TC_PAY_METHOD_01", "TC_PAY_METHOD_02", "TC_PAY_METHOD_03",
            "TC_PAY_METHOD_04", "TC_PAY_METHOD_05",
        ]

    def _body(self) -> dict[str, Any]:
        """Standard body, but pointed at a *fresh* untouched INVOICED order.

        Paying is a one-time INVOICED -> PAID transition, so every case here
        needs its own order - negative cases included. Sharing one order is
        only safe while the app rejects every negative case correctly: the
        moment an app wrongly *accepts* one, the shared order becomes PAID and
        every later case sees a 409 that has nothing to do with the field it
        was testing. That failure mode fires only on buggy apps, so it would
        bias exactly the measurements that matter most.

        `_last_order_id` / `_last_total` expose what was popped, so the cases
        that compute an amount relative to the invoice total use *this*
        order's total rather than a shared one.
        """
        order = self._next_invoiced_order()
        if order is None:
            self._last_order_id = None
            self._last_total = self.seed_invoice_total_amount
            return super()._body()
        order_id, total = order
        self._last_order_id = order_id
        self._last_total = total
        body = super()._body()
        body["orderRef"] = order_id
        body["amount"] = str(total)
        return body

    def _next_invoiced_order(self) -> tuple[str, Decimal] | None:
        """Pop the next dedicated, untouched INVOICED order for a happy-path
        payment test, or None if the bulk queue is exhausted/unavailable.

        Deliberately does NOT fall back to seed_order_invoiced_id: that
        order is also relied on by the negative-path tests (AMOUNT_02..06,
        STATUS_02/03, METHOD_04/05, ORDERREF_02) to stay untouched/INVOICED.
        A happy-path test consuming it via a real payment would corrupt
        those other tests' results too - a caller seeing None should report
        "seed data unavailable" rather than silently reusing that order.
        """
        if self._invoiced_order_queue:
            entry = self._invoiced_order_queue.pop(0)
            return entry["order_id"], entry["invoice_total_amount"]
        return None

    def _seed_unavailable(self, testcase_id: str, expected_status: int) -> TestResult:
        """Result for a happy-path test that couldn't get its own dedicated
        order because bulk seeding fell short - reported distinctly from a
        real HTTP failure so it isn't mistaken for an app defect."""
        return TestResult(
            result=False,
            testcase_id=testcase_id,
            method="",
            url="",
            expected_status=expected_status,
            actual_status=0,
            request_body=None,
            response_body=(
                "seed data unavailable: no dedicated INVOICED order left in "
                "the bulk queue (see seed_context.py warnings)"
            ),
        )

    # ------------------------------------------------------------------ #
    # Dispatcher
    # ------------------------------------------------------------------ #
    def run_testcase(self, testcase_id: str) -> TestResult:
        match testcase_id:
            case "TC_PAY_ORDERREF_01": return self.tc_pay_orderref_01()
            case "TC_PAY_ORDERREF_02": return self.tc_pay_orderref_02()
            case "TC_PAY_ORDERREF_03": return self.tc_pay_orderref_03()
            case "TC_PAY_ORDERREF_04": return self.tc_pay_orderref_04()

            case "TC_PAY_AMOUNT_01": return self.tc_pay_amount_01()
            case "TC_PAY_AMOUNT_02": return self.tc_pay_amount_02()
            case "TC_PAY_AMOUNT_03": return self.tc_pay_amount_03()
            case "TC_PAY_AMOUNT_04": return self.tc_pay_amount_04()
            case "TC_PAY_AMOUNT_05": return self.tc_pay_amount_05()
            case "TC_PAY_AMOUNT_06": return self.tc_pay_amount_06()

            case "TC_PAY_STATUS_01": return self.tc_pay_status_01()
            case "TC_PAY_STATUS_02": return self.tc_pay_status_02()
            case "TC_PAY_STATUS_03": return self.tc_pay_status_03()

            case "TC_PAY_METHOD_01": return self.tc_pay_method_01()
            case "TC_PAY_METHOD_02": return self.tc_pay_method_02()
            case "TC_PAY_METHOD_03": return self.tc_pay_method_03()
            case "TC_PAY_METHOD_04": return self.tc_pay_method_04()
            case "TC_PAY_METHOD_05": return self.tc_pay_method_05()

            case _:
                return TestResult(
                    result=False,
                    testcase_id=testcase_id,
                    method="",
                    url="",
                    expected_status=0,
                    actual_status=0,
                    request_body=None,
                    response_body=f"Unknown testcase id: {testcase_id}",
                )

    # ------------------------------------------------------------------ #
    # orderRef
    # ------------------------------------------------------------------ #
    def tc_pay_orderref_01(self) -> TestResult:
        """EC-Valid-1: orderRef exists and order status is INVOICED -> 201."""
        body = self._body()
        if self._last_order_id is None:
            return self._seed_unavailable("TC_PAY_ORDERREF_01", 201)
        order_id, total = self._last_order_id, self._last_total
        status, resp = self._post(body)
        return self._check("TC_PAY_ORDERREF_01", 201, body, status, resp)

    def tc_pay_orderref_02(self) -> TestResult:
        """EC-Invalid-1 (Wrong State): orderRef exists but order status is
        not payable (e.g. PLACED) -> 409."""
        body = self._body()
        body["orderRef"] = self.seed_order_placed_id
        status, resp = self._post(body)
        return self._check("TC_PAY_ORDERREF_02", 409, body, status, resp)

    def tc_pay_orderref_03(self) -> TestResult:
        """EC-Invalid-2 (Not Found): orderRef does not exist -> 404."""
        body = self._body()
        body["orderRef"] = NOT_FOUND_UUID
        status, resp = self._post(body)
        return self._check("TC_PAY_ORDERREF_03", 404, body, status, resp)

    def tc_pay_orderref_04(self) -> TestResult:
        """EC-Invalid-3 (Wrong Format): malformed UUID string -> 400."""
        body = self._body()
        body["orderRef"] = "order-1"
        status, resp = self._post(body)
        return self._check("TC_PAY_ORDERREF_04", 400, body, status, resp, acceptable=(400, 422))

    # ------------------------------------------------------------------ #
    # amount
    # ------------------------------------------------------------------ #
    def tc_pay_amount_01(self) -> TestResult:
        """EC-Valid-1: amount exactly equals invoice.totalAmount -> 201."""
        body = self._body()
        if self._last_order_id is None:
            return self._seed_unavailable("TC_PAY_AMOUNT_01", 201)
        order_id, total = self._last_order_id, self._last_total
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_01", 201, body, status, resp)

    def tc_pay_amount_02(self) -> TestResult:
        """EC-Invalid-1 (Underpayment): amount less than invoice.totalAmount -> 409."""
        body = self._body()
        body["amount"] = str(self._last_total - Decimal("0.01"))
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_02", 409, body, status, resp)

    def tc_pay_amount_03(self) -> TestResult:
        """EC-Invalid-2 (Overpayment): amount greater than invoice.totalAmount -> 409."""
        body = self._body()
        body["amount"] = str(self._last_total + Decimal("0.01"))
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_03", 409, body, status, resp)

    def tc_pay_amount_04(self) -> TestResult:
        """EC-Invalid-3 (Zero): amount equal to zero -> 400."""
        body = self._body()
        body["amount"] = "0.00"
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_04", 400, body, status, resp, acceptable=(400, 422))

    def tc_pay_amount_05(self) -> TestResult:
        """EC-Invalid-4 (Negative): negative value -> 400."""
        body = self._body()
        body["amount"] = "-50.00"
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_05", 400, body, status, resp, acceptable=(400, 422))

    def tc_pay_amount_06(self) -> TestResult:
        """EC-Invalid-5 (Empty): empty/null -> 400."""
        body = self._body()
        body["amount"] = None
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_06", 400, body, status, resp, acceptable=(400, 422))

    # ------------------------------------------------------------------ #
    # status
    # ------------------------------------------------------------------ #
    def tc_pay_status_01(self) -> TestResult:
        """EC-Valid-1: default status on creation is PENDING -> 201."""
        body = self._body()
        if self._last_order_id is None:
            return self._seed_unavailable("TC_PAY_STATUS_01", 201)
        order_id, total = self._last_order_id, self._last_total
        status, resp = self._post(body)
        result = self._check("TC_PAY_STATUS_01", 201, body, status, resp)
        if result.result and isinstance(resp, dict) and resp.get("status") != "PENDING":
            result.result = False
        return result

    def tc_pay_status_02(self) -> TestResult:
        """EC-Invalid-1 (Bypasses Workflow): client sets status to VERIFIED
        on creation (bypassing accountant verification) -> 400."""
        body = self._body()
        body["status"] = "VERIFIED"
        status, resp = self._post(body)
        return self._check("TC_PAY_STATUS_02", 400, body, status, resp, acceptable=(400, 422))

    def tc_pay_status_03(self) -> TestResult:
        """EC-Invalid-2 (Unknown Value): value not part of enum -> 400."""
        body = self._body()
        body["status"] = "DONE"
        status, resp = self._post(body)
        return self._check("TC_PAY_STATUS_03", 400, body, status, resp, acceptable=(400, 422))

    # ------------------------------------------------------------------ #
    # method
    # ------------------------------------------------------------------ #
    def tc_pay_method_01(self) -> TestResult:
        """EC-Valid-1: valid method - CREDIT_CARD -> 201."""
        body = self._body()
        if self._last_order_id is None:
            return self._seed_unavailable("TC_PAY_METHOD_01", 201)
        order_id, total = self._last_order_id, self._last_total
        body["method"] = "CREDIT_CARD"
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_01", 201, body, status, resp)

    def tc_pay_method_02(self) -> TestResult:
        """EC-Valid-2: valid method - BANK_TRANSFER -> 201."""
        body = self._body()
        if self._last_order_id is None:
            return self._seed_unavailable("TC_PAY_METHOD_02", 201)
        order_id, total = self._last_order_id, self._last_total
        body["method"] = "BANK_TRANSFER"
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_02", 201, body, status, resp)

    def tc_pay_method_03(self) -> TestResult:
        """EC-Valid-3: valid method - E_WALLET -> 201."""
        body = self._body()
        if self._last_order_id is None:
            return self._seed_unavailable("TC_PAY_METHOD_03", 201)
        order_id, total = self._last_order_id, self._last_total
        body["method"] = "E_WALLET"
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_03", 201, body, status, resp)

    def tc_pay_method_04(self) -> TestResult:
        """EC-Invalid-1 (Unknown Value): value not part of enum -> 400."""
        body = self._body()
        body["method"] = "CASH"
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_04", 400, body, status, resp, acceptable=(400, 422))

    def tc_pay_method_05(self) -> TestResult:
        """EC-Invalid-2 (Empty): empty/null -> 400."""
        body = self._body()
        body["method"] = None
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_05", 400, body, status, resp, acceptable=(400, 422))
