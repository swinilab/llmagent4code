"""Generating the mechanical half of a boundary-value suite.

A constraint table states, per field, a length range, a numeric range, a regex,
an enum, or a read-only marker. The probes those imply are wholly mechanical --
min-1, min, max, max+1; empty, blank, missing, null; each allowed enum value
plus one outside the list -- and generating them is both less error-prone than
writing them out and makes a missing probe impossible rather than merely
noticeable.

What is *not* mechanical stays hand-written. Whether `Nguyễn` must be accepted
depends on reading `\\p{L}` as meaning Unicode letters; whether `GBP` must be
rejected depends on noticing that a well-formed ISO code can still sit outside
an allow-list; whether `19.9` must be rejected depends on "exactly two decimal
places" overriding a range that would otherwise admit it. A generator cannot
derive those from the table, and pretending otherwise would quietly drop the
cases most likely to separate a careful implementation from a plausible one.

So the contract is: this module emits the probes the table entails, and the
profile supplies interpretive cases alongside them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

# Status codes, per the validation contract both prompts state.
OK_CREATE = 201
OK_READ = 200
BAD_REQUEST = 400
NOT_FOUND = 404
CONFLICT = 409


@dataclass(frozen=True)
class Case:
    """One functional probe.

    `mutate` receives a deep copy of the entity's valid body and alters it in
    place; returning a new object is unnecessary. `partition` records which
    equivalence class or boundary the case covers so results can be grouped by
    intent rather than by case name.
    """

    id: str
    entity: str
    partition: str
    expected_status: int
    mutate: Callable[[dict[str, Any]], None] | None = None
    description: str = ""
    get_id: str | None = None


def set_field(path: str, value: Any) -> Callable[[dict[str, Any]], None]:
    """Build a mutator for a dotted field path, e.g. bankingDetails.bankName."""

    def apply(body: dict[str, Any]) -> None:
        parts = path.split(".")
        cursor: Any = body
        for p in parts[:-1]:
            cursor = cursor.setdefault(p, {})
        cursor[parts[-1]] = value

    return apply


def drop_field(path: str) -> Callable[[dict[str, Any]], None]:
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


def length_boundaries(
    entity: str, prefix: str, path: str, lo: int, hi: int, filler: str = "a"
) -> list[Case]:
    """Four probes around an inclusive [lo, hi] string-length constraint.

    Below-minimum and above-maximum must be rejected; the two endpoints
    themselves must be accepted. Testing only the endpoints would pass an
    implementation that is off by one in either direction.
    """
    return [
        Case(f"{prefix}_LEN_BELOW", entity, f"{path} length {lo - 1} (below min)",
             BAD_REQUEST, set_field(path, filler * (lo - 1))),
        Case(f"{prefix}_LEN_MIN", entity, f"{path} length {lo} (at min)",
             OK_CREATE, set_field(path, filler * lo)),
        Case(f"{prefix}_LEN_MAX", entity, f"{path} length {hi} (at max)",
             OK_CREATE, set_field(path, filler * hi)),
        Case(f"{prefix}_LEN_ABOVE", entity, f"{path} length {hi + 1} (above max)",
             BAD_REQUEST, set_field(path, filler * (hi + 1))),
    ]


def blank_and_missing(entity: str, prefix: str, path: str) -> list[Case]:
    """The four ways a required field can be absent in substance."""
    return [
        Case(f"{prefix}_EMPTY", entity, f"{path} empty string", BAD_REQUEST,
             set_field(path, "")),
        Case(f"{prefix}_BLANK", entity, f"{path} whitespace only", BAD_REQUEST,
             set_field(path, "    ")),
        Case(f"{prefix}_MISSING", entity, f"{path} absent", BAD_REQUEST, drop_field(path)),
        Case(f"{prefix}_NULL", entity, f"{path} null", BAD_REQUEST, set_field(path, None)),
    ]


def decimal_boundaries(
    entity: str, prefix: str, path: str, lo: str, hi: str, places: int = 2
) -> list[Case]:
    """Probes around an inclusive decimal range with fixed precision.

    Both endpoints must be accepted; one step outside either end must not be.
    The precision probes matter more than the range ones in practice -- a
    validator built from a numeric range alone silently accepts `19.999` and
    rounds it, which is exactly the behaviour a money field must not have.
    """
    step = Decimal(1).scaleb(-places)
    low, high = Decimal(lo), Decimal(hi)
    fmt = f"{{:.{places}f}}"
    return [
        Case(f"{prefix}_MIN", entity, f"{path} at minimum {lo}", OK_CREATE,
             set_field(path, fmt.format(low))),
        Case(f"{prefix}_BELOW", entity, f"{path} one step below minimum", BAD_REQUEST,
             set_field(path, fmt.format(low - step))),
        Case(f"{prefix}_MAX", entity, f"{path} at maximum {hi}", OK_CREATE,
             set_field(path, fmt.format(high))),
        Case(f"{prefix}_ABOVE", entity, f"{path} one step above maximum", BAD_REQUEST,
             set_field(path, fmt.format(high + step))),
        Case(f"{prefix}_EXTRA_DP", entity, f"{path} with {places + 1} decimal places",
             BAD_REQUEST, set_field(path, fmt.format(low) + "9"),
             "excess precision is rejected, never silently rounded"),
        Case(f"{prefix}_FEW_DP", entity, f"{path} with {places - 1} decimal places",
             BAD_REQUEST, set_field(path, f"{low:.{max(places - 1, 0)}f}"),
             f"exactly {places} decimal places are required"),
        Case(f"{prefix}_TEXT", entity, f"{path} non-numeric", BAD_REQUEST,
             set_field(path, "not-a-number")),
        Case(f"{prefix}_MISSING", entity, f"{path} absent", BAD_REQUEST, drop_field(path)),
    ]


def enum_cases(
    entity: str, prefix: str, path: str, allowed: list[str], outside: str = "NOT_A_VALUE"
) -> list[Case]:
    """Every allowed value accepted; unknown, mis-cased and absent rejected.

    Each allowed value gets its own probe because an implementation can easily
    admit the first member of an enum and reject the rest -- a defect invisible
    to a suite that only ever sends one valid value.
    """
    cases = [
        Case(f"{prefix}_{value}", entity, f"{path} = {value}", OK_CREATE,
             set_field(path, value))
        for value in allowed
    ]
    cases += [
        Case(f"{prefix}_UNKNOWN", entity, f"{path} outside the allow-list", BAD_REQUEST,
             set_field(path, outside)),
        Case(f"{prefix}_EMPTY", entity, f"{path} empty", BAD_REQUEST, set_field(path, "")),
        Case(f"{prefix}_MISSING", entity, f"{path} absent", BAD_REQUEST, drop_field(path)),
    ]
    if allowed:
        cases.append(
            Case(f"{prefix}_WRONG_CASE", entity, f"{path} in the wrong case", BAD_REQUEST,
                 set_field(path, allowed[0].lower()),
                 "enum matching is case-sensitive")
        )
    return cases


def readonly_cases(entity: str, prefix: str, path: str, sample: Any) -> list[Case]:
    """A client-supplied server-owned field is rejected whatever its value.

    The empty-value probe is the one that matters: an implementation that
    rejects a populated read-only field but accepts an empty one has a
    validation rule keyed on truthiness rather than on presence.
    """
    return [
        Case(f"{prefix}_SUPPLIED", entity, f"client supplies read-only {path}",
             BAD_REQUEST, set_field(path, sample)),
        Case(f"{prefix}_EMPTY", entity, f"client supplies empty read-only {path}",
             BAD_REQUEST, set_field(path, [] if isinstance(sample, list) else ""),
             "read-only fields are rejected regardless of value"),
    ]


def identifier_cases(entity: str) -> list[Case]:
    """GET probes shared by every entity.

    The three-way split -- malformed 400, unknown 404, existing 200 -- is the
    central identifier rule of both prompts, and is checked per entity because
    an application can get it right on one router and wrong on another.
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


# ── constraint-table driven generation ────────────────────────────────────


def cases_from_constraints(entity: str, prefix: str, fields: dict[str, dict]) -> list[Case]:
    """Generate every probe a constraint table entails for one entity.

    `fields` maps a dotted attribute path to its declared constraints, e.g.

        {"name":      {"length": [2, 100], "required": true},
         "role":      {"enum": ["CUSTOMER", "ORDER_STAFF"]},
         "price.amount": {"decimal": ["0.01", "999999.99"], "places": 2},
         "orderHistory": {"readOnly": true, "sample": ["<uuid>"]}}

    Unknown keys are ignored rather than rejected, so a table can carry
    documentation the generator does not consume.
    """
    # The unmutated body must be accepted before any rejection means anything:
    # an application that refuses every request satisfies all the negative
    # probes below for entirely the wrong reason, and without this case that
    # failure mode reads as a near-perfect score.
    cases: list[Case] = [
        Case(f"{prefix}_VALID", entity, "valid creation", OK_CREATE, None,
             "baseline: the unmutated seed body must be accepted")
    ]

    for path, spec in fields.items():
        stem = f"{prefix}_{_stem(path)}"

        if spec.get("readOnly"):
            cases += readonly_cases(entity, stem, path, spec.get("sample", "x"))
            continue

        if "length" in spec:
            lo, hi = spec["length"]
            cases += length_boundaries(entity, stem, path, int(lo), int(hi),
                                       str(spec.get("filler", "a")))
        if "decimal" in spec:
            lo, hi = spec["decimal"]
            cases += decimal_boundaries(entity, stem, path, str(lo), str(hi),
                                        int(spec.get("places", 2)))
        if "enum" in spec:
            cases += enum_cases(entity, stem, path, list(spec["enum"]))
        elif spec.get("required") and "decimal" not in spec:
            cases += blank_and_missing(entity, stem, path)

    return cases


def _stem(path: str) -> str:
    """A stable case-id fragment from a dotted attribute path."""
    return path.replace(".", "_").upper()
