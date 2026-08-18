import copy
import requests
from dataclasses import dataclass, field
from typing import Any
from abc import ABC, abstractmethod

from interfaces.base import ITestGroup, TestResult

class CustomerTestGroup(ITestGroup):
    """Concrete test group for the Customer entity (50 test cases)."""

    # -- construction -------------------------------------------------------

    def __init__(self, api: str = "/api/v1/customers", seed_customer_id: str = "") -> None:
        self.api = api.rstrip("/")
        self.seed_customer_id = seed_customer_id

        self.standard_request_body: dict[str, Any] = {
            "name": "Nguyen Van A",
            "address": "123 Nguyen Trai, Thanh Xuan, Hanoi",
            "phone": "+84912345678",
            "bankingDetails": {
                "accountNumber": "1234567890",
                "bankName": "Vietcombank",
            },
            "role": "CUSTOMER",
            "orderHistory": [],
        }

        self.testcases: list[str] = [
            # ID
            "TC_CUS_ID_01", "TC_CUS_ID_02", "TC_CUS_ID_03", "TC_CUS_ID_04",
            # Name
            "TC_CUS_NAME_01", "TC_CUS_NAME_02", "TC_CUS_NAME_03",
            "TC_CUS_NAME_04", "TC_CUS_NAME_05", "TC_CUS_NAME_06",
            "TC_CUS_NAME_07", "TC_CUS_NAME_08", "TC_CUS_NAME_09",
            "TC_CUS_NAME_10",
            # Address
            "TC_CUS_ADDRESS_01", "TC_CUS_ADDRESS_02", "TC_CUS_ADDRESS_03",
            "TC_CUS_ADDRESS_04", "TC_CUS_ADDRESS_05", "TC_CUS_ADDRESS_06",
            "TC_CUS_ADDRESS_07",
            # Phone
            "TC_CUS_PHONE_01", "TC_CUS_PHONE_02", "TC_CUS_PHONE_03",
            "TC_CUS_PHONE_04", "TC_CUS_PHONE_05", "TC_CUS_PHONE_06",
            "TC_CUS_PHONE_07", "TC_CUS_PHONE_08",
            # Banking – accountNumber
            "TC_CUS_BANKACCTNU_01", "TC_CUS_BANKACCTNU_02",
            "TC_CUS_BANKACCTNU_03", "TC_CUS_BANKACCTNU_04",
            "TC_CUS_BANKACCTNU_05", "TC_CUS_BANKACCTNU_06",
            # Banking – bankName
            "TC_CUS_BANKNAME_01", "TC_CUS_BANKNAME_02",
            "TC_CUS_BANKNAME_03", "TC_CUS_BANKNAME_04",
            "TC_CUS_BANKNAME_05", "TC_CUS_BANKNAME_06",
            # Role
            "TC_CUS_ROLE_01", "TC_CUS_ROLE_02", "TC_CUS_ROLE_03",
            "TC_CUS_ROLE_04", "TC_CUS_ROLE_05", "TC_CUS_ROLE_06",
            # Order History
            "TC_CUS_ORDERHIST_01", "TC_CUS_ORDERHIST_02",
            "TC_CUS_ORDERHIST_03",
        ]

    # -- dispatcher ---------------------------------------------------------

    def run_testcase(self, testcase_id: str) -> TestResult:
        """Match-case to run corresponding test function with testcase_id."""
        match testcase_id:
            # ---- ID (GET) -------------------------------------------------
            case "TC_CUS_ID_01":       return self._tc_cus_id_01()
            case "TC_CUS_ID_02":       return self._tc_cus_id_02()
            case "TC_CUS_ID_03":       return self._tc_cus_id_03()
            case "TC_CUS_ID_04":       return self._tc_cus_id_04()
            # ---- Name (POST) ----------------------------------------------
            case "TC_CUS_NAME_01":     return self._tc_cus_name_01()
            case "TC_CUS_NAME_02":     return self._tc_cus_name_02()
            case "TC_CUS_NAME_03":     return self._tc_cus_name_03()
            case "TC_CUS_NAME_04":     return self._tc_cus_name_04()
            case "TC_CUS_NAME_05":     return self._tc_cus_name_05()
            case "TC_CUS_NAME_06":     return self._tc_cus_name_06()
            case "TC_CUS_NAME_07":     return self._tc_cus_name_07()
            case "TC_CUS_NAME_08":     return self._tc_cus_name_08()
            case "TC_CUS_NAME_09":     return self._tc_cus_name_09()
            case "TC_CUS_NAME_10":     return self._tc_cus_name_10()
            # ---- Address (POST) -------------------------------------------
            case "TC_CUS_ADDRESS_01":  return self._tc_cus_address_01()
            case "TC_CUS_ADDRESS_02":  return self._tc_cus_address_02()
            case "TC_CUS_ADDRESS_03":  return self._tc_cus_address_03()
            case "TC_CUS_ADDRESS_04":  return self._tc_cus_address_04()
            case "TC_CUS_ADDRESS_05":  return self._tc_cus_address_05()
            case "TC_CUS_ADDRESS_06":  return self._tc_cus_address_06()
            case "TC_CUS_ADDRESS_07":  return self._tc_cus_address_07()
            # ---- Phone (POST) ---------------------------------------------
            case "TC_CUS_PHONE_01":    return self._tc_cus_phone_01()
            case "TC_CUS_PHONE_02":    return self._tc_cus_phone_02()
            case "TC_CUS_PHONE_03":    return self._tc_cus_phone_03()
            case "TC_CUS_PHONE_04":    return self._tc_cus_phone_04()
            case "TC_CUS_PHONE_05":    return self._tc_cus_phone_05()
            case "TC_CUS_PHONE_06":    return self._tc_cus_phone_06()
            case "TC_CUS_PHONE_07":    return self._tc_cus_phone_07()
            case "TC_CUS_PHONE_08":    return self._tc_cus_phone_08()
            # ---- Banking accountNumber (POST) -----------------------------
            case "TC_CUS_BANKACCTNU_01": return self._tc_cus_bankacctnu_01()
            case "TC_CUS_BANKACCTNU_02": return self._tc_cus_bankacctnu_02()
            case "TC_CUS_BANKACCTNU_03": return self._tc_cus_bankacctnu_03()
            case "TC_CUS_BANKACCTNU_04": return self._tc_cus_bankacctnu_04()
            case "TC_CUS_BANKACCTNU_05": return self._tc_cus_bankacctnu_05()
            case "TC_CUS_BANKACCTNU_06": return self._tc_cus_bankacctnu_06()
            # ---- Banking bankName (POST) ----------------------------------
            case "TC_CUS_BANKNAME_01": return self._tc_cus_bankname_01()
            case "TC_CUS_BANKNAME_02": return self._tc_cus_bankname_02()
            case "TC_CUS_BANKNAME_03": return self._tc_cus_bankname_03()
            case "TC_CUS_BANKNAME_04": return self._tc_cus_bankname_04()
            case "TC_CUS_BANKNAME_05": return self._tc_cus_bankname_05()
            case "TC_CUS_BANKNAME_06": return self._tc_cus_bankname_06()
            # ---- Role (POST) ----------------------------------------------
            case "TC_CUS_ROLE_01":     return self._tc_cus_role_01()
            case "TC_CUS_ROLE_02":     return self._tc_cus_role_02()
            case "TC_CUS_ROLE_03":     return self._tc_cus_role_03()
            case "TC_CUS_ROLE_04":     return self._tc_cus_role_04()
            case "TC_CUS_ROLE_05":     return self._tc_cus_role_05()
            case "TC_CUS_ROLE_06":     return self._tc_cus_role_06()
            # ---- Order History (POST) -------------------------------------
            case "TC_CUS_ORDERHIST_01": return self._tc_cus_orderhist_01()
            case "TC_CUS_ORDERHIST_02": return self._tc_cus_orderhist_02()
            case "TC_CUS_ORDERHIST_03": return self._tc_cus_orderhist_03()
            # ---- Fallback -------------------------------------------------
            case _:
                return TestResult(
                    result=False,
                    testcase_id=testcase_id,
                    message=f"Unknown testcase_id: {testcase_id}",
                )

    # =======================================================================
    #  ID  (GET – retrieve by path parameter)
    # =======================================================================

    def _tc_cus_id_01(self) -> TestResult:
        """Well-formed, existing UUID → 200."""
        status, body = self._get(self.seed_customer_id)
        return self._check("TC_CUS_ID_01", 200, {}, status, body)

    def _tc_cus_id_02(self) -> TestResult:
        """Well-formed UUID that does not exist → 404."""
        status, body = self._get("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        return self._check("TC_CUS_ID_02", 404, {}, status, body)

    def _tc_cus_id_03(self) -> TestResult:
        """Malformed UUID string → 422."""
        status, body = self._get("not-a-uuid-123")
        return self._check("TC_CUS_ID_03", 422, {}, status, body)

    def _tc_cus_id_04(self) -> TestResult:
        """Empty / null id → 422."""
        status, body = self._get("")
        return self._check("TC_CUS_ID_04", 422, {}, status, body)

    # =======================================================================
    #  NAME  (POST)
    # =======================================================================

    def _tc_cus_name_01(self) -> TestResult:
        """1 char – below minimum → 422."""
        b = self._body(); b["name"] = "A"
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_01", 422, b, s, r)

    def _tc_cus_name_02(self) -> TestResult:
        """2 chars – at minimum → 201."""
        b = self._body(); b["name"] = "An"
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_02", 201, b, s, r)

    def _tc_cus_name_03(self) -> TestResult:
        """100 chars – at maximum → 201."""
        b = self._body(); b["name"] = "A" * 100
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_03", 201, b, s, r)

    def _tc_cus_name_04(self) -> TestResult:
        """101 chars – above maximum → 422."""
        b = self._body(); b["name"] = "A" * 101
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_04", 422, b, s, r)

    def _tc_cus_name_05(self) -> TestResult:
        """Ordinary name with space → 201."""
        b = self._body(); b["name"] = "Nguyen Van A"
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_05", 201, b, s, r)

    def _tc_cus_name_06(self) -> TestResult:
        """Hyphen / apostrophe → 201."""
        b = self._body(); b["name"] = "Jean-Luc O'Brien"
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_06", 201, b, s, r)

    def _tc_cus_name_07(self) -> TestResult:
        """Empty string → 422."""
        b = self._body(); b["name"] = ""
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_07", 422, b, s, r)

    def _tc_cus_name_08(self) -> TestResult:
        """Digits only → 422."""
        b = self._body(); b["name"] = "12345"
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_08", 422, b, s, r)

    def _tc_cus_name_09(self) -> TestResult:
        """Symbols only → 422."""
        b = self._body(); b["name"] = "@#$%^&"
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_09", 422, b, s, r)

    def _tc_cus_name_10(self) -> TestResult:
        """Whitespace only → 422."""
        b = self._body(); b["name"] = "      "
        s, r = self._post(b)
        return self._check("TC_CUS_NAME_10", 422, b, s, r)

    # =======================================================================
    #  ADDRESS  (POST)
    # =======================================================================

    def _tc_cus_address_01(self) -> TestResult:
        """4 chars – below minimum → 422."""
        b = self._body(); b["address"] = "12 A"
        s, r = self._post(b)
        return self._check("TC_CUS_ADDRESS_01", 422, b, s, r)

    def _tc_cus_address_02(self) -> TestResult:
        """5 chars – at minimum → 201."""
        b = self._body(); b["address"] = "12345"
        s, r = self._post(b)
        return self._check("TC_CUS_ADDRESS_02", 201, b, s, r)

    def _tc_cus_address_03(self) -> TestResult:
        """255 chars – at maximum → 201."""
        b = self._body(); b["address"] = "A" * 255
        s, r = self._post(b)
        return self._check("TC_CUS_ADDRESS_03", 201, b, s, r)

    def _tc_cus_address_04(self) -> TestResult:
        """256 chars – above maximum → 422."""
        b = self._body(); b["address"] = "A" * 256
        s, r = self._post(b)
        return self._check("TC_CUS_ADDRESS_04", 422, b, s, r)

    def _tc_cus_address_05(self) -> TestResult:
        """Empty string → 422."""
        b = self._body(); b["address"] = ""
        s, r = self._post(b)
        return self._check("TC_CUS_ADDRESS_05", 422, b, s, r)

    def _tc_cus_address_06(self) -> TestResult:
        """Whitespace only → 422."""
        b = self._body(); b["address"] = "         "
        s, r = self._post(b)
        return self._check("TC_CUS_ADDRESS_06", 422, b, s, r)

    def _tc_cus_address_07(self) -> TestResult:
        """Ordinary full address → 201."""
        b = self._body(); b["address"] = "123 Nguyen Trai, Thanh Xuan, Hanoi"
        s, r = self._post(b)
        return self._check("TC_CUS_ADDRESS_07", 201, b, s, r)

    # =======================================================================
    #  PHONE  (POST)
    # =======================================================================

    def _tc_cus_phone_01(self) -> TestResult:
        """7 digits – below minimum → 422."""
        b = self._body(); b["phone"] = "+8412345"
        s, r = self._post(b)
        return self._check("TC_CUS_PHONE_01", 422, b, s, r)

    def _tc_cus_phone_02(self) -> TestResult:
        """8 digits – at minimum → 201."""
        b = self._body(); b["phone"] = "+84912345"
        s, r = self._post(b)
        return self._check("TC_CUS_PHONE_02", 201, b, s, r)

    def _tc_cus_phone_03(self) -> TestResult:
        """15 digits – at maximum → 201."""
        b = self._body(); b["phone"] = "+841234567890123"
        s, r = self._post(b)
        return self._check("TC_CUS_PHONE_03", 201, b, s, r)

    def _tc_cus_phone_04(self) -> TestResult:
        """16 digits – above maximum → 422."""
        b = self._body(); b["phone"] = "+8412345678901234"
        s, r = self._post(b)
        return self._check("TC_CUS_PHONE_04", 422, b, s, r)

    def _tc_cus_phone_05(self) -> TestResult:
        """E.164 without leading + → 201."""
        b = self._body(); b["phone"] = "84912345678"
        s, r = self._post(b)
        return self._check("TC_CUS_PHONE_05", 201, b, s, r)

    def _tc_cus_phone_06(self) -> TestResult:
        """Contains letters → 422."""
        b = self._body(); b["phone"] = "+849abc45678"
        s, r = self._post(b)
        return self._check("TC_CUS_PHONE_06", 422, b, s, r)

    def _tc_cus_phone_07(self) -> TestResult:
        """Leading zero after country code → 422."""
        b = self._body(); b["phone"] = "+8401234567"
        s, r = self._post(b)
        return self._check("TC_CUS_PHONE_07", 422, b, s, r)

    def _tc_cus_phone_08(self) -> TestResult:
        """Empty / null → 422."""
        b = self._body(); b["phone"] = ""
        s, r = self._post(b)
        return self._check("TC_CUS_PHONE_08", 422, b, s, r)

    # =======================================================================
    #  BANKING DETAILS – accountNumber  (POST)
    # =======================================================================

    def _tc_cus_bankacctnu_01(self) -> TestResult:
        """5 digits – below minimum → 422."""
        b = self._body(); b["bankingDetails"]["accountNumber"] = "12345"
        s, r = self._post(b)
        return self._check("TC_CUS_BANKACCTNU_01", 422, b, s, r)

    def _tc_cus_bankacctnu_02(self) -> TestResult:
        """6 digits – at minimum → 201."""
        b = self._body(); b["bankingDetails"]["accountNumber"] = "123456"
        s, r = self._post(b)
        return self._check("TC_CUS_BANKACCTNU_02", 201, b, s, r)

    def _tc_cus_bankacctnu_03(self) -> TestResult:
        """20 digits – at maximum → 201."""
        b = self._body(); b["bankingDetails"]["accountNumber"] = "1" * 20
        s, r = self._post(b)
        return self._check("TC_CUS_BANKACCTNU_03", 201, b, s, r)

    def _tc_cus_bankacctnu_04(self) -> TestResult:
        """21 digits – above maximum → 422."""
        b = self._body(); b["bankingDetails"]["accountNumber"] = "1" * 21
        s, r = self._post(b)
        return self._check("TC_CUS_BANKACCTNU_04", 422, b, s, r)

    def _tc_cus_bankacctnu_05(self) -> TestResult:
        """Contains letters → 422."""
        b = self._body(); b["bankingDetails"]["accountNumber"] = "12ab56"
        s, r = self._post(b)
        return self._check("TC_CUS_BANKACCTNU_05", 422, b, s, r)

    def _tc_cus_bankacctnu_06(self) -> TestResult:
        """Empty string → 422."""
        b = self._body(); b["bankingDetails"]["accountNumber"] = ""
        s, r = self._post(b)
        return self._check("TC_CUS_BANKACCTNU_06", 422, b, s, r)

    # =======================================================================
    #  BANKING DETAILS – bankName  (POST)
    # =======================================================================

    def _tc_cus_bankname_01(self) -> TestResult:
        """1 char – below minimum → 422."""
        b = self._body(); b["bankingDetails"]["bankName"] = "A"
        s, r = self._post(b)
        return self._check("TC_CUS_BANKNAME_01", 422, b, s, r)

    def _tc_cus_bankname_02(self) -> TestResult:
        """2 chars – at minimum → 201."""
        b = self._body(); b["bankingDetails"]["bankName"] = "VP"
        s, r = self._post(b)
        return self._check("TC_CUS_BANKNAME_02", 201, b, s, r)

    def _tc_cus_bankname_03(self) -> TestResult:
        """100 chars – at maximum → 201."""
        b = self._body(); b["bankingDetails"]["bankName"] = "A" * 100
        s, r = self._post(b)
        return self._check("TC_CUS_BANKNAME_03", 201, b, s, r)

    def _tc_cus_bankname_04(self) -> TestResult:
        """101 chars – above maximum → 422."""
        b = self._body(); b["bankingDetails"]["bankName"] = "A" * 101
        s, r = self._post(b)
        return self._check("TC_CUS_BANKNAME_04", 422, b, s, r)

    def _tc_cus_bankname_05(self) -> TestResult:
        """Empty string → 422."""
        b = self._body(); b["bankingDetails"]["bankName"] = ""
        s, r = self._post(b)
        return self._check("TC_CUS_BANKNAME_05", 422, b, s, r)

    def _tc_cus_bankname_06(self) -> TestResult:
        """Realistic bank name → 201."""
        b = self._body(); b["bankingDetails"]["bankName"] = "Vietcombank"
        s, r = self._post(b)
        return self._check("TC_CUS_BANKNAME_06", 201, b, s, r)

    # =======================================================================
    #  ROLE  (POST)
    # =======================================================================

    def _tc_cus_role_01(self) -> TestResult:
        """CUSTOMER → 201."""
        b = self._body(); b["role"] = "CUSTOMER"
        s, r = self._post(b)
        return self._check("TC_CUS_ROLE_01", 201, b, s, r)

    def _tc_cus_role_02(self) -> TestResult:
        """ORDER_STAFF → 201."""
        b = self._body(); b["role"] = "ORDER_STAFF"
        s, r = self._post(b)
        return self._check("TC_CUS_ROLE_02", 201, b, s, r)

    def _tc_cus_role_03(self) -> TestResult:
        """ACCOUNTANT → 201."""
        b = self._body(); b["role"] = "ACCOUNTANT"
        s, r = self._post(b)
        return self._check("TC_CUS_ROLE_03", 201, b, s, r)

    def _tc_cus_role_04(self) -> TestResult:
        """Unknown enum value → 422."""
        b = self._body(); b["role"] = "MANAGER"
        s, r = self._post(b)
        return self._check("TC_CUS_ROLE_04", 422, b, s, r)

    def _tc_cus_role_05(self) -> TestResult:
        """Wrong case → 422."""
        b = self._body(); b["role"] = "customer"
        s, r = self._post(b)
        return self._check("TC_CUS_ROLE_05", 422, b, s, r)

    def _tc_cus_role_06(self) -> TestResult:
        """Empty / null → 422."""
        b = self._body(); b["role"] = ""
        s, r = self._post(b)
        return self._check("TC_CUS_ROLE_06", 422, b, s, r)

    # =======================================================================
    #  ORDER HISTORY  (POST – read-only / server-derived field)
    # =======================================================================

    def _tc_cus_orderhist_01(self) -> TestResult:
        """Empty array → 201."""
        b = self._body(); b["orderHistory"] = []
        s, r = self._post(b)
        return self._check("TC_CUS_ORDERHIST_01", 201, b, s, r)

    def _tc_cus_orderhist_02(self) -> TestResult:
        """Malformed UUID in array → 422."""
        b = self._body(); b["orderHistory"] = ["not-a-uuid"]
        s, r = self._post(b)
        return self._check("TC_CUS_ORDERHIST_02", 422, b, s, r)

    def _tc_cus_orderhist_03(self) -> TestResult:
        """Client-supplied read-only field → 422."""
        b = self._body()
        b["orderHistory"] = ["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
        s, r = self._post(b)
        return self._check("TC_CUS_ORDERHIST_03", 422, b, s, r)