"""
interfaces/base.py
──────────────────
Abstract contracts for every pipeline component.

main.py only imports these types; concrete behaviour lives in the
subclasses under agents/, validators/
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
import copy
import json
import requests


# ─────────────────────────────────────────────────────────────────────────────
#  Shared value objects
# ─────────────────────────────────────────────────────────────────────────────

class Status(Enum):
    PASS  = auto()
    FAIL  = auto()

@dataclass
class ValidationResult:
    """Returned by every validation stage."""
    stage:   str
    status:  Status
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status is Status.PASS

@dataclass
class GenerationResult:
    """Returned by the generation agent."""
    status: Status
    model: str
    code: str           # folder where agent generated app (generated/...)

# @dataclass
# class TestResult:
#     """Functional test result."""
#     result:             bool
#     testcase_id:        str
#     message:            str

@dataclass
class TestResult:
    """Functional test result."""
    result:             bool
    testcase_id:        str
    method:             str
    url:                str
    expected_status:    int
    actual_status:      int
    request_body:       Any
    response_body:      Any


# ─────────────────────────────────────────────────────────────────────────────
#  Report locations
# ─────────────────────────────────────────────────────────────────────────────

def app_label(code: str | Any) -> str:
    """Short name of the app under test, from its path under generated/ -
    e.g. "claude", "codex", "chatdev-qwen35-v1". Reports used to land in one
    flat folder separated only by timestamp, which made a run impossible to
    attribute to an app afterwards."""
    import re
    from pathlib import Path as _Path
    parts = [p for p in _Path(str(code)).parts if p not in (".", "..", "")]
    parts = [p for p in parts if p not in ("code_workspace", "generated")]
    label = parts[-1] if parts else "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "-", label) or "unknown"


def app_run_dir(report_dir: str | Any, stage_slug: str, code: str | Any):
    """`<report_dir>/<stage_slug>_<app>_<timestamp>/`, created.

    Every stage writes its artefacts into one folder per run per app, so a
    number can always be traced back to the app and the run that produced it.
    """
    from datetime import datetime as _dt
    from pathlib import Path as _Path
    path = _Path(report_dir) / (
        f"{stage_slug}_{app_label(code)}_{_dt.now().strftime('%Y%m%d_%H%M%S')}"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


# ─────────────────────────────────────────────────────────────────────────────
#  Abstract interfaces
# ─────────────────────────────────────────────────────────────────────────────
class IGenerationAgent(ABC):
    """Calls an LLM Agent and returns generated code."""

    @abstractmethod
    def generate(self, prompt: str) -> GenerationResult:
        ...

class ICompilabilityValidator(ABC):
    """Stage 1 – checks whether the code compiles/runs inside Docker."""

    @abstractmethod
    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        ...

class IFunctionalValidator(ABC):
    """Stage 2 – fires HTTP requests and checks expected responses."""

    @abstractmethod
    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        ...

class IStaticQualityValidator(ABC):
    """Stage 3 – verifies the NFR trace's claims (files/functions/libraries) exist."""

    @abstractmethod
    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        ...

class INFRValidator(ABC):
    """Stage 4 – runs runtime NFR checks (load, spike, fault injection)
    against a live instance of the generated app and compares measured
    values to fixed thresholds owned by the test harness (not by the
    candidate's own nfr-trace.json claims — those are verified separately
    by IStaticQualityValidator at stage 3)."""

    @abstractmethod
    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        ...

class IReportWriter(ABC):
    """Serialises the final pipeline outcome to report.txt."""

    @abstractmethod
    def write(
        self,
        generation:         GenerationResult | None,
        validation_results: list[ValidationResult],
        all_passed:         bool,
    ) -> str:                           # returns the path written
        ...

class ITestGroup(ABC):
    """
    Group the tests by entity
    Define new member function for each testcase
    Member function modifies standard_request_body to create desired input
    Member function create POST request to api with desired input and return TestResult
    """

    api: str
    standard_request_body = dict()
    testcases: list[str]

    def run_all(self) -> list[TestResult]:
        result = list[TestResult]()
        for t in self.testcases:
            result.append(self.run_testcase(t))
        
        return result

    def _body(self) -> dict[str, Any]:
        """Return a deep copy of the standard request body."""
        return copy.deepcopy(self.standard_request_body)

    def _post(self, body: dict[str, Any]) -> tuple[int, Any]:
        """POST to the collection endpoint; return (status_code, json|text)."""
        self._last_method = "POST"
        self._last_url = self.api
        resp = requests.post(self.api, json=body, timeout=10)
        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, resp.text

    def _get(self, id: str) -> tuple[int, Any]:
        """GET a single object by id; return (status_code, json|text)."""
        url = f"{self.api}/{id}"
        self._last_method = "GET"
        self._last_url = url
        resp = requests.get(url, timeout=10)
        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, resp.text

    def _check(
        self,
        testcase_id: str,
        expected_status: int,
        request_body: Any,
        actual_status: int,
        response_body: Any,
        acceptable: tuple[int, ...] | None = None,
    ) -> TestResult:
        """Build a TestResult by comparing expected vs actual HTTP status.

        `acceptable`, when given, is an additional set of status codes that
        also count as a pass (e.g. some frameworks return 422 instead of 400
        for request-body validation errors) - the reported expected_status
        stays as `expected_status` either way.
        """
        passed = actual_status == expected_status or (
            acceptable is not None and actual_status in acceptable
        )

        return TestResult(
            result=passed,
            testcase_id=testcase_id,
            method=getattr(self, "_last_method", ""),
            url=getattr(self, "_last_url", ""),
            expected_status=expected_status,
            actual_status=actual_status,
            request_body=request_body,
            response_body=response_body,
        )

    @abstractmethod
    def run_testcase(
        self,
        testcase_id: str
    ) -> TestResult:
        """Match-case to run corresponding test function with testcase_id"""
        ...