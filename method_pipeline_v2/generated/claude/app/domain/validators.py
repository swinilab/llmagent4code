"""Reusable field validators implementing the Field Constraint Table.

Composition over inheritance: these are annotated types shared by every DTO
rather than a base-model hierarchy. Each one encodes a rule from the table
verbatim so BVA/EP boundaries hold exactly - no rounding, no coercion, no
relaxation (Implementation notes 3-5).
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any
from uuid import UUID

from pydantic import AfterValidator, BeforeValidator, Field, StringConstraints

# --- regexes, verbatim from the Field Constraint Table ------------------------
# The table's `\p{L}` classes have no equivalent in Python's stdlib `re`, so the
# name/bank-name rules are enforced by the character-wise validators below
# (str.isalpha() is unicode-aware and is the faithful `\p{L}` equivalent).
PHONE_REGEX = re.compile(r"^\+?[1-9]\d{7,14}$")
ACCOUNT_NUMBER_REGEX = re.compile(r"^\d{6,20}$")
CURRENCY_REGEX = re.compile(r"^[A-Z]{3}$")
PRODUCT_PRICE_REGEX = re.compile(r"^\d{1,6}\.\d{2}$")
MONEY_8_REGEX = re.compile(r"^\d{1,8}\.\d{2}$")
DATE_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4}$")
QUANTITY_REGEX = re.compile(r"^\d+$")


def _validate_unicode_name(value: str) -> str:
    """`^[\\p{L} .'-]+$` - unicode letters, space, dot, apostrophe, hyphen."""
    if not value or not value.strip():
        raise ValueError("must not be blank or whitespace-only")
    for ch in value:
        if not (ch.isalpha() or ch in " .'-"):
            raise ValueError("contains characters outside ^[\\p{L} .'-]+$")
    return value


def _validate_bank_name(value: str) -> str:
    """`^[\\p{L}0-9 .&-]+$`."""
    if not value or not value.strip():
        raise ValueError("must not be blank or whitespace-only")
    for ch in value:
        if not (ch.isalnum() or ch in " .&-"):
            raise ValueError("contains characters outside ^[\\p{L}0-9 .&-]+$")
    return value


def _not_blank(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("must not be blank or whitespace-only")
    return value


def _validate_phone(value: str) -> str:
    """E.164: optional +, first digit 1-9, total 8-15 digits."""
    if not PHONE_REGEX.match(value):
        raise ValueError("must match E.164 ^\\+?[1-9]\\d{7,14}$")
    return value


def _make_money_validator(pattern: re.Pattern[str], lo: Decimal, hi: Decimal):
    """Build a decimal validator enforcing exactly 2dp within [lo, hi].

    Rejects extra precision instead of rounding (Implementation note 5). The
    raw string form is checked *before* Decimal conversion so that values like
    ``1.005`` cannot slip through as ``1.00``.
    """

    def _validate(value: Any) -> Decimal:
        if isinstance(value, float):
            raise ValueError(
                "float is not accepted for monetary values; send a string with exactly 2 decimals"
            )
        raw = str(value).strip()
        if not pattern.match(raw):
            raise ValueError(f"must match {pattern.pattern} (exactly 2 decimal places)")
        try:
            amount = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError("not a valid decimal") from exc
        if amount < lo:
            raise ValueError(f"must be >= {lo}")
        if amount > hi:
            raise ValueError(f"must be <= {hi}")
        return amount

    return _validate


def _validate_ddmmyyyy(value: Any) -> date:
    """Two independent layers: regex format, then calendar validity."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    raw = str(value).strip()
    if not DATE_REGEX.match(raw):
        raise ValueError("must match dd/MM/yyyy")
    try:
        return datetime.strptime(raw, "%d/%m/%Y").date()
    except ValueError as exc:
        raise ValueError("not a real calendar date") from exc


def _validate_uuid4_str(value: Any) -> UUID:
    """Format validation only; existence is checked in the service layer (400 vs 404)."""
    if isinstance(value, UUID):
        return value
    raw = str(value).strip()
    if len(raw) != 36:
        raise ValueError("UUID must be 36 characters")
    try:
        parsed = UUID(raw)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("malformed UUID") from exc
    if parsed.version != 4:
        raise ValueError("must be a UUIDv4")
    return parsed


def _validate_quantity(value: Any) -> int:
    """Whole number 1..1000; rejects bools, floats and numeric strings with a point."""
    if isinstance(value, bool):
        raise ValueError("must be a whole number")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("must be a whole number")
    raw = str(value).strip()
    if isinstance(value, str) and not QUANTITY_REGEX.match(raw):
        raise ValueError("must match ^\\d+$")
    try:
        qty = int(Decimal(raw))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("must be an integer") from exc
    if qty < 1:
        raise ValueError("must be >= 1")
    if qty > 1000:
        raise ValueError("must be <= 1000")
    return qty


# --- exported annotated types -------------------------------------------------

PersonName = Annotated[
    str, StringConstraints(min_length=2, max_length=100), AfterValidator(_validate_unicode_name)
]
Address = Annotated[
    str, StringConstraints(min_length=5, max_length=255), AfterValidator(_not_blank)
]
Phone = Annotated[
    str, StringConstraints(min_length=8, max_length=16), AfterValidator(_validate_phone)
]
AccountNumber = Annotated[str, Field(pattern=r"^\d{6,20}$", min_length=6, max_length=20)]
BankName = Annotated[
    str, StringConstraints(min_length=2, max_length=100), AfterValidator(_validate_bank_name)
]
ProductDescription = Annotated[
    str, StringConstraints(min_length=3, max_length=500), AfterValidator(_not_blank)
]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$", min_length=3, max_length=3)]

ProductPrice = Annotated[
    Decimal,
    BeforeValidator(_make_money_validator(PRODUCT_PRICE_REGEX, Decimal("0.01"), Decimal("999999.99"))),
]
OrderMoney = Annotated[
    Decimal,
    BeforeValidator(_make_money_validator(MONEY_8_REGEX, Decimal("0.01"), Decimal("99999999.99"))),
]
Quantity = Annotated[int, BeforeValidator(_validate_quantity)]
DdMmYyyyDate = Annotated[date, BeforeValidator(_validate_ddmmyyyy)]
Uuid4 = Annotated[UUID, BeforeValidator(_validate_uuid4_str)]


def format_ddmmyyyy(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def format_money(value: Decimal) -> str:
    """Always render exactly 2dp so responses round-trip through the validators."""
    return f"{value.quantize(Decimal('0.01')):f}"
