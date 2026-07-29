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
    IReportWriter,
)

@dataclass
class PipelineComponents:
    generation_agent:        IGenerationAgent
    compilability_validator: ICompilabilityValidator
    functional_validator:    IFunctionalValidator
    report_writer:           IReportWriter
    config:                  dict

def _build_generation_agent(cfg: dict) -> IGenerationAgent:
    agent_type = cfg.get("agent", {}).get("type", "chatdev")

    if agent_type == "chatdev":
        from agents.gen import ChatDevGenerationAgent
        return ChatDevGenerationAgent(config=cfg)

    raise ValueError(f"Unknown agent type: {agent_type}")

def build(config_path: str) -> PipelineComponents:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    from repairers.report_writer  import TextReportWriter
    from validators.CompilabilityValidator import CompilabilityValidator
    from validators.FunctionalValidator    import FunctionalValidator
    endpoints = cfg.get("validation", {}).get("http", {}).get("endpoints")

    return PipelineComponents(
        generation_agent        = _build_generation_agent(cfg),
        compilability_validator = CompilabilityValidator(config=cfg),
        functional_validator    = FunctionalValidator(endpoints=endpoints, config=cfg),
        report_writer           = TextReportWriter(
            report_dir=cfg.get("output", {}).get("report_dir", "reports/")
        ),
        config=cfg,
    )