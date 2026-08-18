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
    ):
        self.api = api
        self.seed_order_invoiced_id = seed_order_invoiced_id or NEEDS_SEED_ORDER_INVOICED
        self.seed_order_placed_id = seed_order_placed_id or NEEDS_SEED_ORDER_PLACED
        self.seed_invoice_total_amount = seed_invoice_total_amount or DEFAULT_INVOICE_TOTAL

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
                    message=f"Unknown testcase id: {testcase_id}",
                )

    # ------------------------------------------------------------------ #
    # orderRef
    # ------------------------------------------------------------------ #
    def tc_pay_orderref_01(self) -> TestResult:
        """EC-Valid-1: orderRef exists and order status is INVOICED -> 201."""
        body = self._body()
        body["orderRef"] = self.seed_order_invoiced_id
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
        return self._check("TC_PAY_ORDERREF_04", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # amount
    # ------------------------------------------------------------------ #
    def tc_pay_amount_01(self) -> TestResult:
        """EC-Valid-1: amount exactly equals invoice.totalAmount -> 201."""
        body = self._body()
        body["amount"] = str(self.seed_invoice_total_amount)
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_01", 201, body, status, resp)

    def tc_pay_amount_02(self) -> TestResult:
        """EC-Invalid-1 (Underpayment): amount less than invoice.totalAmount -> 400."""
        body = self._body()
        body["amount"] = str(self.seed_invoice_total_amount - Decimal("0.01"))
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_02", 400, body, status, resp)

    def tc_pay_amount_03(self) -> TestResult:
        """EC-Invalid-2 (Overpayment): amount greater than invoice.totalAmount -> 400."""
        body = self._body()
        body["amount"] = str(self.seed_invoice_total_amount + Decimal("0.01"))
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_03", 400, body, status, resp)

    def tc_pay_amount_04(self) -> TestResult:
        """EC-Invalid-3 (Zero): amount equal to zero -> 400."""
        body = self._body()
        body["amount"] = "0.00"
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_04", 400, body, status, resp)

    def tc_pay_amount_05(self) -> TestResult:
        """EC-Invalid-4 (Negative): negative value -> 400."""
        body = self._body()
        body["amount"] = "-50.00"
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_05", 400, body, status, resp)

    def tc_pay_amount_06(self) -> TestResult:
        """EC-Invalid-5 (Empty): empty/null -> 400."""
        body = self._body()
        body["amount"] = None
        status, resp = self._post(body)
        return self._check("TC_PAY_AMOUNT_06", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # status
    # ------------------------------------------------------------------ #
    def tc_pay_status_01(self) -> TestResult:
        """EC-Valid-1: default status on creation is PENDING -> 201."""
        body = self._body()
        status, resp = self._post(body)
        result = self._check("TC_PAY_STATUS_01", 201, body, status, resp)
        if result.result and isinstance(resp, dict) and resp.get("status") != "PENDING":
            return TestResult(
                result=False,
                testcase_id="TC_PAY_STATUS_01",
                message=f"Expected default status PENDING, got {resp.get('status')!r}",
            )
        return result

    def tc_pay_status_02(self) -> TestResult:
        """EC-Invalid-1 (Bypasses Workflow): client sets status to VERIFIED
        on creation (bypassing accountant verification) -> 400."""
        body = self._body()
        body["status"] = "VERIFIED"
        status, resp = self._post(body)
        return self._check("TC_PAY_STATUS_02", 400, body, status, resp)

    def tc_pay_status_03(self) -> TestResult:
        """EC-Invalid-2 (Unknown Value): value not part of enum -> 400."""
        body = self._body()
        body["status"] = "DONE"
        status, resp = self._post(body)
        return self._check("TC_PAY_STATUS_03", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # method
    # ------------------------------------------------------------------ #
    def tc_pay_method_01(self) -> TestResult:
        """EC-Valid-1: valid method - CREDIT_CARD -> 201."""
        body = self._body()
        body["method"] = "CREDIT_CARD"
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_01", 201, body, status, resp)

    def tc_pay_method_02(self) -> TestResult:
        """EC-Valid-2: valid method - BANK_TRANSFER -> 201."""
        body = self._body()
        body["method"] = "BANK_TRANSFER"
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_02", 201, body, status, resp)

    def tc_pay_method_03(self) -> TestResult:
        """EC-Valid-3: valid method - E_WALLET -> 201."""
        body = self._body()
        body["method"] = "E_WALLET"
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_03", 201, body, status, resp)

    def tc_pay_method_04(self) -> TestResult:
        """EC-Invalid-1 (Unknown Value): value not part of enum -> 400."""
        body = self._body()
        body["method"] = "CASH"
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_04", 400, body, status, resp)

    def tc_pay_method_05(self) -> TestResult:
        """EC-Invalid-2 (Empty): empty/null -> 400."""
        body = self._body()
        body["method"] = None
        status, resp = self._post(body)
        return self._check("TC_PAY_METHOD_05", 400, body, status, resp)
