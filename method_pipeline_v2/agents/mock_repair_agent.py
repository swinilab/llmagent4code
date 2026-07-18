"""
agents/mock_repair_agent.py
────────────────────────────
Mock repair agent — applies hard-coded "fixes" per scenario so the repair
loop can be exercised without a real LLM call.

In production, swap this for a real LLM call that receives:
  - the broken code
  - the error message from the failing ValidationResult
  - iteration number (for prompt chaining / history)
"""

from __future__ import annotations

from interfaces.base import IRepairAgent, ValidationResult
from mock_data.scenarios import MOCK_SCENARIOS


class MockRepairAgent(IRepairAgent):
    def __init__(self, scenario: str = "default") -> None:
        self._scenario = scenario

    def repair(
        self,
        code: str,
        validation_result: ValidationResult,
        iteration: int,
    ) -> str:
        scenario = MOCK_SCENARIOS.get(self._scenario, MOCK_SCENARIOS["default"])
        repairs: list[str] = scenario.get("repairs", [])

        if iteration <= len(repairs):
            return repairs[iteration - 1]

        return code