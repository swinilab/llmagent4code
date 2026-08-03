"""Shared validators enforcing the Field Constraint Table exactly.

Every rule in the table is implemented here or in the entity schemas as real
validation logic. Numeric boundaries and regexes are honoured precisely: values
are rejected rather than rounded, truncated, or relaxed.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ConfigDict

# `\p{L}` is a Unicode property escape that `re` does not support; the explicit
# category test in `_is_letter` provides the same semantics.
_NAME_ALLOWED_PUNCT = set(" .'-")
_BANK_NAME_ALLOWED_PUNCT = set(" .&-")

PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{7,14}$")
ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{6,20}$")
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")
PRODUCT_AMOUNT_PATTERN = re.compile(r"^\d{1,6}\.\d{2}$")
TOTAL_AMOUNT_PATTERN = re.compile(r"^\d{1,8}\.\d{2}$")

DATE_FORMAT = "%d/%m/%Y"


class StrictModel(BaseModel):
    """Rejects unknown keys, which is how client-supplied read-only, computed,
    server-generated, and snapshot fields become HTTP 400."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


def _is_letter(char: str) -> bool:
    return char.isalpha()


def validate_name(value: Any, field: str = "name") -> str:
    """`^[\\p{L} .'-]+$`, length 2-100, not blank or whitespace-only."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must not be blank or whitespace-only")
    if not (2 <= len(value) <= 100):
        raise ValueError(f"{field} must be between 2 and 100 characters")
    for char in value:
        if not (_is_letter(char) or char in _NAME_ALLOWED_PUNCT):
            raise ValueError(f"{field} contains an unsupported character: {char!r}")
    return value


def validate_bank_name(value: Any) -> str:
    """`^[\\p{L}0-9 .&-]+$`, length 2-100."""
    if not isinstance(value, str):
        raise ValueError("bankName must be a string")
    if not value.strip():
        raise ValueError("bankName must not be blank or whitespace-only")
    if not (2 <= len(value) <= 100):
        raise ValueError("bankName must be between 2 and 100 characters")
    for char in value:
        if not (_is_letter(char) or char.isdigit() or char in _BANK_NAME_ALLOWED_PUNCT):
            raise ValueError(f"bankName contains an unsupported character: {char!r}")
    return value


def validate_address(value: Any) -> str:
    """Free text, length 5-255, not blank or whitespace-only."""
    if not isinstance(value, str):
        raise ValueError("address must be a string")
    if not value.strip():
        raise ValueError("address must not be blank or whitespace-only")
    if not (5 <= len(value) <= 255):
        raise ValueError("address must be between 5 and 255 characters")
    return value


def validate_description(value: Any) -> str:
    """Free text, length 3-500, not blank or whitespace-only."""
    if not isinstance(value, str):
        raise ValueError("description must be a string")
    if not value.strip():
        raise ValueError("description must not be blank or whitespace-only")
    if not (3 <= len(value) <= 500):
        raise ValueError("description must be between 3 and 500 characters")
    return value


def validate_phone(value: Any) -> str:
    """E.164: `^\\+?[1-9]\\d{7,14}$`, 8-15 digits, no leading zero."""
    if not isinstance(value, str):
        raise ValueError("phone must be a string")
    if not PHONE_PATTERN.match(value):
        raise ValueError("phone must match E.164 format ^\\+?[1-9]\\d{7,14}$")
    digits = value[1:] if value.startswith("+") else value
    if not (8 <= len(digits) <= 15):
        raise ValueError("phone must contain between 8 and 15 digits")
    return value


def validate_account_number(value: Any) -> str:
    """`^\\d{6,20}$`. Never logged anywhere in the application."""
    if not isinstance(value, str):
        raise ValueError("accountNumber must be a string")
    if not ACCOUNT_NUMBER_PATTERN.match(value):
        raise ValueError("accountNumber must be 6 to 20 digits")
    return value


def _decimal_from_input(value: Any, field: str) -> Decimal:
    """Accept only exact 2-decimal-place representations.

    JSON floats are rejected outright: binary floating point cannot represent
    money exactly, and silently accepting one would violate the no-rounding rule.
    """
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a decimal amount")
    if isinstance(value, float):
        raise ValueError(
            f"{field} must be sent as a string or exact decimal with exactly 2 decimal places"
        )
    if isinstance(value, int):
        raise ValueError(f"{field} must have exactly 2 decimal places")
    if isinstance(value, Decimal):
        text = format(value, "f")
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ValueError(f"{field} must be a decimal amount")
    try:
        Decimal(text)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} is not a valid decimal amount") from None
    return Decimal(text)


def validate_product_amount(value: Any) -> Decimal:
    """`^\\d{1,6}\\.\\d{2}$`, 0.01 - 999999.99, exactly 2 decimal places."""
    text = format(_decimal_from_input(value, "price.amount"), "f")
    if not PRODUCT_AMOUNT_PATTERN.match(text):
        raise ValueError("price.amount must match ^\\d{1,6}\\.\\d{2}$ with exactly 2 decimal places")
    amount = Decimal(text)
    if amount < Decimal("0.01") or amount > Decimal("999999.99"):
        raise ValueError("price.amount must be between 0.01 and 999999.99")
    return amount


def validate_total_amount(value: Any, field: str = "amount") -> Decimal:
    """`^\\d{1,8}\\.\\d{2}$`, 0.01 - 99999999.99, exactly 2 decimal places."""
    text = format(_decimal_from_input(value, field), "f")
    if not TOTAL_AMOUNT_PATTERN.match(text):
        raise ValueError(f"{field} must match ^\\d{{1,8}}\\.\\d{{2}}$ with exactly 2 decimal places")
    amount = Decimal(text)
    if amount < Decimal("0.01") or amount > Decimal("99999999.99"):
        raise ValueError(f"{field} must be between 0.01 and 99999999.99")
    return amount


def validate_quantity(value: Any) -> int:
    """Whole number, 1 - 1000."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("quantity must be a whole number")
    if not (1 <= value <= 1000):
        raise ValueError("quantity must be between 1 and 1000")
    return value


def parse_calendar_date(value: Any, field: str) -> date:
    """Two independent layers: `dd/MM/yyyy` regex, then calendar validity.

    Rejects values such as 31/02/2026 that satisfy the regex but name no real
    calendar date.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string in dd/MM/yyyy format")
    if not DATE_PATTERN.match(value):
        raise ValueError(f"{field} must match dd/MM/yyyy")
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        raise ValueError(f"{field} is not a real calendar date") from None


def format_calendar_date(value: date) -> str:
    return value.strftime(DATE_FORMAT)


def format_amount(value: Decimal) -> str:
    """Render money with exactly two decimal places, never as a float."""
    return f"{Decimal(value):.2f}"
