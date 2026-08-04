"""Functional cases the constraint table entails but cannot generate.

Everything mechanical -- boundaries, blanks, enum allow-lists, read-only
rejection -- comes from `common/bva.py` driven by `domain.yaml`. What remains
here are the probes that require reading a constraint rather than parsing it,
and they are the ones most likely to separate a careful implementation from a
plausible one:

  * `^[\\p{L} .'-]+$` means Unicode letters, so `Nguyễn` must be accepted. A
    generator emitting ASCII fillers never discovers an implementation that
    substituted `[A-Za-z]`.
  * `GBP` is a well-formed ISO 4217 code outside the supported list, so format
    validity and membership are two separate rules. A single-layer validator
    passes every generated case and still fails this one.
  * `19.9` sits inside the numeric range but violates "exactly two decimal
    places". Range and precision are independent constraints, and an
    implementation honouring only the range rounds silently.

Each case cites the table row it comes from. That citation is the discipline
that keeps the suite honest: a case that cannot be traced to a row is one the
agent was never asked to satisfy, and scoring it would be scoring a preference.
"""

from __future__ import annotations

from ...common.bva import BAD_REQUEST, OK_CREATE, Case, set_field


def customer_cases() -> list[Case]:
    e, p = "customer", "TC_CUS"
    return [
        # name -- Format/Regex: ^[\p{L} .'-]+$
        Case(f"{p}_NAME_UNICODE", e, "name with non-ASCII letters", OK_CREATE,
             set_field("name", "Nguyễn Văn Ánh"),
             r"\p{L} is Unicode letters, not [A-Za-z]"),
        Case(f"{p}_NAME_PUNCT", e, "name with hyphen and apostrophe", OK_CREATE,
             set_field("name", "Jean-Luc O'Brien"),
             "the character class admits . ' and -"),
        Case(f"{p}_NAME_DIGITS", e, "name containing digits", BAD_REQUEST,
             set_field("name", "Nguyen 123"),
             "digits are outside the class"),
        Case(f"{p}_NAME_SYMBOLS", e, "name of symbols only", BAD_REQUEST,
             set_field("name", "@#$%^&")),

        # phone -- E.164: ^\+?[1-9]\d{7,14}$
        # Length is in digits, not characters, so the generic length generator
        # would produce the wrong probes for this field.
        Case(f"{p}_PHONE_MIN", e, "8 digits (at min)", OK_CREATE,
             set_field("phone", "+12345678")),
        Case(f"{p}_PHONE_BELOW", e, "7 digits (below min)", BAD_REQUEST,
             set_field("phone", "+1234567")),
        Case(f"{p}_PHONE_MAX", e, "15 digits (at max)", OK_CREATE,
             set_field("phone", "+123456789012345")),
        Case(f"{p}_PHONE_ABOVE", e, "16 digits (above max)", BAD_REQUEST,
             set_field("phone", "+1234567890123456")),
        Case(f"{p}_PHONE_NO_PLUS", e, "no leading plus", OK_CREATE,
             set_field("phone", "84912345678"),
             "the plus is optional in the pattern"),
        Case(f"{p}_PHONE_LEADING_ZERO", e, "leading zero", BAD_REQUEST,
             set_field("phone", "+0912345678"),
             "the pattern requires [1-9] first"),
        Case(f"{p}_PHONE_LETTERS", e, "letters in phone", BAD_REQUEST,
             set_field("phone", "+849abc4567")),
        Case(f"{p}_PHONE_MISSING", e, "phone absent", BAD_REQUEST,
             set_field("phone", None)),

        # bankingDetails -- the nested object itself is required, which is a
        # different failure from a missing leaf inside it.
        Case(f"{p}_BANKING_MISSING", e, "bankingDetails absent entirely", BAD_REQUEST,
             set_field("bankingDetails", None)),
        Case(f"{p}_ACCT_LETTERS", e, "account number with letters", BAD_REQUEST,
             set_field("bankingDetails.accountNumber", "12ab56"),
             "^\\d{6,20}$ is numeric-only"),

        # id -- server-generated, so supplying it is a client error even though
        # the table lists no explicit read-only marker for it.
        Case(f"{p}_ID_SUPPLIED", e, "client supplies server-generated id", BAD_REQUEST,
             set_field("id", "3fa85f64-5717-4562-b3fc-2c963f66afa6")),
    ]


def product_cases() -> list[Case]:
    e, p = "product", "TC_PRD"
    return [
        # price.currency -- two independent rules: ISO 4217 shape, then
        # membership of the supported list.
        Case(f"{p}_CUR_UNSUPPORTED", e, "valid ISO code outside allow-list", BAD_REQUEST,
             set_field("price.currency", "GBP"),
             "well-formed but not in the supported list"),
        Case(f"{p}_CUR_TOO_SHORT", e, "two-letter currency", BAD_REQUEST,
             set_field("price.currency", "US"),
             "^[A-Z]{3}$"),

        # price.amount -- the range admits these; the precision rule does not.
        Case(f"{p}_AMT_ONE_DP", e, "one decimal place", BAD_REQUEST,
             set_field("price.amount", "19.9"),
             "exactly two decimal places are required"),
        Case(f"{p}_AMT_NO_DP", e, "no decimal places", BAD_REQUEST,
             set_field("price.amount", "19")),
        Case(f"{p}_AMT_NEGATIVE", e, "negative amount", BAD_REQUEST,
             set_field("price.amount", "-1.00"),
             "must be > 0"),

        # price -- the nested object is required as a whole.
        Case(f"{p}_PRICE_MISSING", e, "price object absent", BAD_REQUEST,
             set_field("price", None)),
        Case(f"{p}_ID_SUPPLIED", e, "client supplies server-generated id", BAD_REQUEST,
             set_field("id", "3fa85f64-5717-4562-b3fc-2c963f66afa6")),
    ]


INTERPRETIVE = {
    "customer": customer_cases,
    "product": product_cases,
}


def for_entity(entity: str) -> list[Case]:
    builder = INTERPRETIVE.get(entity)
    return builder() if builder else []
