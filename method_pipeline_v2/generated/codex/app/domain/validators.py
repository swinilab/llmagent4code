"""Reusable, lossless validators for the public OMS JSON contract.

Money is deliberately accepted as a JSON string. JSON numbers do not preserve
whether a sender wrote ``1.20`` or ``1.2``, so accepting them would make the
required exactly-two-decimal rule impossible to enforce.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any
from uuid import RFC_4122, UUID

import phonenumbers
import regex
from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    PlainSerializer,
    StrictStr,
    WithJsonSchema,
)

UUID4_TEXT_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-"
    r"[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
PERSON_NAME_PATTERN = r"^[\p{L} .'-]+$"
PHONE_PATTERN = r"^\+?[1-9]\d{7,14}$"
ACCOUNT_NUMBER_PATTERN = r"^\d{6,20}$"
BANK_NAME_PATTERN = r"^[\p{L}0-9 .&-]+$"
PRODUCT_AMOUNT_PATTERN = r"^\d{1,6}\.\d{2}$"
TOTAL_AMOUNT_PATTERN = r"^\d{1,8}\.\d{2}$"
DATE_DMY_PATTERN = r"^\d{2}/\d{2}/\d{4}$"

_UUID4_TEXT_RE = re.compile(UUID4_TEXT_PATTERN, re.ASCII)
_PERSON_NAME_RE = regex.compile(PERSON_NAME_PATTERN, regex.VERSION1)
_PHONE_RE = re.compile(PHONE_PATTERN, re.ASCII)
_ACCOUNT_NUMBER_RE = re.compile(ACCOUNT_NUMBER_PATTERN, re.ASCII)
_BANK_NAME_RE = regex.compile(BANK_NAME_PATTERN, regex.VERSION1)
_PRODUCT_AMOUNT_RE = re.compile(PRODUCT_AMOUNT_PATTERN, re.ASCII)
_TOTAL_AMOUNT_RE = re.compile(TOTAL_AMOUNT_PATTERN, re.ASCII)
_DATE_DMY_RE = re.compile(DATE_DMY_PATTERN, re.ASCII)


def parse_uuid4(value: Any) -> UUID:
    """Parse only canonical, hyphenated RFC 4122 UUID version 4 values."""

    if isinstance(value, UUID):
        parsed = value
    elif isinstance(value, str) and _UUID4_TEXT_RE.fullmatch(value):
        parsed = UUID(value)
    else:
        raise ValueError("must be a canonical 36-character UUIDv4")
    if parsed.version != 4 or parsed.variant != RFC_4122:
        raise ValueError("must be a UUIDv4")
    return parsed


def serialize_uuid(value: UUID) -> str:
    return str(value)


def validate_person_name(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank or whitespace-only")
    if _PERSON_NAME_RE.fullmatch(value) is None:
        raise ValueError("contains characters outside the allowed name format")
    return value


def validate_address(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank or whitespace-only")
    return value


def validate_phone(value: str) -> str:
    if _PHONE_RE.fullmatch(value) is None:
        raise ValueError("must match E.164 format with 8 to 15 digits")
    if value.startswith("+"):
        try:
            parsed = phonenumbers.parse(value, None)
        except phonenumbers.NumberParseException as exc:
            raise ValueError("must contain a recognized E.164 country code") from exc
        national_digits = value[len(str(parsed.country_code)) + 1 :]
        if national_digits.startswith("0"):
            raise ValueError("must not start with 0 after the country code")
    return value


def validate_account_number(value: str) -> str:
    if _ACCOUNT_NUMBER_RE.fullmatch(value) is None:
        raise ValueError("must contain 6 to 20 ASCII digits")
    return value


def validate_bank_name(value: str) -> str:
    if _BANK_NAME_RE.fullmatch(value) is None:
        raise ValueError("contains characters outside the allowed bank-name format")
    return value


def validate_product_description(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank or whitespace-only")
    return value


def _parse_money(
    value: Any,
    *,
    pattern: re.Pattern[str],
    minimum: Decimal,
    maximum: Decimal,
) -> Decimal:
    if isinstance(value, Decimal):
        text = format(value, "f")
    elif isinstance(value, str):
        text = value
    else:
        raise ValueError("must be a string containing exactly two decimal places")

    if pattern.fullmatch(text) is None:
        raise ValueError("must contain exactly two decimal places")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:  # Defensive; the regex normally excludes this.
        raise ValueError("must be a valid decimal amount") from exc
    if amount < minimum or amount > maximum:
        raise ValueError(f"must be between {minimum} and {maximum}")
    return amount


def parse_product_amount(value: Any) -> Decimal:
    return _parse_money(
        value,
        pattern=_PRODUCT_AMOUNT_RE,
        minimum=Decimal("0.01"),
        maximum=Decimal("999999.99"),
    )


def parse_total_amount(value: Any) -> Decimal:
    return _parse_money(
        value,
        pattern=_TOTAL_AMOUNT_RE,
        minimum=Decimal("0.01"),
        maximum=Decimal("99999999.99"),
    )


def serialize_money(value: Decimal) -> str:
    return format(value, ".2f")


def parse_date_dmy(value: Any) -> date:
    if isinstance(value, datetime):
        raise ValueError("must be a date, not a datetime")
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or _DATE_DMY_RE.fullmatch(value) is None:
        raise ValueError("must use dd/MM/yyyy format")
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as exc:
        raise ValueError("must be a real calendar date") from exc


def serialize_date_dmy(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def parse_utc_datetime(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("must be an ISO 8601 datetime") from exc
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise ValueError("must be an ISO 8601 datetime")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def serialize_utc_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UUID4Value = Annotated[
    UUID,
    BeforeValidator(parse_uuid4),
    PlainSerializer(serialize_uuid, return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "format": "uuid",
            "minLength": 36,
            "maxLength": 36,
            "pattern": UUID4_TEXT_PATTERN,
        }
    ),
]

PersonName = Annotated[
    StrictStr,
    Field(min_length=2, max_length=100),
    AfterValidator(validate_person_name),
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 2,
            "maxLength": 100,
            "pattern": PERSON_NAME_PATTERN,
        }
    ),
]

Address = Annotated[
    StrictStr,
    Field(min_length=5, max_length=255),
    AfterValidator(validate_address),
]

PhoneNumber = Annotated[
    StrictStr,
    AfterValidator(validate_phone),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": PHONE_PATTERN,
            "description": "E.164-compatible number containing 8 to 15 digits.",
        }
    ),
]

AccountNumber = Annotated[
    StrictStr,
    Field(min_length=6, max_length=20),
    AfterValidator(validate_account_number),
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 6,
            "maxLength": 20,
            "pattern": ACCOUNT_NUMBER_PATTERN,
        }
    ),
]

BankName = Annotated[
    StrictStr,
    Field(min_length=2, max_length=100),
    AfterValidator(validate_bank_name),
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 2,
            "maxLength": 100,
            "pattern": BANK_NAME_PATTERN,
        }
    ),
]

ProductDescription = Annotated[
    StrictStr,
    Field(min_length=3, max_length=500),
    AfterValidator(validate_product_description),
]

ProductAmount = Annotated[
    Decimal,
    BeforeValidator(parse_product_amount),
    PlainSerializer(serialize_money, return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": PRODUCT_AMOUNT_PATTERN,
            "minimum": "0.01",
            "maximum": "999999.99",
        }
    ),
]

TotalAmount = Annotated[
    Decimal,
    BeforeValidator(parse_total_amount),
    PlainSerializer(serialize_money, return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": TOTAL_AMOUNT_PATTERN,
            "minimum": "0.01",
            "maximum": "99999999.99",
        }
    ),
]

DateDMY = Annotated[
    date,
    BeforeValidator(parse_date_dmy),
    PlainSerializer(serialize_date_dmy, return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": DATE_DMY_PATTERN,
            "description": "A real calendar date in dd/MM/yyyy format.",
        }
    ),
]

UtcDateTime = Annotated[
    datetime,
    BeforeValidator(parse_utc_datetime),
    PlainSerializer(serialize_utc_datetime, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "format": "date-time"}),
]
