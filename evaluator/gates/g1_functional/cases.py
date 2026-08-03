"""Functional test cases derived from the Field Constraint Table.

Written fresh against prompts/generate.md rather than adapted from the earlier
ITestGroup suite, for two reasons that would otherwise corrupt the results:

  * the old suite expects HTTP 422 for validation failures, while the
    specification handed to the agents mandates 400. Reusing it would fail all
    three applications on a criterion they were never given.

  * the old suite is internally inconsistent about read-only fields -- it
    accepts an empty client-supplied orderHistory but rejects a populated one.
    The specification rejects any client-supplied read-only field outright.

Cases are declared as data rather than one method per case. A boundary is then
a row -- min-1, min, max, max+1 -- which makes it visible at a glance that every
constrained field really got its four boundary probes, and makes a missing probe
a visible gap rather than a method nobody noticed was absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# Status codes, per the specification's validation contract.
OK_CREATE = 201
OK_READ = 200
BAD_REQUEST = 400        # malformed syntax or field-constraint violation
NOT_FOUND = 404          # well-formed identifier, no such resource
CONFLICT = 409           # referential state / illegal transition


@dataclass(frozen=True)
class Case:
    """One functional probe.

    `mutate` receives a deep copy of the entity's valid body and alters it in
    place; returning a new object is unnecessary. `partition` records which
    equivalence class or boundary the case covers so the results table can be
    grouped by intent rather than by case name.
    """

    id: str
    entity: str
    partition: str
    expected_status: int
    mutate: Callable[[dict[str, Any]], None] | None = None
    description: str = ""
    # Set for cases that probe GET rather than POST.
    get_id: str | None = None


def _set(path: str, value: Any) -> Callable[[dict[str, Any]], None]:
    """Build a mutator for a dotted field path, e.g. bankingDetails.bankName."""

    def apply(body: dict[str, Any]) -> None:
        parts = path.split(".")
        cursor: Any = body
        for p in parts[:-1]:
            cursor = cursor.setdefault(p, {})
        cursor[parts[-1]] = value

    return apply


def _drop(path: str) -> Callable[[dict[str, Any]], None]:
    """Build a mutator that removes a field, for required-field probes."""

    def apply(body: dict[str, Any]) -> None:
        parts = path.split(".")
        cursor: Any = body
        for p in parts[:-1]:
            cursor = cursor.get(p, {})
            if not isinstance(cursor, dict):
                return
        cursor.pop(parts[-1], None)

    return apply


def _length_boundaries(
    entity: str, prefix: str, path: str, lo: int, hi: int, filler: str = "a"
) -> list[Case]:
    """Four probes around an inclusive [lo, hi] string-length constraint.

    Below-minimum and above-maximum must be rejected; the two endpoints
    themselves must be accepted. Testing only the endpoints would pass an
    implementation that is off by one in either direction.
    """
    return [
        Case(f"{prefix}_LEN_BELOW", entity, f"{path} length {lo - 1} (below min)",
             BAD_REQUEST, _set(path, filler * (lo - 1))),
        Case(f"{prefix}_LEN_MIN", entity, f"{path} length {lo} (at min)",
             OK_CREATE, _set(path, filler * lo)),
        Case(f"{prefix}_LEN_MAX", entity, f"{path} length {hi} (at max)",
             OK_CREATE, _set(path, filler * hi)),
        Case(f"{prefix}_LEN_ABOVE", entity, f"{path} length {hi + 1} (above max)",
             BAD_REQUEST, _set(path, filler * (hi + 1))),
    ]


def _blank_and_missing(entity: str, prefix: str, path: str) -> list[Case]:
    return [
        Case(f"{prefix}_EMPTY", entity, f"{path} empty string", BAD_REQUEST, _set(path, "")),
        Case(f"{prefix}_BLANK", entity, f"{path} whitespace only", BAD_REQUEST, _set(path, "    ")),
        Case(f"{prefix}_MISSING", entity, f"{path} absent", BAD_REQUEST, _drop(path)),
        Case(f"{prefix}_NULL", entity, f"{path} null", BAD_REQUEST, _set(path, None)),
    ]


# ── valid bodies ──────────────────────────────────────────────────────────
# Each is the "valid seed" every negative case mutates away from. Values sit
# comfortably inside every constraint so that a failure is attributable to the
# single field the case changed.

VALID_BODIES: dict[str, dict[str, Any]] = {
    "customer": {
        "name": "Nguyen Van An",
        "address": "123 Nguyen Trai, Thanh Xuan, Hanoi",
        "phone": "+84912345678",
        "bankingDetails": {"accountNumber": "1234567890", "bankName": "Vietcombank"},
        "role": "CUSTOMER",
    },
    "product": {
        "description": "Standard evaluation product",
        "price": {"amount": "19.99", "currency": "USD"},
    },
}


# ── Customer ──────────────────────────────────────────────────────────────

def customer_cases() -> list[Case]:
    e, p = "customer", "TC_CUS"
    cases: list[Case] = [
        Case(f"{p}_VALID", e, "valid creation", OK_CREATE, None,
             "baseline: the seed body must be accepted"),
    ]

    # name: 2-100, ^[\p{L} .'-]+$
    cases += _length_boundaries(e, f"{p}_NAME", "name", 2, 100, "A")
    cases += _blank_and_missing(e, f"{p}_NAME", "name")
    cases += [
        Case(f"{p}_NAME_UNICODE", e, "name with non-ASCII letters", OK_CREATE,
             _set("name", "Nguyễn Văn Ánh"),
             "the pattern is \\p{L}, so Unicode letters must be accepted"),
        Case(f"{p}_NAME_PUNCT", e, "name with hyphen and apostrophe", OK_CREATE,
             _set("name", "Jean-Luc O'Brien")),
        Case(f"{p}_NAME_DIGITS", e, "name containing digits", BAD_REQUEST,
             _set("name", "Nguyen 123")),
        Case(f"{p}_NAME_SYMBOLS", e, "name of symbols only", BAD_REQUEST,
             _set("name", "@#$%^&")),
    ]

    # address: 5-255, free text
    cases += _length_boundaries(e, f"{p}_ADDR", "address", 5, 255)
    cases += _blank_and_missing(e, f"{p}_ADDR", "address")

    # phone: E.164, ^\+?[1-9]\d{7,14}$
    cases += [
        Case(f"{p}_PHONE_MIN", e, "8 digits (at min)", OK_CREATE, _set("phone", "+12345678")),
        Case(f"{p}_PHONE_BELOW", e, "7 digits (below min)", BAD_REQUEST, _set("phone", "+1234567")),
        Case(f"{p}_PHONE_MAX", e, "15 digits (at max)", OK_CREATE, _set("phone", "+123456789012345")),
        Case(f"{p}_PHONE_ABOVE", e, "16 digits (above max)", BAD_REQUEST,
             _set("phone", "+1234567890123456")),
        Case(f"{p}_PHONE_NO_PLUS", e, "no leading plus", OK_CREATE, _set("phone", "84912345678"),
             "the plus is optional in the pattern"),
        Case(f"{p}_PHONE_LEADING_ZERO", e, "leading zero", BAD_REQUEST, _set("phone", "+0912345678"),
             "pattern requires [1-9] first"),
        Case(f"{p}_PHONE_LETTERS", e, "letters in phone", BAD_REQUEST, _set("phone", "+849abc4567")),
        Case(f"{p}_PHONE_EMPTY", e, "empty phone", BAD_REQUEST, _set("phone", "")),
        Case(f"{p}_PHONE_MISSING", e, "phone absent", BAD_REQUEST, _drop("phone")),
    ]

    # bankingDetails.accountNumber: 6-20 digits
    cases += _length_boundaries(e, f"{p}_ACCT", "bankingDetails.accountNumber", 6, 20, "1")
    cases += [
        Case(f"{p}_ACCT_LETTERS", e, "account number with letters", BAD_REQUEST,
             _set("bankingDetails.accountNumber", "12ab56")),
        Case(f"{p}_ACCT_EMPTY", e, "account number empty", BAD_REQUEST,
             _set("bankingDetails.accountNumber", "")),
        Case(f"{p}_ACCT_MISSING", e, "account number absent", BAD_REQUEST,
             _drop("bankingDetails.accountNumber")),
        Case(f"{p}_BANKING_MISSING", e, "bankingDetails absent entirely", BAD_REQUEST,
             _drop("bankingDetails")),
    ]

    # bankingDetails.bankName: 2-100
    cases += _length_boundaries(e, f"{p}_BANKNAME", "bankingDetails.bankName", 2, 100, "A")
    cases += [
        Case(f"{p}_BANKNAME_EMPTY", e, "bank name empty", BAD_REQUEST,
             _set("bankingDetails.bankName", "")),
    ]

    # role: strict, case-sensitive allow-list
    cases += [
        Case(f"{p}_ROLE_CUSTOMER", e, "role CUSTOMER", OK_CREATE, _set("role", "CUSTOMER")),
        Case(f"{p}_ROLE_STAFF", e, "role ORDER_STAFF", OK_CREATE, _set("role", "ORDER_STAFF")),
        Case(f"{p}_ROLE_ACCOUNTANT", e, "role ACCOUNTANT", OK_CREATE, _set("role", "ACCOUNTANT")),
        Case(f"{p}_ROLE_UNKNOWN", e, "role not in allow-list", BAD_REQUEST, _set("role", "MANAGER")),
        Case(f"{p}_ROLE_LOWERCASE", e, "role wrong case", BAD_REQUEST, _set("role", "customer"),
             "enum matching is case-sensitive"),
        Case(f"{p}_ROLE_EMPTY", e, "role empty", BAD_REQUEST, _set("role", "")),
        Case(f"{p}_ROLE_MISSING", e, "role absent", BAD_REQUEST, _drop("role")),
    ]

    # orderHistory is read-only and server-derived: supplying it at all is a 400.
    cases += [
        Case(f"{p}_ORDERHIST_SUPPLIED", e, "client supplies read-only orderHistory",
             BAD_REQUEST, _set("orderHistory", ["3fa85f64-5717-4562-b3fc-2c963f66afa6"])),
        Case(f"{p}_ORDERHIST_EMPTY", e, "client supplies empty orderHistory",
             BAD_REQUEST, _set("orderHistory", []),
             "read-only fields are rejected regardless of value"),
        Case(f"{p}_ID_SUPPLIED", e, "client supplies server-generated id",
             BAD_REQUEST, _set("id", "3fa85f64-5717-4562-b3fc-2c963f66afa6")),
    ]

    return cases


# ── Product ───────────────────────────────────────────────────────────────

def product_cases() -> list[Case]:
    e, p = "product", "TC_PRD"
    cases: list[Case] = [
        Case(f"{p}_VALID", e, "valid creation", OK_CREATE, None),
    ]

    # description: 3-500
    cases += _length_boundaries(e, f"{p}_DESC", "description", 3, 500)
    cases += _blank_and_missing(e, f"{p}_DESC", "description")

    # price.amount: 0.01 - 999999.99, exactly two decimal places
    cases += [
        Case(f"{p}_AMT_MIN", e, "amount at minimum 0.01", OK_CREATE,
             _set("price.amount", "0.01")),
        Case(f"{p}_AMT_ZERO", e, "amount 0.00 (below min)", BAD_REQUEST,
             _set("price.amount", "0.00")),
        Case(f"{p}_AMT_NEGATIVE", e, "negative amount", BAD_REQUEST,
             _set("price.amount", "-1.00")),
        Case(f"{p}_AMT_MAX", e, "amount at maximum", OK_CREATE,
             _set("price.amount", "999999.99")),
        Case(f"{p}_AMT_ABOVE", e, "amount above maximum", BAD_REQUEST,
             _set("price.amount", "1000000.00")),
        Case(f"{p}_AMT_THREE_DP", e, "three decimal places", BAD_REQUEST,
             _set("price.amount", "19.999"),
             "excess precision is rejected, never silently rounded"),
        Case(f"{p}_AMT_ONE_DP", e, "one decimal place", BAD_REQUEST,
             _set("price.amount", "19.9"),
             "exactly two decimal places are required"),
        Case(f"{p}_AMT_NO_DP", e, "no decimal places", BAD_REQUEST,
             _set("price.amount", "19")),
        Case(f"{p}_AMT_TEXT", e, "non-numeric amount", BAD_REQUEST,
             _set("price.amount", "nineteen")),
        Case(f"{p}_AMT_MISSING", e, "amount absent", BAD_REQUEST, _drop("price.amount")),
    ]

    # price.currency: ISO 4217, restricted allow-list
    cases += [
        Case(f"{p}_CUR_USD", e, "currency USD", OK_CREATE, _set("price.currency", "USD")),
        Case(f"{p}_CUR_VND", e, "currency VND", OK_CREATE, _set("price.currency", "VND")),
        Case(f"{p}_CUR_EUR", e, "currency EUR", OK_CREATE, _set("price.currency", "EUR")),
        Case(f"{p}_CUR_UNSUPPORTED", e, "valid ISO code outside allow-list", BAD_REQUEST,
             _set("price.currency", "GBP"),
             "well-formed but not in the supported list"),
        Case(f"{p}_CUR_LOWERCASE", e, "currency wrong case", BAD_REQUEST,
             _set("price.currency", "usd")),
        Case(f"{p}_CUR_TOO_SHORT", e, "two-letter currency", BAD_REQUEST,
             _set("price.currency", "US")),
        Case(f"{p}_CUR_MISSING", e, "currency absent", BAD_REQUEST, _drop("price.currency")),
        Case(f"{p}_PRICE_MISSING", e, "price object absent", BAD_REQUEST, _drop("price")),
        Case(f"{p}_ID_SUPPLIED", e, "client supplies server-generated id", BAD_REQUEST,
             _set("id", "3fa85f64-5717-4562-b3fc-2c963f66afa6")),
    ]

    return cases


# ── identifier handling, applied to every entity ──────────────────────────

def identifier_cases(entity: str) -> list[Case]:
    """GET probes shared by all five entities.

    The three-way split -- malformed 400, unknown 404, existing 200 -- is the
    specification's central identifier rule and is checked per entity because
    an application can easily get it right on one router and wrong on another.
    """
    prefix = f"TC_{entity[:3].upper()}_ID"
    return [
        Case(f"{prefix}_MALFORMED", entity, "malformed UUID", BAD_REQUEST,
             get_id="not-a-uuid-123"),
        Case(f"{prefix}_UNKNOWN", entity, "well-formed unknown UUID", NOT_FOUND,
             get_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"),
        Case(f"{prefix}_TRUNCATED", entity, "truncated UUID", BAD_REQUEST,
             get_id="3fa85f64-5717-4562"),
        Case(f"{prefix}_EXISTING", entity, "existing UUID", OK_READ, get_id="<seeded>"),
    ]


ENTITIES_WITH_ID_CHECKS = ("customer", "product", "order", "payment", "invoice")


def all_creation_cases() -> list[Case]:
    """Creation-time cases for the two entities with no foreign keys.

    Order, Payment and Invoice need a live customer, product and workflow state
    before they can be exercised, so their cases are built at run time by
    relational.py where those identifiers exist.
    """
    return customer_cases() + product_cases()