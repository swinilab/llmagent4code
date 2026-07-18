"""
agents/mock_generation_agent.py
────────────────────────────────
Mock LLM agent — returns pre-baked code so the pipeline can be exercised
without a real API key.

To plug in a real model: implement IGenerationAgent in a sibling file,
update pipeline_config.yaml → agent.model, and swap the import
inside pipeline_factory.py.
"""

from __future__ import annotations

from interfaces.base import GenerationResult, IGenerationAgent
from mock_data.scenarios import MOCK_SCENARIOS


class MockGenerationAgent(IGenerationAgent):
    def __init__(self, scenario: str = "default") -> None:
        self._scenario = scenario

    def generate(self, prompt: str) -> GenerationResult:
        scenario = MOCK_SCENARIOS.get(self._scenario, MOCK_SCENARIOS["default"])
        return GenerationResult(
            code=scenario["code"],
            prompt=prompt,
            meta={"scenario": self._scenario, "mock": True},
        )