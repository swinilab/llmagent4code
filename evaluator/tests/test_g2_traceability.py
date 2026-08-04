"""Checks on the traceability resolver.

The function resolver decides whether an application's nfr-trace.json is honest
about what it delivered, so its failure modes matter. A resolver that is too
lenient would credit references to functions that do not exist; one that is too
strict would penalise a correct submission for using a class method or an async
definition. Both are checked here against synthetic sources rather than
discovered later against a real application.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluator.common.trace_check import function_exists as _function_exists
from evaluator.gates.g2_traceability import (
    EXPECTED_TACTICS,
    SCENARIO_ORDER,
    _check_traceability,
)

SAMPLE = '''
CONSTANT = 1

def module_level():
    pass

async def async_reader():
    pass

class ProductRepository:
    def get_with_retry(self):
        pass

    async def fetch(self):
        pass

    class Nested:
        def deep(self):
            pass
'''


def _app(tmp_path: Path) -> Path:
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "repo.py").write_text(SAMPLE, encoding="utf-8")
    return tmp_path


def test_resolver_finds_functions_in_every_form(tmp_path: Path) -> None:
    """Module-level, async and class methods are all legitimate references."""
    app = _app(tmp_path)
    for ref in [
        "app/repo.py::module_level",
        "app/repo.py::async_reader",
        "app/repo.py::ProductRepository.get_with_retry",
        "app/repo.py::ProductRepository.fetch",
        "app/repo.py::ProductRepository.Nested.deep",
        "app/repo.py::get_with_retry",  # bare method name, unambiguous here
    ]:
        assert _function_exists(app, ref), f"{ref} should resolve"


def test_resolver_rejects_what_does_not_exist(tmp_path: Path) -> None:
    """A plausible-sounding name is not evidence; only a real definition is."""
    app = _app(tmp_path)
    for ref in [
        "app/repo.py::does_not_exist",
        "app/missing.py::module_level",
        "app/repo.py::CONSTANT",           # a constant is not a function
        "app/repo.py",                      # malformed: no :: separator
        "app/repo.py::",
    ]:
        assert not _function_exists(app, ref), f"{ref} should not resolve"


def test_resolver_does_not_import_the_module(tmp_path: Path) -> None:
    """Parsing, not importing: application code must never be executed here.

    Importing would run module-level code from a system we are evaluating, which
    could open database connections or fail outright, and would let a submission
    influence its own evaluation.
    """
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "explosive.py").write_text(
        "raise RuntimeError('module-level side effect')\n\ndef target():\n    pass\n",
        encoding="utf-8",
    )
    assert _function_exists(tmp_path, "app/explosive.py::target")


def test_syntax_errors_resolve_to_false_not_crash(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "broken.py").write_text("def (((", encoding="utf-8")
    assert not _function_exists(tmp_path, "app/broken.py::anything")


def test_tactic_strings_must_match_verbatim(tmp_path: Path) -> None:
    """Paraphrase is explicitly forbidden, so near-misses must be caught.

    'Degradation' for 'Graceful Degradation' is the specific abbreviation the
    specification calls out, and it is the one most likely to appear.
    """
    app = _app(tmp_path)
    entries = []
    for scenario in SCENARIO_ORDER:
        tactic = EXPECTED_TACTICS[scenario]
        if scenario == "ASR-A3":
            tactic = tactic.replace("Graceful Degradation", "Degradation")
        entries.append(
            {
                "scenarioId": scenario,
                "nfr": scenario,
                "tacticUsed": tactic,
                "filesImplemented": ["app/repo.py"],
                "functionNames": ["app/repo.py::module_level"],
                "configurationKeys": [],
                "librariesUsed": [],
                "metrics": ["cache_hits_total"],
                "verificationMethod": "x",
            }
        )
    (app / "nfr-trace.json").write_text(json.dumps({"nfrTrace": entries}), encoding="utf-8")

    assertions, _, _ = _check_traceability(app)
    by_name = {a.name: a for a in assertions}
    assert not by_name["ASR-A3 cites the prescribed tactic verbatim"].passed
    assert by_name["ASR-P1 cites the prescribed tactic verbatim"].passed


def test_missing_files_and_functions_are_counted(tmp_path: Path) -> None:
    app = _app(tmp_path)
    entries = [
        {
            "scenarioId": s,
            "nfr": s,
            "tacticUsed": EXPECTED_TACTICS[s],
            "filesImplemented": ["app/repo.py", "app/ghost.py"],
            "functionNames": ["app/repo.py::module_level", "app/repo.py::phantom"],
            "configurationKeys": [],
            "librariesUsed": [],
            "metrics": ["not_a_real_metric"],
            "verificationMethod": "x",
        }
        for s in SCENARIO_ORDER
    ]
    (app / "nfr-trace.json").write_text(json.dumps({"nfrTrace": entries}), encoding="utf-8")

    assertions, issues, resolved = _check_traceability(app)
    assert resolved["files_missing"] == 6      # one ghost per scenario
    assert resolved["functions_missing"] == 6  # one phantom per scenario
    assert any(i.kind == "unknown_metric" for i in issues)

    by_name = {a.name: a for a in assertions}
    assert not by_name["every cited file resolves"].passed
    assert not by_name["every cited function resolves"].passed
    assert not by_name["cited metrics are ones the endpoint exposes"].passed


def test_wrong_entry_count_is_reported(tmp_path: Path) -> None:
    app = _app(tmp_path)
    (app / "nfr-trace.json").write_text(
        json.dumps({"nfrTrace": [{"scenarioId": "ASR-P1"}]}), encoding="utf-8"
    )
    assertions, _, _ = _check_traceability(app)
    by_name = {a.name: a for a in assertions}
    assert not by_name["exactly six ASR entries"].passed
    assert not by_name["all six scenario ids present"].passed


def test_absent_trace_file_does_not_crash(tmp_path: Path) -> None:
    assertions, _, _ = _check_traceability(tmp_path)
    assert assertions and not assertions[0].passed
