"""Tactic citation must be checked structurally, not literally.

The open prompt supplies definitions rather than exact strings, so the same
tactic can be cited several equally correct ways. Failing an agent for
punctuation would measure formatting; accepting any string would measure
nothing. These tests pin where that line sits.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluator.common import manifest_check, trace_check
from evaluator.profiles.open import g2_traceability as g2


class TestTacticResolution:
    def test_canonical_citation_resolves(self):
        assert g2._tactic_problem("Availability > Detect Faults > Timeout") == ""

    def test_alternative_separators_resolve(self):
        # '/' and '>' are punctuation, not architecture.
        assert g2._tactic_problem("Availability / Detect Faults / Timeout") == ""
        assert g2._tactic_problem("availability > detect faults > timeout") == ""

    def test_branch_alone_is_enough_context(self):
        assert g2._tactic_problem("Detect Faults / Timeout") == ""

    def test_invented_tactic_is_rejected(self):
        problem = g2._tactic_problem("Availability > Detect Faults > Magic Healing")
        assert "not a tactic in the taxonomy" in problem

    def test_truncated_leaf_is_rejected(self):
        # 'Degradation' and 'Graceful Degradation' are different names; the
        # prompt's own wording is the latter.
        problem = g2._tactic_problem("Availability > Recover from Faults > Degradation")
        assert problem

    def test_leaf_cited_under_the_wrong_quality_is_rejected(self):
        # Timeout is an Availability tactic; filing it under Performance is a
        # misplacement, not an abbreviation.
        problem = g2._tactic_problem("Performance > Detect Faults > Timeout")
        assert "but it is a availability tactic" in problem

    def test_leaf_cited_under_the_wrong_branch_is_rejected(self):
        problem = g2._tactic_problem("Availability > Prevent Faults > Retry")
        assert "but it sits under" in problem

    def test_bare_leaf_is_accepted(self):
        # No context given is shorthand, not a misplacement: the leaf names are
        # unambiguous across this taxonomy.
        assert g2._tactic_problem("Timeout") == ""
        assert g2._tactic_problem("Graceful Degradation") == ""

    def test_empty_citation_is_rejected(self):
        assert g2._tactic_problem("") == "no tactic cited"

    def test_performance_tactics_resolve(self):
        assert g2._tactic_problem(
            "Performance > Manage Resources > Maintain Multiple Copies of Data"
        ) == ""
        assert g2._tactic_problem(
            "Performance > Control Resource Demand > Limit Event Response"
        ) == ""


class TestFunctionResolution:
    def test_resolves_a_real_function(self, tmp_path):
        (tmp_path / "svc.py").write_text(
            "import tenacity\n\n"
            "class Repo:\n"
            "    @tenacity.retry\n"
            "    def read(self):\n"
            "        return 1\n",
            encoding="utf-8",
        )
        assert trace_check.function_exists(tmp_path, "svc.py::Repo.read")
        assert trace_check.function_exists(tmp_path, "svc.py::read")

    def test_missing_function_does_not_resolve(self, tmp_path):
        (tmp_path / "svc.py").write_text("def other(): pass\n", encoding="utf-8")
        assert not trace_check.function_exists(tmp_path, "svc.py::read")

    def test_syntax_error_does_not_crash(self, tmp_path):
        (tmp_path / "svc.py").write_text("def broken(\n", encoding="utf-8")
        assert not trace_check.function_exists(tmp_path, "svc.py::broken")

    def test_library_visible_in_the_cited_function(self, tmp_path):
        (tmp_path / "svc.py").write_text(
            "import tenacity\n\n"
            "def read():\n"
            "    return tenacity.retry(lambda: 1)\n\n"
            "def handler():\n"
            "    return read()\n",
            encoding="utf-8",
        )
        assert trace_check.function_mentions(tmp_path, "svc.py::read", ["tenacity"])
        # The handler merely calls read(); citing it would misattribute the
        # mechanism, which is what this check exists to surface.
        assert not trace_check.function_mentions(tmp_path, "svc.py::handler", ["tenacity"])

    def test_decorator_usage_counts(self, tmp_path):
        (tmp_path / "svc.py").write_text(
            "from tenacity import retry\n\n@retry\ndef read():\n    return 1\n",
            encoding="utf-8",
        )
        assert trace_check.function_mentions(tmp_path, "svc.py::read", ["retry"])


class TestManifests:
    def _write(self, tmp_path: Path, name: str, payload: dict) -> None:
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_valid_create_manifest_passes(self, tmp_path):
        self._write(tmp_path, "create_apis.json", {
            "customer": {"method": "POST", "path": "/api/v1/customers",
                         "readPathTemplate": "/api/v1/customers/{id}"},
        })
        check = manifest_check.check_create_manifest(
            tmp_path, ["customer"], require_read_template=True
        )
        assert check.ok, [vars(i) for i in check.issues]

    def test_missing_read_template_is_caught_in_open_profile(self, tmp_path):
        self._write(tmp_path, "create_apis.json", {
            "customer": {"method": "POST", "path": "/api/v1/customers"},
        })
        check = manifest_check.check_create_manifest(
            tmp_path, ["customer"], require_read_template=True
        )
        assert any(i.kind == "bad_read_template" for i in check.issues)

    def test_read_template_needs_exactly_one_placeholder(self, tmp_path):
        self._write(tmp_path, "create_apis.json", {
            "customer": {"method": "POST", "path": "/api/v1/customers",
                         "readPathTemplate": "/api/v1/{tenant}/customers/{id}"},
        })
        check = manifest_check.check_create_manifest(
            tmp_path, ["customer"], require_read_template=True
        )
        assert any(i.kind == "bad_read_template" for i in check.issues)

    def test_create_path_must_not_be_templated(self, tmp_path):
        self._write(tmp_path, "create_apis.json", {
            "customer": {"method": "POST", "path": "/api/v1/customers/{id}",
                         "readPathTemplate": "/api/v1/customers/{id}"},
        })
        check = manifest_check.check_create_manifest(
            tmp_path, ["customer"], require_read_template=True
        )
        assert any(i.kind == "bad_path" for i in check.issues)

    def test_workflow_manifest_accepts_agent_chosen_names(self, tmp_path):
        # The prompt derives step names from the Behavior Workflow, so any
        # camelCase verb is legitimate; only invocability is checked.
        self._write(tmp_path, "workflow_apis.json", {
            "acceptOrder": {"method": "POST",
                            "pathTemplate": "/api/v1/orders/{id}/accept",
                            "precondition": "PLACED"},
            "dispatchOrder": {"method": "POST",
                              "pathTemplate": "/api/v1/orders/{id}/dispatch",
                              "precondition": "VERIFIED"},
        })
        check = manifest_check.check_workflow_manifest(tmp_path, minimum_steps=2)
        assert check.ok, [vars(i) for i in check.issues]

    def test_workflow_step_without_precondition_is_caught(self, tmp_path):
        self._write(tmp_path, "workflow_apis.json", {
            "acceptOrder": {"method": "POST", "pathTemplate": "/api/v1/orders/{id}/accept"},
        })
        check = manifest_check.check_workflow_manifest(tmp_path, minimum_steps=1)
        assert any(i.kind == "missing_precondition" for i in check.issues)

    def test_too_few_workflow_steps_is_caught(self, tmp_path):
        self._write(tmp_path, "workflow_apis.json", {
            "acceptOrder": {"method": "POST",
                            "pathTemplate": "/api/v1/orders/{id}/accept",
                            "precondition": "PLACED"},
        })
        check = manifest_check.check_workflow_manifest(tmp_path, minimum_steps=4)
        assert any(i.kind == "too_few_steps" for i in check.issues)

    def test_absent_manifest_is_reported_not_crashed(self, tmp_path):
        check = manifest_check.check_workflow_manifest(tmp_path, minimum_steps=4)
        assert any(i.kind == "unreadable" for i in check.issues)


class TestRouteNormalisation:
    def test_placeholder_names_do_not_affect_comparison(self):
        declared = manifest_check.declared_routes(
            {"acceptOrder": {"method": "POST",
                             "pathTemplate": "/api/v1/orders/{id}/accept"}},
            "pathTemplate",
        )
        served = manifest_check.openapi_routes(
            {"paths": {"/api/v1/orders/{orderId}/accept": {"post": {}}}}
        )
        assert declared == served
