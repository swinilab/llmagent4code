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

@dataclass
class TestResult:
    """Functional test result."""
    result:             bool
    testcase_id:        str
    message:            str


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
        resp = requests.post(self.api, json=body, timeout=10)
        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, resp.text

    def _get(self, id: str) -> tuple[int, Any]:
        """GET a single object by id; return (status_code, json|text)."""
        url = f"{self.api}/{id}"
        resp = requests.get(url, timeout=10)
        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, resp.text

    @staticmethod
    def _check(
        testcase_id: str,
        expected_status: int,
        actual_status: int,
        body: Any,
    ) -> TestResult:
        """Build a TestResult by comparing expected vs actual HTTP status."""
        passed = actual_status == expected_status
        msg = (
            f"Expected {expected_status}, got {actual_status}. Body: {body}"
            if not passed
            else "OK"
        )
        return TestResult(result=passed, testcase_id=testcase_id, message=msg)

    @abstractmethod
    def run_testcase(
        self,
        testcase_id: str
    ) -> TestResult:
        """Match-case to run corresponding test function with testcase_id"""
        ...