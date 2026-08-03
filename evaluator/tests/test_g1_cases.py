"""Checks on the G1 case table itself.

The cases decide each application's functional score, so the table is verified
before it is ever pointed at an application. Two failure modes are worth
guarding against specifically, because both would silently mis-score all three
systems rather than producing an obvious error:

  * expecting the wrong status family (the earlier suite expected 422 where the
    specification says 400), and
  * a boundary that is asserted on one side only, which passes an off-by-one
    implementation.
"""

from __future__ import annotations

import copy
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluator.gates.g1_functional.cases import (
    BAD_REQUEST,
    CONFLICT,
    NOT_FOUND,
    OK_CREATE,
    VALID_BODIES,
    all_creation_cases,
    customer_cases,
    identifier_cases,
    product_cases,
)
from evaluator.gates.g1_functional.relational import (
    all_relational_cases,
    invoice_cases,
    payment_cases,
)


def test_validation_failures_expect_400_not_422() -> None:
    """The specification mandates 400 for every public validation failure.

    The earlier ITestGroup suite expected 422. Reusing it would have failed all
    three applications on a criterion they were never given, so this is checked
    explicitly rather than assumed.
    """
    statuses = {c.expected_status for c in all_creation_cases()}
    assert 422 not in statuses
    assert statuses <= {OK_CREATE, BAD_REQUEST}


def test_read_only_fields_are_rejected_regardless_of_value() -> None:
    """Supplying a server-derived field is a 400 whether or not it is empty.

    The old suite accepted an empty client-supplied orderHistory and rejected a
    populated one; the specification draws no such distinction.
    """
    by_id = {c.id: c for c in customer_cases()}
    assert by_id["TC_CUS_ORDERHIST_SUPPLIED"].expected_status == BAD_REQUEST
    assert by_id["TC_CUS_ORDERHIST_EMPTY"].expected_status == BAD_REQUEST
    assert by_id["TC_CUS_ID_SUPPLIED"].expected_status == BAD_REQUEST


def test_every_length_boundary_is_probed_from_both_sides() -> None:
    """A boundary tested on one side only passes an off-by-one implementation."""
    ids = {c.id for c in all_creation_cases()}
    for stem in ("TC_CUS_NAME", "TC_CUS_ADDR", "TC_CUS_ACCT", "TC_CUS_BANKNAME", "TC_PRD_DESC"):
        for suffix in ("LEN_BELOW", "LEN_MIN", "LEN_MAX", "LEN_ABOVE"):
            assert f"{stem}_{suffix}" in ids, f"{stem} is missing its {suffix} probe"


def test_length_mutators_produce_the_stated_lengths() -> None:
    """Guard the generator itself: an off-by-one here would invert the case."""
    by_id = {c.id: c for c in customer_cases()}
    for case_id, expected_len in [
        ("TC_CUS_NAME_LEN_BELOW", 1),
        ("TC_CUS_NAME_LEN_MIN", 2),
        ("TC_CUS_NAME_LEN_MAX", 100),
        ("TC_CUS_NAME_LEN_ABOVE", 101),
    ]:
        body = copy.deepcopy(VALID_BODIES["customer"])
        by_id[case_id].mutate(body)
        assert len(body["name"]) == expected_len


def test_nested_mutators_reach_nested_fields() -> None:
    body = copy.deepcopy(VALID_BODIES["customer"])
    by_id = {c.id: c for c in customer_cases()}
    by_id["TC_CUS_ACCT_LETTERS"].mutate(body)
    assert body["bankingDetails"]["accountNumber"] == "12ab56"

    dropped = copy.deepcopy(VALID_BODIES["customer"])
    by_id["TC_CUS_ACCT_MISSING"].mutate(dropped)
    assert "accountNumber" not in dropped["bankingDetails"]
    assert "bankName" in dropped["bankingDetails"], "dropping one field must not remove its sibling"


def test_valid_bodies_pass_their_own_constraints() -> None:
    """The seed body must satisfy every rule, or negative cases prove nothing."""
    c = VALID_BODIES["customer"]
    assert 2 <= len(c["name"]) <= 100
    assert 5 <= len(c["address"]) <= 255
    assert re.fullmatch(r"\+?[1-9]\d{7,14}", c["phone"])
    assert re.fullmatch(r"\d{6,20}", c["bankingDetails"]["accountNumber"])
    assert c["role"] in {"CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"}

    p = VALID_BODIES["product"]
    assert 3 <= len(p["description"]) <= 500
    assert re.fullmatch(r"\d{1,6}\.\d{2}", p["price"]["amount"])
    assert p["price"]["currency"] in {"USD", "VND", "EUR"}


def test_decimal_precision_cases_cover_both_directions() -> None:
    """Excess precision must be rejected, not rounded; too little is also invalid."""
    by_id = {c.id: c for c in product_cases()}
    assert by_id["TC_PRD_AMT_THREE_DP"].expected_status == BAD_REQUEST
    assert by_id["TC_PRD_AMT_ONE_DP"].expected_status == BAD_REQUEST
    assert by_id["TC_PRD_AMT_NO_DP"].expected_status == BAD_REQUEST


def test_identifier_rule_is_three_way_for_every_entity() -> None:
    """Malformed 400, unknown 404, existing 200 -- checked per entity."""
    for entity in ("customer", "product", "order", "payment", "invoice"):
        expected = {c.partition: c.expected_status for c in identifier_cases(entity)}
        assert expected["malformed UUID"] == BAD_REQUEST
        assert expected["well-formed unknown UUID"] == NOT_FOUND
        assert expected["existing UUID"] == 200


def test_referential_state_violations_expect_409() -> None:
    """Wrong-state references are 409, distinct from 400 and 404.

    Conflating these is the most common way to get the identifier contract
    wrong, so each of the three is asserted separately on the same entity.
    """
    inv = {c.id: c.expected_status for c in invoice_cases()}
    assert inv["TC_INV_WRONG_STATE"] == CONFLICT
    assert inv["TC_INV_ORDER_UNKNOWN"] == NOT_FOUND
    assert inv["TC_INV_ORDER_MALFORMED"] == BAD_REQUEST

    pay = {c.id: c.expected_status for c in payment_cases()}
    assert pay["TC_PAY_WRONG_STATE"] == CONFLICT


def test_case_ids_are_unique() -> None:
    """Duplicate ids would silently overwrite results in the report."""
    ids = [c.id for c in all_creation_cases()] + [c.id for c in all_relational_cases()]
    for entity in ("customer", "product", "order", "payment", "invoice"):
        ids += [c.id for c in identifier_cases(entity)]
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    assert not duplicates, f"duplicate case ids: {duplicates}"


def test_suite_covers_the_required_scenario_classes() -> None:
    """Every class the specification's scenario matrix names must be present."""
    partitions = " ".join(
        [c.partition for c in all_creation_cases()]
        + [c.partition for c in all_relational_cases()]
        + [c.partition for c in identifier_cases("customer")]
    ).lower()

    for required in [
        "at min",
        "at max",
        "below min",
        "above max",
        "absent",           # missing required field
        "allow-list",       # invalid enum
        "malformed",
        "unknown",
        "duplicate productref",
        "decimal places",
        "calendar date",
        "read-only",
        "computed",
    ]:
        assert required in partitions, f"no case covers {required!r}"


def test_every_entity_is_meaningfully_covered() -> None:
    """No entity may be represented by its identifier probes alone.

    Coverage that looks broad in aggregate can still leave an entity with
    nothing but its four GET checks, which says nothing about whether its
    creation contract is enforced.
    """
    creation_by_entity = Counter(
        [c.entity for c in all_creation_cases()] + [c.entity for c in all_relational_cases()]
    )
    for entity in ("customer", "product", "order", "invoice", "payment"):
        assert creation_by_entity[entity] >= 8, (
            f"{entity} has only {creation_by_entity[entity]} creation-time cases"
        )


def test_both_enum_case_sensitivity_directions_are_covered() -> None:
    all_cases = all_creation_cases() + all_relational_cases()
    wrong_case = [c for c in all_cases if "wrong case" in c.partition]
    assert len(wrong_case) >= 2, "case-sensitivity must be probed on more than one enum"
    assert all(c.expected_status == BAD_REQUEST for c in wrong_case)
