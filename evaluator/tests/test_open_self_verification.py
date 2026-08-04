"""The self-verification audit must catch evidence that only looks like evidence.

The open profile scores an application partly on verification the agent wrote
itself, so the audit is the load-bearing check: if a suite can assert its own
success, the profile measures nothing. Each test below encodes one way a
plausible-looking result file is in fact worthless.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluator.profiles.open import g3_self_verification as g3

NFRS = ["NFR 2.1 Timeout", "NFR 2.3 Retry"]


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    results = tmp_path / "verification" / "results"
    results.mkdir(parents=True, exist_ok=True)
    path = results / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _honest(**overrides) -> dict:
    payload = {
        "nfr": "NFR 2.1 Timeout",
        "tacticUsed": "Availability > Detect Faults > Timeout",
        "faultInduced": {
            "description": "database latency raised beyond the configured limit",
            "mechanism": "toxiproxy",
            "verified": True,
        },
        "baseline": {"metric": "p95_response_ms", "value": 42},
        "observed": [
            {"metric": "p95_response_ms", "value": 1180},
            {"metric": "hanging_requests", "value": 0},
        ],
        "threshold": [
            {"metric": "p95_response_ms", "operator": "<=", "value": 1500},
            {"metric": "hanging_requests", "operator": "==", "value": 0},
        ],
        "passed": True,
    }
    payload.update(overrides)
    return payload


def _failed(result, fragment: str):
    return [a for a in result.assertions if not a.passed and fragment in a.name]


class TestHonestResult:
    def test_a_well_formed_result_passes(self, tmp_path):
        _write(tmp_path, "nfr-2.1.json", _honest())
        _write(tmp_path, "nfr-2.3.json", _honest(nfr="NFR 2.3 Retry"))
        result = g3.run(tmp_path, NFRS)
        assert result.passed, [a.name for a in result.assertions if not a.passed]


class TestVerdictIsRecomputed:
    def test_hard_coded_pass_is_caught(self, tmp_path):
        # Observed exceeds its own threshold, yet the file claims success.
        _write(tmp_path, "nfr-2.1.json", _honest(
            observed=[{"metric": "p95_response_ms", "value": 9000}],
            threshold=[{"metric": "p95_response_ms", "operator": "<=", "value": 1500}],
            passed=True,
        ))
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert _failed(result, "verdict is computed")

    def test_threshold_on_an_unmeasured_metric_is_caught(self, tmp_path):
        _write(tmp_path, "nfr-2.1.json", _honest(
            observed=[{"metric": "p95_response_ms", "value": 100}],
            threshold=[{"metric": "something_else", "operator": "<=", "value": 1}],
        ))
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert _failed(result, "well-formed")


class TestFaultMustBeConfirmed:
    def test_unverified_fault_is_caught(self, tmp_path):
        _write(tmp_path, "nfr-2.1.json", _honest(
            faultInduced={"description": "assumed the proxy was off", "verified": False}
        ))
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert _failed(result, "well-formed")

    def test_missing_verified_flag_is_caught(self, tmp_path):
        _write(tmp_path, "nfr-2.1.json", _honest(
            faultInduced={"description": "latency injected"}
        ))
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert _failed(result, "well-formed")


class TestBaselineMustDiffer:
    def test_identical_baseline_and_observation_is_caught(self, tmp_path):
        # The proxy reported the fault applied, but the measurement is
        # unchanged -- the application never went through the faulted path.
        _write(tmp_path, "nfr-2.1.json", _honest(
            baseline={"metric": "p95_response_ms", "value": 42},
            observed=[{"metric": "p95_response_ms", "value": 42}],
            threshold=[{"metric": "p95_response_ms", "operator": "<=", "value": 1500}],
        ))
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert _failed(result, "well-formed")

    def test_a_real_change_is_accepted(self, tmp_path):
        _write(tmp_path, "nfr-2.1.json", _honest(
            baseline={"metric": "p95_response_ms", "value": 42},
            observed=[{"metric": "p95_response_ms", "value": 1180}],
            threshold=[{"metric": "p95_response_ms", "operator": "<=", "value": 1500}],
        ))
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert not _failed(result, "well-formed")


class TestCoverage:
    def test_a_missing_nfr_is_reported(self, tmp_path):
        _write(tmp_path, "nfr-2.1.json", _honest())
        result = g3.run(tmp_path, NFRS)
        assert _failed(result, "every NFR has a verification result")

    def test_identifier_matching_tolerates_filename_style(self, tmp_path):
        # 'nfr-2.1' and 'NFR 2.1 Timeout' name the same requirement.
        _write(tmp_path, "whatever.json", _honest(nfr="nfr-2.1"))
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert not _failed(result, "every NFR has a verification result")

    def test_absent_suite_fails_the_gate(self, tmp_path):
        result = g3.run(tmp_path, NFRS)
        assert not result.passed
        assert "verification/results/" in result.assertions[0].name


class TestMalformedInput:
    def test_non_numeric_observation_is_caught(self, tmp_path):
        _write(tmp_path, "nfr-2.1.json", _honest(
            observed=[{"metric": "p95_response_ms", "value": "fast"}]
        ))
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert _failed(result, "well-formed")

    def test_unreadable_file_does_not_crash_the_gate(self, tmp_path):
        results = tmp_path / "verification" / "results"
        results.mkdir(parents=True)
        (results / "broken.json").write_text("{not json", encoding="utf-8")
        result = g3.run(tmp_path, ["NFR 2.1 Timeout"])
        assert not result.passed
