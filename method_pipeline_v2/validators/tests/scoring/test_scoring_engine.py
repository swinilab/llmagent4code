"""
test_scoring_engine.py
───────────────────────
Unit and integration tests for the Static QA Scoring Engine mapped to plan.md Part 3.

Covers:
  - score_func:   graded scoring (PRESENT=1.0/0.5 by library evidence, WEAK/ABSENT=0.0)
  - score_tactic: tactic-level function mean (sum(score_func) / num_functions)
  - score_qa:     QA-level tactic mean (avg(score_tactic-by-qa))
  - _tactic_group: NFR prefix mapping ("1.x" -> performance, "2.x" -> availability)
  - build_scoring_hierarchy: full hierarchical aggregation
  - End-to-end trace validation with StaticQualityAttributeValidator
"""

import json
import pytest
from pathlib import Path
import sys

# Ensure method_pipeline_v2 is in sys.path
PIPELINE_ROOT = Path(__file__).resolve().parents[3]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from interfaces.base import GenerationResult, Status
from validators.StaticQualityAttributeValidator import (
    ABSENT,
    PRESENT,
    WEAK,
    StaticQualityAttributeValidator,
    _tactic_group,
    build_scoring_hierarchy,
    score_func,
    score_qa,
    score_tactic,
)


class TestScoreFunc:
    """Tests for score_func(tactic, function) -> 0.0 / 0.5 / 1.0."""

    def test_score_func_present(self):
        assert score_func(PRESENT) == 1.0

    def test_score_func_weak_stub(self):
        assert score_func(WEAK) == 0.0

    def test_score_func_absent(self):
        assert score_func(ABSENT) == 0.0

    def test_score_func_unknown_status(self):
        assert score_func("UNKNOWN") == 0.0

    def test_score_func_present_library_corroborated(self):
        assert score_func(PRESENT, True) == 1.0

    def test_score_func_present_library_claim_unsupported(self):
        """Body exists but references no claimed library -> half credit."""
        assert score_func(PRESENT, False) == 0.5

    def test_score_func_stub_stays_zero_even_if_corroborated(self):
        """A stub scores 0 whatever the library evidence says."""
        assert score_func(WEAK, True) == 0.0
        assert score_func(ABSENT, True) == 0.0

    def test_score_func_default_is_corroborated(self):
        """Callers holding only a status keep the pre-grading behaviour."""
        assert score_func(PRESENT) == score_func(PRESENT, True)


class TestScoreFuncInHierarchy:
    """build_scoring_hierarchy must grade records that carry no explicit score_func."""

    def _hierarchy(self, fn):
        return build_scoring_hierarchy([{
            "nfr": "1.1 Latency", "qa_group": "performance",
            "tactics": ["Limit Event Response"], "functions": [fn],
        }])["score_func"]["Limit Event Response"]["m.py::f"]

    def test_present_without_library_evidence_scores_half(self):
        assert self._hierarchy(
            {"ref": "m.py::f", "status": PRESENT, "uses_any": False, "lib_claimed": True}
        ) == 0.5

    def test_present_with_library_evidence_scores_one(self):
        assert self._hierarchy(
            {"ref": "m.py::f", "status": PRESENT, "uses_any": True, "lib_claimed": True}
        ) == 1.0

    def test_no_library_claimed_is_not_penalised(self):
        assert self._hierarchy(
            {"ref": "m.py::f", "status": PRESENT, "uses_any": False, "lib_claimed": False}
        ) == 1.0

    def test_legacy_score1_key_is_still_read(self):
        """Reports written before the rename must aggregate without a re-run."""
        assert self._hierarchy(
            {"ref": "m.py::f", "status": PRESENT, "score1": 0.5,
             "uses_any": True, "lib_claimed": True}
        ) == 0.5

    def test_explicit_score_func_wins_over_recomputation(self):
        assert self._hierarchy(
            {"ref": "m.py::f", "status": PRESENT, "score_func": 0.5,
             "uses_any": True, "lib_claimed": True}
        ) == 0.5


class TestScoreTactic:
    """Tests for score_tactic(tactic, function-in-trace) = % sum(score_func)/num-functions."""

    def test_score_tactic_empty(self):
        assert score_tactic([]) == 0.0

    def test_score_tactic_all_present(self):
        assert score_tactic([1.0, 1.0, 1.0]) == 1.0

    def test_score_tactic_mixed(self):
        # 2 present (1.0), 1 stub (0.0) -> 2/3 ≈ 0.6667
        score = score_tactic([1.0, 0.0, 1.0])
        assert pytest.approx(score, 0.0001) == 2.0 / 3.0

    def test_score_tactic_all_absent_or_weak(self):
        assert score_tactic([0.0, 0.0]) == 0.0


class TestScoreQA:
    """Tests for score_qa(qa, tacticset) = avg(score_tactic-by-qa)."""

    def test_score_qa_empty(self):
        assert score_qa([]) == 0.0

    def test_score_qa_single_tactic(self):
        assert score_qa([0.8]) == 0.8

    def test_score_qa_multiple_tactics(self):
        # Tactic A: 1.0, Tactic B: 0.5 -> avg: 0.75
        assert score_qa([1.0, 0.5]) == 0.75

    def test_score_qa_four_tactics(self):
        # Availability with 4 tactics: [1.0, 0.5, 0.0, 1.0] -> 2.5 / 4 = 0.625
        assert pytest.approx(score_qa([1.0, 0.5, 0.0, 1.0]), 0.0001) == 0.625


class TestTacticGrouping:
    """Tests for QA categorization from NFR prefix."""

    def test_performance_group(self):
        assert _tactic_group("NFR 1.1: Limit Event Response") == "performance"
        assert _tactic_group("NFR 1.2: Maintain Multiple Copies") == "performance"

    def test_availability_group(self):
        assert _tactic_group("NFR 2.1: Exception Detection") == "availability"
        assert _tactic_group("NFR 2.4: Transactions") == "availability"

    def test_other_group(self):
        assert _tactic_group("NFR 3.1: Security Authentication") == "other"
        assert _tactic_group("Miscellaneous Requirement") == "other"


class TestHierarchicalAggregation:
    """Tests for build_scoring_hierarchy aggregation."""

    def test_build_scoring_hierarchy(self):
        mock_results = [
            {
                "nfr": "NFR 1.1: Limit Event Response",
                "qa_group": "performance",
                "tactics": ["Limit Event Response"],
                "functions": [
                    {"ref": "rate_limiter.py::allow", "status": PRESENT, "score_func": 1.0},
                    {"ref": "middleware.py::dispatch", "status": PRESENT, "score_func": 1.0},
                ],
            },
            {
                "nfr": "NFR 1.2: Maintain Multiple Copies of Data",
                "qa_group": "performance",
                "tactics": ["Maintain Multiple Copies of Data"],
                "functions": [
                    {"ref": "cache.py::get", "status": PRESENT, "score_func": 1.0},
                    {"ref": "cache.py::set", "status": WEAK, "score_func": 0.0},
                ],
            },
            {
                "nfr": "NFR 2.1: Exception Detection",
                "qa_group": "availability",
                "tactics": ["Exception Detection"],
                "functions": [
                    {"ref": "middleware.py::catch", "status": PRESENT, "score_func": 1.0},
                ],
            },
        ]

        hierarchy = build_scoring_hierarchy(mock_results)

        # 1. Check score_func mapping
        assert hierarchy["score_func"]["Limit Event Response"]["rate_limiter.py::allow"] == 1.0
        assert hierarchy["score_func"]["Limit Event Response"]["middleware.py::dispatch"] == 1.0
        assert hierarchy["score_func"]["Maintain Multiple Copies of Data"]["cache.py::get"] == 1.0
        assert hierarchy["score_func"]["Maintain Multiple Copies of Data"]["cache.py::set"] == 0.0
        assert hierarchy["score_func"]["Exception Detection"]["middleware.py::catch"] == 1.0

        # 2. Check score_tactic mapping
        assert hierarchy["score_tactic"]["Limit Event Response"] == 1.0
        assert hierarchy["score_tactic"]["Maintain Multiple Copies of Data"] == 0.5
        assert hierarchy["score_tactic"]["Exception Detection"] == 1.0

        # 3. Check score_qa mapping
        # Performance has 2 tactics: 1.0 and 0.5 -> avg = 0.75
        assert hierarchy["score_qa"]["performance"] == 0.75
        # Availability has 1 tactic: 1.0 -> avg = 1.0
        assert hierarchy["score_qa"]["availability"] == 1.0

        # 4. Check overall score: (0.75 + 1.0) / 2 = 0.875
        assert hierarchy["overall_score"] == 0.875


class TestStaticQualityAttributeValidatorE2E:
    """End-to-end validator tests using generated mock code repository."""

    def test_validate_end_to_end(self, tmp_path):
        # 1. Create a dummy codebase in tmp_path
        app_dir = tmp_path / "app"
        app_dir.mkdir()

        # Non-trivial function in rate_limiter.py
        (app_dir / "rate_limiter.py").write_text(
            "import redis\n\n"
            "class RateLimiter:\n"
            "    def allow(self, key):\n"
            "        r = redis.Redis()\n"
            "        return r.ping()\n",
            encoding="utf-8"
        )

        # Stub function in cache.py
        (app_dir / "cache.py").write_text(
            "class Cache:\n"
            "    def get(self, key):\n"
            "        pass\n",
            encoding="utf-8"
        )

        # 2. Create nfr-trace.json
        trace_data = {
            "nfrTrace": [
                {
                    "nfr": "NFR 1.1: Limit Event Response",
                    "filesImplemented": ["app/rate_limiter.py"],
                    "librariesUsed": ["redis"],
                    "functionNames": ["app/rate_limiter.py::RateLimiter.allow"],
                    "tacticUsed": "QA Performance/Manage Resources/Limit Event Response"
                },
                {
                    "nfr": "NFR 1.2: Maintain Multiple Copies of Data",
                    "filesImplemented": ["app/cache.py"],
                    "librariesUsed": [],
                    "functionNames": ["app/cache.py::Cache.get"],
                    "tacticUsed": "QA Performance/Manage Resources/Maintain Multiple Copies of Data"
                },
                {
                    "nfr": "NFR 2.1: Exception Detection",
                    "filesImplemented": ["app/rate_limiter.py"],
                    "librariesUsed": [],
                    "functionNames": ["app/rate_limiter.py::RateLimiter.missing_func"],
                    "tacticUsed": "QA Availability/Detect Faults/Exception Detection"
                }
            ]
        }
        (tmp_path / "nfr-trace.json").write_text(json.dumps(trace_data), encoding="utf-8")

        # 3. Run validation
        config = {"output": {"report_dir": str(tmp_path / "reports")}}
        validator = StaticQualityAttributeValidator(config=config)
        gen_res = GenerationResult(status=Status.PASS, model="mock-model", code=str(tmp_path))

        val_result = validator.validate(gen_res)

        # 4. Verify outcome
        assert val_result.status == Status.PASS
        tally = val_result.details["tally"]

        # score_func checks:
        # RateLimiter.allow is PRESENT -> 1.0
        assert tally["score_func"]["Limit Event Response"]["app/rate_limiter.py::RateLimiter.allow"] == 1.0
        # Cache.get is WEAK (stub) -> 0.0
        assert tally["score_func"]["Maintain Multiple Copies of Data"]["app/cache.py::Cache.get"] == 0.0
        # RateLimiter.missing_func is ABSENT -> 0.0
        assert tally["score_func"]["Exception Detection"]["app/rate_limiter.py::RateLimiter.missing_func"] == 0.0

        # score_tactic checks:
        assert tally["score_tactic"]["Limit Event Response"] == 1.0
        assert tally["score_tactic"]["Maintain Multiple Copies of Data"] == 0.0
        assert tally["score_tactic"]["Exception Detection"] == 0.0

        # score_qa checks:
        # Performance: (1.0 + 0.0) / 2 = 0.5
        assert tally["score_qa"]["performance"] == 0.5
        # Availability: 0.0 / 1 = 0.0
        assert tally["score_qa"]["availability"] == 0.0

        # Overall score: (0.5 + 0.0) / 2 = 0.25
        assert tally["overall_score"] == 0.25

        # Check report file was written
        report_path = Path(val_result.details["report_path"])
        assert report_path.is_file()
        report_content = json.loads(report_path.read_text(encoding="utf-8"))
        assert report_content["scoring_summary"]["overall_score"] == 0.25


class TestRealTraces:
    """Tests running the refactored scoring engine on existing generated benchmark codebases."""

    def test_chatdev_v1_benchmark(self, tmp_path):
        app_path = PIPELINE_ROOT / "generated" / "chatdev-qwen35-v1" / "code_workspace"
        if not app_path.exists() or not (app_path / "nfr-trace.json").is_file():
            pytest.skip("Benchmark app not found")

        config = {"output": {"report_dir": str(tmp_path / "reports")}}
        validator = StaticQualityAttributeValidator(config=config)
        gen_res = GenerationResult(status=Status.PASS, model="chatdev-qwen35-v1", code=str(app_path))

        val_result = validator.validate(gen_res)
        assert val_result.status == Status.PASS
        tally = val_result.details["tally"]

        # Ensure all 3 score tiers exist in result
        assert "score_func" in tally
        assert "score_tactic" in tally
        assert "score_qa" in tally
        assert "performance" in tally["score_qa"]
        assert "availability" in tally["score_qa"]
        assert 0.0 <= tally["overall_score"] <= 1.0

    def test_claude_latest_benchmark(self, tmp_path):
        app_path = PIPELINE_ROOT.parent / "claude-latest"
        if not app_path.exists() or not (app_path / "nfr-trace.json").is_file():
            pytest.skip("Claude latest benchmark app not found")

        config = {"output": {"report_dir": str(tmp_path / "reports")}}
        validator = StaticQualityAttributeValidator(config=config)
        gen_res = GenerationResult(status=Status.PASS, model="claude-latest", code=str(app_path))

        val_result = validator.validate(gen_res)
        assert val_result.status == Status.PASS
        tally = val_result.details["tally"]

        assert "score_func" in tally
        assert "score_tactic" in tally
        assert "score_qa" in tally
        assert "performance" in tally["score_qa"]
        assert "availability" in tally["score_qa"]
        assert 0.0 <= tally["overall_score"] <= 1.0

