"""
interfaces/base.py
──────────────────
Abstract contracts for every pipeline component.

main.py only imports these types; concrete behaviour lives in the
subclasses under agents/, validators/, repairers/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


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
    model: str
    prompt: str
    output_dir: str

@dataclass
class RepairResult:
    """Returned after one repair iteration."""
    iteration:          int
    repaired_code:      str
    validation_results: list[ValidationResult]
    all_passed:         bool


# ─────────────────────────────────────────────────────────────────────────────
#  Abstract interfaces
# ─────────────────────────────────────────────────────────────────────────────

class IGenerationAgent(ABC):
    """Calls an LLM (or mock) and returns generated code."""

    @abstractmethod
    def generate(self, prompt: str) -> GenerationResult:
        ...


class ICompilabilityValidator(ABC):
    """Stage 1 – checks whether the code compiles/runs inside Docker."""

    @abstractmethod
    def validate(self, code: str) -> ValidationResult:
        ...


class IFunctionalValidator(ABC):
    """Stage 2 – fires HTTP requests and checks expected responses."""

    @abstractmethod
    def validate(self, code: str) -> ValidationResult:
        ...


class IRepairAgent(ABC):
    """
    Given the current code and a failing ValidationResult, produces a
    repaired version of the code.
    """

    @abstractmethod
    def repair(
        self,
        code:              str,
        validation_result: ValidationResult,
        iteration:         int,
    ) -> str:
        ...


class IReportWriter(ABC):
    """Serialises the final pipeline outcome to report.txt."""

    @abstractmethod
    def write(
        self,
        generation:         GenerationResult,
        validation_results: list[ValidationResult],
        repair_history:     list[RepairResult],
        all_passed:         bool,
    ) -> str:                           # returns the path written
        ...