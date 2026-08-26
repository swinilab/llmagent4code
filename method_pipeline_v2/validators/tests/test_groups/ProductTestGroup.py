"""
ProductTestGroup - implements ITestGroup for the Product entity.

Source: OMS_TestCases_BVA_EP_EN.xlsx, sheet "Product" (TC_PRO_*).

Notes:
- TC_PRO_ID_01..03 exercise GET /products/{id}, all other test cases exercise
  POST /products.
- price.amount test cases send the amount as a string in the request body to
  faithfully reproduce non-numeric / wrong-precision inputs from the sheet
  (e.g. "abc", "10.999"); adjust to a numeric type if the API requires it.
"""

from __future__ import annotations

from typing import Any

from interfaces.base import ITestGroup, TestResult

NEEDS_SEED_DATA = "<seed: existing product id>"
NOT_FOUND_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


class ProductTestGroup(ITestGroup):
    """Functional BVA/EP tests for the Product entity."""

    def __init__(self, api: str, seed_product_id: str | None = None):
        self.api = api
        self.seed_product_id = seed_product_id or NEEDS_SEED_DATA

        self.standard_request_body: dict[str, Any] = {
            "description": "Logitech M185 Wireless Mouse",
            "price": {
                "amount": "10.00",
                "currency": "USD",
            },
        }

        self.testcases: list[str] = [
            "TC_PRO_ID_01", "TC_PRO_ID_02", "TC_PRO_ID_03",
            "TC_PRO_DESCRIPTIO_01", "TC_PRO_DESCRIPTIO_02", "TC_PRO_DESCRIPTIO_03",
            "TC_PRO_DESCRIPTIO_04", "TC_PRO_DESCRIPTIO_05", "TC_PRO_DESCRIPTIO_06",
            "TC_PRO_DESCRIPTIO_07",
            "TC_PRO_PRICEAMT_01", "TC_PRO_PRICEAMT_02", "TC_PRO_PRICEAMT_03",
            "TC_PRO_PRICEAMT_04", "TC_PRO_PRICEAMT_05", "TC_PRO_PRICEAMT_06",
            "TC_PRO_PRICEAMT_07", "TC_PRO_PRICEAMT_08",
            "TC_PRO_CURRENCY_01", "TC_PRO_CURRENCY_02", "TC_PRO_CURRENCY_03",
            "TC_PRO_CURRENCY_04", "TC_PRO_CURRENCY_05", "TC_PRO_CURRENCY_06",
            "TC_PRO_CURRENCY_07",
        ]

    # ------------------------------------------------------------------ #
    # Dispatcher
    # ------------------------------------------------------------------ #
    def run_testcase(self, testcase_id: str) -> TestResult:
        match testcase_id:
            case "TC_PRO_ID_01": return self.tc_pro_id_01()
            case "TC_PRO_ID_02": return self.tc_pro_id_02()
            case "TC_PRO_ID_03": return self.tc_pro_id_03()

            case "TC_PRO_DESCRIPTIO_01": return self.tc_pro_descriptio_01()
            case "TC_PRO_DESCRIPTIO_02": return self.tc_pro_descriptio_02()
            case "TC_PRO_DESCRIPTIO_03": return self.tc_pro_descriptio_03()
            case "TC_PRO_DESCRIPTIO_04": return self.tc_pro_descriptio_04()
            case "TC_PRO_DESCRIPTIO_05": return self.tc_pro_descriptio_05()
            case "TC_PRO_DESCRIPTIO_06": return self.tc_pro_descriptio_06()
            case "TC_PRO_DESCRIPTIO_07": return self.tc_pro_descriptio_07()

            case "TC_PRO_PRICEAMT_01": return self.tc_pro_priceamt_01()
            case "TC_PRO_PRICEAMT_02": return self.tc_pro_priceamt_02()
            case "TC_PRO_PRICEAMT_03": return self.tc_pro_priceamt_03()
            case "TC_PRO_PRICEAMT_04": return self.tc_pro_priceamt_04()
            case "TC_PRO_PRICEAMT_05": return self.tc_pro_priceamt_05()
            case "TC_PRO_PRICEAMT_06": return self.tc_pro_priceamt_06()
            case "TC_PRO_PRICEAMT_07": return self.tc_pro_priceamt_07()
            case "TC_PRO_PRICEAMT_08": return self.tc_pro_priceamt_08()

            case "TC_PRO_CURRENCY_01": return self.tc_pro_currency_01()
            case "TC_PRO_CURRENCY_02": return self.tc_pro_currency_02()
            case "TC_PRO_CURRENCY_03": return self.tc_pro_currency_03()
            case "TC_PRO_CURRENCY_04": return self.tc_pro_currency_04()
            case "TC_PRO_CURRENCY_05": return self.tc_pro_currency_05()
            case "TC_PRO_CURRENCY_06": return self.tc_pro_currency_06()
            case "TC_PRO_CURRENCY_07": return self.tc_pro_currency_07()

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
    # id  (GET /products/{id})
    # ------------------------------------------------------------------ #
    def tc_pro_id_01(self) -> TestResult:
        """EC-Valid-1: retrieve product using a well-formed, existing UUID -> 200."""
        status, body = self._get(self.seed_product_id)
        return self._check("TC_PRO_ID_01", 200, {}, status, body)

    def tc_pro_id_02(self) -> TestResult:
        """EC-Invalid-1 (Not Found): well-formed UUID that does not exist -> 404."""
        status, body = self._get(NOT_FOUND_UUID)
        return self._check("TC_PRO_ID_02", 404, {}, status, body)

    def tc_pro_id_03(self) -> TestResult:
        """EC-Invalid-2 (Wrong Format): malformed UUID string -> 400."""
        status, body = self._get("prod-123")
        return self._check("TC_PRO_ID_03", 400, {}, status, body)

    # ------------------------------------------------------------------ #
    # description
    # ------------------------------------------------------------------ #
    def tc_pro_descriptio_01(self) -> TestResult:
        """BC-Min-1: length one below minimum (2 chars) -> 400."""
        body = self._body()
        body["description"] = "AB"
        status, resp = self._post(body)
        return self._check("TC_PRO_DESCRIPTIO_01", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_descriptio_02(self) -> TestResult:
        """BC-Min: length at minimum (3 chars) -> 201."""
        body = self._body()
        body["description"] = "USB"
        status, resp = self._post(body)
        return self._check("TC_PRO_DESCRIPTIO_02", 201, body, status, resp)

    def tc_pro_descriptio_03(self) -> TestResult:
        """BC-Max: length at maximum (500 chars) -> 201."""
        body = self._body()
        body["description"] = "A" * 500
        status, resp = self._post(body)
        return self._check("TC_PRO_DESCRIPTIO_03", 201, body, status, resp)

    def tc_pro_descriptio_04(self) -> TestResult:
        """BC-Max+1: length one above maximum (501 chars) -> 400."""
        body = self._body()
        body["description"] = "A" * 501
        status, resp = self._post(body)
        return self._check("TC_PRO_DESCRIPTIO_04", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_descriptio_05(self) -> TestResult:
        """EC-Invalid-1 (Empty): empty string -> 400."""
        body = self._body()
        body["description"] = ""
        status, resp = self._post(body)
        return self._check("TC_PRO_DESCRIPTIO_05", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_descriptio_06(self) -> TestResult:
        """EC-Invalid-2 (Whitespace Only): whitespace-only string -> 400."""
        body = self._body()
        body["description"] = "     "
        status, resp = self._post(body)
        return self._check("TC_PRO_DESCRIPTIO_06", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_descriptio_07(self) -> TestResult:
        """EC-Valid-1: ordinary product description -> 201."""
        body = self._body()
        body["description"] = "Logitech M185 Wireless Mouse"
        status, resp = self._post(body)
        return self._check("TC_PRO_DESCRIPTIO_07", 201, body, status, resp)

    # ------------------------------------------------------------------ #
    # price.amount
    # ------------------------------------------------------------------ #
    def tc_pro_priceamt_01(self) -> TestResult:
        """BC-Min-1: value below minimum boundary (0.00) -> 400."""
        body = self._body()
        body["price"]["amount"] = "0.00"
        status, resp = self._post(body)
        return self._check("TC_PRO_PRICEAMT_01", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_priceamt_02(self) -> TestResult:
        """BC-Min: value at minimum (0.01) -> 201."""
        body = self._body()
        body["price"]["amount"] = "0.01"
        status, resp = self._post(body)
        return self._check("TC_PRO_PRICEAMT_02", 201, body, status, resp)

    def tc_pro_priceamt_03(self) -> TestResult:
        """BC-Max: value at maximum (999999.99) -> 201."""
        body = self._body()
        body["price"]["amount"] = "999999.99"
        status, resp = self._post(body)
        return self._check("TC_PRO_PRICEAMT_03", 201, body, status, resp)

    def tc_pro_priceamt_04(self) -> TestResult:
        """BC-Max+1: value above maximum (1000000.00) -> 400."""
        body = self._body()
        body["price"]["amount"] = "1000000.00"
        status, resp = self._post(body)
        return self._check("TC_PRO_PRICEAMT_04", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_priceamt_05(self) -> TestResult:
        """EC-Invalid-1 (Negative): negative value -> 400."""
        body = self._body()
        body["price"]["amount"] = "-10.00"
        status, resp = self._post(body)
        return self._check("TC_PRO_PRICEAMT_05", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_priceamt_06(self) -> TestResult:
        """EC-Invalid-2 (Wrong Decimal Precision): more than 2 decimal places -> 400."""
        body = self._body()
        body["price"]["amount"] = "10.999"
        status, resp = self._post(body)
        return self._check("TC_PRO_PRICEAMT_06", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_priceamt_07(self) -> TestResult:
        """EC-Invalid-3 (Non-Numeric): non-numeric string -> 400."""
        body = self._body()
        body["price"]["amount"] = "abc"
        status, resp = self._post(body)
        return self._check("TC_PRO_PRICEAMT_07", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_priceamt_08(self) -> TestResult:
        """EC-Invalid-4 (Empty): empty/null -> 400."""
        body = self._body()
        body["price"]["amount"] = ""
        status, resp = self._post(body)
        return self._check("TC_PRO_PRICEAMT_08", 400, body, status, resp, acceptable=(400, 422))

    # ------------------------------------------------------------------ #
    # price.currency
    # ------------------------------------------------------------------ #
    def tc_pro_currency_01(self) -> TestResult:
        """EC-Valid-1: supported currency - USD -> 201."""
        body = self._body()
        body["price"]["currency"] = "USD"
        status, resp = self._post(body)
        return self._check("TC_PRO_CURRENCY_01", 201, body, status, resp)

    def tc_pro_currency_02(self) -> TestResult:
        """EC-Valid-2: supported currency - VND -> 201."""
        body = self._body()
        body["price"]["currency"] = "VND"
        status, resp = self._post(body)
        return self._check("TC_PRO_CURRENCY_02", 201, body, status, resp)

    def tc_pro_currency_03(self) -> TestResult:
        """EC-Valid-3: supported currency - EUR -> 201."""
        body = self._body()
        body["price"]["currency"] = "EUR"
        status, resp = self._post(body)
        return self._check("TC_PRO_CURRENCY_03", 201, body, status, resp)

    def tc_pro_currency_04(self) -> TestResult:
        """BC-Length-Mismatch: length below fixed length (2 chars, also invalid code) -> 400."""
        body = self._body()
        body["price"]["currency"] = "US"
        status, resp = self._post(body)
        return self._check("TC_PRO_CURRENCY_04", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_currency_05(self) -> TestResult:
        """EC-Invalid-1 (Unsupported Code): well-formed 3-letter code not in supported list -> 400."""
        body = self._body()
        body["price"]["currency"] = "XYZ"
        status, resp = self._post(body)
        return self._check("TC_PRO_CURRENCY_05", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_currency_06(self) -> TestResult:
        """EC-Invalid-2 (Wrong Case): lowercase value -> 400."""
        body = self._body()
        body["price"]["currency"] = "usd"
        status, resp = self._post(body)
        return self._check("TC_PRO_CURRENCY_06", 400, body, status, resp, acceptable=(400, 422))

    def tc_pro_currency_07(self) -> TestResult:
        """EC-Invalid-3 (Empty): empty/null -> 400."""
        body = self._body()
        body["price"]["currency"] = ""
        status, resp = self._post(body)
        return self._check("TC_PRO_CURRENCY_07", 400, body, status, resp, acceptable=(400, 422))
