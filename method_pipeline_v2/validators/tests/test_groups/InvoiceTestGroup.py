"""
InvoiceTestGroup - implements ITestGroup for the Invoice entity.

Source: OMS_TestCases_BVA_EP_EN.xlsx, sheet "Invoice" (TC_INV_*).

Notes:
- All test cases exercise POST /invoices.
- Dates use the dd/MM/yyyy format specified in the sheet.
- billingInfo.name is a snapshot of Customer.name (see Remarks column);
  it is still submitted directly in the request body per the sheet's
  Input Value column.
- totalAmount is server-computed; TC_INV_TOTALAMT_01 verifies it via a
  seeded order's totalAmount rather than asserting a literal value.
"""

from __future__ import annotations

from typing import Any

from interfaces.base import ITestGroup, TestResult

NEEDS_SEED_ORDER_ACCEPTED = "<seed: order status=ACCEPTED>"
NEEDS_SEED_ORDER_PLACED = "<seed: order status=PLACED>"
NOT_FOUND_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


class InvoiceTestGroup(ITestGroup):
    """Functional BVA/EP tests for the Invoice entity."""

    def __init__(
        self,
        api: str,
        seed_order_accepted_id: str | None = None,
        seed_order_placed_id: str | None = None,
        seed_order_accepted_total_amount: str | None = None,
    ):
        self.api = api
        self.seed_order_accepted_id = seed_order_accepted_id or NEEDS_SEED_ORDER_ACCEPTED
        self.seed_order_placed_id = seed_order_placed_id or NEEDS_SEED_ORDER_PLACED
        self.seed_order_accepted_total_amount = seed_order_accepted_total_amount or "100.00"

        self.standard_request_body: dict[str, Any] = {
            "orderRef": self.seed_order_accepted_id,
            "billingInfo": {
                "name": "Nguyen Van A",
            },
            "issueDate": "23/07/2026",
            "dueDate": "30/07/2026",
        }

        self.testcases: list[str] = [
            "TC_INV_ORDERREF_01", "TC_INV_ORDERREF_02", "TC_INV_ORDERREF_03",
            "TC_INV_BILLNAME_01", "TC_INV_BILLNAME_02", "TC_INV_BILLNAME_03",
            "TC_INV_BILLNAME_04",
            "TC_INV_TOTALAMT_01", "TC_INV_TOTALAMT_02", "TC_INV_TOTALAMT_03",
            "TC_INV_ISSUEDATE_01", "TC_INV_ISSUEDATE_02", "TC_INV_ISSUEDATE_03",
            "TC_INV_ISSUEDATE_04", "TC_INV_ISSUEDATE_05", "TC_INV_ISSUEDATE_06",
            "TC_INV_ISSUEDATE_07",
            "TC_INV_DUEDATE_01", "TC_INV_DUEDATE_02", "TC_INV_DUEDATE_03",
            "TC_INV_DUEDATE_04", "TC_INV_DUEDATE_05",
            "TC_INV_STATUS_01", "TC_INV_STATUS_02", "TC_INV_STATUS_03",
        ]

    # ------------------------------------------------------------------ #
    # Dispatcher
    # ------------------------------------------------------------------ #
    def run_testcase(self, testcase_id: str) -> TestResult:
        match testcase_id:
            case "TC_INV_ORDERREF_01": return self.tc_inv_orderref_01()
            case "TC_INV_ORDERREF_02": return self.tc_inv_orderref_02()
            case "TC_INV_ORDERREF_03": return self.tc_inv_orderref_03()

            case "TC_INV_BILLNAME_01": return self.tc_inv_billname_01()
            case "TC_INV_BILLNAME_02": return self.tc_inv_billname_02()
            case "TC_INV_BILLNAME_03": return self.tc_inv_billname_03()
            case "TC_INV_BILLNAME_04": return self.tc_inv_billname_04()

            case "TC_INV_TOTALAMT_01": return self.tc_inv_totalamt_01()
            case "TC_INV_TOTALAMT_02": return self.tc_inv_totalamt_02()
            case "TC_INV_TOTALAMT_03": return self.tc_inv_totalamt_03()

            case "TC_INV_ISSUEDATE_01": return self.tc_inv_issuedate_01()
            case "TC_INV_ISSUEDATE_02": return self.tc_inv_issuedate_02()
            case "TC_INV_ISSUEDATE_03": return self.tc_inv_issuedate_03()
            case "TC_INV_ISSUEDATE_04": return self.tc_inv_issuedate_04()
            case "TC_INV_ISSUEDATE_05": return self.tc_inv_issuedate_05()
            case "TC_INV_ISSUEDATE_06": return self.tc_inv_issuedate_06()
            case "TC_INV_ISSUEDATE_07": return self.tc_inv_issuedate_07()

            case "TC_INV_DUEDATE_01": return self.tc_inv_duedate_01()
            case "TC_INV_DUEDATE_02": return self.tc_inv_duedate_02()
            case "TC_INV_DUEDATE_03": return self.tc_inv_duedate_03()
            case "TC_INV_DUEDATE_04": return self.tc_inv_duedate_04()
            case "TC_INV_DUEDATE_05": return self.tc_inv_duedate_05()

            case "TC_INV_STATUS_01": return self.tc_inv_status_01()
            case "TC_INV_STATUS_02": return self.tc_inv_status_02()
            case "TC_INV_STATUS_03": return self.tc_inv_status_03()

            case _:
                return TestResult(
                    result=False,
                    testcase_id=testcase_id,
                    message=f"Unknown testcase id: {testcase_id}",
                )

    # ------------------------------------------------------------------ #
    # orderRef
    # ------------------------------------------------------------------ #
    def tc_inv_orderref_01(self) -> TestResult:
        """EC-Valid-1: orderRef exists and order status is ACCEPTED -> 201."""
        body = self._body()
        body["orderRef"] = self.seed_order_accepted_id
        status, resp = self._post(body)
        return self._check("TC_INV_ORDERREF_01", 201, body, status, resp)

    def tc_inv_orderref_02(self) -> TestResult:
        """EC-Invalid-1 (Wrong State): orderRef exists but order status is
        not ACCEPTED (e.g. PLACED) -> 409."""
        body = self._body()
        body["orderRef"] = self.seed_order_placed_id
        status, resp = self._post(body)
        return self._check("TC_INV_ORDERREF_02", 409, body, status, resp)

    def tc_inv_orderref_03(self) -> TestResult:
        """EC-Invalid-2 (Not Found): orderRef does not exist -> 404."""
        body = self._body()
        body["orderRef"] = NOT_FOUND_UUID
        status, resp = self._post(body)
        return self._check("TC_INV_ORDERREF_03", 404, body, status, resp)

    # ------------------------------------------------------------------ #
    # billingInfo.name
    # ------------------------------------------------------------------ #
    def tc_inv_billname_01(self) -> TestResult:
        """BC-Min-1: length one below minimum (1 char) -> 400."""
        body = self._body()
        body["billingInfo"]["name"] = "A"
        status, resp = self._post(body)
        return self._check("TC_INV_BILLNAME_01", 400, body, status, resp)

    def tc_inv_billname_02(self) -> TestResult:
        """BC-Min: length at minimum (2 chars) -> 201."""
        body = self._body()
        body["billingInfo"]["name"] = "An"
        status, resp = self._post(body)
        return self._check("TC_INV_BILLNAME_02", 201, body, status, resp)

    def tc_inv_billname_03(self) -> TestResult:
        """BC-Max: length at maximum (100 chars) -> 201."""
        body = self._body()
        body["billingInfo"]["name"] = "A" * 100
        status, resp = self._post(body)
        return self._check("TC_INV_BILLNAME_03", 201, body, status, resp)

    def tc_inv_billname_04(self) -> TestResult:
        """BC-Max+1: length one above maximum (101 chars) -> 400."""
        body = self._body()
        body["billingInfo"]["name"] = "A" * 101
        status, resp = self._post(body)
        return self._check("TC_INV_BILLNAME_04", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # totalAmount (server-computed)
    # ------------------------------------------------------------------ #
    def tc_inv_totalamt_01(self) -> TestResult:
        """EC-Valid-1: server-computed totalAmount equals Order.totalAmount -> 201."""
        body = self._body()
        status, resp = self._post(body)
        result = self._check("TC_INV_TOTALAMT_01", 201, body, status, resp)
        if (
            result.result
            and isinstance(resp, dict)
            and str(resp.get("totalAmount")) != str(self.seed_order_accepted_total_amount)
        ):
            return TestResult(
                result=False,
                testcase_id="TC_INV_TOTALAMT_01",
                message=(
                    f"Expected totalAmount to match order.totalAmount "
                    f"({self.seed_order_accepted_total_amount!r}), got "
                    f"{resp.get('totalAmount')!r}"
                ),
            )
        return result

    def tc_inv_totalamt_02(self) -> TestResult:
        """EC-Invalid-1 (Client-Supplied Mismatch): client supplies a
        totalAmount different from order.totalAmount -> 400 (rejected, or
        ignored/recomputed server-side per API contract)."""
        body = self._body()
        body["totalAmount"] = "0.01"
        status, resp = self._post(body)
        return self._check("TC_INV_TOTALAMT_02", 400, body, status, resp)

    def tc_inv_totalamt_03(self) -> TestResult:
        """BC-Min-1: value at zero boundary -> 400."""
        body = self._body()
        body["totalAmount"] = "0.00"
        status, resp = self._post(body)
        return self._check("TC_INV_TOTALAMT_03", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # issueDate
    # ------------------------------------------------------------------ #
    def tc_inv_issuedate_01(self) -> TestResult:
        """EC-Valid-1: valid date in dd/MM/yyyy format -> 201."""
        body = self._body()
        body["issueDate"] = "23/07/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_ISSUEDATE_01", 201, body, status, resp)

    def tc_inv_issuedate_02(self) -> TestResult:
        """EC-Invalid-1 (Wrong Separator): uses hyphen instead of slash -> 400."""
        body = self._body()
        body["issueDate"] = "23-07-2026"
        status, resp = self._post(body)
        return self._check("TC_INV_ISSUEDATE_02", 400, body, status, resp)

    def tc_inv_issuedate_03(self) -> TestResult:
        """EC-Invalid-2 (Wrong Order): yyyy/MM/dd order -> 400."""
        body = self._body()
        body["issueDate"] = "2026/07/23"
        status, resp = self._post(body)
        return self._check("TC_INV_ISSUEDATE_03", 400, body, status, resp)

    def tc_inv_issuedate_04(self) -> TestResult:
        """EC-Invalid-3 (Non-Existent Date): well-formed but calendar-invalid
        date (Feb 31) -> 400."""
        body = self._body()
        body["issueDate"] = "31/02/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_ISSUEDATE_04", 400, body, status, resp)

    def tc_inv_issuedate_05(self) -> TestResult:
        """EC-Invalid-4 (Non-Existent Date): well-formed but calendar-invalid
        date (Feb 30) -> 400."""
        body = self._body()
        body["issueDate"] = "30/02/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_ISSUEDATE_05", 400, body, status, resp)

    def tc_inv_issuedate_06(self) -> TestResult:
        """BC-Month-Min-1: month value below minimum (0) -> 400."""
        body = self._body()
        body["issueDate"] = "23/00/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_ISSUEDATE_06", 400, body, status, resp)

    def tc_inv_issuedate_07(self) -> TestResult:
        """BC-Month-Max+1: month value above maximum (13) -> 400."""
        body = self._body()
        body["issueDate"] = "23/13/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_ISSUEDATE_07", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # dueDate
    # ------------------------------------------------------------------ #
    def tc_inv_duedate_01(self) -> TestResult:
        """EC-Valid-1: dueDate = issueDate + 7 days (default) -> 201."""
        body = self._body()
        body["issueDate"] = "23/07/2026"
        body["dueDate"] = "30/07/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_DUEDATE_01", 201, body, status, resp)

    def tc_inv_duedate_02(self) -> TestResult:
        """BC-Equal-Min: dueDate equals issueDate (0-day term, boundary
        equality) -> 201 (accepted since dueDate >= issueDate)."""
        body = self._body()
        body["issueDate"] = "23/07/2026"
        body["dueDate"] = "23/07/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_DUEDATE_02", 201, body, status, resp)

    def tc_inv_duedate_03(self) -> TestResult:
        """BC-Min-1: dueDate one day before issueDate -> 400."""
        body = self._body()
        body["issueDate"] = "23/07/2026"
        body["dueDate"] = "22/07/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_DUEDATE_03", 400, body, status, resp)

    def tc_inv_duedate_04(self) -> TestResult:
        """EC-Invalid-1 (Wrong Format): ISO format instead of dd/MM/yyyy -> 400."""
        body = self._body()
        body["issueDate"] = "23/07/2026"
        body["dueDate"] = "2026-07-30"
        status, resp = self._post(body)
        return self._check("TC_INV_DUEDATE_04", 400, body, status, resp)

    def tc_inv_duedate_05(self) -> TestResult:
        """EC-Invalid-2 (Non-Existent Date): well-formed but calendar-invalid
        date (April 31) -> 400."""
        body = self._body()
        body["issueDate"] = "23/07/2026"
        body["dueDate"] = "31/04/2026"
        status, resp = self._post(body)
        return self._check("TC_INV_DUEDATE_05", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # status
    # ------------------------------------------------------------------ #
    def tc_inv_status_01(self) -> TestResult:
        """EC-Valid-1: default status on creation is ISSUED -> 201."""
        body = self._body()
        status, resp = self._post(body)
        result = self._check("TC_INV_STATUS_01", 201, body, status, resp)
        if result.result and isinstance(resp, dict) and resp.get("status") != "ISSUED":
            return TestResult(
                result=False,
                testcase_id="TC_INV_STATUS_01",
                message=f"Expected default status ISSUED, got {resp.get('status')!r}",
            )
        return result

    def tc_inv_status_02(self) -> TestResult:
        """EC-Invalid-1 (Bypasses Workflow): client sets status other than
        ISSUED on creation -> 400."""
        body = self._body()
        body["status"] = "PAID"
        status, resp = self._post(body)
        return self._check("TC_INV_STATUS_02", 400, body, status, resp)

    def tc_inv_status_03(self) -> TestResult:
        """EC-Invalid-2 (Unknown Value): value not part of enum -> 400."""
        body = self._body()
        body["status"] = "DRAFT"
        status, resp = self._post(body)
        return self._check("TC_INV_STATUS_03", 400, body, status, resp)
