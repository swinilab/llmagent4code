"""G0 -- artifact completeness, clean build, and startup.

The entry gate. Everything downstream assumes a running system, so a failure
here yields NOT_EXECUTABLE for the whole application and no scenario is
attempted: a system that never started has not been shown to lack any tactic.

Two properties are checked that a simple "does it respond" probe would miss:

  * the system starts from the command the submission itself declares, not one
    we invent on its behalf, and with no manual intervention afterwards;

  * it stays up. An application that crash-loops while Docker restarts it will
    answer HTTP perfectly well between restarts, so restart counts are sampled
    after a settling period rather than only at first response.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..harness.compose import Compose, DeploymentError
from ..harness.toxiproxy import Toxiproxy, ToxiproxyError
from ..report.schema import Assertion, Evidence, GateResult, assert_that

REQUIRED_FILES = (
    "README.md",
    "start_command.txt",
    "create_apis.json",
    "workflow_apis.json",
    "nfr-trace.json",
    "openapi.json",
    "Dockerfile",
    "docker-compose.yml",
    "alembic.ini",
    "architecture/ADRs.md",
    "architecture/tactic-traceability.md",
    "docs/API_CONTRACT.md",
)

PARSEABLE_JSON = ("create_apis.json", "workflow_apis.json", "nfr-trace.json", "openapi.json")

# Long enough for a crash-loop to reveal itself, short enough not to dominate
# a five-run evaluation.
SETTLE_SECONDS = 20


def run(
    app_dir: Path,
    compose: Compose,
    base_url: str,
    thresholds: dict,
    toxi: Toxiproxy | None = None,
) -> GateResult:
    assertions: list[Assertion] = []
    details: dict = {}

    assertions += _check_artifacts(app_dir)

    # A missing or malformed start command makes startup untestable, so stop
    # here rather than reporting a misleading build failure.
    try:
        command = compose.declared_start_command()
        assertions.append(
            assert_that("start_command.txt declares a single command", True,
                        "one non-empty line", command, evidence=Evidence.ARTIFACT)
        )
        details["start_command"] = command
    except DeploymentError as exc:
        assertions.append(
            assert_that("start_command.txt declares a single command", False,
                        "one non-empty line", str(exc), evidence=Evidence.ARTIFACT)
        )
        return GateResult("G0", False, assertions, details)

    # ── build and start ───────────────────────────────────────────────────
    started_at = time.monotonic()
    try:
        compose.up()
        build_ok, build_detail = True, "succeeded"
    except DeploymentError as exc:
        build_ok, build_detail = False, str(exc)[-1500:]

    assertions.append(
        assert_that("clean build and startup", build_ok, "exit status 0", build_detail)
    )
    if not build_ok:
        details["logs"] = _safe_logs(compose)
        return GateResult("G0", False, assertions, details)

    # ── readiness ─────────────────────────────────────────────────────────
    try:
        ready_after = compose.wait_until_ready(base_url)
        assertions.append(
            assert_that("/health/ready reaches 200 unaided", True,
                        "200 with no manual step", f"after {ready_after:.1f}s")
        )
        details["ready_after_s"] = round(ready_after, 2)
        details["startup_total_s"] = round(time.monotonic() - started_at, 2)
    except DeploymentError as exc:
        assertions.append(
            assert_that("/health/ready reaches 200 unaided", False, "200", str(exc))
        )
        details["logs"] = _safe_logs(compose)
        return GateResult("G0", False, assertions, details)

    assertions.append(_liveness(base_url))

    # ── stability ─────────────────────────────────────────────────────────
    # Sampled after settling: a crash-looping container answers fine in between.
    time.sleep(SETTLE_SECONDS)
    restarts = compose.total_restarts()
    assertions.append(
        assert_that(
            "no container restarts during settling",
            restarts == 0,
            0,
            restarts,
            note=f"sampled {SETTLE_SECONDS}s after readiness; a crash loop shows up here",
        )
    )
    details["restart_count"] = restarts

    states = compose.inspect()
    not_running = [c.name for c in states if not c.running]
    assertions.append(
        assert_that("every container is running", not not_running, "all running",
                    ", ".join(not_running) or "all running")
    )
    details["containers"] = [
        {"name": c.name, "running": c.running, "restarts": c.restart_count} for c in states
    ]

    # ── migrations ────────────────────────────────────────────────────────
    assertions.append(_migrations_applied(compose))

    # ── deployment contract ───────────────────────────────────────────────
    if toxi is not None:
        assertions.append(_toxiproxy_contract(toxi, thresholds))

    assertions.append(_config_echoed(compose, thresholds))

    if not all(a.passed for a in assertions):
        details["logs"] = _safe_logs(compose)

    return GateResult("G0", all(a.passed for a in assertions), assertions, details)


# ── individual checks ─────────────────────────────────────────────────────


def _check_artifacts(app_dir: Path) -> list[Assertion]:
    out: list[Assertion] = []
    missing = [f for f in REQUIRED_FILES if not (app_dir / f).exists()]
    out.append(
        assert_that(
            "required artifacts present",
            not missing,
            f"{len(REQUIRED_FILES)} files",
            f"missing: {missing}" if missing else "all present",
            evidence=Evidence.ARTIFACT,
        )
    )

    # Machine-readable files must actually parse; a downstream gate reading a
    # broken manifest would report a confusing error far from its cause.
    for name in PARSEABLE_JSON:
        path = app_dir / name
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            ok, detail = True, "parsed"
        except (ValueError, UnicodeDecodeError) as exc:
            ok, detail = False, str(exc)[:200]
        out.append(
            assert_that(f"{name} parses as JSON", ok, "valid JSON", detail,
                        evidence=Evidence.ARTIFACT)
        )
    return out


def _liveness(base_url: str) -> Assertion:
    import httpx

    try:
        with httpx.Client(timeout=5.0) as client:
            status = client.get(f"{base_url}/health/live").status_code
        return assert_that("/health/live responds 200", status == 200, 200, status)
    except httpx.RequestError as exc:
        return assert_that("/health/live responds 200", False, 200, str(exc))


def _migrations_applied(compose: Compose) -> Assertion:
    """Confirm migrations ran as part of startup, not as a manual step.

    Evidence is taken from the startup logs rather than from the schema, because
    a schema created by SQLAlchemy's create_all would look identical while
    leaving the required Alembic migration path untested.
    """
    logs = _safe_logs(compose).lower()
    markers = ("alembic", "running upgrade", "migration")
    found = [m for m in markers if m in logs]
    return assert_that(
        "migrations ran automatically at startup",
        bool(found),
        "alembic upgrade evident in startup logs",
        f"markers found: {found}" if found else "no migration evidence in logs",
        note="the specification requires migrations to run without a manual step",
    )


def _toxiproxy_contract(toxi: Toxiproxy, thresholds: dict) -> Assertion:
    """Verify the database really is reached through the proxy.

    This is load-bearing for the whole availability half of the study. An
    application wired straight to db:5432 would pass ASR-A1 and ASR-A3 without
    implementing anything, because our injected faults would simply miss it.
    """
    cfg = thresholds["toxiproxy"]
    try:
        toxi.verify_contract(cfg["proxy_name"], cfg["upstream"])
        state = toxi.state(cfg["proxy_name"])
        return assert_that(
            "database traffic is routed through Toxiproxy",
            state.enabled,
            f"proxy {cfg['proxy_name']} -> {cfg['upstream']}, enabled",
            f"{state.listen} -> {state.upstream}, enabled={state.enabled}",
        )
    except ToxiproxyError as exc:
        return assert_that(
            "database traffic is routed through Toxiproxy", False,
            f"proxy {cfg['proxy_name']} -> {cfg['upstream']}", str(exc),
            note="without this, injected database faults cannot reach the application",
        )


def _config_echoed(compose: Compose, thresholds: dict) -> Assertion:
    """Check the effective configuration matches what the scenarios assume.

    The thresholds are derived from specific configured values -- ten in-flight
    requests, three attempts, a five-second TTL. Measuring a differently
    configured system would produce numbers that are not comparable with the
    other applications, so the startup log line is used to confirm them.
    """
    logs = _safe_logs(compose)
    expected = thresholds["app_config"]
    keys_to_check = ("MAX_IN_FLIGHT_REQUESTS", "DB_MAX_ATTEMPTS", "CACHE_TTL_SECONDS")

    mismatches: list[str] = []
    unverifiable: list[str] = []
    for key in keys_to_check:
        want = str(expected[key])
        if key not in logs:
            unverifiable.append(key)
        elif not _value_near_key(logs, key, want):
            mismatches.append(f"{key} != {want}")

    if mismatches:
        return assert_that("effective configuration matches the specification", False,
                           "specified values", "; ".join(mismatches))
    return assert_that(
        "effective configuration matches the specification",
        True,
        "specified values",
        f"verified {len(keys_to_check) - len(unverifiable)}/{len(keys_to_check)}"
        + (f"; not echoed: {unverifiable}" if unverifiable else ""),
        note="read from the startup log line the specification requires",
    )


def _value_near_key(logs: str, key: str, value: str) -> bool:
    """Look for a key and its expected value on the same log line.

    Deliberately format-agnostic: the specification mandates one structured line
    but not its exact field layout, so requiring a particular JSON shape would
    fail applications that satisfy the requirement in a different style.
    """
    for line in logs.splitlines():
        if key in line and value in line:
            return True
    return False


def _safe_logs(compose: Compose, tail: int = 3000) -> str:
    try:
        return compose.logs(tail=tail)
    except Exception:
        return ""
