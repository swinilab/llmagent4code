"""
pipeline_factory.py
────────────────────
Reads pipeline_config.yaml and returns concrete instances bound to the
interfaces declared in interfaces/base.py.
"""

from __future__ import annotations
from dataclasses import dataclass
import yaml
from interfaces.base import (
    ICompilabilityValidator,
    IFunctionalValidator,
    IGenerationAgent,
    IRepairAgent,
    IReportWriter,
)

@dataclass
class PipelineComponents:
    generation_agent:        IGenerationAgent
    compilability_validator: ICompilabilityValidator
    functional_validator:    IFunctionalValidator
    repair_agent:            IRepairAgent
    report_writer:           IReportWriter
    config:                  dict

def _build_generation_agent(cfg: dict, scenario: str) -> IGenerationAgent:
    agent_type = cfg.get("agent", {}).get("type", "mock")

    if agent_type == "chatdev":
        from agents.gen import ChatDevGenerationAgent
        return ChatDevGenerationAgent(config=cfg)

    if agent_type == "mock":
        from agents.mock_generation_agent import MockGenerationAgent
        return MockGenerationAgent(scenario=scenario)

    raise ValueError(f"Unknown agent type: {agent_type}")

def _build_repair_agent(cfg: dict, scenario: str) -> IRepairAgent:
    agent_type = cfg.get("repair", {}).get("type", "mock")

    if agent_type == "mini":
        from agents.repair import MiniRepairAgent
        return MiniRepairAgent(config=cfg)

    if agent_type == "mock":
        from agents.mock_generation_agent import MockGenerationAgent
        return MockGenerationAgent(scenario=scenario)

    raise ValueError(f"Unknown agent type: {agent_type}")

def build(config_path: str, scenario: str = "default") -> PipelineComponents:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    from agents.mock_repair_agent      import MockRepairAgent
    from repairers.report_writer       import TextReportWriter
    from validators.validators    import CompilabilityValidator, FunctionalValidator
    endpoints = cfg.get("validation", {}).get("http", {}).get("endpoints")

    return PipelineComponents(
        generation_agent        = _build_generation_agent(cfg, scenario),
        compilability_validator = CompilabilityValidator(),
        functional_validator    = FunctionalValidator(endpoints=endpoints),
        repair_agent            = _build_repair_agent(cfg, scenario),
        report_writer           = TextReportWriter(
            report_dir=cfg.get("output", {}).get("report_dir", "reports/")
        ),
        config=cfg,
    )