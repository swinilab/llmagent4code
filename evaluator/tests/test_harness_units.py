"""Unit checks for the parts of the harness that decide pass/fail.

Percentiles, rate arithmetic and verdict aggregation are what turn observations
into the numbers printed in the paper, so they are tested directly rather than
being trusted to be obviously right. A silent off-by-one in the percentile rank
would shift every latency figure in the results tables.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluator.harness.context import Thresholds
from evaluator.harness.httpclient import Response, Workload
from evaluator.report.schema import (
    Assertion,
    Evidence,
    Result,
    ScenarioRun,
    ScenarioSummary,
    assert_that,
)


def _resp(status: int | None, ms: float, body=None) -> Response:
    return Response(status=status, elapsed_ms=ms, body=body)


def test_percentile_uses_nearest_rank_without_interpolation() -> None:
    w = Workload([_resp(200, float(i)) for i in range(1, 101)])
    # 95th of 1..100 by nearest rank is the 95th value, not an interpolated 95.5
    assert w.percentile_ms(95) == 95.0
    assert w.percentile_ms(100) == 100.0
    assert w.percentile_ms(1) == 1.0


def test_percentile_keeps_slow_outliers() -> None:
    """A hung request must not be smoothed away -- it is the failure signal."""
    w = Workload([_resp(200, 10.0) for _ in range(95)] + [_resp(503, 9000.0) for _ in range(5)])
    assert w.p95_ms() == 10.0
    assert w.max_ms() == 9000.0
    assert w.hanging(threshold_s=4.5) == 5


def test_transport_errors_count_as_failures_not_gaps() -> None:
    w = Workload([_resp(200, 5.0), _resp(None, 30000.0)])
    assert w.success_rate() == 0.5
    assert w.status_distribution()["transport_error"] == 1


def test_controlled_500_is_not_an_unhandled_500() -> None:
    """ASR-A4's injected failure answers 500 by design; that must not be counted."""
    controlled = _resp(500, 12.0, {"error": {"code": "TRANSACTION_FAILED", "message": "x"}})
    genuine = _resp(500, 12.0, {"detail": "Internal Server Error"})
    assert Workload([controlled]).unhandled_500s() == 0
    assert Workload([genuine]).unhandled_500s() == 1


def test_error_code_extraction() -> None:
    r = _resp(503, 1.0, {"error": {"code": "DEPENDENCY_TIMEOUT", "message": "slow"}})
    assert r.error_code() == "DEPENDENCY_TIMEOUT"
    assert _resp(503, 1.0, {"error": "flat string"}).error_code() is None
    assert _resp(200, 1.0, "not json").error_code() is None


def test_scenario_verdict_is_derived_from_assertions() -> None:
    passing = [assert_that("a", True, 1, 1), assert_that("b", True, 2, 2)]
    failing = passing + [assert_that("c", False, 3, 4)]
    assert ScenarioRun.from_assertions("app", "ASR-A2", 0, passing, {}).result is Result.PASS
    assert ScenarioRun.from_assertions("app", "ASR-A2", 0, failing, {}).result is Result.FAIL


def test_deterministic_scenarios_require_every_run() -> None:
    """Retry and Transactions are 5/5: one flake is a real defect, not noise."""
    runs = [
        ScenarioRun("app", "ASR-A2", i, Result.PASS if i < 4 else Result.FAIL) for i in range(5)
    ]
    assert ScenarioSummary("ASR-A2", runs, required_passes=5).result is Result.FAIL
    assert ScenarioSummary("ASR-P1", runs, required_passes=4).result is Result.PASS


def test_short_runs_are_judged_proportionally() -> None:
    """A one-run session must not demand five passes.

    The repetition policy is written for five runs. Taken literally at shorter
    lengths it marks every scenario FAIL no matter what happened -- which is
    what a calibration run against a known-good application first exposed.
    """
    passing = [ScenarioRun("x", "ASR-A2", 0, Result.PASS)]
    assert ScenarioSummary("ASR-A2", passing, required_passes=5).result is Result.PASS
    assert ScenarioSummary("ASR-P1", passing, required_passes=4).result is Result.PASS

    failing = [ScenarioRun("x", "ASR-A2", 0, Result.FAIL)]
    assert ScenarioSummary("ASR-A2", failing, required_passes=5).result is Result.FAIL

    # At full length the stated policy applies unchanged.
    four_of_five = [
        ScenarioRun("x", "ASR-P1", i, Result.PASS if i < 4 else Result.FAIL) for i in range(5)
    ]
    assert ScenarioSummary("ASR-P1", four_of_five, required_passes=4).result is Result.PASS
    assert ScenarioSummary("ASR-A2", four_of_five, required_passes=5).result is Result.FAIL


def test_deterministic_scenarios_tolerate_nothing_at_any_length() -> None:
    """Retry and transactions allow no failures, however many runs there are."""
    for n in (1, 2, 3, 5):
        runs = [ScenarioRun("x", "ASR-A4", i, Result.PASS) for i in range(n - 1)]
        runs.append(ScenarioRun("x", "ASR-A4", n - 1, Result.FAIL))
        assert ScenarioSummary("ASR-A4", runs, required_passes=5).result is Result.FAIL


def test_scenario_id_survives_serialisation() -> None:
    """The report must name its scenarios in the spelling readers expect.

    The dataclass field is snake_case while every identifier the study exchanges
    is camelCase; without an alias the obvious lookup returns nothing and the
    results tables come out blank.
    """
    import json

    from evaluator.report.schema import AppReport

    report = AppReport(app_id="x")
    report.scenarios.append(
        ScenarioSummary("ASR-P1", [ScenarioRun("x", "ASR-P1", 0, Result.PASS)], 4)
    )
    encoded = json.loads(report.to_json())["scenarios"][0]
    assert encoded["scenarioId"] == "ASR-P1"
    assert encoded["runs_performed"] == 1
    assert encoded["effective_requirement"] == 1


def test_unexercisable_never_becomes_fail() -> None:
    """Missing an interface is not evidence the tactic is absent."""
    runs = [ScenarioRun.not_exercisable("app", "ASR-A1", i, "no metrics endpoint") for i in range(5)]
    summary = ScenarioSummary("ASR-A1", runs, required_passes=4)
    assert summary.result is Result.NOT_EXERCISABLE
    assert summary.pass_count == 0


def test_summary_reports_median_and_range() -> None:
    runs = [
        ScenarioRun("app", "ASR-P1", i, Result.PASS, observations={"p95_ms": v})
        for i, v in enumerate([120.0, 90.0, 150.0, 110.0, 130.0])
    ]
    s = ScenarioSummary("ASR-P1", runs, required_passes=4)
    assert s.median("p95_ms") == 120.0
    assert s.range("p95_ms") == (90.0, 150.0)


def test_thresholds_match_the_generation_prompt() -> None:
    """Guard against the evaluator drifting from the prompt the agents received.

    These specific numbers were relaxed from earlier drafts for stated technical
    reasons; if the prompt is ever re-tightened this test fails loudly rather
    than letting us score agents against a criterion they were never given.
    """
    t = Thresholds.load(ROOT / "evaluator" / "thresholds.yaml")
    assert t["asr_p1"]["db_product_reads_max"] == 100
    assert t["asr_p1"]["measured_reads"] == 1000
    assert t["asr_a1"]["total_response_seconds_max"] == 4.5
    assert t["asr_a1"]["per_attempt_timeout_seconds_max"] == 1.2
    assert t["asr_a2"]["expected_attempt_delta"] == 3
    assert t["asr_a2"]["expected_retry_delta"] == 2
    assert t["asr_a2"]["expected_db_read_delta"] == 1
    assert t["repetition"]["required_passes"]["ASR-A2"] == 5
    assert t["repetition"]["required_passes"]["ASR-A4"] == 5
    assert t["app_config"]["MAX_IN_FLIGHT_REQUESTS"] == 10


def test_serialised_report_contains_the_verdicts() -> None:
    """The verdicts are computed properties, which asdict() silently drops.

    Without folding them back in, the emitted file carries every observation but
    no PASS/FAIL -- the one thing the results tables are built from. The loss is
    invisible until someone reads the file, so it is asserted here.
    """
    import json

    from evaluator.report.schema import AppReport, GateResult

    report = AppReport(app_id="x")
    report.gates.append(GateResult("G0", True))
    report.scenarios.append(
        ScenarioSummary(
            "ASR-A2",
            [ScenarioRun("x", "ASR-A2", i, Result.PASS) for i in range(5)],
            required_passes=5,
        )
    )
    payload = json.loads(report.to_json())
    assert payload["scenarios"][0]["result"] == "PASS"
    assert payload["scenarios"][0]["pass_count"] == 5
    assert payload["tactic_pass_rate"] > 0


def test_cache_scenario_isolates_a_single_refill() -> None:
    """ASR-P1 must probe one refill, not just aggregate throughput.

    Over a thousand reads the few TTL refills cost so little that a cache
    loading once per reader is indistinguishable from one loading once per
    refill -- a calibration run with single-flight deliberately disabled passed
    comfortably. Only timing the expiry and hitting it with every reader at once
    separates them, so the scenario must contain that probe.
    """
    import ast
    import inspect
    import textwrap

    from evaluator.gates.g3 import asr_p1_cache

    probe = textwrap.dedent(inspect.getsource(asr_p1_cache._measure_refill_cost))
    tree = ast.parse(probe)
    calls = {
        n.func.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    # Warm, wait past the TTL, then arrive together -- all three are required
    # for the entry to be expired at the moment the readers hit it.
    assert "sleep" in calls, "the probe must let the entry expire"
    assert "run_simultaneous" in calls, "readers must arrive together, not in sequence"

    # The tolerance must stay well below any plausible concurrency, or a cache
    # without single-flight would slip under it.
    assert asr_p1_cache._SINGLE_FLIGHT_TOLERANCE < 10


def test_recreate_always_waits_for_readiness() -> None:
    """A failed bring-up must not skip the readiness wait.

    recreate() tears the old stack down before anything can go wrong, so
    abandoning the wait on error leaves nothing running -- and the next scenario
    fails with a connection error that reads like an application defect. A
    calibration run hit exactly that when a registry lookup broke `--build`.
    """
    import ast
    import inspect
    import textwrap

    from evaluator.run import _recreate

    tree = ast.parse(textwrap.dedent(inspect.getsource(_recreate)))

    # The wait must not sit inside the same try as the bring-up, where an
    # exception from recreate() would jump straight past it.
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            body_calls = {
                n.func.attr
                for stmt in node.body
                for n in ast.walk(stmt)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            }
            assert not {"recreate", "wait_until_ready"} <= body_calls, (
                "bring-up and readiness wait share a try block; a failed build "
                "would skip the wait"
            )

    calls = {
        n.func.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert "wait_until_ready" in calls


def test_burst_workload_does_not_queue_on_its_own_pool() -> None:
    """The overload stimulus must not throttle itself before reaching the server.

    ASR-P2 measures how quickly the server refuses. If the client's connection
    pool is smaller than the burst, requests wait for a slot and that wait lands
    inside the measured time -- a server refusing in nine milliseconds was
    recorded at 2.4 seconds this way, which reads exactly like the bounded queue
    the tactic is defined against.
    """
    import ast
    import inspect
    import textwrap

    from evaluator.harness.httpclient import HttpHarness

    source = textwrap.dedent(inspect.getsource(HttpHarness._run_burst))
    tree = ast.parse(source)

    limits = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Limits"
    ]
    assert limits, "the burst path must configure its own connection limits"

    kwargs = {k.arg: k.value for call in limits for k in call.keywords}
    # Keep-alive must be off: a finished request handing its connection to a
    # waiting one serialises the two and inflates the measurement.
    assert isinstance(kwargs.get("max_keepalive_connections"), ast.Constant)
    assert kwargs["max_keepalive_connections"].value == 0
    # The pool must exceed the burst so nothing waits for a slot.
    assert isinstance(kwargs.get("max_connections"), ast.BinOp)


def test_background_probes_do_not_shadow_thread_internals() -> None:
    """A probe thread must not define attributes threading.Thread owns.

    threading.Thread already has a `_stop`, and overwriting it with an Event
    replaces a method the base class calls during teardown. The failure appears
    only when the thread is actually stopped, so no unit test of the probe's
    logic would reach it -- a live run did.
    """
    import threading

    from evaluator.gates.g3.asr_p2_overload import _HealthProbe

    reserved = {n for n in dir(threading.Thread) if n.startswith("_")}
    declared = set(_HealthProbe.__init__.__code__.co_names)
    collisions = {n for n in declared if n in reserved and n != "__init__"}
    assert not collisions, f"probe shadows Thread internals: {collisions}"


def test_observation_paths_are_declared() -> None:
    """Losing metrics mid-fault is a FAIL, not an inability to measure.

    The prompt states the observation paths must stay servable under every
    condition it exercises, so an application that answers before a fault and
    goes silent after it has failed a stated requirement. Reserving
    NOT_EXERCISABLE for paths that were never usable keeps that distinction.
    """
    t = Thresholds.load(ROOT / "evaluator" / "thresholds.yaml")
    survive = t["observation_paths"]["must_survive_fault"]
    assert "/internal/metrics" in survive
    assert "/health/live" in survive
    # readiness may legitimately report unready, so it is classified separately
    assert "/health/ready" not in survive
    assert "/health/ready" in t["observation_paths"]["must_answer_but_may_report_unready"]


def test_evidence_is_recorded_per_assertion() -> None:
    """Every assertion must state whether it is external or self-reported."""
    a = assert_that("x", True, 1, 1, evidence=Evidence.APP_REPORTED)
    assert a.evidence is Evidence.APP_REPORTED
    assert Assertion("y", "1", "1", True).evidence is Evidence.EXTERNAL