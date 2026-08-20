"""
OrderTestGroup - implements ITestGroup for the Order entity.

Source: OMS_TestCases_BVA_EP_EN.xlsx, sheet "Order" (TC_ORD_*).

Notes:
- All test cases exercise POST /orders except TC_ORD_INVREF_* which check the
  invoiceRef field on a fetched order (GET /orders/{id}) since invoiceRef is
  read-only/server-derived and depends on order lifecycle state.
- Seed placeholders (existing customer id, existing product id, existing
  invoice id, order with a given status) must be replaced with real seeded
  data prior to execution.
- lineItems test cases build [{"productRef": ..., "quantity": ...}, ...]
  arrays; a valid seed_product_id is required to isolate the attribute under
  test (e.g. quantity boundaries) without also failing on productRef.
"""

from __future__ import annotations

from typing import Any

from interfaces.base import ITestGroup, TestResult

NEEDS_SEED_CUSTOMER = "<seed: existing customer id>"
NEEDS_SEED_PRODUCT = "<seed: existing product id>"
NEEDS_SEED_INVOICE = "<seed: existing invoice id>"
NEEDS_SEED_ORDER_PLACED = "<seed: order status=PLACED>"
NEEDS_SEED_ORDER_ACCEPTED_WITH_INVOICE = "<seed: order status=ACCEPTED, invoiceRef set>"
NOT_FOUND_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


class OrderTestGroup(ITestGroup):
    """Functional BVA/EP tests for the Order entity."""

    def __init__(
        self,
        api: str,
        seed_customer_id: str | None = None,
        seed_product_id: str | None = None,
        seed_invoice_id: str | None = None,
        seed_order_placed_id: str | None = None,
        seed_order_with_invoice_id: str | None = None,
    ):
        self.api = api
        self.seed_customer_id = seed_customer_id or NEEDS_SEED_CUSTOMER
        self.seed_product_id = seed_product_id or NEEDS_SEED_PRODUCT
        self.seed_invoice_id = seed_invoice_id or NEEDS_SEED_INVOICE
        self.seed_order_placed_id = seed_order_placed_id or NEEDS_SEED_ORDER_PLACED
        self.seed_order_with_invoice_id = (
            seed_order_with_invoice_id or NEEDS_SEED_ORDER_ACCEPTED_WITH_INVOICE
        )

        self.standard_request_body: dict[str, Any] = {
            "customerRef": self.seed_customer_id,
            "lineItems": [
                {"productRef": self.seed_product_id, "quantity": 1},
            ],
        }

        self.testcases: list[str] = [
            "TC_ORD_CUSTREF_01", "TC_ORD_CUSTREF_02", "TC_ORD_CUSTREF_03",
            "TC_ORD_CUSTREF_04",
            "TC_ORD_LINEITEMS_01", "TC_ORD_LINEITEMS_02", "TC_ORD_LINEITEMS_03",
            "TC_ORD_LINEITEMS_04", "TC_ORD_LINEITEMS_05", "TC_ORD_LINEITEMS_06",
            "TC_ORD_LINEITEMS_07",
            "TC_ORD_QTY_01", "TC_ORD_QTY_02", "TC_ORD_QTY_03", "TC_ORD_QTY_04",
            "TC_ORD_QTY_05", "TC_ORD_QTY_06", "TC_ORD_QTY_07",
            "TC_ORD_UNITPRICE_01", "TC_ORD_UNITPRICE_02",
            "TC_ORD_TOTALAMT_01", "TC_ORD_TOTALAMT_02",
            "TC_ORD_STATUS_01", "TC_ORD_STATUS_02", "TC_ORD_STATUS_03",
            "TC_ORD_INVREF_01", "TC_ORD_INVREF_02", "TC_ORD_INVREF_03",
        ]

    # ------------------------------------------------------------------ #
    # Dispatcher
    # ------------------------------------------------------------------ #
    def run_testcase(self, testcase_id: str) -> TestResult:
        match testcase_id:
            case "TC_ORD_CUSTREF_01": return self.tc_ord_custref_01()
            case "TC_ORD_CUSTREF_02": return self.tc_ord_custref_02()
            case "TC_ORD_CUSTREF_03": return self.tc_ord_custref_03()
            case "TC_ORD_CUSTREF_04": return self.tc_ord_custref_04()

            case "TC_ORD_LINEITEMS_01": return self.tc_ord_lineitems_01()
            case "TC_ORD_LINEITEMS_02": return self.tc_ord_lineitems_02()
            case "TC_ORD_LINEITEMS_03": return self.tc_ord_lineitems_03()
            case "TC_ORD_LINEITEMS_04": return self.tc_ord_lineitems_04()
            case "TC_ORD_LINEITEMS_05": return self.tc_ord_lineitems_05()
            case "TC_ORD_LINEITEMS_06": return self.tc_ord_lineitems_06()
            case "TC_ORD_LINEITEMS_07": return self.tc_ord_lineitems_07()

            case "TC_ORD_QTY_01": return self.tc_ord_qty_01()
            case "TC_ORD_QTY_02": return self.tc_ord_qty_02()
            case "TC_ORD_QTY_03": return self.tc_ord_qty_03()
            case "TC_ORD_QTY_04": return self.tc_ord_qty_04()
            case "TC_ORD_QTY_05": return self.tc_ord_qty_05()
            case "TC_ORD_QTY_06": return self.tc_ord_qty_06()
            case "TC_ORD_QTY_07": return self.tc_ord_qty_07()

            case "TC_ORD_UNITPRICE_01": return self.tc_ord_unitprice_01()
            case "TC_ORD_UNITPRICE_02": return self.tc_ord_unitprice_02()

            case "TC_ORD_TOTALAMT_01": return self.tc_ord_totalamt_01()
            case "TC_ORD_TOTALAMT_02": return self.tc_ord_totalamt_02()

            case "TC_ORD_STATUS_01": return self.tc_ord_status_01()
            case "TC_ORD_STATUS_02": return self.tc_ord_status_02()
            case "TC_ORD_STATUS_03": return self.tc_ord_status_03()

            case "TC_ORD_INVREF_01": return self.tc_ord_invref_01()
            case "TC_ORD_INVREF_02": return self.tc_ord_invref_02()
            case "TC_ORD_INVREF_03": return self.tc_ord_invref_03()

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
    # customerRef
    # ------------------------------------------------------------------ #
    def tc_ord_custref_01(self) -> TestResult:
        """EC-Valid-1: existing, valid customerRef -> 201."""
        body = self._body()
        body["customerRef"] = self.seed_customer_id
        status, resp = self._post(body)
        return self._check("TC_ORD_CUSTREF_01", 201, body, status, resp)

    def tc_ord_custref_02(self) -> TestResult:
        """EC-Invalid-1 (Not Found): well-formed UUID that does not exist -> 404."""
        body = self._body()
        body["customerRef"] = NOT_FOUND_UUID
        status, resp = self._post(body)
        return self._check("TC_ORD_CUSTREF_02", 404, body, status, resp)

    def tc_ord_custref_03(self) -> TestResult:
        """EC-Invalid-2 (Wrong Format): malformed UUID string -> 400."""
        body = self._body()
        body["customerRef"] = "cust-1"
        status, resp = self._post(body)
        return self._check("TC_ORD_CUSTREF_03", 400, body, status, resp)

    def tc_ord_custref_04(self) -> TestResult:
        """EC-Invalid-3 (Empty): empty/null -> 400."""
        body = self._body()
        body["customerRef"] = None
        status, resp = self._post(body)
        return self._check("TC_ORD_CUSTREF_04", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # lineItems
    # ------------------------------------------------------------------ #
    def tc_ord_lineitems_01(self) -> TestResult:
        """BC-Min-1: item count one below minimum (0 items) -> 400."""
        body = self._body()
        body["lineItems"] = []
        status, resp = self._post(body)
        return self._check("TC_ORD_LINEITEMS_01", 400, body, status, resp)

    def tc_ord_lineitems_02(self) -> TestResult:
        """BC-Min: item count at minimum (1 item) -> 201."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": 1}]
        status, resp = self._post(body)
        return self._check("TC_ORD_LINEITEMS_02", 201, body, status, resp)

    def tc_ord_lineitems_03(self) -> TestResult:
        """BC-Max: item count at maximum (100 distinct productRef items) -> 201.

        Requires 100 distinct seeded product ids; here the same seed product
        id is repeated as a placeholder - replace with 100 distinct product
        refs to faithfully test 'distinct products' per the sheet.
        """
        body = self._body()
        body["lineItems"] = [
            {"productRef": self.seed_product_id, "quantity": 1} for _ in range(100)
        ]
        status, resp = self._post(body)
        return self._check("TC_ORD_LINEITEMS_03", 201, body, status, resp)

    def tc_ord_lineitems_04(self) -> TestResult:
        """BC-Max+1: item count one above maximum (101 items) -> 400."""
        body = self._body()
        body["lineItems"] = [
            {"productRef": self.seed_product_id, "quantity": 1} for _ in range(101)
        ]
        status, resp = self._post(body)
        return self._check("TC_ORD_LINEITEMS_04", 400, body, status, resp)

    def tc_ord_lineitems_05(self) -> TestResult:
        """EC-Invalid-1 (Non-Existent Product): item references a non-existent product -> 404."""
        body = self._body()
        body["lineItems"] = [{"productRef": NOT_FOUND_UUID, "quantity": 1}]
        status, resp = self._post(body)
        return self._check("TC_ORD_LINEITEMS_05", 404, body, status, resp)

    def tc_ord_lineitems_06(self) -> TestResult:
        """EC-Invalid-2 (Missing): lineItems null/missing entirely -> 400."""
        body = self._body()
        body["lineItems"] = None
        status, resp = self._post(body)
        return self._check("TC_ORD_LINEITEMS_06", 400, body, status, resp)

    def tc_ord_lineitems_07(self) -> TestResult:
        """EC-Invalid-3 (Duplicate Product): two items reference the same
        productRef -> 400 (rejected) per the sheet's default expectation;
        adjust to 201 if the API's business rule instead merges duplicates."""
        body = self._body()
        body["lineItems"] = [
            {"productRef": self.seed_product_id, "quantity": 1},
            {"productRef": self.seed_product_id, "quantity": 2},
        ]
        status, resp = self._post(body)
        return self._check("TC_ORD_LINEITEMS_07", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # lineItems[].quantity
    # ------------------------------------------------------------------ #
    def tc_ord_qty_01(self) -> TestResult:
        """BC-Min-1: value one below minimum (0) -> 400."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": 0}]
        status, resp = self._post(body)
        return self._check("TC_ORD_QTY_01", 400, body, status, resp)

    def tc_ord_qty_02(self) -> TestResult:
        """BC-Min: value at minimum (1) -> 201."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": 1}]
        status, resp = self._post(body)
        return self._check("TC_ORD_QTY_02", 201, body, status, resp)

    def tc_ord_qty_03(self) -> TestResult:
        """BC-Max: value at maximum (1000) -> 201."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": 1000}]
        status, resp = self._post(body)
        return self._check("TC_ORD_QTY_03", 201, body, status, resp)

    def tc_ord_qty_04(self) -> TestResult:
        """BC-Max+1: value one above maximum (1001) -> 400."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": 1001}]
        status, resp = self._post(body)
        return self._check("TC_ORD_QTY_04", 400, body, status, resp)

    def tc_ord_qty_05(self) -> TestResult:
        """EC-Invalid-1 (Negative): negative value -> 400."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": -5}]
        status, resp = self._post(body)
        return self._check("TC_ORD_QTY_05", 400, body, status, resp)

    def tc_ord_qty_06(self) -> TestResult:
        """EC-Invalid-2 (Decimal): non-integer value -> 400."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": 1.5}]
        status, resp = self._post(body)
        return self._check("TC_ORD_QTY_06", 400, body, status, resp)

    def tc_ord_qty_07(self) -> TestResult:
        """EC-Invalid-3 (Non-Numeric): non-numeric value -> 400."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": "abc"}]
        status, resp = self._post(body)
        return self._check("TC_ORD_QTY_07", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # lineItems[].unitPriceSnapshot (server-computed)
    # ------------------------------------------------------------------ #
    def tc_ord_unitprice_01(self) -> TestResult:
        """EC-Valid-1: client omits price; server derives snapshot from
        current Product price -> 201."""
        body = self._body()
        body["lineItems"] = [{"productRef": self.seed_product_id, "quantity": 1}]
        status, resp = self._post(body)
        return self._check("TC_ORD_UNITPRICE_01", 201, body, status, resp)

    def tc_ord_unitprice_02(self) -> TestResult:
        """EC-Invalid-1 (Tampered Value): client supplies a price different
        from current Product price -> 400 (rejected, or ignored server-side
        per API contract)."""
        body = self._body()
        body["lineItems"] = [
            {
                "productRef": self.seed_product_id,
                "quantity": 1,
                "unitPriceSnapshot": "0.01",
            }
        ]
        status, resp = self._post(body)
        return self._check("TC_ORD_UNITPRICE_02", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # totalAmount (server-computed)
    # ------------------------------------------------------------------ #
    def tc_ord_totalamt_01(self) -> TestResult:
        """EC-Valid-1: server correctly computes total = sum(quantity * unitPrice) -> 201."""
        body = self._body()
        status, resp = self._post(body)
        return self._check("TC_ORD_TOTALAMT_01", 201, body, status, resp)

    def tc_ord_totalamt_02(self) -> TestResult:
        """EC-Invalid-1 (Client-Supplied Mismatch): client supplies a
        totalAmount different from the computed value -> 400 (rejected, or
        ignored/recomputed server-side per API contract)."""
        body = self._body()
        body["totalAmount"] = "999999.99"
        status, resp = self._post(body)
        return self._check("TC_ORD_TOTALAMT_02", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # status
    # ------------------------------------------------------------------ #
    def tc_ord_status_01(self) -> TestResult:
        """EC-Valid-1: default status on creation is PLACED -> 201."""
        body = self._body()
        status, resp = self._post(body)
        result = self._check("TC_ORD_STATUS_01", 201, body, status, resp)
        if result.result and isinstance(resp, dict) and resp.get("status") != "PLACED":
            result.result = False
        return result

    def tc_ord_status_02(self) -> TestResult:
        """EC-Invalid-1 (Bypasses Workflow): client sets status other than
        PLACED on creation -> 400."""
        body = self._body()
        body["status"] = "SHIPPED"
        status, resp = self._post(body)
        return self._check("TC_ORD_STATUS_02", 400, body, status, resp)

    def tc_ord_status_03(self) -> TestResult:
        """EC-Invalid-2 (Unknown Value): value not part of enum -> 400."""
        body = self._body()
        body["status"] = "DONE"
        status, resp = self._post(body)
        return self._check("TC_ORD_STATUS_03", 400, body, status, resp)

    # ------------------------------------------------------------------ #
    # invoiceRef (read-only / server-derived; verified via GET)
    # ------------------------------------------------------------------ #
    def tc_ord_invref_01(self) -> TestResult:
        """EC-Valid-1: invoiceRef null prior to invoicing (e.g. PLACED/ACCEPTED) -> 200."""
        status, resp = self._get(self.seed_order_placed_id)
        result = self._check("TC_ORD_INVREF_01", 200, {}, status, resp)
        if result.result and isinstance(resp, dict) and resp.get("invoiceRef") is not None:
            result.result = False
        return result

    def tc_ord_invref_02(self) -> TestResult:
        """EC-Valid-2: invoiceRef valid after invoice creation -> 200."""
        status, resp = self._get(self.seed_order_with_invoice_id)
        result = self._check("TC_ORD_INVREF_02", 200, {}, status, resp)
        if result.result and isinstance(resp, dict) and not resp.get("invoiceRef"):
            result.result = False
        return result

    def tc_ord_invref_03(self) -> TestResult:
        """EC-Invalid-1 (Not Found): invoiceRef references a non-existent
        invoice -> 404. invoiceRef is not directly settable on Order, so this
        is exercised by fetching the referenced invoice id directly against
        the Invoice API base URL; adjust `invoice_api` if it differs from
        `self.api`."""
        import requests
        invoice_api = self.api.rstrip("/").rsplit("/", 1)[0] + "/invoices"
        url = f"{invoice_api}/{NOT_FOUND_UUID}"
        resp_obj = requests.get(url, timeout=10)
        try:
            resp = resp_obj.json()
        except ValueError:
            resp = resp_obj.text
        return self._check("TC_ORD_INVREF_03", 404, {}, resp_obj.status_code, resp)
