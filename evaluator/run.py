"""Evaluation entry point.

    python -m evaluator.run --app path/to/generated/app --runs 5 \
                            --output evaluation-results/app-1

Runs the gates in order and stops early when continuing would be meaningless: a
system that will not start cannot be scored on anything, and recording six
speculative failures for it would misrepresent what was observed.

Reset policy, applied uniformly so runs stay comparable:

  between runs       POST /internal/test/reset -- clears counters, cache and
                     injected-fault state
  between scenarios  docker compose down -v && up -- a clean database, so the
                     orders one scenario leaves behind cannot perturb the next

The scenarios are ordered cheapest-first. When an application is badly broken
this surfaces it in seconds rather than after a sixty-second outage test.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

from .gates import g0_artifact, g2_traceability
from .gates.g1_functional import runner as g1_runner
from .gates.g3 import (
    asr_a1_timeout,
    asr_a2_retry,
    asr_a3_degradation,
    asr_a4_transaction,
    asr_p1_cache,
    asr_p2_overload,
)
from .harness import trace
from .harness.compose import Compose, DeploymentError
from .harness.context import Context, Thresholds
from .harness.pgprobe import PgProbe
from .harness.toxiproxy import Toxiproxy, ToxiproxyError
from .report.schema import AppReport, Result, ScenarioRun, ScenarioSummary

# Ordered by cost: a broken application fails the cheap ones immediately.
SCENARIOS = [
    ("ASR-A4", asr_a4_transaction.run),
    ("ASR-A2", asr_a2_retry.run),
    ("ASR-A1", asr_a1_timeout.run),
    ("ASR-P1", asr_p1_cache.run),
    ("ASR-P2", asr_p2_overload.run),
    ("ASR-A3", asr_a3_degradation.run),
]

# Used only for the human-readable trace header, so a reader does not have to
# remember which identifier is which tactic.
SCENARIO_TITLES = {
    "ASR-A1": "dependency timeout",
    "ASR-A2": "retry with backoff",
    "ASR-A3": "graceful degradation",
    "ASR-A4": "transaction rollback",
    "ASR-P1": "cache-backed read performance",
    "ASR-P2": "overload rejection",
}


def main(argv: list[str] | None = None) -> int:
    # Python block-buffers stdout when it is redirected to a file or a pipe, so
    # a run whose output is captured shows nothing at all until it exits. That
    # defeats the narration, whose value is in being watchable while a
    # sixty-second outage scenario is in progress. Line buffering is forced
    # here rather than left to the caller remembering `-u`.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):  # a replaced or unusual stdout
        pass

    args = _parse_args(argv)
    thresholds = Thresholds.load(args.thresholds)
    app_dir = Path(args.app).resolve()
    output = Path(args.output)

    if not app_dir.is_dir():
        print(f"error: {app_dir} is not a directory", file=sys.stderr)
        return 2

    report = AppReport(
        app_id=args.app_id or app_dir.name,
        metadata={
            "app_dir": str(app_dir),
            "runs_requested": args.runs,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "base_url": args.base_url,
        },
    )

    # One log per evaluation, named after the application, next to its report.
    # Appending rather than truncating keeps a repeated run of the same
    # application from silently destroying the evidence for the previous one.
    log_path = Path(args.trace_log) if args.trace_log else output / f"{report.app_id}.trace.jsonl"
    tracer = trace.configure(
        None if args.no_trace_log else log_path,
        console=not args.quiet,
        verbose_requests=args.verbose_requests,
    )
    report.metadata["trace_log"] = None if args.no_trace_log else str(log_path)
    # The log is appended to, so a marker is written first: without it, two
    # evaluations of the same application run days apart are one undifferentiated
    # stream of events.
    tracer.emit("session_start", **report.metadata)

    compose = Compose(app_dir, project_name=f"eval-{report.app_id}".lower())
    # The Toxiproxy API port is a host-side detail, so it can be overridden when
    # a stack is published on shifted ports to run alongside another one. The
    # in-network contract from thresholds.yaml is what the application must
    # honour and is checked separately in G0.
    toxi = Toxiproxy(port=args.toxiproxy_port or int(thresholds["toxiproxy"]["api_port"]))
    pg = PgProbe(args.dsn)

    try:
        _evaluate(report, args, thresholds, compose, toxi, pg)
    except KeyboardInterrupt:
        print("\ninterrupted; writing partial results", file=sys.stderr)
    finally:
        toxi.close()
        if not args.keep_running:
            _quietly(compose.down)
        report.metadata["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        report.metadata["trace_event_counts"] = tracer.counts()
        report.write(output / f"{report.app_id}.json")
        _print_summary(report, output, None if args.no_trace_log else log_path, tracer)
        tracer.close()

    g0 = report.gate("G0")
    return 0 if g0 and g0.passed else 1


def _evaluate(
    report: AppReport,
    args: argparse.Namespace,
    thresholds: Thresholds,
    compose: Compose,
    toxi: Toxiproxy,
    pg: PgProbe,
) -> None:
    # ── G0 ────────────────────────────────────────────────────────────────
    print("[G0] artifacts, build, startup")
    with trace.phase("G0 -- artifacts, build, startup", gate="G0"):
        g0 = g0_artifact.run(compose.app_dir, compose, args.base_url, thresholds.raw, toxi)
    report.gates.append(g0)
    _report_gate(g0)

    if not g0.passed:
        # Nothing downstream is meaningful without a running system.
        print("      -> NOT_EXECUTABLE; skipping remaining gates")
        report.scenarios = [
            ScenarioSummary(sid, [], _required(thresholds, sid)) for sid, _ in SCENARIOS
        ]
        return

    ctx = Context(report.app_id, args.base_url, compose, pg, toxi, thresholds)

    # ── G1 ────────────────────────────────────────────────────────────────
    print("[G1] functional correctness")
    with trace.phase("G1 -- functional correctness", gate="G1"):
        g1 = g1_runner.run(ctx)
    report.gates.append(g1)
    _report_gate(g1)
    print(
        f"      pass rate {g1.details['pass_rate']:.1%} "
        f"({g1.details['passed']}/{g1.details['total']}), "
        f"workflow {'PASS' if g1.details['critical_workflow_pass'] else 'FAIL'}"
    )

    # ── G2 ────────────────────────────────────────────────────────────────
    print("[G2] traceability and observability contract")
    with trace.phase("G2 -- traceability and observability", gate="G2"):
        g2 = g2_traceability.run(compose.app_dir, args.base_url, thresholds.raw)
    report.gates.append(g2)
    _report_gate(g2)
    exercisable = g2.details.get("exercisable_scenarios", {})

    # ── G3 ────────────────────────────────────────────────────────────────
    for scenario_id, run_fn in SCENARIOS:
        required = _required(thresholds, scenario_id)
        runs: list[ScenarioRun] = []

        if not exercisable.get(scenario_id, True):
            reason = "required observability interface unavailable"
            print(f"[G3] {scenario_id}: NOT_EXERCISABLE ({reason})")
            runs = [
                ScenarioRun.not_exercisable(report.app_id, scenario_id, i, reason)
                for i in range(args.runs)
            ]
            report.scenarios.append(ScenarioSummary(scenario_id, runs, required))
            continue

        print(f"[G3] {scenario_id} ({args.runs} runs, {required} required)")
        for index in range(args.runs):
            if index > 0:
                _reset_between_runs(ctx, toxi, compose, args)
            title = f"{scenario_id} -- {SCENARIO_TITLES.get(scenario_id, '')} (run {index + 1}/{args.runs})"
            with trace.phase(title, scenario=scenario_id, run=index):
                run = _one_run(ctx, run_fn, scenario_id, index, report.app_id)
            runs.append(run)
            _report_run(run, index, args.runs)

        summary = ScenarioSummary(scenario_id, runs, required)
        report.scenarios.append(summary)
        print(f"      -> {summary.result.value} ({summary.pass_count}/{args.runs})")
        trace.tracer().emit(
            "scenario_summary",
            scenario=scenario_id,
            result=summary.result.value,
            pass_count=summary.pass_count,
            runs=len(runs),
            required=summary.effective_requirement,
        )

        _recreate_between_scenarios(compose, toxi, args)


def _report_run(run: ScenarioRun, index: int, total: int) -> None:
    """Show what a finished run decided, assertion by assertion.

    The assertions are the scenario's own reasoning made explicit; echoing them
    here means a FAIL on the console already names the measurement that caused
    it, instead of requiring the JSON report to be opened.
    """
    print(f"      run {index + 1}/{total}: {run.result.value}")
    trace.assertions(run.assertions)
    if run.error:
        trace.note(f"error: {run.error}")
    if run.observations:
        trace.tracer().emit("observations", **run.observations)


def _one_run(ctx: Context, run_fn, scenario_id: str, index: int, app_id: str) -> ScenarioRun:
    """Execute one repetition, converting an unexpected crash into a result.

    An exception from the harness must not abort the whole evaluation; it is
    recorded against the run so the remaining scenarios still produce data.
    """
    try:
        return run_fn(ctx, index)
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        run = ScenarioRun(app_id, scenario_id, index, Result.FAIL, error=str(exc))
        run.observations["traceback"] = traceback.format_exc()[-2000:]
        return run


def _reset_between_runs(
    ctx: Context, toxi: Toxiproxy, compose: Compose, args: argparse.Namespace
) -> None:
    """Clear state between repetitions of the same scenario.

    A test reset clears counters, cache and injected-fault state, which is what
    repeated runs of one scenario need. Toxiproxy is reset too, so a fault left
    behind by a crashed run cannot be misread as the next run's own failure.

    Recreating containers here is available but off by default: it would add
    minutes to every scenario, and within a single scenario the accumulated data
    is the scenario's own and does not distort it.
    """
    _quietly(toxi.reset)
    _quietly(ctx.reset)
    if args.recreate_every_run:
        _recreate(compose, args)


def _recreate_between_scenarios(
    compose: Compose, toxi: Toxiproxy, args: argparse.Namespace
) -> None:
    """Restore a clean database before moving to the next scenario.

    ASR-A4 in particular leaves completed orders behind, and ASR-P1 leaves a
    product whose row was mutated behind the application's back. Carrying either
    into the next scenario would change what that scenario is measuring, so the
    volumes go with the containers.
    """
    _quietly(toxi.reset)
    _recreate(compose, args)


def _recreate(compose: Compose, args: argparse.Namespace) -> None:
    """Tear the stack down and bring it back, then wait for it to answer.

    Readiness is awaited even when the bring-up reports failure, and that is not
    belt-and-braces. `recreate` has already taken the old containers down by the
    time anything can go wrong, so abandoning the wait leaves nothing running
    and the next scenario fails with a connection error that looks like an
    application defect. A calibration run hit exactly that: a transient registry
    lookup broke `--build`, the wait was skipped, and the following scenario was
    scored against a stack that was still starting.
    """
    build_error: DeploymentError | None = None
    try:
        compose.recreate()
    except DeploymentError as exc:
        build_error = exc
        print(f"      warning: recreate failed: {exc}", file=sys.stderr)

    try:
        compose.wait_until_ready(args.base_url)
    except DeploymentError as exc:
        # Now the stack really is unusable. Say so plainly rather than letting
        # the next scenario report a misleading transport error.
        print(f"      ERROR: stack did not come back: {exc}", file=sys.stderr)
        if build_error is not None:
            print(f"      (bring-up had already failed: {build_error})", file=sys.stderr)


def _required(thresholds: Thresholds, scenario_id: str) -> int:
    return int(thresholds["repetition"]["required_passes"][scenario_id])


def _report_gate(gate) -> None:
    """Announce the verdict, then every assertion behind it.

    Failures were always printed; passes are now shown too, through the tracer.
    Seeing which checks were actually made -- and what each one observed -- is
    the difference between "G0 passed" and knowing the proxy contract, the
    health endpoints and the build were each verified.
    """
    status = "PASS" if gate.passed else "FAIL"
    trace.tracer().emit(
        "gate", gate=gate.gate, passed=gate.passed, details=gate.details
    )
    print(f"      {gate.gate}: {status}")
    trace.assertions(gate.assertions)
    if not trace.tracer().console:
        for a in gate.assertions:
            if not a.passed:
                print(f"        - {a.name}: expected {a.expected}, observed {a.actual}")


def _print_summary(
    report: AppReport, output: Path, log_path: Path | None, tracer: trace.Tracer
) -> None:
    print("\n" + "=" * 62)
    print(f"application: {report.app_id}")
    for gate in report.gates:
        print(f"  {gate.gate}: {'PASS' if gate.passed else 'FAIL'}")
    for s in report.scenarios:
        line = f"  {s.scenario_id}: {s.result.value}"
        if s.runs and s.result in (Result.PASS, Result.FAIL):
            line += f" ({s.pass_count}/{len(s.runs)})"
        print(line)
    passed = sum(1 for s in report.scenarios if s.result is Result.PASS)
    print(f"  tactic scenarios passed: {passed}/6 ({report.tactic_pass_rate():.1%})")
    print(f"  written to {output / (report.app_id + '.json')}")
    if log_path is not None:
        counts = tracer.counts()
        print(
            f"  trace log: {log_path} "
            f"({counts.get('http', 0)} requests, {sum(counts.values())} events)"
        )
    print("=" * 62)


def _quietly(fn) -> None:
    try:
        fn()
    except Exception:
        pass


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="evaluator.run", description=__doc__)
    p.add_argument("--app", required=True, help="path to the generated application repository")
    p.add_argument("--app-id", default=None, help="identifier used in the report")
    p.add_argument("--runs", type=int, default=5, help="repetitions per scenario")
    p.add_argument("--output", default="evaluation-results", help="output directory")
    p.add_argument("--base-url", default="http://localhost:8080")
    p.add_argument(
        "--dsn",
        default="postgresql://postgres:postgres@localhost:5432/postgres",
        help="direct PostgreSQL connection, bypassing Toxiproxy",
    )
    p.add_argument(
        "--toxiproxy-port",
        type=int,
        default=None,
        help="host port of the Toxiproxy API (default: the value in thresholds.yaml)",
    )
    p.add_argument(
        "--thresholds",
        default=str(Path(__file__).parent / "thresholds.yaml"),
        help="acceptance thresholds; must match the generation prompt",
    )
    p.add_argument(
        "--recreate-every-run",
        action="store_true",
        help="recreate containers between runs as well as between scenarios",
    )
    p.add_argument("--keep-running", action="store_true", help="leave containers up afterwards")
    p.add_argument(
        "--trace-log",
        default=None,
        help="JSONL request/response log (default: <output>/<app-id>.trace.jsonl)",
    )
    p.add_argument(
        "--no-trace-log",
        action="store_true",
        help="do not write the JSONL log; console narration is unaffected",
    )
    p.add_argument(
        "--verbose-requests",
        action="store_true",
        help="also print every individual request to the console (very noisy under load)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the step-by-step narration, keeping only gate and run verdicts",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
