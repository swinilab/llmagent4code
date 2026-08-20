"""
test_scoring_engine.py
───────────────────────
Unit and integration tests for the Static QA Scoring Engine mapped to plan.md Part 3.

Covers:
  - compute_score1: binary scoring (PRESENT=1.0, WEAK=0.0, ABSENT=0.0)
  - compute_score2: tactic-level function mean (sum(score1) / num_functions)
  - compute_score3: QA-level tactic mean (avg(score2-by-qa))
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
    compute_score1,
    compute_score2,
    compute_score3,
)


class TestScore1:
    """Tests for score1(tactic, function) -> absent (0)/present (1)."""

    def test_score1_present(self):
        assert compute_score1(PRESENT) == 1.0

    def test_score1_weak_stub(self):
        assert compute_score1(WEAK) == 0.0

    def test_score1_absent(self):
        assert compute_score1(ABSENT) == 0.0

    def test_score1_unknown_status(self):
        assert compute_score1("UNKNOWN") == 0.0


class TestScore2:
    """Tests for score2(tactic, function-in-trace) = % sum(score1)/num-functions."""

    def test_score2_empty(self):
        assert compute_score2([]) == 0.0

    def test_score2_all_present(self):
        assert compute_score2([1.0, 1.0, 1.0]) == 1.0

    def test_score2_mixed(self):
        # 2 present (1.0), 1 stub (0.0) -> 2/3 ≈ 0.6667
        score = compute_score2([1.0, 0.0, 1.0])
        assert pytest.approx(score, 0.0001) == 2.0 / 3.0

    def test_score2_all_absent_or_weak(self):
        assert compute_score2([0.0, 0.0]) == 0.0


class TestScore3:
    """Tests for score3(qa, tacticset) = avg(score2-by-qa)."""

    def test_score3_empty(self):
        assert compute_score3([]) == 0.0

    def test_score3_single_tactic(self):
        assert compute_score3([0.8]) == 0.8

    def test_score3_multiple_tactics(self):
        # Tactic A: 1.0, Tactic B: 0.5 -> avg: 0.75
        assert compute_score3([1.0, 0.5]) == 0.75

    def test_score3_four_tactics(self):
        # Availability with 4 tactics: [1.0, 0.5, 0.0, 1.0] -> 2.5 / 4 = 0.625
        assert pytest.approx(compute_score3([1.0, 0.5, 0.0, 1.0]), 0.0001) == 0.625


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
                    {"ref": "rate_limiter.py::allow", "status": PRESENT, "score1": 1.0},
                    {"ref": "middleware.py::dispatch", "status": PRESENT, "score1": 1.0},
                ],
            },
            {
                "nfr": "NFR 1.2: Maintain Multiple Copies of Data",
                "qa_group": "performance",
                "tactics": ["Maintain Multiple Copies of Data"],
                "functions": [
                    {"ref": "cache.py::get", "status": PRESENT, "score1": 1.0},
                    {"ref": "cache.py::set", "status": WEAK, "score1": 0.0},
                ],
            },
            {
                "nfr": "NFR 2.1: Exception Detection",
                "qa_group": "availability",
                "tactics": ["Exception Detection"],
                "functions": [
                    {"ref": "middleware.py::catch", "status": PRESENT, "score1": 1.0},
                ],
            },
        ]

        hierarchy = build_scoring_hierarchy(mock_results)

        # 1. Check score1 mapping
        assert hierarchy["score1"]["Limit Event Response"]["rate_limiter.py::allow"] == 1.0
        assert hierarchy["score1"]["Limit Event Response"]["middleware.py::dispatch"] == 1.0
        assert hierarchy["score1"]["Maintain Multiple Copies of Data"]["cache.py::get"] == 1.0
        assert hierarchy["score1"]["Maintain Multiple Copies of Data"]["cache.py::set"] == 0.0
        assert hierarchy["score1"]["Exception Detection"]["middleware.py::catch"] == 1.0

        # 2. Check score2 mapping
        assert hierarchy["score2"]["Limit Event Response"] == 1.0
        assert hierarchy["score2"]["Maintain Multiple Copies of Data"] == 0.5
        assert hierarchy["score2"]["Exception Detection"] == 1.0

        # 3. Check score3 mapping
        # Performance has 2 tactics: 1.0 and 0.5 -> avg = 0.75
        assert hierarchy["score3"]["performance"] == 0.75
        # Availability has 1 tactic: 1.0 -> avg = 1.0
        assert hierarchy["score3"]["availability"] == 1.0

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

        # score1 checks:
        # RateLimiter.allow is PRESENT -> 1.0
        assert tally["score1"]["Limit Event Response"]["app/rate_limiter.py::RateLimiter.allow"] == 1.0
        # Cache.get is WEAK (stub) -> 0.0
        assert tally["score1"]["Maintain Multiple Copies of Data"]["app/cache.py::Cache.get"] == 0.0
        # RateLimiter.missing_func is ABSENT -> 0.0
        assert tally["score1"]["Exception Detection"]["app/rate_limiter.py::RateLimiter.missing_func"] == 0.0

        # score2 checks:
        assert tally["score2"]["Limit Event Response"] == 1.0
        assert tally["score2"]["Maintain Multiple Copies of Data"] == 0.0
        assert tally["score2"]["Exception Detection"] == 0.0

        # score3 checks:
        # Performance: (1.0 + 0.0) / 2 = 0.5
        assert tally["score3"]["performance"] == 0.5
        # Availability: 0.0 / 1 = 0.0
        assert tally["score3"]["availability"] == 0.0

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
        assert "score1" in tally
        assert "score2" in tally
        assert "score3" in tally
        assert "performance" in tally["score3"]
        assert "availability" in tally["score3"]
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

        assert "score1" in tally
        assert "score2" in tally
        assert "score3" in tally
        assert "performance" in tally["score3"]
        assert "availability" in tally["score3"]
        assert 0.0 <= tally["overall_score"] <= 1.0

