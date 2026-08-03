"""Result types shared by every gate and scenario.

A scenario never decides its own verdict in prose. It emits a list of typed
assertions, each carrying what was expected, what was observed, and where the
observation came from; the verdict is then derived mechanically. That keeps the
pass/fail rule identical across all six scenarios and all three applications,
and it means a FAIL in the results table can always be traced to the specific
assertion and the specific number that produced it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Sequence


class Result(str, Enum):
    """The four outcomes a scenario may receive.

    NOT_EXECUTABLE and NOT_EXERCISABLE are kept distinct from FAIL on purpose:
    an application that cannot be started, or that lacks the interface a
    stimulus needs, has not been shown to lack the tactic. Collapsing these into
    FAIL would overstate what the study observed.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EXECUTABLE = "NOT_EXECUTABLE"
    NOT_EXERCISABLE = "NOT_EXERCISABLE"


class Evidence(str, Enum):
    """Where an observation came from, ranked by independence."""

    EXTERNAL = "external"          # client, docker, postgres, toxiproxy
    APP_REPORTED = "app_reported"  # /internal/metrics
    ARTIFACT = "artifact"          # files in the repository


@dataclass
class Assertion:
    name: str
    expected: str
    actual: str
    passed: bool
    evidence: Evidence = Evidence.EXTERNAL
    note: str = ""


def assert_that(
    name: str,
    passed: bool,
    expected: Any,
    actual: Any,
    evidence: Evidence = Evidence.EXTERNAL,
    note: str = "",
) -> Assertion:
    return Assertion(name, str(expected), str(actual), bool(passed), evidence, note)


@dataclass
class ScenarioRun:
    """One execution of one scenario against one application."""

    app_id: str
    scenario_id: str
    run_index: int
    result: Result
    assertions: list[Assertion] = field(default_factory=list)
    observations: dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0
    error: str | None = None
    logs_excerpt: str = ""

    @classmethod
    def from_assertions(
        cls,
        app_id: str,
        scenario_id: str,
        run_index: int,
        assertions: Sequence[Assertion],
        observations: dict[str, Any],
        duration_s: float = 0.0,
        logs_excerpt: str = "",
    ) -> "ScenarioRun":
        result = Result.PASS if all(a.passed for a in assertions) else Result.FAIL
        return cls(
            app_id=app_id,
            scenario_id=scenario_id,
            run_index=run_index,
            result=result,
            assertions=list(assertions),
            observations=observations,
            duration_s=duration_s,
            logs_excerpt=logs_excerpt,
        )

    @classmethod
    def not_exercisable(
        cls, app_id: str, scenario_id: str, run_index: int, reason: str
    ) -> "ScenarioRun":
        return cls(app_id, scenario_id, run_index, Result.NOT_EXERCISABLE, error=reason)

    @classmethod
    def not_executable(
        cls, app_id: str, scenario_id: str, run_index: int, reason: str
    ) -> "ScenarioRun":
        return cls(app_id, scenario_id, run_index, Result.NOT_EXECUTABLE, error=reason)

    def failed_assertions(self) -> list[Assertion]:
        return [a for a in self.assertions if not a.passed]


@dataclass
class ScenarioSummary:
    """A scenario's verdict across its repeated runs."""

    scenario_id: str
    runs: list[ScenarioRun]
    required_passes: int

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.runs if r.result is Result.PASS)

    # The repetition policy is stated for the five-run protocol: 5/5 for the
    # deterministic scenarios, 4/5 elsewhere.
    PROTOCOL_RUNS = 5

    @property
    def effective_requirement(self) -> int:
        """Passes needed, scaled to the number of runs actually performed.

        The policy is written for five runs, but shorter runs are used during
        calibration and debugging. Applying the five-run figure to a one-run
        session would demand five passes from one execution and mark every
        scenario FAIL regardless of what happened -- so the tolerance is scaled
        instead of the requirement being taken literally.

        A scenario allowed no failures at five runs is allowed none at any
        length; one allowed a single failure keeps that allowance only once
        there are enough runs for it to be meaningful.
        """
        performed = len(self.runs)
        if performed >= self.PROTOCOL_RUNS:
            return self.required_passes
        tolerated = self.PROTOCOL_RUNS - self.required_passes
        return max(1, performed - min(tolerated, performed - 1))

    @property
    def result(self) -> Result:
        """Aggregate verdict over the repetitions.

        A scenario that could never be exercised stays NOT_EXERCISABLE rather
        than becoming a FAIL by attrition.
        """
        if not self.runs:
            return Result.NOT_EXECUTABLE
        if all(r.result is Result.NOT_EXERCISABLE for r in self.runs):
            return Result.NOT_EXERCISABLE
        if all(r.result is Result.NOT_EXECUTABLE for r in self.runs):
            return Result.NOT_EXECUTABLE
        return Result.PASS if self.pass_count >= self.effective_requirement else Result.FAIL

    def observation_series(self, key: str) -> list[float]:
        out: list[float] = []
        for r in self.runs:
            v = r.observations.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(float(v))
        return out

    def median(self, key: str) -> float | None:
        vals = sorted(self.observation_series(key))
        if not vals:
            return None
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2

    def range(self, key: str) -> tuple[float, float] | None:
        vals = self.observation_series(key)
        return (min(vals), max(vals)) if vals else None


@dataclass
class GateResult:
    gate: str                      # "G0" | "G1" | "G2"
    passed: bool
    assertions: list[Assertion] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AppReport:
    """Everything observed about one generated application."""

    app_id: str
    gates: list[GateResult] = field(default_factory=list)
    scenarios: list[ScenarioSummary] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def tactic_pass_rate(self) -> float:
        """Fraction of the six prescribed tactic scenarios that passed.

        Reported alongside the raw measures, never instead of them: a rate of
        4/6 says nothing about which two failed or by how much.
        """
        if not self.scenarios:
            return 0.0
        return sum(1 for s in self.scenarios if s.result is Result.PASS) / 6.0

    def gate(self, name: str) -> GateResult | None:
        return next((g for g in self.gates if g.gate == name), None)

    def to_json(self) -> str:
        payload = asdict(self)
        # `result` and `pass_count` are computed properties, so asdict() drops
        # them -- and they are the verdicts the results tables are built from.
        # They are folded back in explicitly rather than being recomputed by
        # every consumer of the file.
        #
        # `scenarioId` is also aliased here. The dataclass field is snake_case,
        # but every other identifier the study exchanges -- nfr-trace.json, the
        # manifests, the scenario ids themselves -- is camelCase, and a reader
        # reaching for the obvious spelling silently gets nothing back.
        for summary, encoded in zip(self.scenarios, payload["scenarios"]):
            encoded["scenarioId"] = summary.scenario_id
            encoded["result"] = summary.result.value
            encoded["pass_count"] = summary.pass_count
            encoded["runs_performed"] = len(summary.runs)
            encoded["effective_requirement"] = summary.effective_requirement
        payload["tactic_pass_rate"] = self.tactic_pass_rate()
        return json.dumps(payload, indent=2, default=_encode)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")


def _encode(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"cannot serialise {type(obj).__name__}")