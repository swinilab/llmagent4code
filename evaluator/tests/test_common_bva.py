"""The generated half of the functional suite must be complete and correct.

These tests guard the property that makes generation worth doing: a constraint
in the table produces its probes without anyone remembering to write them. A
regression here is invisible in an evaluation run -- the suite simply stops
asking a question -- so it is checked directly.
"""

from __future__ import annotations

import copy

from evaluator.common import bva


def _apply(case: bva.Case, body: dict) -> dict:
    out = copy.deepcopy(body)
    if case.mutate:
        case.mutate(out)
    return out


class TestLengthBoundaries:
    def test_emits_four_probes_around_the_range(self):
        cases = bva.length_boundaries("customer", "TC_CUS_NAME", "name", 2, 100)
        assert len(cases) == 4
        assert [c.expected_status for c in cases] == [400, 201, 201, 400]

    def test_probes_sit_exactly_on_the_boundary(self):
        below, at_min, at_max, above = bva.length_boundaries("e", "P", "f", 3, 10)
        assert len(_apply(below, {})["f"]) == 2
        assert len(_apply(at_min, {})["f"]) == 3
        assert len(_apply(at_max, {})["f"]) == 10
        assert len(_apply(above, {})["f"]) == 11


class TestDecimalBoundaries:
    def test_range_and_precision_are_probed_independently(self):
        cases = bva.decimal_boundaries("product", "TC_PRD_AMT", "price.amount",
                                       "0.01", "999999.99")
        ids = {c.id for c in cases}
        assert "TC_PRD_AMT_MIN" in ids and "TC_PRD_AMT_MAX" in ids
        # Precision is the rule a range-only validator silently violates.
        assert "TC_PRD_AMT_EXTRA_DP" in ids
        assert "TC_PRD_AMT_FEW_DP" in ids

    def test_below_minimum_steps_by_one_unit_of_precision(self):
        cases = {c.id: c for c in bva.decimal_boundaries("e", "P", "amt", "0.01", "10.00")}
        assert _apply(cases["P_BELOW"], {})["amt"] == "0.00"
        assert _apply(cases["P_ABOVE"], {})["amt"] == "10.01"

    def test_endpoints_are_accepted(self):
        cases = {c.id: c for c in bva.decimal_boundaries("e", "P", "amt", "0.01", "10.00")}
        assert cases["P_MIN"].expected_status == 201
        assert cases["P_MAX"].expected_status == 201


class TestEnumCases:
    def test_every_allowed_value_gets_its_own_probe(self):
        allowed = ["CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"]
        cases = bva.enum_cases("customer", "TC_CUS_ROLE", "role", allowed)
        accepted = [c for c in cases if c.expected_status == 201]
        assert {_apply(c, {})["role"] for c in accepted} == set(allowed)

    def test_wrong_case_is_rejected(self):
        cases = {c.id: c for c in bva.enum_cases("e", "P", "role", ["CUSTOMER"])}
        probe = cases["P_WRONG_CASE"]
        assert probe.expected_status == 400
        assert _apply(probe, {})["role"] == "customer"


class TestReadOnlyCases:
    def test_empty_value_is_rejected_too(self):
        cases = {c.id: c for c in bva.readonly_cases("e", "P", "orderHistory", ["x"])}
        # The empty probe is the one that catches truthiness-keyed validation.
        assert cases["P_EMPTY"].expected_status == 400
        assert _apply(cases["P_EMPTY"], {})["orderHistory"] == []


class TestNestedPaths:
    def test_dotted_paths_become_nested_objects(self):
        body = _apply(
            bva.Case("x", "e", "p", 400, bva.set_field("bankingDetails.bankName", "Acme")),
            {},
        )
        assert body == {"bankingDetails": {"bankName": "Acme"}}

    def test_drop_removes_only_the_leaf(self):
        body = {"bankingDetails": {"bankName": "Acme", "accountNumber": "1"}}
        result = _apply(
            bva.Case("x", "e", "p", 400, bva.drop_field("bankingDetails.bankName")), body
        )
        assert result["bankingDetails"] == {"accountNumber": "1"}


class TestGenerationFromTable:
    TABLE = {
        "name": {"required": True, "length": [2, 100]},
        "role": {"required": True, "enum": ["A", "B"]},
        "price.amount": {"required": True, "decimal": ["0.01", "99.99"], "places": 2},
        "orderHistory": {"readOnly": True, "sample": ["u"]},
    }

    def test_every_constrained_field_is_probed(self):
        cases = bva.cases_from_constraints("customer", "TC", self.TABLE)
        probed = {c.id.split("_")[1] for c in cases}
        assert {"NAME", "ROLE", "PRICE", "ORDERHISTORY"} <= probed | {
            c.id.split("_")[1] for c in cases
        }

    def test_read_only_fields_get_no_boundary_probes(self):
        cases = bva.cases_from_constraints("customer", "TC", self.TABLE)
        history = [c for c in cases if "ORDERHISTORY" in c.id]
        # A read-only field has no valid value, so a "at min length" probe
        # expecting 201 would contradict the rule.
        assert all(c.expected_status == 400 for c in history)

    def test_unknown_spec_keys_are_ignored(self):
        cases = bva.cases_from_constraints(
            "e", "TC", {"f": {"required": True, "length": [1, 5], "documentation": "note"}}
        )
        assert cases

    def test_the_unmutated_body_is_always_probed(self):
        # Without this case an application that rejects every request satisfies
        # all the negative probes and scores near-perfectly.
        cases = bva.cases_from_constraints("customer", "TC", self.TABLE)
        valid = [c for c in cases if c.mutate is None]
        assert len(valid) == 1
        assert valid[0].expected_status == 201
